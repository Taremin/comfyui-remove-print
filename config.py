import os
import json
import folder_paths


# Custom node directory path
_node_dir = os.path.dirname(os.path.abspath(__file__))

# Default settings file path
_default_hooks_path = os.path.join(_node_dir, "default_hooks.json")

# Relative path for user settings in userdata directory
_user_hooks_relative = os.path.join("comfyui-remove-print", "hooks.json")


def get_user_hooks_path():
    """Return the absolute path to the user settings file"""
    user_dir = folder_paths.get_user_directory()
    return os.path.join(user_dir, "default", _user_hooks_relative)


def load_default_hooks():
    """Load the default settings file"""
    try:
        with open(_default_hooks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("hooks", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[comfyui-remove-print]: Failed to load default hooks: {e}")
        return []


def load_hooks():
    """Load user settings if they exist, otherwise load default settings"""
    user_path = get_user_hooks_path()

    if os.path.exists(user_path):
        try:
            with open(user_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("hooks", [])
        except (json.JSONDecodeError, OSError) as e:
            print(f"[comfyui-remove-print]: Failed to load user hooks, falling back to defaults: {e}")

    return load_default_hooks()
