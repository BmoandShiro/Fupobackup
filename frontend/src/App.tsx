import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import { api, type Settings, type MicItem } from "./utils/api";

type TabId = "home" | "weather" | "system" | "chat" | "tools" | "commands" | "help" | "settings";

const tabs: { id: TabId; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "weather", label: "Weather" },
  { id: "system", label: "System" },
  { id: "chat", label: "Chat" },
  { id: "tools", label: "Tools" },
  { id: "commands", label: "Commands" },
  { id: "help", label: "Help" },
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
      {activeTab === "commands" && <CommandsTab />}
      {activeTab === "help" && <HelpTab />}
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
        <footer className="app-footer">Developed by: BMOandShiro v1.0.0</footer>
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
      <div className="main-and-footer">
        <main className="content">{renderContent()}</main>
        <footer className="app-footer">Developed by: BMOandShiro v1.0.0</footer>
      </div>
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
  const [duckingAvailable, setDuckingAvailable] = useState<boolean | null>(null);
  const [duckingError, setDuckingError] = useState<string | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<{ message: string; followUpPrefix: string } | null>(null);
  const [promptInput, setPromptInput] = useState("");
  const scanPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Sync ducking state and pycaw availability from backend on mount
  useEffect(() => {
    api.getDucking()
      .then((r) => {
        setDuckingEnabled(r.enabled);
        setDuckingAvailable(r.available ?? true);
        setDuckingError(r.error ?? null);
      })
      .catch(() => {});
    return () => {
      if (scanPollRef.current) clearInterval(scanPollRef.current);
    };
  }, []);

  const handleListen = () => {
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: new () => SpeechRecognition }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognition }).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus("Voice input is not supported in this browser. Try Chrome or Edge, or use the Chat tab.");
      return;
    }
    setListening(true);
    setStatus("Listening… say your command.");
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[event.resultIndex][0].transcript.trim();
      if (!transcript) {
        setStatus("No speech detected. Try again.");
        setListening(false);
        return;
      }
      setStatus(`Heard: "${transcript}". Processing…`);
      api
        .command(transcript)
        .then((r) => {
          const res = r as { display?: string; spoken?: string; prompt_for?: string; follow_up_prefix?: string };
          if (res.prompt_for) {
            setPendingPrompt({
              message: res.display || res.spoken || "Enter value:",
              followUpPrefix: res.follow_up_prefix || "",
            });
            setStatus(res.display || res.spoken || "");
          } else {
            setStatus(res.display || res.spoken || "Done.");
            setPendingPrompt(null);
          }
        })
        .catch((e) => {
          setStatus(`Command failed: ${e instanceof Error ? e.message : String(e)}`);
          setPendingPrompt(null);
        })
        .finally(() => setListening(false));
    };
    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const msg =
        event.error === "no-speech"
          ? "No speech detected. Try again."
          : event.error === "not-allowed"
            ? "Microphone access denied."
            : `Listening error: ${event.error}`;
      setStatus(msg);
      setListening(false);
    };
    recognition.onend = () => {
      setListening(false);
    };
    try {
      recognition.start();
    } catch (e) {
      setStatus(`Could not start listening: ${e instanceof Error ? e.message : String(e)}`);
      setListening(false);
    }
  };

  const handleReset = () => {
    setStatus("Please restart the Fupo app from the taskbar or shortcut to reset.");
  };

  const handleScan = async () => {
    setScanProgress(0);
    setStatus("Starting scan…");
    try {
      await api.startScan();
      setStatus("Scanning for programs…");
      scanPollRef.current = setInterval(async () => {
        try {
          const s = await api.getScanStatus();
          setScanProgress(s.progress);
          setStatus(s.message);
          if (!s.running) {
            if (scanPollRef.current) {
              clearInterval(scanPollRef.current);
              scanPollRef.current = null;
            }
            if (s.error) setStatus(`Scan failed: ${s.error}`);
          }
        } catch {
          if (scanPollRef.current) {
            clearInterval(scanPollRef.current);
            scanPollRef.current = null;
          }
          setStatus("Could not get scan status.");
        }
      }, 500);
    } catch (e) {
      setStatus(`Scan failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handleShowMics = async () => {
    try {
      const r = await api.getMics();
      setStatus(r.message || "No microphones listed.");
    } catch (e) {
      setStatus(`Microphones: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handleShowShortcuts = async () => {
    try {
      const r = await api.getShortcuts();
      setStatus(r.message || "No desktop shortcuts found.");
    } catch (e) {
      setStatus(`Shortcuts: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handleAddPath = async () => {
    const path = window.prompt("Enter the executable path:");
    if (!path?.trim()) return;
    try {
      const r = await api.addPath(path.trim());
      setStatus(r.message);
    } catch (e) {
      setStatus(`Add path failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handleWeather = () => {
    navigateTo("weather");
  };

  const handleToggleDucking = async () => {
    const next = !duckingEnabled;
    try {
      const r = await api.setDucking(next);
      setDuckingEnabled(r.enabled);
      setStatus(r.message);
    } catch (e) {
      setStatus(`Audio ducking: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const handlePromptSubmit = async () => {
    if (!pendingPrompt || !promptInput.trim()) return;
    const followUp = pendingPrompt.followUpPrefix + promptInput.trim();
    setPendingPrompt(null);
    setPromptInput("");
    setStatus("Creating playlist…");
    try {
      const r = await api.command(followUp);
      const res = r as { display?: string; spoken?: string };
      setStatus(res.display || res.spoken || "Done.");
    } catch (e) {
      setStatus(`Failed: ${e instanceof Error ? e.message : String(e)}`);
    }
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
          disabled={duckingAvailable === false}
          style={
            duckingEnabled
              ? { borderColor: "#a855f7", background: "#161320" }
              : undefined
          }
        >
          {duckingEnabled ? "Disable Audio Ducking" : "Enable Audio Ducking"}
        </button>
      </div>
      {duckingAvailable === false && duckingError && (
        <p className="muted ducking-error" style={{ marginTop: "8px", fontSize: "0.85rem", color: "#f87171" }}>
          pycaw unavailable: {duckingError}
        </p>
      )}

      <div className="status-card">
        <div className="status-label">Status</div>
        <div className="status-text">{status}</div>
        {pendingPrompt && (
          <div className="prompt-follow-up">
            <p className="muted">{pendingPrompt.message}</p>
            <div className="prompt-row">
              <input
                type="text"
                className="settings-input"
                placeholder="Playlist name"
                value={promptInput}
                onChange={(e) => setPromptInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handlePromptSubmit()}
              />
              <button className="btn primary" onClick={handlePromptSubmit}>
                Create
              </button>
            </div>
          </div>
        )}
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

// --- Help tab with search ---

const HELP_SECTIONS = [
  {
    id: "audio-ducking",
    title: "Audio ducking",
    body: "Audio ducking lowers your system (or Spotify) volume when you speak into the microphone, so your voice is easier to hear over music or other audio. Enable it from the Home tab with “Enable Audio Ducking.” It uses the pycaw library on Windows to control the default output device. If you see “Audio ducking unavailable (pycaw not set up),” the audio device or driver may not support the control the app uses (e.g. on some Windows setups). You can still use the app without ducking.",
  },
  {
    id: "pycaw-setup",
    title: "Setting up pycaw (audio ducking)",
    body: "Audio ducking needs pycaw and comtypes on Windows. From your project folder in a terminal: (1) Install: pip install pycaw comtypes. Or install everything: pip install -r requirements.txt. (2) Use a 64-bit Python if your Windows is 64-bit. (3) If it still fails, run the terminal (or backend) as Administrator once so COM can register. (4) Restart the backend after installing. Audio ducking only works on Windows with a default playback device that supports volume control.",
  },
  {
    id: "settings",
    title: "Settings menu",
    body: "The Settings tab loads and saves options from your project’s settings.json. You can set: Theme (Dark, Nord Dark, High Contrast Dark), Spotify Client ID and Secret and Redirect URI (for “play song” and other Spotify commands), AI provider and API keys (Chat tab), NLP and macro keys (voice), Firefox and GeckoDriver paths, screenshot folder, and other options. Click “Save settings” to write changes. The backend must be running for the Settings tab to load or save.",
  },
  {
    id: "spotify",
    title: "Using Spotify",
    body: "Add your Spotify app’s Client ID and Client Secret in Settings (from the Spotify Developer Dashboard), set Redirect URI to http://localhost:8080, and save. Log in once (e.g. from the desktop app or when the API opens a browser) so .spotify_cache is created. Then you can say “play song [name],” “pause,” “play my liked songs,” “play Discover Weekly,” “create a playlist,” and use the other Spotify commands listed in the Commands tab. Say “create a playlist” and you’ll be asked for the name, then the playlist is created.",
  },
];

const HelpTab: React.FC = () => {
  const [search, setSearch] = useState("");
  const q = search.trim().toLowerCase();
  const filtered = q
    ? HELP_SECTIONS.filter(
        (s) =>
          s.title.toLowerCase().includes(q) ||
          s.body.toLowerCase().includes(q)
      )
    : HELP_SECTIONS;

  return (
    <Card title="Help" subtitle="Search for explanations and how-to.">
      <div className="help-search-row">
        <input
          type="text"
          className="settings-input help-search"
          placeholder="Search help…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="help-sections">
        {filtered.length ? (
          filtered.map((s) => (
            <section key={s.id} className="help-section">
              <h3 className="help-section-title">{s.title}</h3>
              <p className="help-section-body">{s.body}</p>
            </section>
          ))
        ) : (
          <p className="muted">No help topics match your search.</p>
        )}
      </div>
    </Card>
  );
};

const WeatherTab: React.FC = () => {
  const [location, setLocation] = useState("");
  const [display, setDisplay] = useState<string | null>(null);
  const [resolvedLocation, setResolvedLocation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGetWeather = async () => {
    setLoading(true);
    setError(null);
    setDisplay(null);
    setResolvedLocation(null);
    try {
      const r = await api.getWeather(location.trim() || undefined);
      setDisplay(r.display);
      setResolvedLocation(r.location ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Weather" subtitle="Detailed conditions (Open-Meteo). City name or US ZIP — leave blank for current location.">
      <p className="weather-tip muted">
        Enter a city (e.g. Chicago, London) or a US ZIP code (e.g. 90210). Leave blank to use your current location.
      </p>
      <div className="weather-row">
        <input
          type="text"
          className="settings-input"
          placeholder="City or US ZIP (e.g. 60601) — blank = current location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleGetWeather()}
        />
        <button className="btn primary" onClick={handleGetWeather} disabled={loading}>
          {loading ? "Loading…" : "Get weather"}
        </button>
      </div>
      {error && <p className="muted" style={{ color: "#f87171" }}>{error}</p>}
      {resolvedLocation && display != null && (
        <p className="weather-resolved muted">Showing: {resolvedLocation}</p>
      )}
      {display != null && (
        <pre className="weather-display">{display}</pre>
      )}
    </Card>
  );
};

const MAX_POINTS = 60;
const POLL_MS = 2000;

const LiveLineChart: React.FC<{
  data: number[];
  color: string;
  label: string;
  currentValue: string;
}> = ({ data, color, label, currentValue }) => {
  const w = 400;
  const h = 72;
  if (data.length < 2) {
    return (
      <div className="system-chart-block">
        <div className="system-chart-header">
          <span className="system-label">{label}</span>
          <span className="system-value">{currentValue}</span>
        </div>
        <div className="system-chart-svg-wrap" style={{ width: w, height: h }}>
          <span className="muted">Collecting…</span>
        </div>
      </div>
    );
  }
  const points = data
    .map((v, i) => {
      const x = (i / Math.max(1, data.length - 1)) * w;
      const y = h - (Math.min(100, Math.max(0, v)) / 100) * h;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <div className="system-chart-block">
      <div className="system-chart-header">
        <span className="system-label">{label}</span>
        <span className="system-value">{currentValue}</span>
      </div>
      <div className="system-chart-svg-wrap" style={{ width: w, height: h }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
          <polyline
            fill="none"
            stroke={color}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={points}
          />
        </svg>
      </div>
    </div>
  );
};

type SystemViewMode = "charts" | "bars";

const SystemTab: React.FC = () => {
  const [viewMode, setViewMode] = useState<SystemViewMode>("charts");
  const [history, setHistory] = useState<{
    cpu: number[];
    ram: number[];
    disk: number[];
    latest: { cpu_percent: number; ram_percent: number; ram_used_gb: number; ram_total_gb: number; disk_percent: number } | null;
  }>({ cpu: [], ram: [], disk: [], latest: null });
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    api.getSystem()
      .then((s) => {
        setError(null);
        setHistory((prev) => {
          const cpu = [...prev.cpu, s.cpu_percent].slice(-MAX_POINTS);
          const ram = [...prev.ram, s.ram_percent].slice(-MAX_POINTS);
          const disk = [...prev.disk, s.disk_percent].slice(-MAX_POINTS);
          return { cpu, ram, disk, latest: s };
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, []);

  if (error && !history.latest) {
    return (
      <Card title="System" subtitle="CPU, RAM, and disk usage.">
        <p className="muted" style={{ color: "#f87171" }}>{error}</p>
      </Card>
    );
  }

  const latest = history.latest;
  return (
    <Card title="System" subtitle="Live CPU, RAM, and disk usage. Updates every 2s.">
      <div className="system-view-toggle">
        <span className="system-toggle-label">View:</span>
        <div className="system-toggle-buttons">
          <button
            type="button"
            className={`btn ${viewMode === "charts" ? "primary" : ""}`}
            onClick={() => setViewMode("charts")}
          >
            Charts
          </button>
          <button
            type="button"
            className={`btn ${viewMode === "bars" ? "primary" : ""}`}
            onClick={() => setViewMode("bars")}
          >
            Bars
          </button>
        </div>
      </div>
      {viewMode === "charts" && (
        <div className="system-charts">
          <LiveLineChart
            data={history.cpu}
            color="#a855f7"
            label="CPU"
            currentValue={latest ? `${latest.cpu_percent}%` : "—"}
          />
          <LiveLineChart
            data={history.ram}
            color="#6366f1"
            label="RAM"
            currentValue={latest ? `${latest.ram_percent}% (${latest.ram_used_gb} / ${latest.ram_total_gb} GB)` : "—"}
          />
          <LiveLineChart
            data={history.disk}
            color="#22c55e"
            label="Disk"
            currentValue={latest ? `${latest.disk_percent}%` : "—"}
          />
        </div>
      )}
      {viewMode === "bars" && latest && (
        <div className="system-stats">
          <div className="system-row">
            <span className="system-label">CPU</span>
            <div className="system-bar-wrap">
              <div className="system-bar" style={{ width: `${Math.min(100, latest.cpu_percent)}%` }} />
            </div>
            <span className="system-value">{latest.cpu_percent}%</span>
          </div>
          <div className="system-row">
            <span className="system-label">RAM</span>
            <div className="system-bar-wrap">
              <div className="system-bar" style={{ width: `${latest.ram_percent}%` }} />
            </div>
            <span className="system-value">{latest.ram_percent}% ({latest.ram_used_gb} / {latest.ram_total_gb} GB)</span>
          </div>
          <div className="system-row">
            <span className="system-label">Disk</span>
            <div className="system-bar-wrap">
              <div className="system-bar" style={{ width: `${latest.disk_percent}%` }} />
            </div>
            <span className="system-value">{latest.disk_percent}%</span>
          </div>
        </div>
      )}
      {viewMode === "bars" && !latest && (
        <p className="muted">Collecting…</p>
      )}
    </Card>
  );
};

const ChatTab: React.FC = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);
    try {
      const r = await api.chat(text);
      setMessages((prev) => [...prev, { role: "assistant", text: r.display }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${e instanceof Error ? e.message : String(e)}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Chat" subtitle="Talk to your configured AI (ChatGPT / Grok / Cursor CLI). Backend /api/chat is currently a stub.">
      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="muted">Send a message to test the chat endpoint. Wire backend to your AI in Settings to get real replies.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <span className="chat-role">{m.role === "user" ? "You" : "Assistant"}</span>
            <span className="chat-text">{m.text}</span>
          </div>
        ))}
      </div>
      <div className="chat-input-row">
        <input
          type="text"
          className="settings-input"
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
        />
        <button className="btn primary" onClick={handleSend} disabled={loading}>
          {loading ? "…" : "Send"}
        </button>
      </div>
    </Card>
  );
};

const ToolsTab: React.FC = () => {
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const handleScreenshot = async () => {
    setLoading(true);
    setStatus("");
    try {
      const r = await api.screenshot();
      setStatus(r.message);
    } catch (e) {
      setStatus(`Failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Tools" subtitle="Screenshots and utilities.">
      <div className="btn-column">
        <button className="btn primary" onClick={handleScreenshot} disabled={loading}>
          {loading ? "Capturing…" : "Take screenshot"}
        </button>
      </div>
      {status && <p className="muted" style={{ marginTop: "8px" }}>{status}</p>}
    </Card>
  );
};

// --- Commands tab: reference for voice/text commands ---

const CommandRow: React.FC<{ phrase: string; desc: string; badge?: string }> = ({ phrase, desc, badge }) => (
  <div className="command-row">
    <div className="command-phrase">{phrase}</div>
    <div className="command-desc">{desc}</div>
    {badge && <span className={`command-badge ${badge === "soon" ? "badge-soon" : "badge-rec"}`}>{badge === "soon" ? "Coming soon" : "Recommended"}</span>}
  </div>
);

const CommandsTab: React.FC = () => (
  <Card title="Commands" subtitle="Voice and text command reference. Say these or type in Chat.">
    <section className="commands-section">
      <h2 className="commands-section-title">Spotify</h2>

      <h3 className="commands-subtitle">Currently supported</h3>
      <div className="command-list">
        <CommandRow phrase="Play song [name]" desc="Search and play a track. Optional: … by [artist]." />
        <CommandRow phrase="Play song [name] from my liked songs" desc="Play that track from your Liked Songs." />
        <CommandRow phrase="Play artist [name]" desc="Play artist’s top tracks (shuffled)." />
        <CommandRow phrase="Play artist radio [name] / Play radio [name]" desc="Play artist radio." />
        <CommandRow phrase="Play album [name]" desc="Play an album." />
        <CommandRow phrase="Play playlist [name]" desc="Play one of your playlists by name." />
        <CommandRow phrase="Play daylist" desc="Play your Spotify Daylist." />
        <CommandRow phrase="Play my liked songs" desc="Start playing your Liked Songs library." />
        <CommandRow phrase="Play Discover Weekly" desc="Play the Discover Weekly playlist." />
        <CommandRow phrase="Play Release Radar" desc="Play the Release Radar playlist." />
        <CommandRow phrase="Play [genre] / Play rock music" desc="Play recommendations by genre." />
        <CommandRow phrase="Play something similar / More like this" desc="Recommendations from current track." />
        <CommandRow phrase="Pause" desc="Pause playback." />
        <CommandRow phrase="Resume / Play music" desc="Resume playback." />
        <CommandRow phrase="Skip / Next" desc="Skip to next track." />
        <CommandRow phrase="Previous / Back" desc="Go to previous track." />
        <CommandRow phrase="What’s playing / Current song / Check song" desc="Say what track is playing." />
        <CommandRow phrase="Like song / Favorite song" desc="Add current track to Liked Songs." />
        <CommandRow phrase="Unlike song / Remove song / Unfavorite song" desc="Remove current track from Liked Songs." />
        <CommandRow phrase="Toggle shuffle / Switch shuffle" desc="Turn shuffle on/off." />
        <CommandRow phrase="Toggle repeat / Switch repeat" desc="Cycle repeat off → context → track." />
        <CommandRow phrase="Set Spotify volume [0–100]%" desc="Set playback volume (e.g. set Spotify volume 50%)." />
        <CommandRow phrase="Spotify volume up" desc="Increase volume by 10%." />
        <CommandRow phrase="Spotify volume down" desc="Decrease volume by 10%." />
        <CommandRow phrase="Mute Spotify" desc="Set Spotify volume to 0 (stores level for unmute)." />
        <CommandRow phrase="Unmute Spotify" desc="Restore volume to level before mute (or 70%)." />
        <CommandRow phrase="Create a playlist called [name]" desc="Create a new playlist." />
        <CommandRow phrase="Add this song to my [name] playlist" desc="Add current track to a playlist." />
        <CommandRow phrase="Delete playlist [name]" desc="Unfollow/delete a playlist." />
        <CommandRow phrase="Recommend songs like [X] / Find [genre] music" desc="Play recommendations from song/artist/genre." />
        <CommandRow phrase="Play music for [N] minutes/hours then stop" desc="Timed playback; stops after the time." />
        <CommandRow phrase="Add to queue / Add [song] to queue" desc="Add current or searched track to queue." />
      </div>

      <h3 className="commands-subtitle">Not yet supported</h3>
      <div className="command-list">
        <CommandRow phrase="Play on [device name]" desc="Transfer playback to another device." badge="soon" />
        <CommandRow phrase="Save this album" desc="Add current album to your library." badge="soon" />
        <CommandRow phrase="Clear queue" desc="Not in Spotify Web API; could map to skip until end." badge="soon" />
      </div>
    </section>
  </Card>
);

interface SettingsTabProps {
  layoutMode: LayoutMode;
  setLayoutMode: (mode: LayoutMode) => void;
}

const str = (v: unknown): string => (v == null ? "" : String(v));
const num = (v: unknown, def: number): number => (typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? parseInt(v, 10) || def : def);
const bool = (v: unknown): boolean => v === true || v === "true" || v === 1;

const SettingsTab: React.FC<SettingsTabProps> = ({
  layoutMode,
  setLayoutMode,
}) => {
  const [settings, setSettings] = useState<Settings>({});
  const [mics, setMics] = useState<MicItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<string>("");

  useEffect(() => {
    api
      .getSettings()
      .then((s) => setSettings(s))
      .catch(() => setSettings({}))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api.getMics().then((r) => setMics(r.mics || [])).catch(() => setMics([]));
  }, []);

  const update = (key: string, value: string | number | boolean) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaveStatus("Saving…");
    try {
      const toSave: Settings = {
        ...settings,
        theme: str(settings.theme) || "Dark",
        spotify_client_id: str(settings.spotify_client_id),
        spotify_client_secret: str(settings.spotify_client_secret),
        spotify_redirect_uri: str(settings.spotify_redirect_uri) || "http://localhost:8080",
        asana_token: str(settings.asana_token),
        openai_api_key: str(settings.openai_api_key),
        xai_api_key: str(settings.xai_api_key),
        ai_choice: str(settings.ai_choice) || "ChatGPT",
        nlp_choice: str(settings.nlp_choice) || "Transformers",
        macro_key: str(settings.macro_key) || "F24",
        macro_key_hold: bool(settings.macro_key_hold),
        reset_macro_key: str(settings.reset_macro_key) || "Ctrl+Alt+R",
        firefox_path: str(settings.firefox_path),
        geckodriver_path: str(settings.geckodriver_path),
        firefox_executable_path: str(settings.firefox_executable_path),
        screenshot_dir: str(settings.screenshot_dir),
        training_mode: bool(settings.training_mode),
        system_refresh_interval: num(settings.system_refresh_interval, 5000),
        monitor_weather_statements: bool(settings.monitor_weather_statements),
        weather_check_interval: num(settings.weather_check_interval, 60),
        microphone_index: num(settings.microphone_index, 0),
      };
      if (Array.isArray(settings.weather_monitor_locations)) {
        toSave.weather_monitor_locations = settings.weather_monitor_locations;
      } else {
        toSave.weather_monitor_locations = [];
      }
      await api.saveSettings(toSave);
      setSaveStatus("Saved.");
      setTimeout(() => setSaveStatus(""), 2000);
    } catch (e) {
      setSaveStatus(`Save failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  if (loading) {
    return (
      <Card title="Settings" subtitle="Loading…">
        <p className="muted">Loading settings…</p>
      </Card>
    );
  }

  return (
    <Card title="Settings" subtitle="Spotify, AI, paths, and layout. Changes apply after Save.">
      <div className="settings-section">
        <h3 className="settings-heading">Microphone</h3>
        <div className="settings-row">
          <label className="settings-label">Default microphone</label>
          <select
            className="settings-input"
            value={num(settings.microphone_index, 0)}
            onChange={(e) => update("microphone_index", parseInt(e.target.value, 10) || 0)}
            title="Microphone used for Listen and voice commands"
          >
            {mics.length === 0 ? (
              <option value={0}>Loading…</option>
            ) : (
              mics.map((m) => (
                <option key={m.index} value={m.index}>
                  {m.name || `Device ${m.index}`}
                </option>
              ))
            )}
          </select>
        </div>

        <h3 className="settings-heading">Layout</h3>
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

        <h3 className="settings-heading">Theme</h3>
        <div className="settings-row">
          <label className="settings-label">Theme</label>
          <select
            className="settings-input"
            value={str(settings.theme)}
            onChange={(e) => update("theme", e.target.value)}
          >
            <option value="Dark">Dark</option>
            <option value="Nord Dark">Nord Dark</option>
            <option value="High Contrast Dark">High Contrast Dark</option>
          </select>
        </div>

        <h3 className="settings-heading">Spotify (for “play song” etc.)</h3>
        <div className="settings-row">
          <label className="settings-label">Client ID</label>
          <input
            type="text"
            className="settings-input"
            placeholder="Spotify app Client ID"
            value={str(settings.spotify_client_id)}
            onChange={(e) => update("spotify_client_id", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <label className="settings-label">Client Secret</label>
          <input
            type="password"
            className="settings-input"
            placeholder="Spotify app Client Secret"
            value={str(settings.spotify_client_secret)}
            onChange={(e) => update("spotify_client_secret", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <label className="settings-label">Redirect URI</label>
          <input
            type="text"
            className="settings-input"
            placeholder="http://localhost:8080"
            value={str(settings.spotify_redirect_uri)}
            onChange={(e) => update("spotify_redirect_uri", e.target.value)}
          />
        </div>

        <h3 className="settings-heading">AI (Chat tab)</h3>
        <div className="settings-row">
          <label className="settings-label">AI provider</label>
          <select
            className="settings-input"
            value={str(settings.ai_choice)}
            onChange={(e) => update("ai_choice", e.target.value)}
          >
            <option value="ChatGPT">ChatGPT</option>
            <option value="Grok">Grok</option>
            <option value="Cursor CLI">Cursor CLI</option>
            <option value="Compare Both">Compare Both</option>
          </select>
        </div>
        <div className="settings-row">
          <label className="settings-label">OpenAI API key</label>
          <input
            type="password"
            className="settings-input"
            placeholder="For ChatGPT"
            value={str(settings.openai_api_key)}
            onChange={(e) => update("openai_api_key", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <label className="settings-label">xAI API key (Grok)</label>
          <input
            type="password"
            className="settings-input"
            placeholder="For Grok"
            value={str(settings.xai_api_key)}
            onChange={(e) => update("xai_api_key", e.target.value)}
          />
        </div>

        <h3 className="settings-heading">Voice &amp; macros</h3>
        <div className="settings-row">
          <label className="settings-label">NLP for commands</label>
          <select
            className="settings-input"
            value={str(settings.nlp_choice)}
            onChange={(e) => update("nlp_choice", e.target.value)}
          >
            <option value="Transformers">Transformers</option>
            <option value="Spacy">Spacy</option>
          </select>
        </div>
        <div className="settings-row">
          <label className="settings-label">Listen macro key</label>
          <input
            type="text"
            className="settings-input"
            placeholder="e.g. F24"
            value={str(settings.macro_key)}
            onChange={(e) => update("macro_key", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <label className="settings-label">Reset macro key</label>
          <input
            type="text"
            className="settings-input"
            placeholder="e.g. Ctrl+Alt+R"
            value={str(settings.reset_macro_key)}
            onChange={(e) => update("reset_macro_key", e.target.value)}
          />
        </div>
        <div className="settings-row settings-row-check">
          <label>
            <input
              type="checkbox"
              checked={bool(settings.macro_key_hold)}
              onChange={(e) => update("macro_key_hold", e.target.checked)}
            />
            Hold macro key to listen
          </label>
        </div>
        <div className="settings-row settings-row-check">
          <label>
            <input
              type="checkbox"
              checked={bool(settings.training_mode)}
              onChange={(e) => update("training_mode", e.target.checked)}
            />
            Training mode (confirm voice interpretations)
          </label>
        </div>

        <h3 className="settings-heading">Paths</h3>
        <div className="settings-row">
          <label className="settings-label">Firefox executable</label>
          <input
            type="text"
            className="settings-input"
            placeholder="C:\...\firefox.exe"
            value={str(settings.firefox_path)}
            onChange={(e) => update("firefox_path", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <label className="settings-label">GeckoDriver path</label>
          <input
            type="text"
            className="settings-input"
            placeholder="Path to geckodriver.exe"
            value={str(settings.geckodriver_path)}
            onChange={(e) => update("geckodriver_path", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <label className="settings-label">Screenshot folder</label>
          <input
            type="text"
            className="settings-input"
            placeholder="Leave empty for default"
            value={str(settings.screenshot_dir)}
            onChange={(e) => update("screenshot_dir", e.target.value)}
          />
        </div>

        <h3 className="settings-heading">Other</h3>
        <div className="settings-row">
          <label className="settings-label">Asana token</label>
          <input
            type="password"
            className="settings-input"
            placeholder="Optional"
            value={str(settings.asana_token)}
            onChange={(e) => update("asana_token", e.target.value)}
          />
        </div>
        <div className="settings-row">
          <label className="settings-label">System refresh (ms)</label>
          <input
            type="number"
            className="settings-input"
            min={1000}
            step={1000}
            value={num(settings.system_refresh_interval, 5000)}
            onChange={(e) => update("system_refresh_interval", parseInt(e.target.value, 10) || 5000)}
          />
        </div>
        <div className="settings-row settings-row-check">
          <label>
            <input
              type="checkbox"
              checked={bool(settings.monitor_weather_statements)}
              onChange={(e) => update("monitor_weather_statements", e.target.checked)}
            />
            Monitor NWS weather statements
          </label>
        </div>
        <div className="settings-row">
          <label className="settings-label">Weather check interval (s)</label>
          <input
            type="number"
            className="settings-input"
            min={30}
            value={num(settings.weather_check_interval, 60)}
            onChange={(e) => update("weather_check_interval", parseInt(e.target.value, 10) || 60)}
          />
        </div>

        <div className="settings-row" style={{ marginTop: "16px" }}>
          <button className="btn primary" onClick={handleSave}>
            Save settings
          </button>
          {saveStatus && <span className="muted" style={{ marginLeft: "12px" }}>{saveStatus}</span>}
        </div>
      </div>
    </Card>
  );
};

export default App;
