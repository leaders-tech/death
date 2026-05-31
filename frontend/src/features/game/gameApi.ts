/*
This file wraps lobby API calls for the browser game.
Edit this file when lobby endpoints or request payloads change.
Copy this file when you add another small API helper group.
*/

import { postJson } from "../../shared/api";
import type { GameSnapshot, LivesSetting, Lobby } from "../../shared/types";

export type JoinResult = {
  lobby: Lobby;
  player_id: string;
  player_token: string;
};

export function listLobbies() {
  return postJson<{ lobbies: Lobby[] }>("/lobbies/list");
}

export function createLobby(nickname: string) {
  return postJson<JoinResult>("/lobbies/create", { nickname });
}

export function joinLobby(lobbyId: string, nickname: string) {
  return postJson<JoinResult>("/lobbies/join", { lobby_id: lobbyId, nickname });
}

export function configureLobby(lobbyId: string, playerToken: string, daemonId: string, lives: LivesSetting) {
  return postJson<{ lobby: Lobby }>("/lobbies/configure", {
    lobby_id: lobbyId,
    player_token: playerToken,
    daemon_id: daemonId,
    lives,
  });
}

export function startLobby(lobbyId: string, playerToken: string) {
  return postJson<{ lobby: Lobby; game: GameSnapshot }>("/lobbies/start", { lobby_id: lobbyId, player_token: playerToken });
}
