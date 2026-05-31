/*
This file builds the main frontend route for the game prototype.
Edit this file when top-level pages or routes change.
Copy the route pattern here when you add another top-level page.
*/

import { Route, Routes } from "react-router-dom";
import { GamePage } from "../pages/GamePage";

export function App() {
  return (
    <Routes>
      <Route path="*" element={<GamePage />} />
    </Routes>
  );
}
