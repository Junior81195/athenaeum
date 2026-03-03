"use client";

import { useState, useEffect } from "react";
import { api, type Library } from "@/lib/api";

export default function LibrarySelector({
  selected,
  onChange,
}: {
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    api.libraries().then(setLibraries).catch(() => {});
  }, []);

  function toggleLib(id: number) {
    onChange(
      selected.includes(id)
        ? selected.filter((x) => x !== id)
        : [...selected, id]
    );
  }

  function selectAll() {
    onChange(libraries.map((l) => l.id));
  }

  function clearAll() {
    onChange([]);
  }

  if (libraries.length === 0) {
    return (
      <div className="card p-3">
        <div className="skeleton h-4 w-32" />
      </div>
    );
  }

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-2.5"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium" style={{ color: "var(--text)" }}>
            Libraries
          </span>
          {selected.length > 0 && (
            <span className="badge text-[10px]">{selected.length} selected</span>
          )}
        </div>
        <svg
          aria-hidden="true"
          width="12" height="12" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          style={{
            color: "var(--muted-2)",
            transform: collapsed ? "rotate(0deg)" : "rotate(180deg)",
            transition: "transform 0.2s",
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {!collapsed && (
        <div className="px-4 pb-3 animate-in">
          <div className="flex gap-2 mb-2">
            <button
              onClick={selectAll}
              className="text-[10px] transition-colors"
              style={{ color: "var(--accent)" }}
            >
              Select all
            </button>
            <span style={{ color: "var(--border)" }}>|</span>
            <button
              onClick={clearAll}
              className="text-[10px] transition-colors"
              style={{ color: "var(--muted-2)" }}
            >
              Clear
            </button>
          </div>
          <div className="grid gap-1.5" role="group" aria-label="Available libraries">
            {libraries.map((lib) => {
              const isSelected = selected.includes(lib.id);
              return (
                <button
                  key={lib.id}
                  onClick={() => toggleLib(lib.id)}
                  role="checkbox"
                  aria-checked={isSelected}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-all"
                  style={{
                    background: isSelected ? "var(--accent-dim)" : "transparent",
                    border: `1px solid ${isSelected ? "rgba(99,162,255,0.25)" : "transparent"}`,
                  }}
                >
                  <div
                    className="w-4 h-4 rounded flex items-center justify-center shrink-0 transition-all"
                    style={{
                      background: isSelected ? "var(--accent)" : "transparent",
                      border: `1.5px solid ${isSelected ? "var(--accent)" : "var(--muted-2)"}`,
                    }}
                  >
                    {isSelected && (
                      <svg aria-hidden="true" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#0a0e14" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate" style={{ color: isSelected ? "var(--text)" : "var(--muted)" }}>
                      {lib.name}
                    </p>
                  </div>
                  <span className="badge text-[10px] shrink-0">{lib.document_count} docs</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
