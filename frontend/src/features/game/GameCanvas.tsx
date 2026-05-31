/*
This file draws the platformer arena on a responsive canvas.
Edit this file when game rendering or canvas sizing changes.
Copy this file as a starting point for another simple canvas game view.
*/

import { useEffect, useRef } from "react";
import type { GameSnapshot } from "../../shared/types";

type GameCanvasProps = {
  snapshot: GameSnapshot;
  playerId: string;
};

export function GameCanvas({ snapshot, playerId }: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const width = canvas.width;
    const height = canvas.height;
    const scale = Math.min(width / snapshot.arena.width, height / snapshot.arena.height);
    const offsetX = (width - snapshot.arena.width * scale) / 2;
    const offsetY = (height - snapshot.arena.height * scale) / 2;

    context.clearRect(0, 0, width, height);
    context.fillStyle = "#111827";
    context.fillRect(0, 0, width, height);

    context.save();
    context.translate(offsetX, offsetY);
    context.scale(scale, scale);

    context.fillStyle = "#1f2937";
    context.fillRect(0, 0, snapshot.arena.width, snapshot.arena.height);
    context.strokeStyle = "#38bdf8";
    context.lineWidth = 8;
    context.strokeRect(0, 0, snapshot.arena.width, snapshot.arena.height);

    for (const platform of snapshot.arena.platforms) {
      context.fillStyle = "#22c55e";
      context.fillRect(platform.x, platform.y, platform.width, platform.height);
      context.fillStyle = "rgba(255,255,255,0.22)";
      context.fillRect(platform.x, platform.y, platform.width, 5);
    }

    for (const player of snapshot.lobby.players) {
      const isDaemon = snapshot.lobby.daemon_id === player.id;
      context.fillStyle = isDaemon ? "#f43f5e" : player.id === playerId ? "#facc15" : "#60a5fa";
      context.fillRect(player.x, player.y, snapshot.arena.player_width, snapshot.arena.player_height);
      context.fillStyle = "#f8fafc";
      context.font = "22px Segoe UI, sans-serif";
      context.fillText(player.nickname, player.x - 6, player.y - 12);
    }

    context.restore();
  }, [playerId, snapshot]);

  return <canvas ref={canvasRef} aria-label="Game arena" className="h-full min-h-[420px] w-full rounded-lg border border-cyan-300 bg-slate-950" height={720} width={1280} />;
}
