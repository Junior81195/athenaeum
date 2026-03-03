"use client";

import type { SourceDetail } from "@/lib/api";

export default function SourceCard({
  source,
  expanded,
  onToggle,
  libraryName,
}: {
  source: SourceDetail;
  expanded: boolean;
  onToggle: () => void;
  libraryName?: string;
}) {
  return (
    <div
      className="rounded-lg overflow-hidden transition-all"
      style={{
        background: expanded ? "var(--surface)" : "transparent",
        border: `1px solid ${expanded ? "rgba(99,162,255,0.2)" : "var(--border)"}`,
      }}
    >
      <button
        onClick={onToggle}
        className="w-full text-left px-3 py-2 flex items-center gap-2"
      >
        <span
          className="flex items-center justify-center text-[10px] font-bold rounded-full shrink-0"
          style={{
            width: "20px",
            height: "20px",
            background: "var(--accent-dim)",
            color: "var(--accent)",
            border: "1px solid rgba(99,162,255,0.3)",
          }}
        >
          {source.index}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium truncate" style={{ color: "var(--text)" }}>
            {source.title}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            {libraryName && (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
                style={{
                  background: "var(--accent-dim)",
                  color: "var(--accent)",
                  border: "1px solid rgba(99,162,255,0.15)",
                }}
              >
                {libraryName}
              </span>
            )}
            {source.section && source.section !== source.title && (
              <span className="text-[10px] truncate" style={{ color: "var(--muted)" }}>
                {source.section}
              </span>
            )}
            {source.page_start && (
              <span className="text-[10px]" style={{ color: "var(--muted-2)" }}>
                pp. {source.page_start}{source.page_end && source.page_end !== source.page_start ? `\u2013${source.page_end}` : ""}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[10px] font-mono" style={{ color: "var(--accent)" }}>
            {Math.round(source.similarity * 100)}%
          </span>
          <svg
            width="12" height="12" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            style={{ color: "var(--muted-2)", transform: expanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 animate-in">
          <div
            className="rounded-md px-3 py-2.5 text-xs leading-relaxed font-mono"
            style={{
              background: "rgba(0,0,0,0.2)",
              border: "1px solid var(--border)",
              color: "var(--muted)",
              maxHeight: "200px",
              overflow: "auto",
              whiteSpace: "pre-wrap",
            }}
          >
            {source.text}
          </div>
        </div>
      )}
    </div>
  );
}
