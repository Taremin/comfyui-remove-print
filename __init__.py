import os
import json
from contextlib import redirect_stdout
from .prestartup_script import on_custom_nodes_loaded
from .config import load_hooks, load_default_hooks, get_user_hooks_path

NAME = "ComfyUI Remove Print"

# フックの状態管理: {(node_name, method_name): original_method}
_hooked_methods = {}

# ノードクラスマッピングへの参照を保持（reload時に使用）
_node_class_mappings = {}


def console_print(*args):
    for argv in args:
        print(f"[{NAME}]: " + argv)


def _apply_hooks(mappings: dict):
    """設定に基づいてフックを適用する。enabledなフックのみ適用。"""
    hooks = load_hooks()
    hook_dict = {hook["node"]: hook for hook in hooks}

    for key, value in mappings.items():
        hook = hook_dict.get(key)
        if hook is None:
            continue

        # 無効なフックはスキップ
        if not hook.get("enabled", True):
            console_print(f"""スキップ（無効）: {hook["node"]}.{hook["method"]}""")
            continue

        method_name = hook["method"]
        if not hasattr(value, method_name):
            console_print(f"""メソッドが見つかりません: {hook["node"]}.{method_name}""")
            continue

        hook_key = (key, method_name)

        # 既にフック済みならスキップ
        if hook_key in _hooked_methods:
            console_print(f"""既にフック済み: {hook["node"]}.{method_name}""")
            continue

        original_method = getattr(value, method_name)
        _hooked_methods[hook_key] = original_method
        console_print(f"""フック適用: {hook["node"]}.{method_name}""")

        def make_hooked_method(original):
            def hooked_method(*args, **kwargs):
                with redirect_stdout(open(os.devnull, 'w')):
                    return original(*args, **kwargs)
            return hooked_method

        setattr(value, method_name, make_hooked_method(original_method))


def _restore_hooks(mappings: dict):
    """適用済みのフックをすべて解除し、元のメソッドに戻す。"""
    for (node_name, method_name), original_method in list(_hooked_methods.items()):
        node_class = mappings.get(node_name)
        if node_class is not None:
            setattr(node_class, method_name, original_method)
            console_print(f"""フック解除: {node_name}.{method_name}""")
    _hooked_methods.clear()


def reload_hooks():
    """設定を再読み込みし、フックを再適用する（リアルタイム更新用）。"""
    console_print("設定を再読み込みしてフックを再適用します...")
    _restore_hooks(_node_class_mappings)
    _apply_hooks(_node_class_mappings)
    console_print("フックの再適用が完了しました。")


def on_load(mappings: dict):
    """カスタムノード読み込み完了後のコールバック。"""
    global _node_class_mappings
    _node_class_mappings = mappings
    _apply_hooks(mappings)


on_custom_nodes_loaded(on_load)


# === APIエンドポイント ===
try:
    from aiohttp import web
    from server import PromptServer

    if hasattr(PromptServer, "instance"):
        @PromptServer.instance.routes.get("/remove-print/default-hooks")
        async def get_default_hooks(request):
            """デフォルトのフック設定を返す"""
            hooks = load_default_hooks()
            return web.json_response({"hooks": hooks})

        @PromptServer.instance.routes.get("/remove-print/hooks")
        async def get_hooks(request):
            """現在のフック設定を返す（ユーザー設定 or デフォルト）"""
            hooks = load_hooks()
            return web.json_response({"hooks": hooks})

        @PromptServer.instance.routes.post("/remove-print/hooks")
        async def save_hooks(request):
            """ユーザー設定を保存してフックを再適用する"""
            try:
                body = await request.read()
                data = json.loads(body)
                hooks = data.get("hooks", [])

                # ユーザー設定ファイルに保存
                user_path = get_user_hooks_path()
                os.makedirs(os.path.dirname(user_path), exist_ok=True)
                with open(user_path, "w", encoding="utf-8") as f:
                    json.dump({"hooks": hooks}, f, indent=2, ensure_ascii=False)

                # フックを再適用
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
            """ユーザー設定を削除してデフォルトに戻し、フックを再適用する"""
            user_path = get_user_hooks_path()
            if os.path.exists(user_path):
                os.remove(user_path)

            # フックを再適用
            reload_hooks()

            return web.json_response({
                "status": "ok",
                "hooks": load_hooks(),
                "hooked": list(_hooked_methods.keys())
            })

        @PromptServer.instance.routes.get("/remove-print/nodes")
        async def get_nodes(request):
            """登録済みノードの一覧を返す"""
            nodes = sorted(_node_class_mappings.keys())
            return web.json_response({"nodes": nodes})

        @PromptServer.instance.routes.get("/remove-print/methods/{node_name}")
        async def get_methods(request):
            """指定ノードのメソッド一覧を返す（リフレクション）"""
            node_name = request.match_info.get("node_name", "")
            node_class = _node_class_mappings.get(node_name)
            if node_class is None:
                return web.json_response({"methods": []}, status=404)

            import inspect
            methods = []
            for name, method in inspect.getmembers(node_class, predicate=inspect.isfunction):
                # dunderメソッドを除外
                if not name.startswith("_"):
                    methods.append(name)
            methods.sort()
            return web.json_response({"methods": methods})

except ImportError:
    console_print("PromptServerが利用できないため、APIエンドポイントは無効です。")


# === WebUI拡張 ===
WEB_DIRECTORY = "./js"

NODE_CLASS_MAPPINGS = {}
