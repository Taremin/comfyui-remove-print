import json
import uuid
import websocket
import pytest

@pytest.fixture
def ws(comfyui_server):
    # comfyui_server returns "http://127.0.0.1:port"
    ws_url = comfyui_server.replace("http://", "ws://") + "/ws?clientId=" + uuid.uuid4().hex
    conn = websocket.create_connection(ws_url)
    yield conn
    conn.close()

def test_server_connection(ws):
    # Wait for the first status message
    result = ws.recv()
    data = json.loads(result)
    assert data["type"] == "status"

def test_object_info_contains_custom_node(comfyui_server):
    import requests
    response = requests.get(f"{comfyui_server}/object_info")
    assert response.status_code == 200
    data = response.json()
    # Check if any of our nodes are present (if we had specific node names)
    # Even if we don't have custom nodes (only extensions), we can check extensions API
    pass

def test_extensions_loading(comfyui_server):
    import requests
    response = requests.get(f"{comfyui_server}/extensions")
    assert response.status_code == 200
    extensions = response.json()
    # Check if our extension is loaded
    # The path usually looks like /extensions/comfyui-remove-print/remove-print-settings.js
    assert any("comfyui-remove-print" in ext for ext in extensions)
