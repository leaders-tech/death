/*
This file keeps shared TypeScript types for lobbies, game snapshots, API results, and websocket messages.
Edit this file when backend JSON shapes or websocket message shapes change.
Copy a type pattern here when you add another shared API or websocket type.
*/

export type LivesSetting = number | "infinite";

export type Player = {
  id: string;
  nickname: string;
  is_host: boolean;
  x: number;
  y: number;
  vx: number;
  vy: number;
  on_ground: boolean;
  wall_dir: number;
};

export type Lobby = {
  id: string;
  name: string;
  status: "waiting" | "playing";
  daemon_id: string | null;
  lives: LivesSetting;
  players: Player[];
};

export type Platform = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type Arena = {
  width: number;
  height: number;
  platforms: Platform[];
  player_width: number;
  player_height: number;
};

export type GameSnapshot = {
  type: "game.snapshot";
  lobby: Lobby;
  arena: Arena;
};

export type ApiOk<T> = {
  ok: true;
  data: T;
};

export type ApiFail = {
  ok: false;
  error: {
    code: string;
    message: string;
  };
};

export type ApiResponse<T> = ApiOk<T> | ApiFail;

export type WsMessage =
  | { type: "ws.ready"; lobby_id: string; connections: number }
  | { type: "pong" }
  | { type: "lobby.changed"; lobby: Lobby }
  | GameSnapshot;
