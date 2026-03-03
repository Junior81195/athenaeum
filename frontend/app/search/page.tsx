"use client";

import { useState, useRef, useMemo } from "react";
import Link from "next/link";
import { api, type MultiSearchResult } from "@/lib/api";
import { useKeyboard } from "@/lib/useKeyboard";
import LibrarySelector from "@/components/LibrarySelector";

export default function MultiSearchPage() {
  const [selectedLibs, setSelectedLibs] = useState<number[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MultiSearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const keyHandlers = useMemo(() => ({
    "/": () => searchRef.current?.focus(),
    "Escape": () => {
      if (searched) {
        setSearched(false);
        setResults([]);
        setQuery("");
      }
    },
  }), [searched]);
  useKeyboard(keyHandlers);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || selectedLibs.length === 0) return;
    setSearched(true);
    setLoading(true);
    setError(null);
    try {
      const data = await api.multiSearch(query.trim(), selectedLibs, 20);
      setResults(data.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Search Across Libraries</h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Run a single query across multiple libraries with per-library attribution
        </p>
      </div>

      <div className="max-w-xl mb-6">
        <LibrarySelector selected={selectedLibs} onChange={setSelectedLibs} />
      </div>

      <div className="max-w-xl mb-8">
        <form onSubmit={handleSearch} className="relative">
          <svg
            aria-hidden="true"
            className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
            width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ color: "var(--muted-2)" }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={searchRef}
            type="text"
            aria-label="Search across libraries"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              selectedLibs.length === 0
                ? "Select libraries above, then search... (press /)"
                : `Search ${selectedLibs.length} ${selectedLibs.length === 1 ? "library" : "libraries"}... (press /)`
            }
            disabled={selectedLibs.length === 0}
            className="input"
            style={{ paddingLeft: "2.25rem", paddingRight: searched ? "4rem" : undefined }}
          />
          {searched && (
            <button
              type="button"
              onClick={() => { setSearched(false); setResults([]); setQuery(""); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] transition-colors"
              style={{ color: "var(--muted-2)" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--muted-2)")}
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {error && <p role="alert" className="text-xs mb-4" style={{ color: "var(--red)" }}>{error}</p>}

      {searched && (
        <div className="animate-in">
          <p className="text-[11px] mb-3" style={{ color: "var(--muted)" }}>
            {loading ? "Searching..." : `${results.length} ${results.length === 1 ? "result" : "results"} for \u201c${query}\u201d`}
          </p>
          {results.length === 0 && !loading && (
            <p className="text-sm" style={{ color: "var(--muted)" }}>No results found.</p>
          )}
          <div className="grid gap-2.5">
            {results.map((r) => (
              <div key={`${r.library_id}-${r.chunk_id}`} className="card p-4 flex items-start gap-3.5">
                <div
                  className="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-xs font-mono font-semibold"
                  style={{
                    background: r.similarity >= 0.65 ? "var(--accent-dim)" : "rgba(255,255,255,0.03)",
                    color: r.similarity >= 0.65 ? "var(--accent)" : "var(--muted)",
                    border: `1px solid ${r.similarity >= 0.65 ? "rgba(91,154,255,0.15)" : "var(--border)"}`,
                  }}
                >
                  {Math.round(r.similarity * 100)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-sm font-medium leading-snug">{r.document_title}</p>
                    <Link
                      href={`/library/${r.library_slug}`}
                      className="shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors"
                      style={{
                        background: "var(--accent-dim)",
                        color: "var(--accent)",
                        border: "1px solid rgba(99,162,255,0.15)",
                      }}
                    >
                      {r.library_name}
                    </Link>
                  </div>
                  {r.section && r.section !== r.document_title && (
                    <p className="text-[11px] mb-1" style={{ color: "var(--muted-2)" }}>{r.section}</p>
                  )}
                  <p className="text-xs leading-relaxed line-clamp-2" style={{ color: "var(--muted)" }}>
                    {r.text}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!searched && selectedLibs.length === 0 && (
        <div className="card p-10 text-center">
          <svg
            className="mx-auto mb-3"
            width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
            style={{ color: "var(--muted-2)" }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Select one or more libraries above, then search across all of them at once.
          </p>
        </div>
      )}
    </div>
  );
}
