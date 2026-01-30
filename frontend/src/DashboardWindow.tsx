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
        // setOpacity not available in this Tauri version; use background color with alpha
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

  return (
    <div className="dashboard-window">
      <div className="dashboard-window-drag" data-tauri-drag-region>
        Fupo Dashboard
      </div>
      <div className="dashboard-window-controls">
        <button
          className="btn primary dashboard-btn"
          onClick={handleListen}
          disabled={listening}
        >
          {listening ? "Listening…" : "Listen"}
        </button>
        <button
          className="btn dashboard-btn"
          onClick={handleToggleDucking}
          disabled={duckingAvailable === false}
          style={duckingEnabled ? { borderColor: "var(--theme-accent)", background: "rgba(168,85,247,0.15)" } : undefined}
        >
          {duckingEnabled ? "Disable Audio Ducking" : "Enable Audio Ducking"}
        </button>
        <button
          className="btn dashboard-btn"
          onClick={handleToggleSpotifyDucking}
          disabled={spotifyDuckingAvailable === false}
          style={spotifyDuckingEnabled ? { borderColor: "var(--theme-accent)", background: "rgba(168,85,247,0.15)" } : undefined}
        >
          {spotifyDuckingEnabled ? "Disable Spotify Ducking" : "Enable Spotify Ducking"}
        </button>
      </div>
      <div className="dashboard-window-status">
        <div className="dashboard-window-status-label">Status</div>
        <div className="dashboard-window-status-text">{status}</div>
      </div>
      <div className="dashboard-window-opacity">
        <label className="dashboard-window-opacity-label">Opacity</label>
        <input
          type="range"
          className="dashboard-window-opacity-slider"
          min={0.2}
          max={1}
          step={0.05}
          value={opacity}
          onChange={(e) => setOpacityState(parseFloat(e.target.value))}
        />
        <span className="dashboard-window-opacity-value">{Math.round(opacity * 100)}%</span>
      </div>
    </div>
  );
};
