"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type Library, type ChatSource } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

export default function LibraryChatPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [library, setLibrary] = useState<Library | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeSources, setActiveSources] = useState<ChatSource[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.libraryBySlug(slug).then(setLibrary).catch(() => {});
  }, [slug]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading || !library) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);

    try {
      const data = await api.chat(library.id, msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response, sources: data.sources },
      ]);
      setActiveSources(data.sources);
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "Something went wrong";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errMsg}` },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const suggestions = library?.config?.frontend?.suggestions || [
    "What does this document cover?",
    "Summarize the key policies",
    "What are the main sections?",
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">
          {library ? `Chat — ${library.name}` : "Loading..."}
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          AI answers grounded in your uploaded documents via semantic search.
        </p>
      </div>

      <div className="flex gap-5" style={{ height: "calc(100vh - 12rem)" }}>
        {/* Conversation pane */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {messages.length === 0 && (
              <div className="py-10 text-center animate-in">
                <div
                  className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center text-sm font-bold"
                  style={{
                    background: "var(--accent-dim)",
                    border: "1px solid rgba(99,162,255,0.35)",
                    color: "var(--accent)",
                    boxShadow: "0 0 16px rgba(99,162,255,0.3), 0 0 40px rgba(99,162,255,0.1)",
                  }}
                >
                  AI
                </div>
                <p className="text-xl font-light mb-1" style={{ color: "var(--text)" }}>
                  Ask anything about this library.
                </p>
                <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>
                  {library ? `${library.document_count} documents, ${library.chunk_count} indexed chunks` : ""}
                </p>
                <div className="flex flex-col items-center gap-2">
                  {suggestions.map((s: string) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="text-sm px-4 py-2 rounded-full transition-all"
                      style={{
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        color: "var(--muted)",
                      }}
                      onMouseEnter={(e) => {
                        const el = e.currentTarget;
                        el.style.borderColor = "rgba(99,162,255,0.35)";
                        el.style.color = "var(--text)";
                      }}
                      onMouseLeave={(e) => {
                        const el = e.currentTarget;
                        el.style.borderColor = "var(--border)";
                        el.style.color = "var(--muted)";
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex animate-in ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <div
                    className="w-7 h-7 rounded-full shrink-0 mr-2.5 mt-1 flex items-center justify-center text-xs font-bold"
                    style={{
                      background: "var(--accent-dim)",
                      border: "1px solid rgba(99,162,255,0.35)",
                      color: "var(--accent)",
                      boxShadow: "0 0 8px rgba(99,162,255,0.3)",
                    }}
                  >
                    AI
                  </div>
                )}
                <div
                  className="max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed"
                  style={{
                    background: m.role === "user" ? "var(--accent)" : "var(--surface)",
                    color: m.role === "user" ? "#0a0e14" : "var(--text)",
                    border: m.role === "assistant" ? "1px solid var(--border)" : "none",
                    borderBottomRightRadius: m.role === "user" ? "4px" : undefined,
                    borderBottomLeftRadius: m.role === "assistant" ? "4px" : undefined,
                  }}
                >
                  {m.content}
                  {m.sources && m.sources.length > 0 && (
                    <div
                      className="mt-3 pt-2.5 flex flex-wrap gap-1.5"
                      style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
                    >
                      {m.sources.slice(0, 3).map((s, j) => (
                        <span
                          key={j}
                          className="text-xs px-2 py-0.5 rounded"
                          style={{
                            background: "rgba(99,162,255,0.1)",
                            color: "var(--accent)",
                            border: "1px solid rgba(99,162,255,0.15)",
                          }}
                        >
                          {s.title}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div
                  className="w-7 h-7 rounded-full shrink-0 mr-2.5 mt-1 flex items-center justify-center text-xs font-bold"
                  style={{
                    background: "var(--accent-dim)",
                    border: "1px solid rgba(99,162,255,0.35)",
                    color: "var(--accent)",
                    boxShadow: "0 0 8px rgba(99,162,255,0.3)",
                  }}
                >
                  AI
                </div>
                <div
                  className="rounded-2xl rounded-bl px-4 py-3"
                  style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
                >
                  <span className="dot-pulse">
                    <span /><span /><span />
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input area */}
          <div className="mt-4 flex flex-col gap-1.5">
            <div className="flex gap-2 items-end">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question... (Enter to send)"
                disabled={loading}
                rows={1}
                className="input flex-1 resize-none"
                style={{ minHeight: "2.75rem", maxHeight: "8rem", lineHeight: "1.5" }}
                onInput={(e) => {
                  const t = e.target as HTMLTextAreaElement;
                  t.style.height = "auto";
                  t.style.height = Math.min(t.scrollHeight, 128) + "px";
                }}
              />
              <button
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                className="btn btn-primary shrink-0"
                style={{ height: "2.75rem", padding: "0 1.25rem" }}
              >
                Send
              </button>
            </div>
            {messages.length > 0 && (
              <button
                onClick={() => { setMessages([]); setActiveSources([]); }}
                className="text-xs self-start"
                style={{ color: "var(--muted-2)" }}
              >
                Clear conversation
              </button>
            )}
          </div>
        </div>

        {/* Sources sidebar */}
        <aside
          className="w-60 shrink-0 rounded-xl border hidden md:flex flex-col overflow-hidden"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <div className="p-4 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
            <p className="section-label">Sources</p>
          </div>
          <div className="p-4 overflow-y-auto flex-1">
            {activeSources.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                Cited documents from the last response appear here.
              </p>
            ) : (
              <ul className="space-y-4">
                {activeSources.map((s, i) => (
                  <li key={i}>
                    <p className="text-sm font-medium leading-snug" style={{ color: "var(--text)" }}>
                      {s.title}
                    </p>
                    {s.section && (
                      <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                        {s.section}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-1.5">
                      <div className="h-1 rounded-full flex-1" style={{ background: "var(--border)" }}>
                        <div
                          className="h-1 rounded-full transition-all"
                          style={{ width: `${Math.round(s.similarity * 100)}%`, background: "var(--accent)" }}
                        />
                      </div>
                      <span className="text-xs font-mono" style={{ color: "var(--accent)" }}>
                        {Math.round(s.similarity * 100)}%
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
