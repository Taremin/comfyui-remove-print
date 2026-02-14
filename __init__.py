import os
from contextlib import redirect_stdout
from .prestartup_script import on_custom_nodes_loaded

NAME = "ComfyUI Remove Print"

hooks = [
    {"node": "DPRandomGenerator", "method": "get_prompt"},
    {"node": "DPJinja", "method": "get_prompt"}
]

hook_dict = {hook["node"]: hook for hook in hooks}


def console_print(*args):
    for argv in args:
        print(f"[{NAME}]: " + argv)


def on_load(mappings: dict):
    for key, value in mappings.items():
        hook = hook_dict.get(key)
        if hook is None:
            continue

        console_print(f"""Class: {hook["node"]} => {value}""")
        if not hasattr(value, hook["method"]):
            console_print(f"""function not found: {hook["method"]}""")
            continue

        original_method = getattr(value, hook["method"])
        console_print(f"replace function: {original_method}")

        def make_hooked_method(original):
            def hooked_method(*args, **kwargs):
                with redirect_stdout(open(os.devnull, 'w')):
                    return original(*args, **kwargs)
            return hooked_method

        setattr(value, hook["method"], make_hooked_method(original_method))

    return


on_custom_nodes_loaded(on_load)

NODE_CLASS_MAPPINGS = {}
