"""Track live websocket connections per lobby and send messages to them.

Edit this file when websocket connection storage or lobby fan-out behavior changes.
Copy the helper style here when you add another small websocket utility.
"""

from __future__ import annotations

from collections import defaultdict

from aiohttp import web


class WebSocketHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[web.WebSocketResponse]] = defaultdict(set)

    def add(self, lobby_id: str, ws: web.WebSocketResponse) -> None:
        self._connections[lobby_id].add(ws)

    def remove(self, lobby_id: str, ws: web.WebSocketResponse) -> None:
        sockets = self._connections.get(lobby_id)
        if sockets is None:
            return
        sockets.discard(ws)
        if len(sockets) == 0:
            self._connections.pop(lobby_id, None)

    async def broadcast_lobby(self, lobby_id: str, message: dict[str, object]) -> None:
        sockets = list(self._connections.get(lobby_id, ()))
        for ws in sockets:
            if ws.closed:
                self.remove(lobby_id, ws)
                continue
            await ws.send_json(message)

    def count_for_lobby(self, lobby_id: str) -> int:
        return len(self._connections.get(lobby_id, ()))
