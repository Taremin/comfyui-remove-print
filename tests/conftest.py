import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# --- ComfyUI モックセクション ---
# 本体の巨大な依存関係を避けるため、インポート前にモックを注入する
mock_folder_paths = MagicMock()
sys.modules["folder_paths"] = mock_folder_paths
sys.modules["nodes"] = MagicMock()

import json
import subprocess
import time
import socket
import pytest

# Add ComfyUI to path
TESTS_DIR = Path(__file__).parent
SETTINGS_PATH = TESTS_DIR / "test_settings.json"

@pytest.fixture(scope="session")
def test_settings():
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def wait_for_port(port, host="127.0.0.1", timeout=120.0):
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (OSError, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                return False
            time.sleep(1)

@pytest.fixture(scope="session")
def comfyui_server(test_settings):
    # Resolve paths relative to TESTS_DIR if they are relative
    comfyui_path_raw = test_settings["comfyui_path"]
    python_exe_raw = test_settings["python_executable"]
    
    comfyui_path = (TESTS_DIR / comfyui_path_raw).resolve()
    python_exe = (TESTS_DIR / python_exe_raw).resolve()
    
    port = test_settings["test_port"]

    cmd = [str(python_exe), "main.py", "--port", str(port), "--listen", "127.0.0.1"]
    
    # Simple environment inheritance
    env = os.environ.copy()
    
    # Don't manually set PYTHONPATH, let the python interpreter handle it relative to cwd
    if "PYTHONPATH" in env:
        del env["PYTHONPATH"]
        
    env["PATH"] = os.environ.get("PATH", "")

    process = subprocess.Popen(
        cmd,
        cwd=comfyui_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        env=env
    )

    if not wait_for_port(port):
        process.terminate()
        stdout, _ = process.communicate()
        pytest.fail(f"ComfyUI server failed to start on port {port}. Output:\n{stdout}")

    yield f"http://127.0.0.1:{port}"

    # Shutdown server
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

@pytest.fixture(autouse=True)
def mock_folder_paths(monkeypatch, tmp_path):
    # Setup temporary directory for user settings
    user_dir = tmp_path / "comfyui_user"
    user_dir.mkdir()
    (user_dir / "default").mkdir()
    
    # Mock folder_paths.get_user_directory
    import folder_paths
    monkeypatch.setattr(folder_paths, "get_user_directory", lambda: str(user_dir))
    
    return user_dir
