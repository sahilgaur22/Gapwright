"use client";

import React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "./theme-provider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label="Toggle colour theme"
      className="p-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-main)] hover:bg-[var(--bg-surface-elevated)] hover:border-[var(--border-strong)] transition-all cursor-pointer"
    >
      {theme === "dark" ? (
        <Sun className="w-4 h-4 text-[var(--color-brand-yellow)]" />
      ) : (
        <Moon className="w-4 h-4 text-[var(--color-brand-navy)]" />
      )}
    </button>
  );
}
