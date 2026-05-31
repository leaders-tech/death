"""Keep in-memory lobby and platformer game state.

Edit this file when lobby rules, arena physics, or game snapshots change.
Copy this file as a starting point only for another small in-memory realtime game.
"""

from __future__ import annotations

import asyncio
import secrets
import string
from dataclasses import dataclass, field
from time import monotonic
from typing import Literal

from backend.http.json_api import AppError

LivesSetting = int | Literal["infinite"]

ARENA_WIDTH = 1600
ARENA_HEIGHT = 900
PLAYER_WIDTH = 34
PLAYER_HEIGHT = 46
MOVE_SPEED = 330.0
JUMP_SPEED = 650.0
WALL_JUMP_X_SPEED = 430.0
WALL_JUMP_Y_SPEED = 620.0
GRAVITY = 1600.0
MAX_FALL_SPEED = 900.0

PLATFORMS = [
    {"x": 0, "y": 850, "width": 1600, "height": 50},
    {"x": 160, "y": 690, "width": 300, "height": 28},
    {"x": 560, "y": 590, "width": 340, "height": 28},
    {"x": 1020, "y": 700, "width": 360, "height": 28},
    {"x": 760, "y": 430, "width": 260, "height": 28},
]


@dataclass(slots=True)
class PlayerInput:
    left: bool = False
    right: bool = False
    jump_pressed: bool = False


@dataclass(slots=True)
class Player:
    id: str
    token: str
    nickname: str
    is_host: bool
    x: float = 120.0
    y: float = 760.0
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    wall_dir: int = 0
    input: PlayerInput = field(default_factory=PlayerInput)


@dataclass(slots=True)
class Lobby:
    id: str
    name: str
    players: dict[str, Player] = field(default_factory=dict)
    status: Literal["waiting", "playing"] = "waiting"
    daemon_id: str | None = None
    lives: LivesSetting = 3
    created_at: float = field(default_factory=monotonic)


def _public_player(player: Player) -> dict[str, object]:
    return {
        "id": player.id,
        "nickname": player.nickname,
        "is_host": player.is_host,
        "x": round(player.x, 2),
        "y": round(player.y, 2),
        "vx": round(player.vx, 2),
        "vy": round(player.vy, 2),
        "on_ground": player.on_ground,
        "wall_dir": player.wall_dir,
    }


def _public_lobby(lobby: Lobby) -> dict[str, object]:
    return {
        "id": lobby.id,
        "name": lobby.name,
        "status": lobby.status,
        "daemon_id": lobby.daemon_id,
        "lives": lobby.lives,
        "players": [_public_player(player) for player in lobby.players.values()],
    }


class GameState:
    def __init__(self) -> None:
        self._lobbies: dict[str, Lobby] = {}
        self._lock = asyncio.Lock()

    async def list_lobbies(self) -> list[dict[str, object]]:
        async with self._lock:
            lobbies = sorted(self._lobbies.values(), key=lambda lobby: lobby.created_at, reverse=True)
            return [_public_lobby(lobby) for lobby in lobbies]

    async def create_lobby(self, nickname: str) -> dict[str, object]:
        async with self._lock:
            lobby = Lobby(id=_short_id(), name=f"{nickname}'s lobby")
            player = _new_player(nickname, is_host=True)
            lobby.players[player.id] = player
            self._lobbies[lobby.id] = lobby
            return {"lobby": _public_lobby(lobby), "player_id": player.id, "player_token": player.token}

    async def join_lobby(self, lobby_id: str, nickname: str) -> dict[str, object]:
        async with self._lock:
            lobby = self._get_lobby(lobby_id)
            if lobby.status != "waiting":
                raise AppError(400, "game_started", "This lobby has already started.")
            player = _new_player(nickname, is_host=False)
            player.x += len(lobby.players) * 48
            lobby.players[player.id] = player
            return {"lobby": _public_lobby(lobby), "player_id": player.id, "player_token": player.token}

    async def configure_lobby(self, lobby_id: str, player_token: str, daemon_id: str, lives: LivesSetting) -> dict[str, object]:
        async with self._lock:
            lobby, player = self._get_lobby_and_player(lobby_id, player_token)
            if not player.is_host:
                raise AppError(403, "host_required", "Only the host can configure the lobby.")
            if daemon_id not in lobby.players:
                raise AppError(400, "bad_daemon", "Choose a player in this lobby as daemon.")
            lobby.daemon_id = daemon_id
            lobby.lives = lives
            return {"lobby": _public_lobby(lobby)}

    async def start_lobby(self, lobby_id: str, player_token: str) -> dict[str, object]:
        async with self._lock:
            lobby, player = self._get_lobby_and_player(lobby_id, player_token)
            if not player.is_host:
                raise AppError(403, "host_required", "Only the host can start the game.")
            if lobby.daemon_id is None:
                raise AppError(400, "daemon_required", "Choose a daemon before starting.")
            lobby.status = "playing"
            _spawn_players(lobby)
            return {"lobby": _public_lobby(lobby), "game": self._snapshot_unlocked(lobby)}

    async def leave_lobby(self, lobby_id: str, player_token: str) -> dict[str, object]:
        async with self._lock:
            lobby, player = self._get_lobby_and_player(lobby_id, player_token)
            lobby.players.pop(player.id)
            if not lobby.players:
                self._lobbies.pop(lobby.id, None)
                return {"left": True}
            if player.is_host:
                next_host = next(iter(lobby.players.values()))
                next_host.is_host = True
            if lobby.daemon_id == player.id:
                lobby.daemon_id = None
            return {"left": True, "lobby": _public_lobby(lobby)}

    async def set_input(self, lobby_id: str, player_token: str, data: dict[str, object]) -> dict[str, object]:
        async with self._lock:
            lobby, player = self._get_lobby_and_player(lobby_id, player_token)
            if lobby.daemon_id == player.id:
                return self._snapshot_unlocked(lobby)
            player.input.left = data.get("left") is True
            player.input.right = data.get("right") is True
            player.input.jump_pressed = data.get("jump_pressed") is True
            return self._snapshot_unlocked(lobby)

    async def snapshot_for_token(self, lobby_id: str, player_token: str) -> dict[str, object]:
        async with self._lock:
            lobby, _ = self._get_lobby_and_player(lobby_id, player_token)
            return self._snapshot_unlocked(lobby)

    async def tick(self, dt: float) -> list[dict[str, object]]:
        async with self._lock:
            snapshots = []
            for lobby in self._lobbies.values():
                if lobby.status != "playing":
                    continue
                _tick_lobby(lobby, min(dt, 0.05))
                snapshots.append(self._snapshot_unlocked(lobby))
            return snapshots

    def _get_lobby(self, lobby_id: str) -> Lobby:
        lobby = self._lobbies.get(lobby_id)
        if lobby is None:
            raise AppError(404, "not_found", "Lobby does not exist.")
        return lobby

    def _get_lobby_and_player(self, lobby_id: str, player_token: str) -> tuple[Lobby, Player]:
        lobby = self._get_lobby(lobby_id)
        for player in lobby.players.values():
            if player.token == player_token:
                return lobby, player
        raise AppError(401, "bad_player_token", "Player token is invalid.")

    def _snapshot_unlocked(self, lobby: Lobby) -> dict[str, object]:
        return {
            "type": "game.snapshot",
            "lobby": _public_lobby(lobby),
            "arena": {
                "width": ARENA_WIDTH,
                "height": ARENA_HEIGHT,
                "platforms": PLATFORMS,
                "player_width": PLAYER_WIDTH,
                "player_height": PLAYER_HEIGHT,
            },
        }


def _new_player(nickname: str, is_host: bool) -> Player:
    return Player(id=secrets.token_urlsafe(8), token=secrets.token_urlsafe(24), nickname=nickname, is_host=is_host)


def _short_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(5))


def _spawn_players(lobby: Lobby) -> None:
    index = 0
    for player in lobby.players.values():
        if player.id == lobby.daemon_id:
            player.x = 64
            player.y = 64
            player.vx = 0
            player.vy = 0
            continue
        player.x = 120 + index * 58
        player.y = 760
        player.vx = 0
        player.vy = 0
        index += 1


def _tick_lobby(lobby: Lobby, dt: float) -> None:
    for player in lobby.players.values():
        if player.id == lobby.daemon_id:
            continue
        _tick_player(player, dt)


def _tick_player(player: Player, dt: float) -> None:
    move = 0
    if player.input.left:
        move -= 1
    if player.input.right:
        move += 1
    player.vx = move * MOVE_SPEED

    if player.input.jump_pressed:
        if player.on_ground:
            player.vy = -JUMP_SPEED
        elif player.wall_dir != 0:
            player.vx = -player.wall_dir * WALL_JUMP_X_SPEED
            player.vy = -WALL_JUMP_Y_SPEED
        player.input.jump_pressed = False

    player.vy = min(player.vy + GRAVITY * dt, MAX_FALL_SPEED)
    _move_x(player, dt)
    _move_y(player, dt)


def _move_x(player: Player, dt: float) -> None:
    player.x += player.vx * dt
    player.wall_dir = 0
    if player.x < 0:
        player.x = 0
        player.wall_dir = -1
    if player.x + PLAYER_WIDTH > ARENA_WIDTH:
        player.x = ARENA_WIDTH - PLAYER_WIDTH
        player.wall_dir = 1

    for platform in PLATFORMS:
        if not _overlaps(player, platform):
            continue
        if player.vx > 0:
            player.x = platform["x"] - PLAYER_WIDTH
            player.wall_dir = 1
        elif player.vx < 0:
            player.x = platform["x"] + platform["width"]
            player.wall_dir = -1
        player.vx = 0


def _move_y(player: Player, dt: float) -> None:
    player.y += player.vy * dt
    player.on_ground = False
    if player.y < 0:
        player.y = 0
        player.vy = 0
    if player.y + PLAYER_HEIGHT > ARENA_HEIGHT:
        player.y = ARENA_HEIGHT - PLAYER_HEIGHT
        player.vy = 0
        player.on_ground = True

    for platform in PLATFORMS:
        if not _overlaps(player, platform):
            continue
        if player.vy > 0:
            player.y = platform["y"] - PLAYER_HEIGHT
            player.vy = 0
            player.on_ground = True
        elif player.vy < 0:
            player.y = platform["y"] + platform["height"]
            player.vy = 0


def _overlaps(player: Player, rect: dict[str, int]) -> bool:
    return (
        player.x < rect["x"] + rect["width"]
        and player.x + PLAYER_WIDTH > rect["x"]
        and player.y < rect["y"] + rect["height"]
        and player.y + PLAYER_HEIGHT > rect["y"]
    )
