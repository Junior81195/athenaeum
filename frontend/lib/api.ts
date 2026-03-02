const API_URL =
  (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Library {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  owner: string | null;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
  document_count: number;
  chunk_count: number;
}

export interface SearchResult {
  chunk_id: number;
  document_id: number;
  document_title: string;
  section: string | null;
  text: string;
  similarity: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface ChatSource {
  title: string;
  section: string | null;
  similarity: number;
}

export interface ChatResponse {
  response: string;
  sources: ChatSource[];
}

export interface DocumentSummary {
  id: number;
  title: string;
  section: string | null;
  source: string | null;
  word_count: number;
}

export interface DocumentDetail extends DocumentSummary {
  full_text: string;
  page_start: number | null;
  page_end: number | null;
}

export interface TopicSummary {
  id: number;
  name: string;
  chunk_count: number;
  document_count: number;
  keywords: string[];
}

export interface LibraryInfo {
  library: {
    id: number;
    slug: string;
    name: string;
    description: string | null;
  };
  corpus: {
    document_count: number;
    chunk_count: number;
    topic_count: number;
    section_count: number;
  };
  config: Record<string, any>;
}

export interface UploadResponse {
  filename: string;
  sections_created: number;
  chunks_created: number;
  chunks_embedded: number;
}

// ── API client ────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body);
      detail = parsed.detail ?? body;
    } catch {}
    throw new Error(detail || `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // ── Libraries ──────────────────────────────────────────────

  libraries: (): Promise<Library[]> => apiFetch("/api/libraries"),

  createLibrary: (data: {
    name: string;
    slug: string;
    description?: string;
    config?: Record<string, any>;
  }): Promise<Library> =>
    apiFetch("/api/libraries", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  library: (id: number): Promise<Library> =>
    apiFetch(`/api/libraries/${id}`),

  libraryBySlug: (slug: string): Promise<Library> =>
    apiFetch(`/api/libraries/by-slug/${slug}`),

  updateLibrary: (
    id: number,
    data: { name?: string; description?: string; config?: Record<string, any> }
  ): Promise<Library> =>
    apiFetch(`/api/libraries/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteLibrary: (id: number): Promise<void> =>
    apiFetch(`/api/libraries/${id}`, { method: "DELETE" }),

  // ── Library-scoped endpoints ───────────────────────────────

  libraryInfo: (id: number): Promise<LibraryInfo> =>
    apiFetch(`/api/libraries/${id}/info`),

  search: (libraryId: number, q: string, limit = 10): Promise<SearchResponse> =>
    apiFetch(
      `/api/libraries/${libraryId}/search?q=${encodeURIComponent(q)}&limit=${limit}`
    ),

  chat: (
    libraryId: number,
    message: string,
    contextLimit = 10
  ): Promise<ChatResponse> =>
    apiFetch(`/api/libraries/${libraryId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message, context_limit: contextLimit }),
    }),

  documents: (
    libraryId: number,
    params?: { search?: string; limit?: number; offset?: number }
  ): Promise<DocumentSummary[]> => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set("search", params.search);
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    if (params?.offset !== undefined) qs.set("offset", String(params.offset));
    return apiFetch(`/api/libraries/${libraryId}/documents?${qs}`);
  },

  document: (libraryId: number, docId: number): Promise<DocumentDetail> =>
    apiFetch(`/api/libraries/${libraryId}/documents/${docId}`),

  topics: (libraryId: number): Promise<TopicSummary[]> =>
    apiFetch(`/api/libraries/${libraryId}/topics`),

  upload: async (libraryId: number, file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_URL}/api/libraries/${libraryId}/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      let detail = body;
      try {
        const parsed = JSON.parse(body);
        detail = parsed.detail ?? body;
      } catch {}
      throw new Error(detail || `Upload error ${res.status}`);
    }
    return res.json() as Promise<UploadResponse>;
  },
};
