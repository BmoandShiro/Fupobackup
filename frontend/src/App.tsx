import React, { useState } from "react";
import "./App.css";

type TabId = "home" | "weather" | "system" | "chat" | "tools" | "settings";

const tabs: { id: TabId; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "weather", label: "Weather" },
  { id: "system", label: "System" },
  { id: "chat", label: "Chat" },
  { id: "tools", label: "Tools" },
  { id: "settings", label: "Settings" },
];

type LayoutMode = "sidebar" | "top";

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>("home");
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("sidebar");

  const renderContent = () => (
    <>
      {activeTab === "home" && <HomeTab navigateTo={setActiveTab} />}
      {activeTab === "weather" && <WeatherTab />}
      {activeTab === "system" && <SystemTab />}
      {activeTab === "chat" && <ChatTab />}
      {activeTab === "tools" && <ToolsTab />}
      {activeTab === "settings" && (
        <SettingsTab layoutMode={layoutMode} setLayoutMode={setLayoutMode} />
      )}
    </>
  );

  if (layoutMode === "top") {
    return (
      <div className="app-root top-layout">
        <header className="topbar">
          <div className="logo">Fupo</div>
          <nav className="nav nav-top">
            {tabs.map((t) => (
              <button
                key={t.id}
                className={`nav-item ${activeTab === t.id ? "active" : ""}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </header>
        <main className="content">{renderContent()}</main>
      </div>
    );
  }

  // default: sidebar layout
  return (
    <div className="app-root">
      <aside className="sidebar">
        <div className="logo">Fupo</div>
        <nav className="nav">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`nav-item ${activeTab === t.id ? "active" : ""}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">{renderContent()}</main>
    </div>
  );
};

// --- Simple placeholder tabs; we will flesh these out further ---

const Card: React.FC<{ title: string; subtitle?: string; children?: React.ReactNode }> = ({
  title,
  subtitle,
  children,
}) => (
  <div className="panel">
    <div className="panel-header">
      <h1>{title}</h1>
      {subtitle && <p className="muted">{subtitle}</p>}
    </div>
    {children}
  </div>
);

interface HomeTabProps {
  navigateTo: (tab: TabId) => void;
}

const HomeTab: React.FC<HomeTabProps> = ({ navigateTo }) => {
  const [status, setStatus] = useState<string>(
    "Welcome to your Desktop Assistant!"
  );
  const [scanProgress, setScanProgress] = useState<number>(0);
  const [listening, setListening] = useState<boolean>(false);
  const [duckingEnabled, setDuckingEnabled] = useState<boolean>(false);

  // TODO: Wire these up to real backend endpoints (FastAPI).
  const handleListen = async () => {
    setListening(true);
    try {
      // placeholder behaviour
      setStatus("Listening for a command… (stub)");
    } finally {
      setListening(false);
    }
  };

  const handleReset = () => {
    setStatus("Reset requested (stub).");
  };

  const handleScan = async () => {
    setScanProgress(0);
    setStatus("Scanning for programs… (stub)");
    // simple fake progress for now
    setTimeout(() => setScanProgress(35), 200);
    setTimeout(() => setScanProgress(70), 400);
    setTimeout(() => {
      setScanProgress(100);
      setStatus("Scan complete! (stub)");
    }, 700);
  };

  const handleShowMics = () => {
    setStatus("Microphone list requested (stub).");
  };

  const handleShowShortcuts = () => {
    setStatus("Desktop shortcuts requested (stub).");
  };

  const handleAddPath = () => {
    setStatus("Add-path dialog requested (stub).");
  };

  const handleWeather = () => {
    navigateTo("weather");
  };

  const handleToggleDucking = () => {
    const next = !duckingEnabled;
    setDuckingEnabled(next);
    setStatus(
      next
        ? "Audio ducking enabled (stub – will call backend)."
        : "Audio ducking disabled (stub)."
    );
  };

  return (
    <Card title="Home" subtitle="Quick controls & assistant overview.">
      <div className="btn-column">
        <button
          className="btn primary"
          onClick={handleListen}
          disabled={listening}
        >
          {listening ? "Listening…" : "Listen"}
        </button>
        <button className="btn" onClick={handleReset}>
          Reset Application
        </button>
        <button className="btn" onClick={handleScan}>
          Scan for Programs
        </button>
        <button className="btn" onClick={handleShowMics}>
          Show Microphones
        </button>
        <button className="btn" onClick={handleShowShortcuts}>
          Show Shortcuts
        </button>
        <button className="btn" onClick={handleAddPath}>
          Add Path…
        </button>
        <button className="btn" onClick={handleWeather}>
          🌦️ Weather Dashboard
        </button>
        <button
          className="btn"
          onClick={handleToggleDucking}
          style={
            duckingEnabled
              ? { borderColor: "#a855f7", background: "#161320" }
              : undefined
          }
        >
          {duckingEnabled ? "Disable Audio Ducking" : "Enable Audio Ducking"}
        </button>
      </div>

      <div className="status-card">
        <div className="status-label">Status</div>
        <div className="status-text">{status}</div>
        <div className="progress-bar">
          <div
            className="progress-inner"
            style={{ width: `${scanProgress}%` }}
          />
        </div>
      </div>
    </Card>
  );
};

const WeatherTab: React.FC = () => (
  <Card title="Weather" subtitle="Detailed conditions & map.">
    <p className="muted">Weather dashboard UI will live here, backed by your existing WeatherAPI.</p>
  </Card>
);

const SystemTab: React.FC = () => (
  <Card title="System" subtitle="CPU, RAM, and disk usage.">
    <p className="muted">System monitoring charts will go here, calling a /api/system endpoint.</p>
  </Card>
);

const ChatTab: React.FC = () => (
  <Card title="Chat" subtitle="Talk to your configured AI (ChatGPT / Grok / Cursor CLI).">
    <p className="muted">
      Next step: add a chat log, input box, and wire it to /api/chat on the Python backend.
    </p>
  </Card>
);

const ToolsTab: React.FC = () => (
  <Card title="Tools" subtitle="Screenshots and utilities.">
    <p className="muted">Screenshot and other tools will be triggered from here via /api/tools endpoints.</p>
  </Card>
);

interface SettingsTabProps {
  layoutMode: LayoutMode;
  setLayoutMode: (mode: LayoutMode) => void;
}

const SettingsTab: React.FC<SettingsTabProps> = ({
  layoutMode,
  setLayoutMode,
}) => (
  <Card title="Settings" subtitle="Spotify, Asana, AI provider, layout, macros, and more.">
    <div className="settings-section">
      <div className="settings-row">
        <span className="settings-label">Tab layout</span>
        <div className="settings-options">
          <button
            className={`btn ${layoutMode === "sidebar" ? "primary" : ""}`}
            onClick={() => setLayoutMode("sidebar")}
          >
            Sidebar (left)
          </button>
          <button
            className={`btn ${layoutMode === "top" ? "primary" : ""}`}
            onClick={() => setLayoutMode("top")}
          >
            Top Tabs
          </button>
        </div>
      </div>
      <p className="muted">
        (Next: add forms here that read/write settings via /api/settings, mirroring your current settings.json.)
      </p>
    </div>
  </Card>
);

export default App;
