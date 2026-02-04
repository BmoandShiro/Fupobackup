import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { DashboardWindow } from "./DashboardWindow";
import "./App.css";

const isDashboard = typeof window !== "undefined" && window.location.hash === "#dashboard";

if (isDashboard) {
  document.documentElement.classList.add("dashboard-window");
  document.body.classList.add("dashboard-window");
  const root = document.getElementById("root");
  if (root) root.classList.add("dashboard-window");
  // Set native window transparent immediately so corner cutouts show desktop, not black
  void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
    getCurrentWindow().setBackgroundColor({ r: 0, g: 0, b: 0, a: 0 }).catch(() => {});
  });
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {isDashboard ? <DashboardWindow /> : <App />}
  </React.StrictMode>,
);
