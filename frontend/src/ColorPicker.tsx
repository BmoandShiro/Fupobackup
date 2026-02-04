import React, { useState, useEffect, useRef, useCallback } from "react";

/** Parse #RRGGBB to { r, g, b } (0-255). */
function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const m = hex.match(/^#?([0-9a-fA-F]{6})$/);
  if (!m) return { r: 153, g: 85, b: 247 };
  const n = parseInt(m[1], 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

function rgbToHex(r: number, g: number, b: number): string {
  return "#" + [r, g, b].map((x) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, "0")).join("");
}

function rgbToHsv(r: number, g: number, b: number): { h: number; s: number; v: number } {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const d = max - min;
  const v = max;
  const s = max === 0 ? 0 : d / max;
  let h = 0;
  if (d !== 0) {
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
    else if (max === g) h = ((b - r) / d + 2) / 6;
    else h = ((r - g) / d + 4) / 6;
  }
  return { h: h * 360, s: s * 100, v: v * 100 };
}

function hsvToRgb(h: number, s: number, v: number): { r: number; g: number; b: number } {
  h = (h % 360) / 60; s /= 100; v /= 100;
  const c = v * s, x = c * (1 - Math.abs((h % 2) - 1)), m = v - c;
  let r = 0, g = 0, b = 0;
  if (h < 1) { r = c; g = x; }
  else if (h < 2) { r = x; g = c; }
  else if (h < 3) { g = c; b = x; }
  else if (h < 4) { g = x; b = c; }
  else if (h < 5) { r = x; b = c; }
  else { r = c; b = x; }
  return { r: (r + m) * 255, g: (g + m) * 255, b: (b + m) * 255 };
}

const HUE_GRADIENT = "linear-gradient(to right, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000)";

export interface ColorPickerProps {
  value: string;
  onChange: (hex: string) => void;
  onClose?: () => void;
  anchorRef?: React.RefObject<HTMLElement | null>;
}

export const ColorPicker: React.FC<ColorPickerProps> = ({ value, onChange, onClose, anchorRef }) => {
  const hex = value.match(/^#([0-9a-fA-F]{6})$/) ? value : "#a855f7";
  const rgb = hexToRgb(hex);
  const hsv = rgbToHsv(rgb.r, rgb.g, rgb.b);
  const [h, setH] = useState(hsv.h);
  const [s, setS] = useState(hsv.s);
  const [v, setV] = useState(hsv.v);
  const [r, setR] = useState(rgb.r);
  const [g, setG] = useState(rgb.g);
  const [b, setB] = useState(rgb.b);
  const [eyedropperAvailable, setEyedropperAvailable] = useState(false);
  const squareRef = useRef<HTMLDivElement>(null);
  const hueRef = useRef<HTMLDivElement>(null);
  const hRef = useRef(h);
  const sRef = useRef(s);
  const vRef = useRef(v);
  hRef.current = h;
  sRef.current = s;
  vRef.current = v;

  useEffect(() => {
    setEyedropperAvailable(typeof (window as unknown as { EyeDropper?: unknown }).EyeDropper === "function");
  }, []);

  const syncFromHex = useCallback((newHex: string) => {
    const parsed = hexToRgb(newHex);
    const { h: nh, s: ns, v: nv } = rgbToHsv(parsed.r, parsed.g, parsed.b);
    setH(nh); setS(ns); setV(nv);
    setR(parsed.r); setG(parsed.g); setB(parsed.b);
  }, []);

  useEffect(() => {
    const currentHex = rgbToHex(r, g, b);
    if (currentHex.toLowerCase() !== hex.toLowerCase()) syncFromHex(hex);
  }, [hex]);

  const commit = useCallback((newR: number, newG: number, newB: number) => {
    const newHex = rgbToHex(newR, newG, newB);
    setR(newR); setG(newG); setB(newB);
    const { h: nh, s: ns, v: nv } = rgbToHsv(newR, newG, newB);
    setH(nh); setS(ns); setV(nv);
    onChange(newHex);
  }, [onChange]);

  const addSquareDrag = useCallback(() => {
    const onMove = (e: MouseEvent) => {
      const el = squareRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
      const newS = x * 100;
      const newV = (1 - y) * 100;
      setS(newS); setV(newV);
      const { r: nr, g: ng, b: nb } = hsvToRgb(hRef.current, newS, newV);
      commit(nr, ng, nb);
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [commit]);

  const addHueDrag = useCallback(() => {
    const onMove = (e: MouseEvent) => {
      const el = hueRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const newH = x * 360;
      setH(newH);
      const { r: nr, g: ng, b: nb } = hsvToRgb(newH, sRef.current, vRef.current);
      commit(nr, ng, nb);
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [commit]);

  const currentHex = rgbToHex(r, g, b);
  const hueColor = `hsl(${h}, 100%, 50%)`;

  const openEyedropper = async () => {
    try {
      const EyeDropper = (window as unknown as { EyeDropper: new () => { open: () => Promise<{ sRGBHex: string }> } }).EyeDropper;
      const picker = new EyeDropper();
      const result = await picker.open();
      if (result?.sRGBHex) {
        syncFromHex(result.sRGBHex);
        onChange(result.sRGBHex);
      }
    } catch {
      // user cancelled or API not supported
    }
  };

  return (
    <div className="color-picker-popover" role="dialog" aria-label="Color picker">
      <div className="color-picker-row">
        <div
          ref={squareRef}
          className="color-picker-square"
          style={{ background: `linear-gradient(to top, #000, transparent), linear-gradient(to right, transparent, ${hueColor}), #fff` }}
          onMouseDown={(e) => {
            e.preventDefault();
            const el = squareRef.current;
            if (el) {
              const rect = el.getBoundingClientRect();
              const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
              const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
              const newS = x * 100;
              const newV = (1 - y) * 100;
              setS(newS); setV(newV);
              const { r: nr, g: ng, b: nb } = hsvToRgb(h, newS, newV);
              commit(nr, ng, nb);
            }
            addSquareDrag();
          }}
        >
          <div
            className="color-picker-handle"
            style={{ left: `${s}%`, top: `${100 - v}%`, background: currentHex }}
          />
        </div>
        <div className="color-picker-right">
          <div className="color-picker-preview-row">
            {eyedropperAvailable && (
              <button type="button" className="color-picker-eyedropper" onClick={openEyedropper} title="Pick color from screen" aria-label="Eyedropper">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 22c1.25-.987 2.5-1.975 3.5-2.5 1-.525 2.5-.5 3.5.5 1 1 2 2.5 2 3.5 0 1-1 2-2 2-1.5 0-2.5-.5-3.5-1.5-1-1-1.5-2.5-1.5-4 0-1 .5-2 1.5-2.5 1-.5 2.5 0 3.5 1 1 1 1.5 2.5 1.5 3.5 0 0-.5 1.5-1.5 2.5-1 1-2.5 1.5-4 1.5" /></svg>
              </button>
            )}
            <div className="color-picker-swatch" style={{ background: currentHex }} />
          </div>
          <div
            ref={hueRef}
            className="color-picker-hue-bar"
            style={{ background: HUE_GRADIENT }}
            onMouseDown={(e) => {
              e.preventDefault();
              const el = hueRef.current;
              if (el) {
                const rect = el.getBoundingClientRect();
                const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                const newH = x * 360;
                setH(newH);
                const { r: nr, g: ng, b: nb } = hsvToRgb(newH, s, v);
                commit(nr, ng, nb);
              }
              addHueDrag();
            }}
          >
            <div className="color-picker-handle hue-handle" style={{ left: `${(h / 360) * 100}%`, background: hueColor }} />
          </div>
        </div>
      </div>
      <div className="color-picker-rgb-row">
        <label className="color-picker-rgb-label">R</label>
        <input
          type="number"
          className="color-picker-rgb-input"
          min={0}
          max={255}
          value={Math.round(r)}
          onChange={(e) => {
            const nr = Math.max(0, Math.min(255, parseInt(e.target.value, 10) || 0));
            setR(nr);
            const { g: ng, b: nb } = hsvToRgb(h, s, v);
            commit(nr, ng, nb);
          }}
        />
        <label className="color-picker-rgb-label">G</label>
        <input
          type="number"
          className="color-picker-rgb-input"
          min={0}
          max={255}
          value={Math.round(g)}
          onChange={(e) => {
            const ng = Math.max(0, Math.min(255, parseInt(e.target.value, 10) || 0));
            setG(ng);
            commit(r, ng, b);
          }}
        />
        <label className="color-picker-rgb-label">B</label>
        <input
          type="number"
          className="color-picker-rgb-input"
          min={0}
          max={255}
          value={Math.round(b)}
          onChange={(e) => {
            const nb = Math.max(0, Math.min(255, parseInt(e.target.value, 10) || 0));
            setB(nb);
            commit(r, g, nb);
          }}
        />
      </div>
      {onClose && (
        <button type="button" className="btn color-picker-close" onClick={onClose}>
          Done
        </button>
      )}
    </div>
  );
};
