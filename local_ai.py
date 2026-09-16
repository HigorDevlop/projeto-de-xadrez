"""Start the explicitly installed, loopback-only Ollama runtime for this app."""
import json
import os
from pathlib import Path
import subprocess
import threading
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get("ACERVO_AI_CONFIG", ROOT / ".streamlit/local_ai.json"))
_lock = threading.Lock()
_process = None


def configuration():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def default_model():
    return os.environ.get("ACERVO_AI_MODEL", configuration().get("model", ""))


def ensure_running():
    global _process
    try:
        with urlopen("http://127.0.0.1:11434/api/version", timeout=1):
            return True
    except OSError:
        pass
    config = configuration()
    executable = Path(config.get("executable", ""))
    if not executable.is_file():
        return False
    with _lock:
        if _process is None or _process.poll() is not None:
            env = dict(os.environ, OLLAMA_HOST="127.0.0.1:11434", OLLAMA_NUM_PARALLEL="1",
                       OLLAMA_MAX_LOADED_MODELS="1", OLLAMA_CONTEXT_LENGTH="4096")
            if config.get("models"):
                env["OLLAMA_MODELS"] = config["models"]
            log = executable.parent / "acervo-server.log"
            with log.open("ab") as output:
                _process = subprocess.Popen([str(executable), "serve"], env=env, stdin=subprocess.DEVNULL,
                                            stdout=output, stderr=output,
                                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    return True
