"""Handle the lobby websocket endpoint and player input messages.

Edit this file when websocket join rules, message types, or connection flow changes.
Copy the route pattern here when you add another websocket endpoint.
"""

from __future__ import annotations

import json

from aiohttp import WSMsgType, web

from backend.http.json_api import AppError
from backend.http.middleware import require_allowed_origin


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    require_allowed_origin(request)
    lobby_id = request.query.get("lobby_id", "").strip()
    player_token = request.query.get("player_token", "").strip()
    if not lobby_id or not player_token:
        raise web.HTTPBadRequest(reason="Lobby id and player token are required.")

    try:
        first_snapshot = await request.app["game_state"].snapshot_for_token(lobby_id, player_token)
    except AppError as error:
        raise web.HTTPUnauthorized(reason=error.message) from error

    ws = web.WebSocketResponse(heartbeat=30.0)
    await ws.prepare(request)

    hub = request.app["ws_hub"]
    hub.add(lobby_id, ws)
    await ws.send_json({"type": "ws.ready", "lobby_id": lobby_id, "connections": hub.count_for_lobby(lobby_id)})
    await ws.send_json(first_snapshot)

    try:
        async for message in ws:
            if message.type != WSMsgType.TEXT:
                continue
            try:
                data = json.loads(message.data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "code": "bad_request", "message": "WebSocket message must be valid JSON."})
                continue
            if not isinstance(data, dict):
                await ws.send_json({"type": "error", "code": "bad_request", "message": "WebSocket message must be an object."})
                continue
            message_type = data.get("type")
            if message_type == "ping":
                await ws.send_json({"type": "pong"})
            elif message_type == "player.input":
                snapshot = await request.app["game_state"].set_input(lobby_id, player_token, data)
                await hub.broadcast_lobby(lobby_id, snapshot)
    finally:
        hub.remove(lobby_id, ws)

    return ws


def setup_ws_routes(app: web.Application) -> None:
    app.router.add_get("/ws", websocket_handler)
