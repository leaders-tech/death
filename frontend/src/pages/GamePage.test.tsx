/*
This file tests the main game page lobby and arena states.
Edit this file when the first game flow changes.
Copy a test pattern here when you add another page with API-driven state.
*/

import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const listLobbies = vi.fn();
const createLobby = vi.fn();
const joinLobby = vi.fn();
const configureLobby = vi.fn();
const startLobby = vi.fn();

vi.mock("../features/game/gameApi", () => ({
  listLobbies: () => listLobbies(),
  createLobby: (nickname: string) => createLobby(nickname),
  joinLobby: (lobbyId: string, nickname: string) => joinLobby(lobbyId, nickname),
  configureLobby: (lobbyId: string, playerToken: string, daemonId: string, lives: number | "infinite") => configureLobby(lobbyId, playerToken, daemonId, lives),
  startLobby: (lobbyId: string, playerToken: string) => startLobby(lobbyId, playerToken),
}));

vi.mock("../shared/socket", () => ({
  createGameSocket: vi.fn(() => ({ sendInput: vi.fn(), sendPing: vi.fn(), stop: vi.fn() })),
}));

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GamePage } from "./GamePage";
import type { GameSnapshot, Lobby } from "../shared/types";

const waitingLobby: Lobby = {
  id: "ABCDE",
  name: "Host's lobby",
  status: "waiting",
  daemon_id: null,
  lives: 3,
  players: [
    { id: "host", nickname: "Host", is_host: true, x: 120, y: 760, vx: 0, vy: 0, on_ground: true, wall_dir: 0 },
    { id: "friend", nickname: "Friend", is_host: false, x: 180, y: 760, vx: 0, vy: 0, on_ground: true, wall_dir: 0 },
  ],
};

const gameSnapshot: GameSnapshot = {
  type: "game.snapshot",
  lobby: { ...waitingLobby, status: "playing", daemon_id: "friend" },
  arena: {
    width: 1600,
    height: 900,
    player_width: 34,
    player_height: 46,
    platforms: [{ x: 0, y: 850, width: 1600, height: 50 }],
  },
};

describe("GamePage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    listLobbies.mockResolvedValue({ lobbies: [waitingLobby] });
  });

  it("shows public lobbies and can create a lobby", async () => {
    createLobby.mockResolvedValue({ lobby: waitingLobby, player_id: "host", player_token: "token" });
    render(<GamePage />);

    expect(await screen.findByText("Host's lobby")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Nickname"), "Host");
    await userEvent.click(screen.getByRole("button", { name: "Create lobby" }));

    expect(createLobby).toHaveBeenCalledWith("Host");
    expect(await screen.findByText("Players")).toBeInTheDocument();
  });

  it("shows host setup after joining as host", async () => {
    createLobby.mockResolvedValue({ lobby: waitingLobby, player_id: "host", player_token: "token" });
    configureLobby.mockResolvedValue({ lobby: { ...waitingLobby, daemon_id: "friend", lives: 5 } });
    render(<GamePage />);

    await userEvent.type(await screen.findByLabelText("Nickname"), "Host");
    await userEvent.click(screen.getByRole("button", { name: "Create lobby" }));
    await screen.findByText("Host setup");
    await userEvent.selectOptions(screen.getByLabelText("Daemon"), "friend");
    await userEvent.selectOptions(screen.getByLabelText("Lives"), "5");
    await userEvent.click(screen.getByRole("button", { name: "Save setup" }));

    expect(configureLobby).toHaveBeenCalledWith("ABCDE", "token", "friend", 5);
  });

  it("shows the game canvas and daemon placeholder after start", async () => {
    createLobby.mockResolvedValue({ lobby: waitingLobby, player_id: "host", player_token: "token" });
    configureLobby.mockResolvedValue({ lobby: { ...waitingLobby, daemon_id: "friend" } });
    startLobby.mockResolvedValue({ lobby: gameSnapshot.lobby, game: gameSnapshot });
    render(<GamePage />);

    await userEvent.type(await screen.findByLabelText("Nickname"), "Host");
    await userEvent.click(screen.getByRole("button", { name: "Create lobby" }));
    await userEvent.selectOptions(await screen.findByLabelText("Daemon"), "friend");
    await userEvent.click(screen.getByRole("button", { name: "Start game" }));

    expect(await screen.findByLabelText("Game arena")).toBeInTheDocument();
    expect(screen.getByText(/Use A\/D or arrows/)).toBeInTheDocument();
  });
});
