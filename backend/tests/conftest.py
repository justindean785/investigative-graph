"""
Shared test configuration and fixtures for backend integration tests.

Starts a real MongoDB in Docker (testcontainers) and the FastAPI app once per
pytest session. No local mongod binary is required — only Docker.

If REACT_APP_BACKEND_URL is already set (e.g. you started the API manually),
all auto-start logic is skipped.
"""
import os
import subprocess
import sys
import tempfile
import time
import socket

import requests

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8001
BASE_URL = f"http://localhost:{SERVER_PORT}"
TEST_DB_NAME = "trace_analyst_test"
_TMP = tempfile.gettempdir()

_mongo_container = None
_server_proc = None
_env_created = False


def _wait_for_port(host, port, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _wait_for_http(url, timeout=30, headers=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(url, headers=headers or {}, timeout=3)
            if resp.status_code == 200:
                return True
        except requests.ConnectionError:
            time.sleep(0.5)
    return False


def _ensure_emergent_stub():
    """Install a lightweight stub for the private emergentintegrations package."""
    try:
        from emergentintegrations.llm.chat import LlmChat
        chat = LlmChat()
        if hasattr(chat, "with_model"):
            return
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


def pytest_configure(config):
    """Session setup: MongoDB (testcontainers) + uvicorn + REACT_APP_BACKEND_URL."""
    global _mongo_container, _server_proc, _env_created

    if os.environ.get("REACT_APP_BACKEND_URL", "").strip():
        return

    _ensure_emergent_stub()

    try:
        from testcontainers.mongodb import MongoDbContainer
    except ImportError as e:
        raise RuntimeError(
            "testcontainers[mongodb] is required to run integration tests. "
            "Install dependencies (pip install -r backend/requirements.txt) "
            "and ensure Docker is running."
        ) from e

    _mongo_container = MongoDbContainer("mongo:7")
    try:
        _mongo_container.start()
    except Exception as e:
        _mongo_container = None
        raise RuntimeError(
            "Could not start MongoDB via testcontainers. "
            "Is Docker running? (Docker Desktop / dockerd required.)"
        ) from e

    mongo_url = _mongo_container.get_connection_url()

    env_path = os.path.join(BACKEND_DIR, ".env")
    if not os.path.exists(env_path):
        _env_created = True
        with open(env_path, "w") as f:
            f.write(f"MONGO_URL={mongo_url}\n")
            f.write(f"DB_NAME={TEST_DB_NAME}\n")

    if not _wait_for_port("127.0.0.1", SERVER_PORT, timeout=1):
        server_env = os.environ.copy()
        server_env["MONGO_URL"] = mongo_url
        server_env["DB_NAME"] = TEST_DB_NAME

        _server_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "server:app",
                "--host",
                SERVER_HOST,
                "--port",
                str(SERVER_PORT),
            ],
            cwd=BACKEND_DIR,
            env=server_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        api_key = os.environ.get("API_KEY", "trace-analyst-secret-2026")
        if not _wait_for_http(
            f"{BASE_URL}/api/",
            timeout=45,
            headers={"x-api-key": api_key},
        ):
            if _server_proc.poll() is None:
                _server_proc.terminate()
            out = ""
            if _server_proc.stdout:
                out = _server_proc.stdout.read().decode(errors="replace")
            if _mongo_container is not None:
                try:
                    _mongo_container.stop()
                except Exception:
                    pass
                _mongo_container = None
            raise RuntimeError(
                f"Backend server failed to start on port {SERVER_PORT}.\n"
                f"Server output:\n{out}"
            )

    os.environ["REACT_APP_BACKEND_URL"] = BASE_URL


def pytest_unconfigure(config):
    global _mongo_container, _server_proc, _env_created

    if _server_proc and _server_proc.poll() is None:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()

    if _mongo_container is not None:
        try:
            _mongo_container.stop()
        except Exception:
            pass
        _mongo_container = None

    if _env_created:
        env_path = os.path.join(BACKEND_DIR, ".env")
        if os.path.exists(env_path):
            os.remove(env_path)
