import os
import json
import folder_paths


# カスタムノードのディレクトリパス
_node_dir = os.path.dirname(os.path.abspath(__file__))

# デフォルト設定ファイルのパス
_default_hooks_path = os.path.join(_node_dir, "default_hooks.json")

# ユーザー設定ファイルのuserdataディレクトリ内の相対パス
_user_hooks_relative = os.path.join("comfyui-remove-print", "hooks.json")


def get_user_hooks_path():
    """ユーザー設定ファイルの絶対パスを返す"""
    user_dir = folder_paths.get_user_directory()
    return os.path.join(user_dir, "default", _user_hooks_relative)


def load_default_hooks():
    """デフォルトの設定ファイルを読み込む"""
    try:
        with open(_default_hooks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("hooks", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[comfyui-remove-print]: デフォルト設定の読み込みに失敗: {e}")
        return []


def load_hooks():
    """ユーザー設定が存在すればそれを、なければデフォルト設定を読み込む"""
    user_path = get_user_hooks_path()

    if os.path.exists(user_path):
        try:
            with open(user_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("hooks", [])
        except (json.JSONDecodeError, OSError) as e:
            print(f"[comfyui-remove-print]: ユーザー設定の読み込みに失敗、デフォルトを使用: {e}")

    return load_default_hooks()
