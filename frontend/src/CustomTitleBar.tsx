import React, { useState, useEffect, useCallback } from "react";

const TITLE_BAR_HEIGHT = 36;

/** Use in App to know if we're in Tauri (so we can show custom title bar and adjust layout). */
export function useIsTauri(): boolean {
  const [isTauri, setIsTauri] = useState(false);
  useEffect(() => {
    void import("@tauri-apps/api/window")
      .then(({ getCurrentWindow }) => getCurrentWindow())
      .then(() => setIsTauri(true))
      .catch(() => {});
  }, []);
  return isTauri;
}

const Icons = {
  minimize: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  maximize: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
    </svg>
  ),
  restore: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 4H5a2 2 0 0 0-2 2v3" />
      <path d="M16 20h3a2 2 0 0 0 2-2v-3" />
      <path d="M4 16v3a2 2 0 0 0 2 2h3" />
      <path d="M20 8V5a2 2 0 0 0-2-2h-3" />
    </svg>
  ),
  close: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
};

interface CustomTitleBarProps {
  /** Optional content in the center (e.g. nav tabs for top layout). */
  children?: React.ReactNode;
  /** Height in px. Default 36. */
  height?: number;
}

export const CustomTitleBar: React.FC<CustomTitleBarProps> = ({ children, height = TITLE_BAR_HEIGHT }) => {
  const [isTauri, setIsTauri] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void import("@tauri-apps/api/window")
      .then(({ getCurrentWindow }) => getCurrentWindow())
      .then((win) => {
        if (cancelled) return;
        setIsTauri(true);
        return win.isMaximized().then((max) => {
          if (!cancelled) setIsMaximized(max);
        });
      })
      .catch(() => {});
    const unlisten = (async () => {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        const w = getCurrentWindow();
        return await w.onResized(() => {
          if (cancelled) return;
          w.isMaximized().then((max) => {
            if (!cancelled) setIsMaximized(max);
          }).catch(() => {});
        });
      } catch {
        return () => {};
      }
    })();
    return () => {
      cancelled = true;
      unlisten.then((fn) => fn());
    };
  }, []);

  const handleMinimize = useCallback(() => {
    void import("@tauri-apps/api/window").then(({ getCurrentWindow }) =>
      getCurrentWindow().minimize().catch(() => {})
    );
  }, []);

  const handleToggleMaximize = useCallback(() => {
    void import("@tauri-apps/api/window").then(({ getCurrentWindow }) =>
      getCurrentWindow().toggleMaximize().catch(() => {})
    );
    setIsMaximized((prev) => !prev);
  }, []);

  const handleClose = useCallback(() => {
    void import("@tauri-apps/api/window").then(({ getCurrentWindow }) =>
      getCurrentWindow().close().catch(() => {})
    );
  }, []);

  if (!isTauri) return null;

  return (
    <header
      className="custom-title-bar"
      data-tauri-drag-region
      style={{ height: `${height}px`, minHeight: `${height}px` }}
    >
      <div className="custom-title-bar-drag">
        <span className="custom-title-bar-logo">Fupo</span>
      </div>
      {children != null ? (
        <div className="custom-title-bar-center">{children}</div>
      ) : (
        <div className="custom-title-bar-spacer" data-tauri-drag-region />
      )}
      <div className="custom-title-bar-controls">
        <button
          type="button"
          className="custom-title-bar-btn"
          onClick={handleMinimize}
          title="Minimize"
          aria-label="Minimize"
        >
          <span className="custom-title-bar-icon">{Icons.minimize}</span>
        </button>
        <button
          type="button"
          className="custom-title-bar-btn"
          onClick={handleToggleMaximize}
          title={isMaximized ? "Restore" : "Maximize"}
          aria-label={isMaximized ? "Restore" : "Maximize"}
        >
          <span className="custom-title-bar-icon">{isMaximized ? Icons.restore : Icons.maximize}</span>
        </button>
        <button
          type="button"
          className="custom-title-bar-btn custom-title-bar-btn-close"
          onClick={handleClose}
          title="Close"
          aria-label="Close"
        >
          <span className="custom-title-bar-icon">{Icons.close}</span>
        </button>
      </div>
    </header>
  );
};

export const TITLE_BAR_HEIGHT_PX = TITLE_BAR_HEIGHT;
