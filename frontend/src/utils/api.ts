/**
 * API client for the Fupo FastAPI backend.
 * Ensure the backend is running: python -m uvicorn backend.api:app --reload
 */

const DEFAULT_BASE = "http://127.0.0.1:8000";

function getBase(): string {
  return (import.meta as unknown as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ?? DEFAULT_BASE;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${getBase()}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const j = JSON.parse(text);
      detail = j.detail ?? text;
    } catch {
      // use raw text
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
}

export interface ChatResponse {
  display: string;
  spoken: string;
}

export interface CommandResponse {
  display: string;
  spoken: string;
  /** When set, frontend should show an input and send follow_up_prefix + user input as next command */
  prompt_for?: string;
  follow_up_prefix?: string;
}

export interface MicItem {
  index: number;
  name: string;
}

export interface MicsResponse {
  mics: MicItem[];
  message: string;
}

export interface ShortcutsResponse {
  shortcuts: Record<string, string>;
  message: string;
}

export interface ScanStatusResponse {
  running: boolean;
  progress: number;
  message: string;
  error: string | null;
}

export interface ScanStartResponse {
  status: string;
  message: string;
}

export interface PathResponse {
  message: string;
  name: string;
}

export interface DuckingResponse {
  enabled: boolean;
  message: string;
}

/** Keys and types matching settings.json (strings, numbers, booleans, arrays). */
export type Settings = Record<string, string | number | boolean | string[]>;

export const api = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },

  chat(text: string): Promise<ChatResponse> {
    return request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  },

  command(text: string): Promise<CommandResponse> {
    return request<CommandResponse>("/api/command", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  },

  getMics(): Promise<MicsResponse> {
    return request<MicsResponse>("/api/mics");
  },

  getShortcuts(): Promise<ShortcutsResponse> {
    return request<ShortcutsResponse>("/api/shortcuts");
  },

  startScan(): Promise<ScanStartResponse> {
    return request<ScanStartResponse>("/api/scan", { method: "POST" });
  },

  getScanStatus(): Promise<ScanStatusResponse> {
    return request<ScanStatusResponse>("/api/scan/status");
  },

  addPath(path: string): Promise<PathResponse> {
    return request<PathResponse>("/api/path", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
  },

  setDucking(enabled: boolean): Promise<DuckingResponse> {
    return request<DuckingResponse>("/api/ducking", {
      method: "POST",
      body: JSON.stringify({ enabled }),
    });
  },

  getDucking(): Promise<{ enabled: boolean }> {
    return request<{ enabled: boolean }>("/api/ducking");
  },

  getSettings(): Promise<Settings> {
    return request<Settings>("/api/settings");
  },

  saveSettings(settings: Settings): Promise<Settings> {
    return request<Settings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
  },
};
