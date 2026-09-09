"""resuMe native messaging host.

Chrome launches this executable when the extension calls
chrome.runtime.sendNativeMessage('com.resume.host', ...).
It ensures the local FastAPI backend is running on the configured port,
spawning it detached if necessary, and replies with a status JSON.

Protocol: 4-byte little-endian length prefix + UTF-8 JSON on stdin/stdout.
Never write anything else to stdout.
"""
from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
else:
    HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "resume-host.json"


def read_message() -> dict:
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) < 4:
        return {}
    (length,) = struct.unpack("<I", raw_len)
    data = sys.stdin.buffer.read(length)
    try:
        return json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def write_message(payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)) + data)
    sys.stdout.buffer.flush()


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def ensure_backend(cfg: dict) -> dict:
    port = int(cfg.get("port", 8322))
    if port_open(port):
        return {"running": True, "spawned": False}

    python = cfg.get("python")
    backend_dir = cfg.get("backend_dir")
    if not python or not backend_dir or not Path(python).exists() or not Path(backend_dir).exists():
        return {"running": False, "error": "Host nao configurado. Execute install-host.ps1."}

    log_path = Path(cfg.get("log") or (Path(backend_dir) / "data" / "resume-backend.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["RESUME_PORT"] = str(port)
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    with open(log_path, "a", encoding="utf-8") as log:
        subprocess.Popen(
            [python, "run.py"],
            cwd=backend_dir,
            creationflags=flags,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            env=env,
        )

    deadline = time.time() + float(cfg.get("startup_timeout", 12))
    while time.time() < deadline:
        if port_open(port):
            return {"running": True, "spawned": True}
        time.sleep(0.4)

    return {"running": False, "spawned": True, "error": "Backend nao respondeu dentro do prazo."}


def main() -> None:
    msg = read_message()
    if msg.get("action") != "ensure-backend":
        write_message({"running": False, "error": "Acao desconhecida."})
        return
    try:
        write_message(ensure_backend(load_config()))
    except Exception as exc:  # never crash silently: Chrome shows nothing
        write_message({"running": False, "error": str(exc)})


if __name__ == "__main__":
    main()
