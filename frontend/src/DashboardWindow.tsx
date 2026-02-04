import React, { useState, useEffect, useCallback } from "react";
import { api } from "./utils/api";
import { loadThemeState, getEffectiveColors, applyTheme } from "./theme";

const DASHBOARD_OPACITY_KEY = "fupo_dashboard_opacity";
const DASHBOARD_SCALE_KEY = "fupo_dashboard_scale";

function loadOpacity(): number {
  try {
    const raw = localStorage.getItem(DASHBOARD_OPACITY_KEY);
    if (raw == null) return 1;
    const n = parseFloat(raw);
    return Number.isFinite(n) && n >= 0 && n <= 1 ? n : 1;
  } catch {
    return 1;
  }
}

function loadScale(): number {
  try {
    const raw = localStorage.getItem(DASHBOARD_SCALE_KEY);
    if (raw == null) return 1;
    const n = parseFloat(raw);
    return Number.isFinite(n) && n >= 0.5 && n <= 1 ? n : 1;
  } catch {
    return 1;
  }
}

// Purple outline icons (stroke only), 20x20 viewBox
const Icons = {
  mic: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  ),
  speaker: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  ),
  music: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </svg>
  ),
  minus: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  chevronDown: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  chevronUp: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="18 15 12 9 6 15" />
    </svg>
  ),
  close: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
};

function Sep() {
  return <span className="dashboard-bar-sep" aria-hidden />;
}

function speakStatus(text: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

export const DashboardWindow: React.FC = () => {
  const [status, setStatus] = useState<string>("Ready.");
  const [listening, setListening] = useState(false);
  const [duckingEnabled, setDuckingEnabled] = useState(false);
  const [duckingAvailable, setDuckingAvailable] = useState<boolean | null>(null);
  const [spotifyDuckingEnabled, setSpotifyDuckingEnabled] = useState(false);
  const [spotifyDuckingAvailable, setSpotifyDuckingAvailable] = useState<boolean | null>(null);
  const [opacity, setOpacityState] = useState(loadOpacity);
  const [scale, setScaleState] = useState(loadScale);
  const [statusExpanded, setStatusExpanded] = useState(false);

  useEffect(() => {
    const themeState = loadThemeState();
    applyTheme(getEffectiveColors(themeState));
  }, []);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === DASHBOARD_OPACITY_KEY && e.newValue != null) {
        const n = parseFloat(e.newValue);
        if (Number.isFinite(n) && n >= 0 && n <= 1) setOpacityState(n);
      }
      if (e.key === DASHBOARD_SCALE_KEY && e.newValue != null) {
        const n = parseFloat(e.newValue);
        if (Number.isFinite(n) && n >= 0.5 && n <= 1) setScaleState(n);
      }
      if (e.key === "fupo_theme" || e.key === "fupo_theme_presets") {
        const themeState = loadThemeState();
        applyTheme(getEffectiveColors(themeState));
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    try {
      void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
        const w = getCurrentWindow();
        w.setBackgroundColor({ r: 0, g: 0, b: 0, a: 0 }).catch(() => {});
      });
    } catch {
      // not in Tauri
    }
  }, []);

  useEffect(() => {
    api
      .getDucking()
      .then((r) => {
        setDuckingEnabled(r.enabled ?? false);
        setDuckingAvailable(r.available ?? true);
        setSpotifyDuckingEnabled(r.spotify_enabled ?? false);
        setSpotifyDuckingAvailable(r.spotify_available ?? false);
      })
      .catch(() => {
        setDuckingAvailable(false);
        setSpotifyDuckingAvailable(false);
      });
  }, []);

  const handleListen = useCallback(() => {
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: new () => SpeechRecognition }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognition }).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus("Voice input not supported.");
      return;
    }
    setListening(true);
    setStatus("Listening…");
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[event.resultIndex][0].transcript.trim();
      if (!transcript) {
        setStatus("No speech detected.");
        setListening(false);
        return;
      }
      setStatus(`Heard: "${transcript}". Processing…`);
      api
        .command(transcript)
        .then((r) => {
          const res = r as { display?: string; spoken?: string };
          const msg = res.display || res.spoken || "Done.";
          setStatus(msg);
          api.getSettings().then((s) => {
            if (s && (s.read_status_after_command === true || s.read_status_after_command === "true")) {
              speakStatus(msg);
            }
          }).catch(() => {});
        })
        .catch((e) => {
          const msg = `Failed: ${e instanceof Error ? e.message : String(e)}`;
          setStatus(msg);
          api.getSettings().then((s) => {
            if (s && (s.read_status_after_command === true || s.read_status_after_command === "true")) {
              speakStatus(msg);
            }
          }).catch(() => {});
        })
        .finally(() => setListening(false));
    };
    recognition.onerror = () => {
      setStatus("Listening error.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    try {
      recognition.start();
    } catch {
      setStatus("Could not start listening.");
      setListening(false);
    }
  }, []);

  const handleToggleDucking = useCallback(async () => {
    try {
      const r = await api.setDucking(!duckingEnabled);
      setDuckingEnabled(r.enabled);
      setStatus(r.message);
    } catch (e) {
      setStatus(`Audio ducking: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [duckingEnabled]);

  const handleToggleSpotifyDucking = useCallback(async () => {
    try {
      const r = await api.setSpotifyDucking(!spotifyDuckingEnabled);
      setSpotifyDuckingEnabled(r.enabled);
      setStatus(r.message);
    } catch (e) {
      setStatus(`Spotify ducking: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [spotifyDuckingEnabled]);

  const handleMinimize = useCallback(() => {
    try {
      void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
        getCurrentWindow().minimize().catch(() => {});
      });
    } catch {
      // not in Tauri
    }
  }, []);

  const handleClose = useCallback(() => {
    try {
      void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
        getCurrentWindow().close().catch(() => {});
      });
    } catch {
      // not in Tauri
    }
  }, []);

  const toggleStatusExpanded = useCallback(() => {
    setStatusExpanded((prev) => !prev);
  }, []);

  useEffect(() => {
    let cancelled = false;
    import("@tauri-apps/api/window")
      .then(({ getCurrentWindow, LogicalSize }) => {
        if (cancelled) return;
        const w = getCurrentWindow();
        const PILL_WIDTH = 560;
        const PILL_HEIGHT_COLLAPSED = 52;
        const PILL_HEIGHT_EXPANDED = 132;
        const WRAP_PADDING_H = 28;
        const ww = Math.round(PILL_WIDTH * scale) + WRAP_PADDING_H;
        const hh = Math.round((statusExpanded ? PILL_HEIGHT_EXPANDED : PILL_HEIGHT_COLLAPSED) * scale);
        return w.setSize(new LogicalSize(ww, hh));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [scale, statusExpanded]);

  return (
    <div className="dashboard-bar-wrap" style={{ ["--pill-opacity" as string]: opacity }}>
      <div
        className="dashboard-bar-scaled"
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "left center",
        }}
      >
        <div className={`dashboard-bar-layout ${statusExpanded ? "status-expanded" : ""}`}>
          <div className="dashboard-bar" data-tauri-drag-region title="Drag to move">
            <div className="dashboard-bar-drag">
              <span className="dashboard-bar-logo">Fupo</span>
            </div>
            <Sep />
            <div className="dashboard-bar-actions">
              <button
                type="button"
                className={`dashboard-bar-btn ${listening ? "active listening" : ""}`}
                onClick={handleListen}
                disabled={listening}
                title="Listen"
                aria-label="Listen"
              >
                <span className="dashboard-bar-icon">{Icons.mic}</span>
              </button>
              <button
                type="button"
                className={`dashboard-bar-btn ${duckingEnabled ? "active" : ""}`}
                onClick={handleToggleDucking}
                disabled={duckingAvailable === false}
                title={duckingEnabled ? "Disable Audio Ducking" : "Enable Audio Ducking"}
                aria-label={duckingEnabled ? "Disable Audio Ducking" : "Enable Audio Ducking"}
              >
                <span className="dashboard-bar-icon">{Icons.speaker}</span>
              </button>
              <button
                type="button"
                className={`dashboard-bar-btn ${spotifyDuckingEnabled ? "active" : ""}`}
                onClick={handleToggleSpotifyDucking}
                disabled={spotifyDuckingAvailable === false}
                title={spotifyDuckingEnabled ? "Disable Spotify Ducking" : "Enable Spotify Ducking"}
                aria-label={spotifyDuckingEnabled ? "Disable Spotify Ducking" : "Enable Spotify Ducking"}
              >
                <span className="dashboard-bar-icon">{Icons.music}</span>
              </button>
            </div>
            <Sep />
            <div className="dashboard-bar-status" title={status}>
              <span className="dashboard-bar-status-text">{status}</span>
              <button
                type="button"
                className="dashboard-bar-status-toggle"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  toggleStatusExpanded();
                }}
                onPointerDown={(e) => e.stopPropagation()}
                title={statusExpanded ? "Collapse status" : "Expand status (full width)"}
                aria-label={statusExpanded ? "Collapse status" : "Expand status"}
                aria-expanded={statusExpanded}
              >
                <span className="dashboard-bar-icon">{statusExpanded ? Icons.chevronUp : Icons.chevronDown}</span>
              </button>
            </div>
            <Sep />
            <div className="dashboard-bar-window-actions">
          <button
            type="button"
            className="dashboard-bar-btn dashboard-bar-btn-ghost"
            onClick={handleMinimize}
            title="Minimize"
            aria-label="Minimize"
          >
            <span className="dashboard-bar-icon">{Icons.minus}</span>
          </button>
          <button
            type="button"
            className="dashboard-bar-btn dashboard-bar-btn-close"
            onClick={handleClose}
            title="Close"
            aria-label="Close"
          >
            <span className="dashboard-bar-icon">{Icons.close}</span>
          </button>
        </div>
        </div>
        {statusExpanded && (
          <div
            className="dashboard-bar-status-expanded"
            onClick={(e) => e.stopPropagation()}
            role="region"
            aria-label="Status (expanded)"
          >
            <span className="dashboard-bar-status-expanded-text">{status}</span>
          </div>
        )}
      </div>
      </div>
    </div>
  );
};
