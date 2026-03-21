"""Install emergentintegrations stub for local dev when the real package is unavailable."""
import os
import sys
import subprocess
import tempfile

_TMP = tempfile.gettempdir()
stub_dir = os.path.join(_TMP, "emergentintegrations_stub")
os.makedirs(os.path.join(stub_dir, "emergentintegrations", "llm"), exist_ok=True)

with open(os.path.join(stub_dir, "setup.py"), "w") as f:
    f.write(
        "from setuptools import setup, find_packages\n"
        "setup(name='emergentintegrations', version='0.1.0', packages=find_packages())\n"
    )
with open(os.path.join(stub_dir, "emergentintegrations", "__init__.py"), "w") as f:
    f.write("")
with open(os.path.join(stub_dir, "emergentintegrations", "llm", "__init__.py"), "w") as f:
    f.write("")
with open(os.path.join(stub_dir, "emergentintegrations", "llm", "chat.py"), "w") as f:
    f.write(
        "class UserMessage:\n"
        "    def __init__(self, text=''):\n"
        "        self.text = text\n"
        "\n"
        "class LlmChat:\n"
        "    def __init__(self, **kwargs):\n"
        "        self.api_key = kwargs.get('api_key', '')\n"
        "        self.model = kwargs.get('model', '')\n"
        "        self.session_id = kwargs.get('session_id', '')\n"
        "        self.system_message = kwargs.get('system_message', '')\n"
        "\n"
        "    def with_model(self, provider='', model=''):\n"
        "        self.provider = provider\n"
        "        self.model = model\n"
        "        return self\n"
        "\n"
        "    async def send_message(self, message=None, history=None):\n"
        "        return ('This is a placeholder AI response. '\n"
        "                'The EMERGENT_LLM_KEY is not configured.')\n"
    )

subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", stub_dir, "-q"])
print("emergentintegrations stub installed")
