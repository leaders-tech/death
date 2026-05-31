/*
This file checks the main browser lobby and first arena flow.
Edit this file when the real game flow changes across pages or websockets.
Copy a test pattern here when you add another end-to-end game flow.
*/

import { expect, test } from "@playwright/test";

test("two players can join a public lobby and start the arena", async ({ browser }) => {
  const hostContext = await browser.newContext();
  const playerContext = await browser.newContext();
  const host = await hostContext.newPage();
  const player = await playerContext.newPage();

  await host.goto("/");
  await host.getByLabel("Nickname").fill("Host");
  await host.getByRole("button", { name: "Create lobby" }).click();
  await expect(host.getByText("Host setup")).toBeVisible();

  await player.goto("/");
  await player.getByLabel("Nickname").fill("Friend");
  await expect(player.getByText("Host's lobby")).toBeVisible();
  await player.getByRole("button", { name: "Join selected lobby" }).click();
  await expect(player.getByText("Friend")).toBeVisible();

  await expect(host.getByText("Friend")).toBeVisible();
  await host.getByLabel("Daemon").selectOption({ label: "Friend" });
  await host.getByLabel("Lives").selectOption("5");
  await host.getByRole("button", { name: "Start game" }).click();

  await expect(host.getByLabel("Game arena")).toBeVisible();
  await expect(player.getByLabel("Game arena")).toBeVisible();
  await expect(player.getByText("Daemon controls coming next. Watch the arena for now.")).toBeVisible();

  await hostContext.close();
  await playerContext.close();
});
