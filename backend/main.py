"""Build and run the backend aiohttp application.

Edit this file when startup, cleanup, or top-level route setup changes.
Do not copy this file. Change it when the whole backend app boot flow changes.
"""

from __future__ import annotations

import asyncio
from time import monotonic

from aiohttp import web

from backend.config import Settings, load_settings, validate_settings
from backend.db.connection import open_db
from backend.db.migrations import run_migrations
from backend.game.state import GameState
from backend.http.middleware import cors_middleware, error_middleware
from backend.http.routes import setup_api_routes
from backend.ws.hub import WebSocketHub
from backend.ws.routes import setup_ws_routes


async def on_startup(app: web.Application) -> None:
    settings: Settings = app["settings"]
    run_migrations(settings.db_path, settings.migrations_path)
    app["db"] = await open_db(settings.db_path)
    app["game_tick_task"] = asyncio.create_task(tick_games(app))


async def on_cleanup(app: web.Application) -> None:
    tick_task = app.get("game_tick_task")
    if tick_task is not None:
        tick_task.cancel()
        try:
            await tick_task
        except asyncio.CancelledError:
            pass
    db = app.get("db")
    if db is not None:
        await db.close()


async def tick_games(app: web.Application) -> None:
    last_time = monotonic()
    while True:
        await asyncio.sleep(1 / 30)
        now = monotonic()
        snapshots = await app["game_state"].tick(now - last_time)
        last_time = now
        for snapshot in snapshots:
            lobby = snapshot["lobby"]
            if isinstance(lobby, dict):
                await app["ws_hub"].broadcast_lobby(str(lobby["id"]), snapshot)


def create_app(settings: Settings | None = None) -> web.Application:
    app = web.Application(middlewares=[error_middleware, cors_middleware])
    resolved_settings = settings or load_settings()
    validate_settings(resolved_settings)
    app["settings"] = resolved_settings
    app["ws_hub"] = WebSocketHub()
    app["game_state"] = GameState()

    setup_api_routes(app)
    setup_ws_routes(app)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


def run() -> None:
    settings = load_settings()
    web.run_app(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
