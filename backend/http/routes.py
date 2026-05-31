"""Handle health and lobby JSON endpoints.

Edit this file when app endpoints outside the websocket group change.
Copy the route pattern here when you add another small endpoint group.
"""

from __future__ import annotations

from aiohttp import web

from backend.http.json_api import AppError, ok, read_json
from backend.http.middleware import require_allowed_origin


async def health(request: web.Request) -> web.Response:
    return ok({"status": "ok"})


def _read_nickname(payload: dict[str, object]) -> str:
    nickname = str(payload.get("nickname", "")).strip()
    if not 2 <= len(nickname) <= 18:
        raise AppError(400, "bad_nickname", "Nickname must be 2 to 18 characters.")
    return nickname


def _read_lobby_id(payload: dict[str, object]) -> str:
    lobby_id = str(payload.get("lobby_id", "")).strip()
    if not lobby_id:
        raise AppError(400, "bad_lobby", "Lobby id is required.")
    return lobby_id


def _read_player_token(payload: dict[str, object]) -> str:
    player_token = str(payload.get("player_token", "")).strip()
    if not player_token:
        raise AppError(400, "bad_player_token", "Player token is required.")
    return player_token


def _read_lives(payload: dict[str, object]) -> int | str:
    lives = payload.get("lives")
    if lives == "infinite":
        return "infinite"
    if isinstance(lives, int) and 1 <= lives <= 7:
        return lives
    raise AppError(400, "bad_lives", "Lives must be 1 to 7 or infinite.")


async def lobbies_list(request: web.Request) -> web.Response:
    return ok({"lobbies": await request.app["game_state"].list_lobbies()})


async def lobbies_create(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    payload = await read_json(request)
    return ok(await request.app["game_state"].create_lobby(_read_nickname(payload)))


async def lobbies_join(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    payload = await read_json(request)
    data = await request.app["game_state"].join_lobby(_read_lobby_id(payload), _read_nickname(payload))
    await request.app["ws_hub"].broadcast_lobby(data["lobby"]["id"], {"type": "lobby.changed", "lobby": data["lobby"]})
    return ok(data)


async def lobbies_configure(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    payload = await read_json(request)
    data = await request.app["game_state"].configure_lobby(
        _read_lobby_id(payload),
        _read_player_token(payload),
        str(payload.get("daemon_id", "")).strip(),
        _read_lives(payload),
    )
    await request.app["ws_hub"].broadcast_lobby(data["lobby"]["id"], {"type": "lobby.changed", "lobby": data["lobby"]})
    return ok(data)


async def lobbies_start(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    payload = await read_json(request)
    data = await request.app["game_state"].start_lobby(_read_lobby_id(payload), _read_player_token(payload))
    await request.app["ws_hub"].broadcast_lobby(data["lobby"]["id"], data["game"])
    return ok(data)


async def lobbies_leave(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    payload = await read_json(request)
    data = await request.app["game_state"].leave_lobby(_read_lobby_id(payload), _read_player_token(payload))
    lobby = data.get("lobby")
    if isinstance(lobby, dict):
        await request.app["ws_hub"].broadcast_lobby(lobby["id"], {"type": "lobby.changed", "lobby": lobby})
    return ok(data)


def setup_api_routes(app: web.Application) -> None:
    app.router.add_get("/api/health", health)
    app.router.add_post("/api/lobbies/list", lobbies_list)
    app.router.add_post("/api/lobbies/create", lobbies_create)
    app.router.add_post("/api/lobbies/join", lobbies_join)
    app.router.add_post("/api/lobbies/configure", lobbies_configure)
    app.router.add_post("/api/lobbies/start", lobbies_start)
    app.router.add_post("/api/lobbies/leave", lobbies_leave)
