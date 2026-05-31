"""Test lobby routes, host rules, and websocket game snapshots.

Edit this file when lobby, websocket, or first-slice game behavior changes.
Copy a test pattern here when you add another realtime game rule.
"""

from __future__ import annotations

import pytest
from aiohttp import WSServerHandshakeError


async def create_lobby(client, headers: dict[str, str], nickname: str = "Host") -> dict[str, object]:
    response = await client.post("/api/lobbies/create", json={"nickname": nickname}, headers=headers)
    assert response.status == 200
    payload = await response.json()
    assert payload["ok"] is True
    return payload["data"]


async def join_lobby(client, headers: dict[str, str], lobby_id: str, nickname: str = "Player") -> dict[str, object]:
    response = await client.post("/api/lobbies/join", json={"lobby_id": lobby_id, "nickname": nickname}, headers=headers)
    assert response.status == 200
    payload = await response.json()
    assert payload["ok"] is True
    return payload["data"]


@pytest.mark.asyncio
async def test_lobby_create_join_list_and_configure(client, auth_headers) -> None:
    created = await create_lobby(client, auth_headers)
    lobby = created["lobby"]
    joined = await join_lobby(client, auth_headers, lobby["id"])

    list_response = await client.post("/api/lobbies/list", json={})
    assert list_response.status == 200
    list_payload = await list_response.json()
    assert len(list_payload["data"]["lobbies"]) == 1
    assert len(list_payload["data"]["lobbies"][0]["players"]) == 2

    configure_response = await client.post(
        "/api/lobbies/configure",
        json={"lobby_id": lobby["id"], "player_token": created["player_token"], "daemon_id": joined["player_id"], "lives": "infinite"},
        headers=auth_headers,
    )
    assert configure_response.status == 200
    configure_payload = await configure_response.json()
    assert configure_payload["data"]["lobby"]["daemon_id"] == joined["player_id"]
    assert configure_payload["data"]["lobby"]["lives"] == "infinite"


@pytest.mark.asyncio
async def test_only_host_can_configure_or_start(client, auth_headers) -> None:
    created = await create_lobby(client, auth_headers)
    lobby = created["lobby"]
    joined = await join_lobby(client, auth_headers, lobby["id"])

    response = await client.post(
        "/api/lobbies/configure",
        json={"lobby_id": lobby["id"], "player_token": joined["player_token"], "daemon_id": joined["player_id"], "lives": 3},
        headers=auth_headers,
    )
    assert response.status == 403

    start_response = await client.post("/api/lobbies/start", json={"lobby_id": lobby["id"], "player_token": joined["player_token"]}, headers=auth_headers)
    assert start_response.status == 403


@pytest.mark.asyncio
async def test_start_requires_daemon_and_accepts_good_setup(client, auth_headers) -> None:
    created = await create_lobby(client, auth_headers)
    lobby = created["lobby"]
    joined = await join_lobby(client, auth_headers, lobby["id"])

    missing_daemon = await client.post("/api/lobbies/start", json={"lobby_id": lobby["id"], "player_token": created["player_token"]}, headers=auth_headers)
    assert missing_daemon.status == 400

    await client.post(
        "/api/lobbies/configure",
        json={"lobby_id": lobby["id"], "player_token": created["player_token"], "daemon_id": joined["player_id"], "lives": 5},
        headers=auth_headers,
    )
    start_response = await client.post("/api/lobbies/start", json={"lobby_id": lobby["id"], "player_token": created["player_token"]}, headers=auth_headers)
    assert start_response.status == 200
    payload = await start_response.json()
    assert payload["data"]["lobby"]["status"] == "playing"
    assert payload["data"]["game"]["arena"]["width"] == 1600


@pytest.mark.asyncio
async def test_bad_player_token_is_rejected(client, auth_headers) -> None:
    created = await create_lobby(client, auth_headers)
    lobby = created["lobby"]

    response = await client.post(
        "/api/lobbies/configure",
        json={"lobby_id": lobby["id"], "player_token": "wrong", "daemon_id": created["player_id"], "lives": 3},
        headers=auth_headers,
    )
    assert response.status == 401


@pytest.mark.asyncio
async def test_websocket_requires_lobby_token_and_broadcasts_input(client, auth_headers) -> None:
    created = await create_lobby(client, auth_headers)
    lobby = created["lobby"]
    await client.post(
        "/api/lobbies/configure",
        json={"lobby_id": lobby["id"], "player_token": created["player_token"], "daemon_id": created["player_id"], "lives": 3},
        headers=auth_headers,
    )
    await client.post("/api/lobbies/start", json={"lobby_id": lobby["id"], "player_token": created["player_token"]}, headers=auth_headers)

    with pytest.raises(WSServerHandshakeError) as error:
        await client.ws_connect("/ws")
    assert error.value.status == 400

    ws = await client.ws_connect(f"/ws?lobby_id={lobby['id']}&player_token={created['player_token']}")
    ready = await ws.receive_json()
    assert ready["type"] == "ws.ready"
    first_snapshot = await ws.receive_json()
    assert first_snapshot["type"] == "game.snapshot"

    await ws.send_json({"type": "player.input", "right": True, "left": False, "jump_pressed": False})
    snapshot = await ws.receive_json()
    assert snapshot["type"] == "game.snapshot"

    await ws.close()
