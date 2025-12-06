import os
from contextlib import redirect_stdout
from .prestartup_script import on_custom_nodes_loaded

NAME = "ComfyUI Remove Print"

hooks = [
    {
        "node": "DPRandomGenerator",
        "method": "get_prompt"
    }
]

hook_dict = {}
for hook in hooks:
    hook_dict[hook["node"]] = hook


def on_load(mappings: dict):
    for key, value in mappings.items():
        hook = hook_dict.get(key)
        if hook is None:
            continue

        if not hasattr(value, hook["method"]):
            continue

        original_method = getattr(value, hook["method"])

        def hooked_method(*args, **kwargs):
            with redirect_stdout(open(os.devnull, 'w')):
                retval = original_method(*args, **kwargs)

            return retval

        setattr(value, hook["method"], hooked_method)

        return


on_custom_nodes_loaded(on_load)

NODE_CLASS_MAPPINGS = {}
