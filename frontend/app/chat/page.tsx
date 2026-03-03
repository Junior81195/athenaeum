"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import {
  api,
  type MultiSourceDetail,
  type MultiChatResponse,
  type ConversationSummary,
} from "@/lib/api";
import { useKeyboard } from "@/lib/useKeyboard";
import LibrarySelector from "@/components/LibrarySelector";
import RenderedAnswer from "@/components/RenderedAnswer";
import SourceCard from "@/components/SourceCard";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: MultiSourceDetail[];
  suggestions?: string[];
}

export default function MultiChatPage() {
  const [selectedLibs, setSelectedLibs] = useState<number[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});
  const [showHistory, setShowHistory] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const keyHandlers = useMemo(() => ({
    "n": () => startNewConversation(),
    "Escape": () => { if (showHistory) setShowHistory(false); },
    "/": () => inputRef.current?.focus(),
  }), [showHistory]);
  useKeyboard(keyHandlers);

  useEffect(() => {
    api.multiConversations().then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleSource = useCallback((sourceIndex: number) => {
    setExpandedSources((prev) => ({ ...prev, [sourceIndex]: !prev[sourceIndex] }));
  }, []);

  async function loadConversation(convId: string) {
    try {
      const detail = await api.conversation(convId);
      setConversationId(convId);
      if (detail.library_ids.length > 0) {
        setSelectedLibs(detail.library_ids);
      }
      setMessages(
        detail.messages.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
          sources: m.sources_json as MultiSourceDetail[] | undefined ?? undefined,
        }))
      );
      setShowHistory(false);
    } catch {}
  }

  function startNewConversation() {
    setMessages([]);
    setConversationId(null);
    setExpandedSources({});
    setShowHistory(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function sendMessage(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading || selectedLibs.length === 0) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    setExpandedSources({});

    try {
      const data: MultiChatResponse = await api.multiChat(
        msg,
        selectedLibs,
        8,
        conversationId ?? undefined
      );
      if (!conversationId) setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          suggestions: data.suggestions,
        },
      ]);
      api.multiConversations().then(setConversations).catch(() => {});
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

  return (
    <div>
      <div className="mb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Chat Across Libraries</h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: "var(--muted)" }}>
            AI answers grounded in multiple libraries with cross-library citations
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="btn text-xs"
            style={{
              background: showHistory ? "var(--accent-dim)" : "transparent",
              color: showHistory ? "var(--accent)" : "var(--muted)",
              border: `1px solid ${showHistory ? "rgba(99,162,255,0.3)" : "var(--border)"}`,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            History
          </button>
          <button onClick={startNewConversation} className="btn text-xs" style={{ color: "var(--muted)", border: "1px solid var(--border)" }}>
            + New
          </button>
        </div>
      </div>

      {/* Library selector — compact at top */}
      <div className="max-w-xl mb-5">
        <LibrarySelector selected={selectedLibs} onChange={setSelectedLibs} />
      </div>

      <div className="flex gap-4 relative" style={{ height: "calc(100vh - 18rem)" }}>
        {/* Conversation history sidebar */}
        {showHistory && (
          <>
            <div
              className="fixed inset-0 z-30 md:hidden"
              style={{ background: "rgba(0,0,0,0.5)" }}
              onClick={() => setShowHistory(false)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setShowHistory(false); }}
              role="button"
              aria-label="Close conversation history"
              tabIndex={0}
            />
            <aside
              aria-label="Conversation history"
              className="fixed left-0 top-12 bottom-0 w-64 z-40 md:relative md:top-auto md:bottom-auto md:w-56 shrink-0 rounded-none md:rounded-xl border-r md:border flex flex-col overflow-hidden animate-in"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="p-3 border-b" style={{ borderColor: "var(--border)" }}>
                <p className="section-label text-xs">Conversations</p>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {conversations.length === 0 ? (
                  <p className="text-xs p-2" style={{ color: "var(--muted-2)" }}>No conversations yet</p>
                ) : (
                  conversations.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => loadConversation(c.id)}
                      className="w-full text-left px-3 py-2 rounded-lg text-xs transition-colors"
                      style={{
                        background: c.id === conversationId ? "var(--accent-dim)" : "transparent",
                        color: c.id === conversationId ? "var(--accent)" : "var(--muted)",
                      }}
                    >
                      <p className="truncate font-medium" style={{ color: c.id === conversationId ? "var(--text)" : undefined }}>
                        {c.title || "Untitled"}
                      </p>
                      <p className="text-[10px] mt-0.5" style={{ color: "var(--muted-2)" }}>
                        {c.message_count} messages
                      </p>
                    </button>
                  ))
                )}
              </div>
            </aside>
          </>
        )}

        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto space-y-5 pr-1">
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
                  {selectedLibs.length === 0
                    ? "Select libraries and ask a question."
                    : `Ask anything across ${selectedLibs.length} ${selectedLibs.length === 1 ? "library" : "libraries"}.`}
                </p>
                <p className="text-sm mb-7" style={{ color: "var(--muted)" }}>
                  {selectedLibs.length === 0
                    ? "Choose one or more libraries above to get started"
                    : "Cross-library search with per-library attribution"}
                </p>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className="animate-in">
                {m.role === "user" ? (
                  <div className="flex justify-end">
                    <div
                      className="max-w-2xl rounded-2xl rounded-br px-4 py-3 text-sm leading-relaxed"
                      style={{ background: "var(--accent)", color: "#0a0e14" }}
                    >
                      {m.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-2.5">
                    <div
                      className="w-7 h-7 rounded-full shrink-0 mt-1 flex items-center justify-center text-xs font-bold"
                      style={{
                        background: "var(--accent-dim)",
                        border: "1px solid rgba(99,162,255,0.35)",
                        color: "var(--accent)",
                        boxShadow: "0 0 8px rgba(99,162,255,0.3)",
                      }}
                    >
                      AI
                    </div>
                    <div className="flex-1 min-w-0 max-w-3xl">
                      <div
                        className="rounded-2xl rounded-bl px-4 py-3 text-sm leading-relaxed"
                        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
                      >
                        <RenderedAnswer text={m.content} onCiteClick={toggleSource} />
                      </div>

                      {m.sources && m.sources.length > 0 && (
                        <div className="mt-2 space-y-1.5">
                          <p className="text-[11px] font-medium uppercase tracking-wider px-1" style={{ color: "var(--muted-2)" }}>
                            Sources ({m.sources.length})
                          </p>
                          {m.sources.map((s) => (
                            <SourceCard
                              key={s.index}
                              source={s}
                              expanded={!!expandedSources[s.index]}
                              onToggle={() => toggleSource(s.index)}
                              libraryName={s.library_name}
                            />
                          ))}
                        </div>
                      )}

                      {m.suggestions && m.suggestions.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {m.suggestions.map((s, j) => (
                            <button
                              key={j}
                              onClick={() => sendMessage(s)}
                              className="suggestion-chip text-xs px-3 py-1.5 rounded-full"
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            <div aria-live="polite" className="sr-only">
              {loading && "Searching documents and generating response"}
            </div>

            {loading && (
              <div className="flex gap-2.5">
                <div
                  className="w-7 h-7 rounded-full shrink-0 mt-1 flex items-center justify-center text-xs font-bold"
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
                  <div className="flex gap-1.5 items-center">
                    <div className="text-xs" style={{ color: "var(--muted)" }}>Searching across libraries and generating response</div>
                    <span className="dot-pulse"><span /><span /><span /></span>
                  </div>
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
                aria-label="Chat message"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  selectedLibs.length === 0
                    ? "Select libraries above to start chatting..."
                    : "Ask a question... (Enter to send)"
                }
                disabled={loading || selectedLibs.length === 0}
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
                disabled={loading || !input.trim() || selectedLibs.length === 0}
                className="btn btn-primary shrink-0"
                style={{ height: "2.75rem", padding: "0 1.25rem" }}
              >
                Send
              </button>
            </div>
            {messages.length > 0 && (
              <button
                onClick={startNewConversation}
                className="text-xs self-start"
                style={{ color: "var(--muted-2)" }}
              >
                Start new conversation
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
