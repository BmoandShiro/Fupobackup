import React, { useState, useEffect, useCallback } from "react";
import { api } from "./utils/api";

const DASHBOARD_OPACITY_KEY = "fupo_dashboard_opacity";

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

function saveOpacity(value: number) {
  try {
    localStorage.setItem(DASHBOARD_OPACITY_KEY, String(value));
  } catch {
    // ignore
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

export const DashboardWindow: React.FC = () => {
  const [status, setStatus] = useState<string>("Ready.");
  const [listening, setListening] = useState(false);
  const [duckingEnabled, setDuckingEnabled] = useState(false);
  const [duckingAvailable, setDuckingAvailable] = useState<boolean | null>(null);
  const [spotifyDuckingEnabled, setSpotifyDuckingEnabled] = useState(false);
  const [spotifyDuckingAvailable, setSpotifyDuckingAvailable] = useState<boolean | null>(null);
  const [opacity, setOpacityState] = useState(loadOpacity);

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

  useEffect(() => {
    saveOpacity(opacity);
    try {
      void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
        const w = getCurrentWindow();
        w.setBackgroundColor({
          r: 15,
          g: 15,
          b: 20,
          a: opacity,
        }).catch(() => {});
      });
    } catch {
      // not in Tauri
    }
  }, [opacity]);

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
          setStatus(res.display || res.spoken || "Done.");
        })
        .catch((e) => {
          setStatus(`Failed: ${e instanceof Error ? e.message : String(e)}`);
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

  return (
    <div className="dashboard-bar-wrap">
      <div className="dashboard-bar">
        <div className="dashboard-bar-drag" data-tauri-drag-region title="Drag to move">
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
        </div>
        <Sep />
        <div className="dashboard-bar-opacity">
          <input
            type="range"
            className="dashboard-bar-opacity-slider"
            min={0.2}
            max={1}
            step={0.05}
            value={opacity}
            onChange={(e) => setOpacityState(parseFloat(e.target.value))}
            title={`Opacity ${Math.round(opacity * 100)}%`}
            aria-label="Window opacity"
          />
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
    </div>
  );
};
