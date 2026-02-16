import os
import json
from contextlib import redirect_stdout
from .prestartup_script import on_custom_nodes_loaded
from .config import load_hooks, load_default_hooks, get_user_hooks_path

NAME = "ComfyUI Remove Print"

# Hook state management: {(node_name, method_name): original_method}
_hooked_methods = {}

# Reference to node class mappings (used for reloading)
_node_class_mappings = {}


def console_print(*args):
    for argv in args:
        print(f"[{NAME}]: " + argv)


def _apply_hooks(mappings: dict):
    """Apply hooks based on settings. Only enabled hooks are applied."""
    hooks = load_hooks()
    hook_dict = {hook["node"]: hook for hook in hooks}

    for key, value in mappings.items():
        hook = hook_dict.get(key)
        if hook is None:
            continue

        # Skip disabled hooks
        if not hook.get("enabled", True):
            console_print(f"""Skipped (disabled): {hook["node"]}.{hook["method"]}""")
            continue

        method_name = hook["method"]
        if not hasattr(value, method_name):
            console_print(f"""Method not found: {hook["node"]}.{method_name}""")
            continue

        hook_key = (key, method_name)

        # Skip if already hooked
        if hook_key in _hooked_methods:
            console_print(f"""Already hooked: {hook["node"]}.{method_name}""")
            continue

        original_method = getattr(value, method_name)
        _hooked_methods[hook_key] = original_method
        console_print(f"""Hook applied: {hook["node"]}.{method_name}""")

        def make_hooked_method(original):
            def hooked_method(*args, **kwargs):
                with redirect_stdout(open(os.devnull, 'w')):
                    return original(*args, **kwargs)
            return hooked_method

        setattr(value, method_name, make_hooked_method(original_method))


def _restore_hooks(mappings: dict):
    """Restore all applied hooks to their original methods."""
    for (node_name, method_name), original_method in list(_hooked_methods.items()):
        node_class = mappings.get(node_name)
        if node_class is not None:
            setattr(node_class, method_name, original_method)
            console_print(f"""Hook removed: {node_name}.{method_name}""")
    _hooked_methods.clear()


def reload_hooks():
    """Reload settings and re-apply hooks (for real-time updates)."""
    console_print("Reloading settings and re-applying hooks...")
    _restore_hooks(_node_class_mappings)
    _apply_hooks(_node_class_mappings)
    console_print("Hooks re-applied successfully.")


def on_load(mappings: dict):
    """Callback after custom nodes are loaded."""
    global _node_class_mappings
    _node_class_mappings = mappings
    _apply_hooks(mappings)


on_custom_nodes_loaded(on_load)


# === API Endpoints ===
try:
    from aiohttp import web
    from server import PromptServer

    if hasattr(PromptServer, "instance"):
        @PromptServer.instance.routes.get("/remove-print/default-hooks")
        async def get_default_hooks(request):
            """Return default hook settings"""
            hooks = load_default_hooks()
            return web.json_response({"hooks": hooks})

        @PromptServer.instance.routes.get("/remove-print/hooks")
        async def get_hooks(request):
            """Return current hook settings (User settings or default)"""
            hooks = load_hooks()
            return web.json_response({"hooks": hooks})

        @PromptServer.instance.routes.post("/remove-print/hooks")
        async def save_hooks(request):
            """Save user settings and re-apply hooks"""
            try:
                body = await request.read()
                data = json.loads(body)
                hooks = data.get("hooks", [])

                # Save to user settings file
                user_path = get_user_hooks_path()
                os.makedirs(os.path.dirname(user_path), exist_ok=True)
                with open(user_path, "w", encoding="utf-8") as f:
                    json.dump({"hooks": hooks}, f, indent=2, ensure_ascii=False)

                # Re-apply hooks
                reload_hooks()

                return web.json_response({
                    "status": "ok",
                    "hooks": load_hooks(),
                    "hooked": list(_hooked_methods.keys())
                })
            except Exception as e:
                return web.json_response({"status": "error", "message": str(e)}, status=500)

        @PromptServer.instance.routes.delete("/remove-print/hooks")
        async def delete_hooks(request):
            """Delete user settings, restore defaults, and re-apply hooks"""
            user_path = get_user_hooks_path()
            if os.path.exists(user_path):
                os.remove(user_path)

            # Re-apply hooks
            reload_hooks()

            return web.json_response({
                "status": "ok",
                "hooks": load_hooks(),
                "hooked": list(_hooked_methods.keys())
            })

        @PromptServer.instance.routes.get("/remove-print/locales/{lang}")
        async def get_locales(request):
            """Return main.json for the specified language"""
            lang = request.match_info.get("lang", "en")
            # Security check: only allow 'en', 'ja' etc.
            if not lang.isalnum() and "-" not in lang:
                return web.json_response({"error": "Invalid language code"}, status=400)

            node_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(node_dir, "locales", lang, "main.json")

            if not os.path.exists(path):
                # Fallback to English
                path = os.path.join(node_dir, "locales", "en", "main.json")

            if not os.path.exists(path):
                return web.json_response({}, status=404)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return web.json_response(data)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.get("/remove-print/nodes")
        async def get_nodes(request):
            """Return list of registered nodes"""
            nodes = sorted(_node_class_mappings.keys())
            return web.json_response({"nodes": nodes})

        @PromptServer.instance.routes.get("/remove-print/methods/{node_name}")
        async def get_methods(request):
            """Return list of methods for specified node (Reflection)"""
            node_name = request.match_info.get("node_name", "")
            node_class = _node_class_mappings.get(node_name)
            if node_class is None:
                return web.json_response({"methods": []}, status=404)

            import inspect
            methods = []
            for name, method in inspect.getmembers(node_class, predicate=inspect.isfunction):
                # Exclude dunder methods
                if not name.startswith("_"):
                    methods.append(name)
            methods.sort()
            return web.json_response({"methods": methods})

except ImportError:
    console_print("PromptServer not available, API endpoints disabled.")


# === WebUI Extension ===
WEB_DIRECTORY = "./js"

NODE_CLASS_MAPPINGS = {}
