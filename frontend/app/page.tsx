"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, type Library } from "@/lib/api";

export default function LibraryCatalog() {
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [newDesc, setNewDesc] = useState("");

  useEffect(() => {
    api.libraries()
      .then(setLibraries)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function autoSlug(name: string) {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim() || !newSlug.trim()) return;
    setCreating(true);
    try {
      const lib = await api.createLibrary({
        name: newName.trim(),
        slug: newSlug.trim(),
        description: newDesc.trim(),
      });
      setLibraries((prev) => [lib, ...prev]);
      setShowCreate(false);
      setNewName("");
      setNewSlug("");
      setNewDesc("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      {/* Hero */}
      <div className="text-center mb-10 pt-4">
        <h1
          className="text-4xl font-bold mb-3 tracking-tight"
          style={{ letterSpacing: "-0.02em" }}
        >
          Handbook Library
        </h1>
        <p className="text-base mb-1" style={{ color: "var(--muted)" }}>
          Upload documents, search semantically, chat with AI
        </p>
        <p className="text-sm" style={{ color: "var(--muted-2)" }}>
          {libraries.length} {libraries.length === 1 ? "library" : "libraries"}
        </p>
      </div>

      {/* Create button */}
      <div className="flex justify-center mb-8">
        <button onClick={() => setShowCreate(!showCreate)} className="btn-glow">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Create New Library
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="max-w-lg mx-auto mb-10 animate-in">
          <form onSubmit={handleCreate} className="card p-6 space-y-4">
            <div>
              <label className="section-label block mb-1.5">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => {
                  setNewName(e.target.value);
                  if (!newSlug || newSlug === autoSlug(newName)) {
                    setNewSlug(autoSlug(e.target.value));
                  }
                }}
                placeholder="PVC Employee Handbook"
                className="input"
                required
              />
            </div>
            <div>
              <label className="section-label block mb-1.5">Slug</label>
              <input
                type="text"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                placeholder="pvc-handbook"
                className="input"
                required
              />
              <p className="text-xs mt-1" style={{ color: "var(--muted-2)" }}>
                URL-safe identifier. Lowercase letters, numbers, hyphens only.
              </p>
            </div>
            <div>
              <label className="section-label block mb-1.5">Description</label>
              <textarea
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="What's in this library?"
                className="input"
                rows={2}
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button type="submit" disabled={creating} className="btn btn-primary">
                {creating ? "Creating..." : "Create Library"}
              </button>
              <button type="button" onClick={() => setShowCreate(false)} className="btn btn-ghost">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {error && (
        <p className="text-center text-sm mb-4" style={{ color: "#f87171" }}>
          {error}
        </p>
      )}

      {/* Loading */}
      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6">
              <div className="skeleton h-5 w-3/4 mb-3" />
              <div className="skeleton h-4 w-full mb-2" />
              <div className="skeleton h-4 w-1/2" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && libraries.length === 0 && !error && (
        <div className="text-center py-16">
          <p className="text-lg mb-2" style={{ color: "var(--muted)" }}>
            No libraries yet
          </p>
          <p className="text-sm" style={{ color: "var(--muted-2)" }}>
            Create your first library to get started
          </p>
        </div>
      )}

      {/* Library grid */}
      {libraries.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {libraries.map((lib) => (
            <Link
              key={lib.id}
              href={`/library/${lib.slug}`}
              className="card-hover p-6 block"
            >
              <h2 className="font-semibold text-base mb-1">{lib.name}</h2>
              {lib.description && (
                <p className="text-sm mb-3 line-clamp-2" style={{ color: "var(--muted)" }}>
                  {lib.description}
                </p>
              )}
              <div className="flex gap-2 mt-auto">
                <span className="badge">
                  {lib.document_count} {lib.document_count === 1 ? "doc" : "docs"}
                </span>
                <span className="badge">
                  {lib.chunk_count} chunks
                </span>
              </div>
              {lib.owner && (
                <p className="text-xs mt-3" style={{ color: "var(--muted-2)" }}>
                  by {lib.owner}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
