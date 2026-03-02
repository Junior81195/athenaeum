"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type Library, type UploadResponse } from "@/lib/api";

export default function UploadPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [library, setLibrary] = useState<Library | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.libraryBySlug(slug).then(setLibrary).catch(() => {});
  }, [slug]);

  const handleFile = useCallback((f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "txt", "md", "text"].includes(ext || "")) {
      setError("Unsupported file type. Please upload PDF, TXT, or MD files.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("File too large (max 50MB).");
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
  }, []);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }

  async function handleUpload() {
    if (!file || !library) return;
    setUploading(true);
    setError(null);
    try {
      const res = await api.upload(library.id, file);
      setResult(res);
      setFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold">
          Upload — {library?.name || "Loading..."}
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Upload PDF or text files. They will be automatically extracted, chunked, and embedded.
        </p>
      </div>

      {/* Drop zone */}
      <div
        className="max-w-xl mx-auto"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div
          className="rounded-xl border-2 border-dashed p-12 text-center cursor-pointer transition-all"
          style={{
            borderColor: dragOver ? "var(--accent)" : "var(--border)",
            background: dragOver ? "var(--accent-dim)" : "transparent",
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md,.text"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <svg
            className="mx-auto mb-4"
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ color: "var(--muted)" }}
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p className="text-sm font-medium mb-1">
            Drop a file here or click to browse
          </p>
          <p className="text-xs" style={{ color: "var(--muted-2)" }}>
            PDF, TXT, MD — up to 50MB
          </p>
        </div>

        {/* Selected file */}
        {file && (
          <div className="mt-4 animate-in">
            <div className="card p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs" style={{ color: "var(--muted)" }}>
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => { setFile(null); setError(null); }}
                  className="btn btn-ghost text-xs"
                >
                  Remove
                </button>
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="btn btn-primary"
                >
                  {uploading ? (
                    <>
                      <span className="dot-pulse"><span /><span /><span /></span>
                      Processing...
                    </>
                  ) : (
                    "Upload & Process"
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Progress / result */}
        {uploading && (
          <div className="mt-4 card p-4 animate-in">
            <p className="text-sm font-medium mb-2">Processing document...</p>
            <div className="space-y-1 text-xs" style={{ color: "var(--muted)" }}>
              <p>Extracting text from file...</p>
              <p>Splitting into sections and chunks...</p>
              <p>Generating embeddings (this may take a moment)...</p>
            </div>
          </div>
        )}

        {result && (
          <div className="mt-4 animate-in">
            <div
              className="rounded-xl p-6 border"
              style={{
                background: "rgba(34,197,94,0.05)",
                borderColor: "rgba(34,197,94,0.2)",
              }}
            >
              <p className="text-sm font-semibold mb-3" style={{ color: "#22c55e" }}>
                Upload complete
              </p>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-2xl font-bold">{result.sections_created}</p>
                  <p className="text-xs" style={{ color: "var(--muted)" }}>sections</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{result.chunks_created}</p>
                  <p className="text-xs" style={{ color: "var(--muted)" }}>chunks</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{result.chunks_embedded}</p>
                  <p className="text-xs" style={{ color: "var(--muted)" }}>embedded</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Link
                  href={`/library/${slug}`}
                  className="btn btn-primary text-xs"
                >
                  View Library
                </Link>
                <Link
                  href={`/library/${slug}/chat`}
                  className="btn btn-ghost text-xs"
                >
                  Start Chatting
                </Link>
                <button
                  onClick={() => setResult(null)}
                  className="btn btn-ghost text-xs"
                >
                  Upload Another
                </button>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4">
            <p className="text-sm" style={{ color: "#f87171" }}>{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
