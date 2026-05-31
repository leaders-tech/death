/*
This file shows the lobby list, host setup, and first platformer arena.
Edit this file when the main game flow or lobby UI changes.
Copy this file as a starting point for another small realtime game page.
*/

import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../shared/api";
import type { GameSnapshot, LivesSetting, Lobby, WsMessage } from "../shared/types";
import { createGameSocket, type PlayerInput, type SocketStatus } from "../shared/socket";
import { configureLobby, createLobby, joinLobby, listLobbies, startLobby } from "../features/game/gameApi";
import { GameCanvas } from "../features/game/GameCanvas";

type Session = {
  lobbyId: string;
  playerId: string;
  playerToken: string;
  nickname: string;
};

const sessionKey = "platformer-session";

function readSavedSession(): Session | null {
  try {
    const raw = window.localStorage.getItem(sessionKey);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

function saveSession(session: Session) {
  window.localStorage.setItem(sessionKey, JSON.stringify(session));
}

function clearSession() {
  window.localStorage.removeItem(sessionKey);
}

function messageFromError(error: unknown) {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function GamePage() {
  const [lobbies, setLobbies] = useState<Lobby[]>([]);
  const [lobby, setLobby] = useState<Lobby | null>(null);
  const [session, setSession] = useState<Session | null>(() => readSavedSession());
  const [nickname, setNickname] = useState(() => readSavedSession()?.nickname ?? "");
  const [selectedLobbyId, setSelectedLobbyId] = useState("");
  const [daemonId, setDaemonId] = useState("");
  const [lives, setLives] = useState<LivesSetting>(3);
  const [snapshot, setSnapshot] = useState<GameSnapshot | null>(null);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("idle");
  const [error, setError] = useState("");
  const socketRef = useRef<ReturnType<typeof createGameSocket> | null>(null);
  const keysRef = useRef({ left: false, right: false });

  const currentPlayer = useMemo(() => lobby?.players.find((player) => player.id === session?.playerId) ?? null, [lobby, session]);
  const isHost = currentPlayer?.is_host === true;
  const isDaemon = lobby?.daemon_id === session?.playerId;

  useEffect(() => {
    void refreshLobbies();
    const timer = window.setInterval(() => void refreshLobbies(), 2500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!session) {
      return;
    }
    socketRef.current?.stop();
    const socket = createGameSocket({
      lobbyId: session.lobbyId,
      playerToken: session.playerToken,
      onMessage(message: WsMessage) {
        if (message.type === "game.snapshot") {
          setSnapshot(message);
          setLobby(message.lobby);
        }
        if (message.type === "lobby.changed") {
          setLobby(message.lobby);
        }
      },
      onStatus: setSocketStatus,
    });
    socketRef.current = socket;
    return () => socket.stop();
  }, [session]);

  useEffect(() => {
    if (!session || isDaemon) {
      return;
    }
    const send = (input: PlayerInput) => socketRef.current?.sendInput(input);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat && ![" ", "ArrowUp", "w", "W"].includes(event.key)) {
        return;
      }
      if (event.key === "a" || event.key === "A" || event.key === "ArrowLeft") {
        keysRef.current.left = true;
      }
      if (event.key === "d" || event.key === "D" || event.key === "ArrowRight") {
        keysRef.current.right = true;
      }
      const jump = event.key === " " || event.key === "w" || event.key === "W" || event.key === "ArrowUp";
      send({ left: keysRef.current.left, right: keysRef.current.right, jump_pressed: jump });
      if (jump || event.key.startsWith("Arrow")) {
        event.preventDefault();
      }
    };
    const onKeyUp = (event: KeyboardEvent) => {
      if (event.key === "a" || event.key === "A" || event.key === "ArrowLeft") {
        keysRef.current.left = false;
      }
      if (event.key === "d" || event.key === "D" || event.key === "ArrowRight") {
        keysRef.current.right = false;
      }
      send({ left: keysRef.current.left, right: keysRef.current.right, jump_pressed: false });
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [isDaemon, session]);

  async function refreshLobbies() {
    try {
      const data = await listLobbies();
      setLobbies(data.lobbies);
      if (!selectedLobbyId && data.lobbies[0]) {
        setSelectedLobbyId(data.lobbies[0].id);
      }
    } catch (caught) {
      setError(messageFromError(caught));
    }
  }

  async function handleCreate() {
    setError("");
    try {
      const data = await createLobby(nickname);
      const nextSession = { lobbyId: data.lobby.id, playerId: data.player_id, playerToken: data.player_token, nickname };
      saveSession(nextSession);
      setSession(nextSession);
      setLobby(data.lobby);
      setDaemonId(data.player_id);
      setLives(data.lobby.lives);
    } catch (caught) {
      setError(messageFromError(caught));
    }
  }

  async function handleJoin() {
    setError("");
    try {
      const data = await joinLobby(selectedLobbyId, nickname);
      const nextSession = { lobbyId: data.lobby.id, playerId: data.player_id, playerToken: data.player_token, nickname };
      saveSession(nextSession);
      setSession(nextSession);
      setLobby(data.lobby);
      setDaemonId(data.lobby.daemon_id ?? data.lobby.players[0]?.id ?? "");
      setLives(data.lobby.lives);
    } catch (caught) {
      setError(messageFromError(caught));
    }
  }

  async function handleConfigure() {
    if (!session) {
      return;
    }
    setError("");
    try {
      const data = await configureLobby(session.lobbyId, session.playerToken, daemonId, lives);
      setLobby(data.lobby);
    } catch (caught) {
      setError(messageFromError(caught));
    }
  }

  async function handleStart() {
    if (!session) {
      return;
    }
    setError("");
    try {
      if (daemonId) {
        await configureLobby(session.lobbyId, session.playerToken, daemonId, lives);
      }
      const data = await startLobby(session.lobbyId, session.playerToken);
      setLobby(data.lobby);
      setSnapshot(data.game);
    } catch (caught) {
      setError(messageFromError(caught));
    }
  }

  function handleLeaveLocal() {
    socketRef.current?.stop();
    clearSession();
    setSession(null);
    setLobby(null);
    setSnapshot(null);
    void refreshLobbies();
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto grid min-h-screen max-w-7xl gap-5 px-4 py-5 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4 rounded-lg border border-slate-700 bg-slate-900 p-4">
          <div>
            <h1 className="text-2xl font-semibold">Daemon Arena</h1>
            <p className="mt-1 text-sm text-slate-300">A public-lobby platformer prototype.</p>
          </div>

          {error && <p className="rounded-md border border-red-500 bg-red-950/70 p-3 text-sm text-red-100">{error}</p>}

          {!session ? (
            <section className="space-y-3">
              <label className="block text-sm font-medium" htmlFor="nickname">
                Nickname
              </label>
              <input
                id="nickname"
                className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2 text-white"
                maxLength={18}
                minLength={2}
                onChange={(event) => setNickname(event.target.value)}
                placeholder="Your name"
                value={nickname}
              />
              <button className="w-full rounded-md bg-cyan-400 px-4 py-2 font-semibold text-slate-950" onClick={() => void handleCreate()}>
                Create lobby
              </button>

              <div className="pt-2">
                <h2 className="text-lg font-semibold">Public lobbies</h2>
                <div className="mt-2 space-y-2">
                  {lobbies.length === 0 ? (
                    <p className="text-sm text-slate-400">No lobbies yet.</p>
                  ) : (
                    lobbies.map((item) => (
                      <label key={item.id} className="flex cursor-pointer items-center justify-between rounded-md border border-slate-700 bg-slate-950 p-3">
                        <span>
                          <span className="block font-medium">{item.name}</span>
                          <span className="text-xs text-slate-400">
                            {item.players.length} players · {item.status}
                          </span>
                        </span>
                        <input checked={selectedLobbyId === item.id} name="lobby" onChange={() => setSelectedLobbyId(item.id)} type="radio" />
                      </label>
                    ))
                  )}
                </div>
                <button className="mt-3 w-full rounded-md border border-cyan-400 px-4 py-2 font-semibold text-cyan-100" disabled={!selectedLobbyId} onClick={() => void handleJoin()}>
                  Join selected lobby
                </button>
              </div>
            </section>
          ) : (
            <section className="space-y-4">
              <div className="rounded-md border border-slate-700 bg-slate-950 p-3 text-sm">
                <p className="font-semibold">{lobby?.name ?? "Joined lobby"}</p>
                <p className="text-slate-400">Socket: {socketStatus}</p>
              </div>
              <button className="w-full rounded-md border border-slate-600 px-4 py-2 text-sm text-slate-200" onClick={handleLeaveLocal}>
                Leave on this device
              </button>
            </section>
          )}

          {lobby && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Players</h2>
              {lobby.players.map((player) => (
                <div key={player.id} className="flex items-center justify-between rounded-md bg-slate-800 px-3 py-2 text-sm">
                  <span>{player.nickname}</span>
                  <span className="text-slate-400">{player.is_host ? "host" : lobby.daemon_id === player.id ? "daemon" : "player"}</span>
                </div>
              ))}
            </section>
          )}

          {lobby && isHost && lobby.status === "waiting" && (
            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Host setup</h2>
              <label className="block text-sm" htmlFor="daemon">
                Daemon
              </label>
              <select id="daemon" className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2" onChange={(event) => setDaemonId(event.target.value)} value={daemonId}>
                <option value="">Choose daemon</option>
                {lobby.players.map((player) => (
                  <option key={player.id} value={player.id}>
                    {player.nickname}
                  </option>
                ))}
              </select>
              <label className="block text-sm" htmlFor="lives">
                Lives
              </label>
              <select
                id="lives"
                className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2"
                onChange={(event) => setLives(event.target.value === "infinite" ? "infinite" : Number(event.target.value))}
                value={lives}
              >
                {[1, 2, 3, 4, 5, 6, 7].map((count) => (
                  <option key={count} value={count}>
                    {count}
                  </option>
                ))}
                <option value="infinite">infinite</option>
              </select>
              <div className="grid grid-cols-2 gap-2">
                <button className="rounded-md border border-cyan-400 px-3 py-2 text-sm font-semibold text-cyan-100" onClick={() => void handleConfigure()}>
                  Save setup
                </button>
                <button className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-semibold text-slate-950" onClick={() => void handleStart()}>
                  Start game
                </button>
              </div>
            </section>
          )}
        </aside>

        <section className="min-h-[520px] rounded-lg border border-slate-700 bg-slate-900 p-4">
          {snapshot && session ? (
            <div className="h-full space-y-3">
              {isDaemon ? (
                <div className="rounded-md border border-rose-400 bg-rose-950/60 p-3 text-sm text-rose-100">Daemon controls coming next. Watch the arena for now.</div>
              ) : (
                <div className="rounded-md border border-cyan-500 bg-cyan-950/50 p-3 text-sm text-cyan-100">Use A/D or arrows to move. Press W, Up, or Space to jump and walljump.</div>
              )}
              <GameCanvas playerId={session.playerId} snapshot={snapshot} />
            </div>
          ) : (
            <div className="flex h-full min-h-[520px] items-center justify-center rounded-lg border border-dashed border-slate-700 text-center text-slate-400">
              <p>Create or join a lobby to start.</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
