# Daemon Arena

Daemon Arena is a small online multiplayer platformer prototype. Players join public lobbies with a nickname, the host chooses a daemon and a lives setting, and the first playable arena focuses on movement, jumping, and walljumping.

## What Is Inside

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, and a Canvas 2D arena.
- **Backend**: Python aiohttp server with POST JSON routes and a `/ws` websocket.
- **Game state**: in-memory lobbies and server-authoritative movement for the first prototype.
- **Infrastructure**: Docker, Makefile commands, tests, local development helpers, and deployment config from the template.

## Run Locally

Install everything once:

```bash
make setup
```

Start the backend in one terminal:

```bash
make back
```

Start the frontend in another terminal:

```bash
make front
```

Open `http://localhost:5101`.

## Play The Prototype

1. Enter a nickname.
2. Create a lobby or join a public lobby.
3. The host chooses the daemon and lives.
4. The host starts the game.
5. Players move with `A/D` or arrow keys and jump with `W`, `Up`, or `Space`.

The daemon does not play in this first slice. Daemon tools, hazards, upgrades, deaths, and player-to-player collision are planned for later.

## Tests

Run the full suite:

```bash
make test
```

Run only backend tests:

```bash
uv run pytest
```

Run only frontend unit tests:

```bash
cd frontend && npm run test
```

Run only browser tests:

```bash
cd frontend && npm run test:e2e
```
