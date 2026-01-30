/**
 * Customizable theme: CSS variables + presets + save/load.
 * Keys map to --theme-{key} on :root.
 */
export type ThemeColorKey =
  | "bgApp"
  | "bgSidebar"
  | "bgPanel"
  | "textPrimary"
  | "textMuted"
  | "textHeading"
  | "accent"
  | "accentEnd"
  | "border"
  | "navHover"
  | "btnBg"
  | "inputBg"
  | "scrollbarTrack"
  | "scrollbarThumb"
  | "chatUser"
  | "chatAssistant"
  | "settingsHeading";

export type ThemeColors = Record<ThemeColorKey, string>;

export const THEME_COLOR_KEYS: ThemeColorKey[] = [
  "bgApp",
  "bgSidebar",
  "bgPanel",
  "textPrimary",
  "textMuted",
  "textHeading",
  "accent",
  "accentEnd",
  "border",
  "navHover",
  "btnBg",
  "inputBg",
  "scrollbarTrack",
  "scrollbarThumb",
  "chatUser",
  "chatAssistant",
  "settingsHeading",
];

/** Human-readable labels for color pickers (grouped in UI). */
export const THEME_COLOR_LABELS: Record<ThemeColorKey, string> = {
  bgApp: "App background",
  bgSidebar: "Sidebar / top bar",
  bgPanel: "Cards / panels",
  textPrimary: "Primary text",
  textMuted: "Muted text",
  textHeading: "Headings & labels",
  accent: "Accent (primary buttons, active tab)",
  accentEnd: "Accent gradient end",
  border: "Borders",
  navHover: "Nav item hover",
  btnBg: "Default button background",
  inputBg: "Inputs & fields",
  scrollbarTrack: "Scrollbar track",
  scrollbarThumb: "Scrollbar thumb",
  chatUser: "Chat – your message",
  chatAssistant: "Chat – assistant message",
  settingsHeading: "Settings section heading",
};

const DARK: ThemeColors = {
  bgApp: "#050505",
  bgSidebar: "rgba(15, 15, 18, 0.97)",
  bgPanel: "rgba(15, 15, 20, 0.96)",
  textPrimary: "#e5e7eb",
  textMuted: "#9ca3af",
  textHeading: "#d1d5db",
  accent: "#a855f7",
  accentEnd: "#6366f1",
  border: "#222222",
  navHover: "#1e1b4b",
  btnBg: "#111022",
  inputBg: "#0f0f12",
  scrollbarTrack: "#0f0f12",
  scrollbarThumb: "#333333",
  chatUser: "#7c3aed",
  chatAssistant: "#1e1b4b",
  settingsHeading: "#a855f7",
};

const NORD_DARK: ThemeColors = {
  bgApp: "#2e3440",
  bgSidebar: "rgba(59, 66, 82, 0.97)",
  bgPanel: "rgba(67, 76, 94, 0.96)",
  textPrimary: "#eceff4",
  textMuted: "#d8dee9",
  textHeading: "#e5e9f0",
  accent: "#88c0d0",
  accentEnd: "#81a1c1",
  border: "#4c566a",
  navHover: "#434c5e",
  btnBg: "#3b4252",
  inputBg: "#3b4252",
  scrollbarTrack: "#2e3440",
  scrollbarThumb: "#4c566a",
  chatUser: "#5e81ac",
  chatAssistant: "#434c5e",
  settingsHeading: "#88c0d0",
};

const HIGH_CONTRAST_DARK: ThemeColors = {
  bgApp: "#000000",
  bgSidebar: "#0a0a0a",
  bgPanel: "#111111",
  textPrimary: "#ffffff",
  textMuted: "#b0b0b0",
  textHeading: "#ffffff",
  accent: "#00d4ff",
  accentEnd: "#00ff88",
  border: "#333333",
  navHover: "#1a1a1a",
  btnBg: "#0d0d0d",
  inputBg: "#0a0a0a",
  scrollbarTrack: "#0a0a0a",
  scrollbarThumb: "#444444",
  chatUser: "#0066cc",
  chatAssistant: "#1a1a1a",
  settingsHeading: "#00d4ff",
};

export const BUILTIN_PRESETS: { name: string; colors: ThemeColors }[] = [
  { name: "Dark", colors: DARK },
  { name: "Nord Dark", colors: NORD_DARK },
  { name: "High Contrast Dark", colors: HIGH_CONTRAST_DARK },
];

const THEME_STORAGE_KEY = "fupo_theme";
const PRESETS_STORAGE_KEY = "fupo_theme_presets";

export interface ThemeState {
  activePresetName: string;
  customColors: ThemeColors | null;
  userPresets: { name: string; colors: ThemeColors }[];
}

function defaultThemeState(): ThemeState {
  return {
    activePresetName: "Dark",
    customColors: null,
    userPresets: [],
  };
}

export function loadThemeState(): ThemeState {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    if (!raw) return defaultThemeState();
    const parsed = JSON.parse(raw) as Partial<ThemeState>;
    const presetsRaw = localStorage.getItem(PRESETS_STORAGE_KEY);
    const userPresets = presetsRaw ? (JSON.parse(presetsRaw) as { name: string; colors: ThemeColors }[]) : [];
    return {
      activePresetName: typeof parsed.activePresetName === "string" ? parsed.activePresetName : "Dark",
      customColors: parsed.customColors && typeof parsed.customColors === "object" ? (parsed.customColors as ThemeColors) : null,
      userPresets: Array.isArray(userPresets) ? userPresets : [],
    };
  } catch {
    return defaultThemeState();
  }
}

export function saveThemeState(state: ThemeState): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify({
      activePresetName: state.activePresetName,
      customColors: state.customColors,
    }));
    localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(state.userPresets));
  } catch {
    // ignore
  }
}

export function getEffectiveColors(state: ThemeState): ThemeColors {
  if (state.activePresetName === "Custom" && state.customColors) return state.customColors;
  const builtin = BUILTIN_PRESETS.find((p) => p.name === state.activePresetName);
  if (builtin) return builtin.colors;
  const user = state.userPresets.find((p) => p.name === state.activePresetName);
  if (user) return user.colors;
  return DARK;
}

/** Convert camelCase to kebab-case so CSS vars match (e.g. accentEnd -> accent-end). */
function toCssVarName(key: string): string {
  return key.replace(/([A-Z])/g, (m) => `-${m.toLowerCase()}`);
}

export function applyTheme(colors: ThemeColors): void {
  const root = document.documentElement;
  THEME_COLOR_KEYS.forEach((key) => {
    const value = colors[key];
    if (value) root.style.setProperty(`--theme-${toCssVarName(key)}`, value);
  });
}

/** Convert theme value (hex or rgba) to #RRGGBB for use in type="color" input. */
export function toHexForPicker(val: string): string {
  const hexMatch = val.match(/^#([0-9a-fA-F]{6})$/);
  if (hexMatch) return val;
  const rgbMatch = val.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
  if (rgbMatch) {
    const r = Number(rgbMatch[1]).toString(16).padStart(2, "0");
    const g = Number(rgbMatch[2]).toString(16).padStart(2, "0");
    const b = Number(rgbMatch[3]).toString(16).padStart(2, "0");
    return `#${r}${g}${b}`;
  }
  return "#a855f7";
}
