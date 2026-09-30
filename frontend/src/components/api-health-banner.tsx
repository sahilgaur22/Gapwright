"use client";

import React, { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

export function ApiHealthBanner() {
  const [isWaking, setIsWaking] = useState(false);
  const [isHealthy, setIsHealthy] = useState(true);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;

    const checkServer = async () => {
      try {
        await api.checkHealth();
        setIsHealthy(true);
        setIsWaking(false);
      } catch {
        setIsHealthy(false);
        setIsWaking(true);
        setAttempts((prev) => prev + 1);
        timer = setTimeout(checkServer, 5000);
      }
    };

    checkServer();
    return () => clearTimeout(timer);
  }, []);

  if (isHealthy && !isWaking) {
    return null;
  }

  return (
    <aside
      aria-label="Server status alert"
      className="bg-[var(--color-status-warning-bg)] border-b border-[var(--color-status-warning)] text-[var(--color-brand-navy)] dark:text-[var(--text-main)] px-4 py-2 text-xs md:text-sm"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {isWaking ? (
            <RefreshCw className="w-4 h-4 animate-spin text-[var(--color-brand-yellow)]" />
          ) : (
            <AlertCircle className="w-4 h-4 text-[var(--color-status-warning)]" />
          )}
          <span>
            <strong>Server spinning up:</strong> Gapwright backend service is waking up
            from idle sleep. Requests may take up to a minute to respond (attempt {attempts}).
          </span>
        </div>
        <button
          onClick={async () => {
            try {
              await api.checkHealth();
              setIsHealthy(true);
              setIsWaking(false);
            } catch {
              // Still sleeping
            }
          }}
          className="text-xs px-2.5 py-1 rounded bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] font-medium transition cursor-pointer"
        >
          Check now
        </button>
      </div>
    </aside>
  );
}
