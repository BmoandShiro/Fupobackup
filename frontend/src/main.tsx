import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { DashboardWindow } from "./DashboardWindow";
import "./App.css";

const isDashboard = typeof window !== "undefined" && window.location.hash === "#dashboard";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {isDashboard ? <DashboardWindow /> : <App />}
  </React.StrictMode>,
);
