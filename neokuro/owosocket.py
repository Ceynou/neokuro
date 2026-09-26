import json
from pathlib import Path
from typing import TypedDict

import websocket


class OwocrResult(TypedDict):
    filename: str
    json_data: dict


class OwocrWebsocket:
    def __init__(self, port: int):
        try:
            self.websocket = websocket.WebSocket()
            self.websocket.connect(f"ws://127.0.0.1:{port}")
        except ConnectionRefusedError:
            raise ConnectionRefusedError(f"owocr server is not active on port {port}")

    def close(self):
        self.websocket.close()

    def process_image(self, path: Path) -> OwocrResult:
        self.websocket.send_binary(path.read_bytes())
        self.websocket.recv()
        response = self.websocket.recv()
        owocr_result = json.loads(response)
        return {"filename": path.name, "json_data": owocr_result}
