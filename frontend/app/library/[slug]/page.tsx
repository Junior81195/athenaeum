"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import SearchBar from "@/components/SearchBar";
import { api, type Library, type SearchResult, type DocumentSummary } from "@/lib/api";

export default function LibraryDashboard() {
  const params = useParams();
  const slug = params.slug as string;

  const [library, setLibrary] = useState<Library | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.libraryBySlug(slug)
      .then((lib) => {
        setLibrary(lib);
        return api.documents(lib.id, { limit: 50 });
      })
      .then(setDocuments)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  async function handleSearch(q: string) {
    if (!library) return;
    setQuery(q);
    setSearched(true);
    setSearchLoading(true);
    try {
      const data = await api.search(library.id, q, 20);
      setSearchResults(data.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearchLoading(false);
    }
  }

  if (loading) {
    return (
      <div>
        <div className="skeleton h-8 w-64 mb-4" />
        <div className="skeleton h-4 w-96 mb-8" />
        <div className="skeleton h-12 w-full mb-4" />
        <div className="grid gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-20 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error && !library) {
    return (
      <div className="text-center py-16">
        <p className="text-lg mb-2" style={{ color: "#f87171" }}>{error}</p>
        <Link href="/" className="btn btn-ghost mt-4">Back to libraries</Link>
      </div>
    );
  }

  if (!library) return null;

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 tracking-tight">{library.name}</h1>
        {library.description && (
          <p className="text-base mb-3" style={{ color: "var(--muted)" }}>
            {library.description}
          </p>
        )}
        <div className="flex items-center gap-2 mb-4">
          <span className="badge">{library.document_count} documents</span>
          <span className="badge">{library.chunk_count} chunks</span>
        </div>
        <div className="flex gap-2">
          <Link href={`/library/${slug}/chat`} className="btn-glow">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            Chat with AI
          </Link>
          <Link href={`/library/${slug}/upload`} className="btn btn-ghost">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            Upload Documents
          </Link>
        </div>
      </div>

      {/* Search */}
      <div className="max-w-2xl mb-8">
        <SearchBar
          onSearch={handleSearch}
          loading={searchLoading}
          placeholder={`Search ${library.name}...`}
        />
      </div>

      {error && (
        <p className="text-sm mb-4" style={{ color: "#f87171" }}>{error}</p>
      )}

      {/* Search results */}
      {searched && (
        <div className="mb-10 animate-in">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              {searchResults.length} results for &ldquo;{query}&rdquo;
            </p>
            <button
              onClick={() => { setSearched(false); setSearchResults([]); }}
              className="text-xs"
              style={{ color: "var(--muted-2)" }}
            >
              Clear search
            </button>
          </div>
          {searchResults.length === 0 && !searchLoading && (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No results found.
            </p>
          )}
          <div className="grid gap-3">
            {searchResults.map((r) => (
              <div key={r.chunk_id} className="card-hover p-5">
                <div className="flex items-start gap-4">
                  <div className="shrink-0 flex flex-col items-center gap-1 pt-0.5">
                    <span
                      className="text-xs font-mono font-semibold"
                      style={{ color: r.similarity >= 0.65 ? "var(--accent)" : "var(--muted)" }}
                    >
                      {Math.round(r.similarity * 100)}%
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm mb-1">{r.document_title}</p>
                    {r.section && (
                      <p className="text-xs mb-1" style={{ color: "var(--muted)" }}>{r.section}</p>
                    )}
                    <p className="text-sm leading-relaxed line-clamp-3" style={{ color: "var(--muted)" }}>
                      &ldquo;{r.text}&rdquo;
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documents list */}
      {!searched && (
        <div>
          <h2 className="section-label mb-4">Documents</h2>
          {documents.length === 0 ? (
            <div className="card p-8 text-center">
              <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
                No documents uploaded yet.
              </p>
              <Link href={`/library/${slug}/upload`} className="btn btn-primary">
                Upload your first document
              </Link>
            </div>
          ) : (
            <div className="grid gap-2">
              {documents.map((doc) => (
                <div key={doc.id} className="card p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{doc.title}</p>
                    {doc.section && doc.section !== doc.title && (
                      <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                        {doc.section}
                      </p>
                    )}
                  </div>
                  <span className="text-xs" style={{ color: "var(--muted-2)" }}>
                    ~{doc.word_count.toLocaleString()} words
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
