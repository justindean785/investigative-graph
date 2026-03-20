"""
Shared test configuration and fixtures for backend integration tests.

This conftest.py automatically starts MongoDB and the FastAPI backend server
before running integration tests, and tears them down afterward.

Key design: We use pytest_configure() (runs before test collection) to set
REACT_APP_BACKEND_URL in the environment so that test modules pick up the
correct BASE_URL at import time.
"""
import pytest
import subprocess
import tempfile
import time
import os
import sys
import shutil
import socket

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8001
BASE_URL = f"http://localhost:{SERVER_PORT}"
MONGO_PORT = 27017
TEST_DB_NAME = "trace_analyst_test"
_TMP = tempfile.gettempdir()
MONGO_DATA_DIR = os.path.join(_TMP, "test_mongodb_data")
MONGO_LOG = os.path.join(_TMP, "test_mongodb.log")

# Track processes so we can clean up
_mongo_proc = None
_server_proc = None
_env_created = False


def _find_mongod():
    """Locate the mongod binary (system install, conda, or PATH)."""
    mongod = shutil.which("mongod")
    if mongod:
        return mongod
    # Check common conda/anaconda installation paths
    for candidate in [
        "/usr/share/miniconda/bin/mongod",
        os.path.expanduser("~/miniconda3/bin/mongod"),
        os.path.expanduser("~/anaconda3/bin/mongod"),
    ]:
        if os.path.isfile(candidate):
            return candidate
    return None


def _wait_for_port(host, port, timeout=30):
    """Block until *host:port* accepts a TCP connection."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _wait_for_http(url, timeout=30, headers=None):
    """Block until a GET to *url* returns HTTP 200."""
    import requests as _requests
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = _requests.get(url, headers=headers or {}, timeout=3)
            if resp.status_code == 200:
                return True
        except _requests.ConnectionError:
            time.sleep(0.5)
    return False


def _ensure_emergent_stub():
    """Install a lightweight stub for the private emergentintegrations package
    so that server.py can import it without errors."""
    try:
        from emergentintegrations.llm.chat import LlmChat
        chat = LlmChat()
        if hasattr(chat, 'with_model'):
            return  # already installed with correct API
    except (ImportError, TypeError):
        pass

    stub_dir = os.path.join(_TMP, "emergentintegrations_stub")
    os.makedirs(f"{stub_dir}/emergentintegrations/llm", exist_ok=True)

    with open(f"{stub_dir}/setup.py", "w") as f:
        f.write(
            "from setuptools import setup, find_packages\n"
            "setup(name='emergentintegrations', version='0.1.0', packages=find_packages())\n"
        )
    with open(f"{stub_dir}/emergentintegrations/__init__.py", "w") as f:
        f.write("")
    with open(f"{stub_dir}/emergentintegrations/llm/__init__.py", "w") as f:
        f.write("")
    with open(f"{stub_dir}/emergentintegrations/llm/chat.py", "w") as f:
        f.write(
            'class UserMessage:\n'
            '    def __init__(self, text=""):\n'
            '        self.text = text\n'
            '\n'
            'class LlmChat:\n'
            '    def __init__(self, **kwargs):\n'
            '        self.api_key = kwargs.get("api_key", "")\n'
            '        self.model = kwargs.get("model", "")\n'
            '        self.session_id = kwargs.get("session_id", "")\n'
            '        self.system_message = kwargs.get("system_message", "")\n'
            '\n'
            '    def with_model(self, provider="", model=""):\n'
            '        """Chain method - returns self for fluent API compatibility."""\n'
            '        self.provider = provider\n'
            '        self.model = model\n'
            '        return self\n'
            '\n'
            '    async def send_message(self, message=None, history=None):\n'
            '        return ("This is a placeholder AI response. "\n'
            '                "The EMERGENT_LLM_KEY is not configured.")\n'
        )

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", stub_dir, "-q"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------------------
# pytest_configure runs BEFORE test collection – ideal for setting env vars
# that test modules read at import time.
# ---------------------------------------------------------------------------
def pytest_configure(config):
    """Early hook: start MongoDB + backend, set REACT_APP_BACKEND_URL."""
    global _mongo_proc, _server_proc, _env_created

    # If URL is already set (e.g. user started server manually), skip setup
    existing_url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if existing_url:
        return

    # 1. Ensure emergent stub
    _ensure_emergent_stub()

    # 2. Start MongoDB
    mongod = _find_mongod()
    if mongod:
        os.makedirs(MONGO_DATA_DIR, exist_ok=True)
        if not _wait_for_port("127.0.0.1", MONGO_PORT, timeout=1):
            _mongo_proc = subprocess.Popen(
                [
                    mongod,
                    "--dbpath", MONGO_DATA_DIR,
                    "--logpath", MONGO_LOG,
                    "--bind_ip", "127.0.0.1",
                    "--port", str(MONGO_PORT),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not _wait_for_port("127.0.0.1", MONGO_PORT, timeout=30):
                raise RuntimeError("MongoDB failed to start")
    else:
        if not _wait_for_port("127.0.0.1", MONGO_PORT, timeout=2):
            raise RuntimeError(
                "mongod binary not found and MongoDB is not running on port 27017. "
                "Install MongoDB or start it before running tests."
            )

    # 3. Write .env if needed
    env_path = os.path.join(BACKEND_DIR, ".env")
    if not os.path.exists(env_path):
        _env_created = True
        with open(env_path, "w") as f:
            f.write("MONGO_URL=mongodb://localhost:27017\n")
            f.write(f"DB_NAME={TEST_DB_NAME}\n")

    # 4. Start FastAPI server
    if not _wait_for_port("127.0.0.1", SERVER_PORT, timeout=1):
        server_env = os.environ.copy()
        server_env["MONGO_URL"] = "mongodb://localhost:27017"
        server_env["DB_NAME"] = TEST_DB_NAME

        _server_proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "server:app",
                "--host", SERVER_HOST,
                "--port", str(SERVER_PORT),
            ],
            cwd=BACKEND_DIR,
            env=server_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        api_key = os.environ.get("API_KEY", "trace-analyst-secret-2026")
        if not _wait_for_http(
            f"{BASE_URL}/api/",
            timeout=30,
            headers={"x-api-key": api_key},
        ):
            if _server_proc.poll() is None:
                _server_proc.terminate()
            out = ""
            if _server_proc.stdout:
                out = _server_proc.stdout.read().decode(errors="replace")
            raise RuntimeError(
                f"Backend server failed to start on port {SERVER_PORT}.\n"
                f"Server output:\n{out}"
            )

    # 5. Set the env var so test modules pick it up at import time
    os.environ["REACT_APP_BACKEND_URL"] = BASE_URL


def pytest_unconfigure(config):
    """Teardown: stop server and MongoDB if we started them."""
    global _mongo_proc, _server_proc, _env_created

    if _server_proc and _server_proc.poll() is None:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()

    if _mongo_proc and _mongo_proc.poll() is None:
        _mongo_proc.terminate()
        try:
            _mongo_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _mongo_proc.kill()

    if _env_created:
        env_path = os.path.join(BACKEND_DIR, ".env")
        if os.path.exists(env_path):
            os.remove(env_path)
