import os
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# --- ComfyUI モックセクション ---
mock_folder_paths = MagicMock()
sys.modules["folder_paths"] = mock_folder_paths

# ノードルートをパスに追加
node_dir = str(Path(__file__).parent.parent)
if node_dir not in sys.path:
    sys.path.insert(0, node_dir)

from config import load_hooks, get_user_hooks_path

@pytest.fixture
def standalone_mock_folder_paths(monkeypatch, tmp_path):
    user_dir = tmp_path / "comfyui_user"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "default").mkdir(parents=True, exist_ok=True)
    mock_folder_paths.get_user_directory.return_value = str(user_dir)
    return user_dir

def test_load_default_hooks(standalone_mock_folder_paths):
    hooks = load_hooks()
    assert isinstance(hooks, list)
    assert len(hooks) > 0

def test_load_user_hooks(standalone_mock_folder_paths):
    user_path = get_user_hooks_path()
    os.makedirs(os.path.dirname(user_path), exist_ok=True)
    test_hooks = [{"node": "TestNode", "method": "test_method"}]
    with open(user_path, "w", encoding="utf-8") as f:
        json.dump({"hooks": test_hooks}, f)
    hooks = load_hooks()
    assert hooks == test_hooks

def test_load_corrupted_user_hooks_fallback(standalone_mock_folder_paths):
    user_path = get_user_hooks_path()
    os.makedirs(os.path.dirname(user_path), exist_ok=True)
    with open(user_path, "w", encoding="utf-8") as f:
        f.write("{ invalid json }")
    hooks = load_hooks()
    assert isinstance(hooks, list)
    assert len(hooks) > 0

if __name__ == "__main__":
    # pytestをプログラムから直接実行
    sys.exit(pytest.main([__file__, "-v", "-p", "no:pytest_cov"]))
