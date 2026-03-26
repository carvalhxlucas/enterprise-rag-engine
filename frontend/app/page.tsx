"use client";

import { useEffect, useState } from "react";

type PersonaOption = "sarcastic" | "technical";
type ChatMessageRole = "user" | "assistant";

type CitationSource = {
  id: string;
  filename: string;
  page_number: number | null;
  chunk_index: number | null;
  text: string;
};

type DocumentItem = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
};

type ChatConfig = {
  persona: PersonaOption;
  temperature: number;
  use_hybrid_search: boolean;
};

type ChatRequest = {
  message: string;
  history: { role: ChatMessageRole; content: string }[];
  config: ChatConfig;
};

type ChatMessage = {
  id: string;
  role: ChatMessageRole;
  content: string;
  citations?: CitationSource[];
};

type UploadStage = "idle" | "uploading" | "processing" | "completed";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const USER_ID = "demo-user-1";

export default function Page() {
  const [persona, setPersona] = useState<PersonaOption>("technical");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");

  const [uploadStage, setUploadStage] = useState<UploadStage>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadTaskId, setUploadTaskId] = useState<string | null>(null);
  const [uploadStep, setUploadStep] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewMimeType, setPreviewMimeType] = useState<string | null>(null);
  const [previewFileName, setPreviewFileName] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [selectedCitation, setSelectedCitation] = useState<CitationSource | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);

  const [latestCostUsd, setLatestCostUsd] = useState<number | null>(null);
  const [latestLatencyMs, setLatestLatencyMs] = useState<number | null>(null);

  // Revoke blob URL on change to avoid memory leaks
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // Load document list on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  async function fetchDocuments() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents`, {
        headers: { "X-User-ID": USER_ID },
      });
      if (!res.ok) return;
      const data = (await res.json()) as { documents: DocumentItem[] };
      setDocuments(data.documents);
    } catch {}
  }

  async function deleteDocument(docId: string) {
    try {
      await fetch(`${API_BASE}/api/v1/documents/${docId}`, {
        method: "DELETE",
        headers: { "X-User-ID": USER_ID },
      });
    } catch {}

    if (docId === documentId) {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      setPreviewMimeType(null);
      setPreviewFileName(null);
      setPreviewText(null);
      setDocumentId(null);
      setUploadStage("idle");
      setUploadProgress(0);
      setUploadStep(null);
      setUploadError(null);
      setSelectedCitation(null);
    }

    await fetchDocuments();
  }

  async function handleDeleteDocument() {
    if (!documentId) return;
    setIsDeleting(true);
    await deleteDocument(documentId);
    setIsDeleting(false);
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    setPreviewMimeType(file.type);
    setPreviewFileName(file.name);
    setPreviewText(null);
    setSelectedCitation(null);

    if (file.type === "text/plain") {
      const reader = new FileReader();
      reader.onload = (e) => setPreviewText((e.target?.result as string) ?? null);
      reader.readAsText(file);
    }

    const formData = new FormData();
    formData.append("file", file);
    setUploadError(null);
    setUploadStage("uploading");
    setUploadProgress(5);
    setUploadStep("uploading");

    try {
      const res = await fetch(`${API_BASE}/api/v1/ingest/upload`, {
        method: "POST",
        headers: { "X-User-ID": USER_ID },
        body: formData,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setUploadError(data?.detail ?? "Upload failed");
        setUploadStage("idle");
        setUploadProgress(0);
        setUploadStep(null);
        return;
      }
      const data = (await res.json()) as { task_id: string };
      setUploadTaskId(data.task_id);
      setUploadStage("processing");
      setUploadProgress(10);
      setUploadStep("pending");
    } catch {
      setUploadError("Network error during upload");
      setUploadStage("idle");
      setUploadProgress(0);
      setUploadStep(null);
    }
  }

  // Poll ingestion status
  useEffect(() => {
    if (!uploadTaskId) return;
    let cancelled = false;

    async function fetchStatus() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/ingest/status/${uploadTaskId}`);
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as {
          status: string;
          step: string | null;
          progress: number;
          error: string | null;
          document_id: string | null;
        };
        if (cancelled) return;
        setUploadStep(data.step);
        setUploadProgress(data.progress);
        if (data.status === "processing" || data.status === "pending") {
          setUploadStage("processing");
        } else if (data.status === "completed") {
          setUploadStage("completed");
          setUploadTaskId(null);
          if (data.document_id) setDocumentId(data.document_id);
          fetchDocuments();
        } else if (data.status === "failed") {
          setUploadStage("idle");
          setUploadTaskId(null);
          setUploadError(data.error ?? "Ingestion failed");
        }
      } catch {}
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [uploadTaskId]);

  async function handleSend() {
    if (!inputValue.trim()) return;

    const previousMessages = messages;
    const idBase = String(Date.now());
    const userMessage: ChatMessage = { id: `${idBase}-user`, role: "user", content: inputValue };
    const assistantMessage: ChatMessage = { id: `${idBase}-assistant`, role: "assistant", content: "" };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInputValue("");
    setSelectedCitation(null);
    setLatestCostUsd(null);
    setLatestLatencyMs(null);

    const body: ChatRequest = {
      message: userMessage.content,
      history: previousMessages.map((m) => ({ role: m.role, content: m.content })),
      config: { persona, temperature: 0.7, use_hybrid_search: true },
    };

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream", "X-User-ID": USER_ID },
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) throw new Error("Chat request failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";

      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sep = buffer.indexOf("\n\n");
        while (sep !== -1) {
          const rawEvent = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);

          let eventType = "message";
          let dataLine = "";
          for (const line of rawEvent.split("\n")) {
            if (line.startsWith("event:")) eventType = line.slice(6).trim();
            else if (line.startsWith("data:")) {
              const part = line.slice(5).trim();
              dataLine = dataLine ? dataLine + part : part;
            }
          }

          if (!dataLine || eventType === "end") {
            sep = buffer.indexOf("\n\n");
            continue;
          }

          try {
            const payload = JSON.parse(dataLine);

            if (eventType === "citations") {
              const citationList = payload as CitationSource[];
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMessage.id ? { ...m, citations: citationList } : m
                )
              );
            } else if (eventType === "metrics") {
              setLatestLatencyMs(payload.latency_ms);
              setLatestCostUsd(payload.cost_usd);
            } else if (typeof payload.content === "string") {
              fullContent += payload.content;
              const snap = fullContent;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMessage.id ? { ...m, content: snap } : m))
              );
            }
          } catch {}

          sep = buffer.indexOf("\n\n");
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessage.id
            ? { ...m, content: "An error occurred while generating the answer." }
            : m
        )
      );
    }
  }

  function handleCitationClick(citation: CitationSource) {
    setSelectedCitation((prev) => (prev?.id === citation.id ? null : citation));
  }

  function statusBadge(status: string) {
    if (status === "completed")
      return <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">indexed</span>;
    if (status === "processing")
      return <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-400">indexing</span>;
    return <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-400">failed</span>;
  }

  return (
    <main className="flex min-h-screen flex-col bg-slate-950 text-slate-50">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex flex-col">
          <span className="text-xs uppercase tracking-wide text-slate-400">Enterprise RAG</span>
          <span className="text-lg font-semibold text-slate-50">Observability-first RAG Workbench</span>
        </div>
        <div className="flex items-center gap-6 text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <span className="shrink-0 font-medium text-slate-200">Persona</span>
            <div className="inline-flex gap-0.5 rounded-full bg-slate-900 p-1">
              {(["sarcastic", "technical"] as PersonaOption[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPersona(p)}
                  className={
                    persona === p
                      ? "rounded-full bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-slate-950"
                      : "rounded-full px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
                  }
                >
                  {p === "sarcastic" ? "Sarcastic" : "Extremely Technical"}
                </button>
              ))}
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1.5 md:flex">
            <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400" />
            <span className="text-[11px] uppercase tracking-wide">Live Evaluation Enabled</span>
          </div>
        </div>
      </header>

      <section className="flex flex-1 flex-row overflow-hidden">
        {/* ── Left sidebar ── */}
        <aside className="flex w-full max-w-xs flex-col border-r border-slate-800 bg-slate-950/40">
          {/* Upload */}
          <div className="border-b border-slate-800 px-4 py-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Upload</span>
            <p className="mt-1 text-xs text-slate-400">Upload a PDF, DOCX, or TXT to index and query.</p>
            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/40 px-4 py-5 text-center text-xs text-slate-300 hover:border-emerald-500 hover:bg-slate-900/70">
              <span className="text-sm font-medium text-slate-100">Drop file here or click to select</span>
              <span className="mt-1 text-[11px] text-slate-500">Supports PDF, DOCX, TXT</span>
              <input type="file" accept=".pdf,.doc,.docx,.txt" className="hidden" onChange={handleFileChange} />
            </label>
            <div className="mt-4 space-y-2 text-xs text-slate-300">
              <div className="flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-500">
                <span>Ingestion</span>
                <span>
                  {uploadStage === "idle" && "Waiting for file"}
                  {uploadStage === "uploading" && "Uploading"}
                  {uploadStage === "processing" && (uploadStep ?? "Processing")}
                  {uploadStage === "completed" && "Completed"}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-900">
                <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${uploadProgress}%` }} />
              </div>
              {uploadError && <div className="text-[11px] text-red-400">{uploadError}</div>}
            </div>
          </div>

          {/* Document list */}
          <div className="border-b border-slate-800 px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Indexed Documents</span>
              <button
                type="button"
                onClick={fetchDocuments}
                className="text-[11px] text-slate-500 hover:text-slate-300"
                title="Refresh"
              >
                ↺
              </button>
            </div>
            {documents.length === 0 ? (
              <p className="mt-2 text-[11px] text-slate-600">No documents indexed yet.</p>
            ) : (
              <ul className="mt-2 space-y-1">
                {documents.map((doc) => (
                  <li
                    key={doc.id}
                    className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-900/60"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[11px] font-medium text-slate-300">{doc.filename}</p>
                      <div className="mt-0.5">{statusBadge(doc.status)}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => deleteDocument(doc.id)}
                      title="Delete document"
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-slate-600 hover:bg-red-500/10 hover:text-red-400"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5">
                        <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Config + metrics */}
          <div className="flex flex-1 flex-col justify-between px-4 py-4 text-xs text-slate-300">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Live Config</span>
              <div className="mt-3 space-y-1 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">Persona</span>
                  <span className="text-[11px] font-medium text-emerald-400">
                    {persona === "sarcastic" ? "Sarcastic" : "Extremely technical"}
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Last interaction</span>
              <div className="mt-2 space-y-1 text-[11px] text-slate-300">
                <div className="flex justify-between">
                  <span>Latency</span>
                  <span>{latestLatencyMs != null ? `${(latestLatencyMs / 1000).toFixed(2)}s` : "–"}</span>
                </div>
                <div className="flex justify-between">
                  <span>Cost</span>
                  <span>{latestCostUsd != null ? `$${latestCostUsd.toFixed(5)}` : "–"}</span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* ── Chat ── */}
        <section className="flex min-w-0 flex-1 flex-col border-r border-slate-800 bg-slate-950/60">
          <div className="flex items-center justify-between border-b border-slate-800 px-6 py-3">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Chat</span>
              <span className="text-xs text-slate-500">Ask anything about your documents.</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-400">
              <span>Dense retrieval</span>
              <span className="h-1 w-1 rounded-full bg-slate-600" />
              <span>Top 5 chunks</span>
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
            {messages.length === 0 && (
              <div className="mt-16 text-center text-sm text-slate-500">
                <p>Upload a document, choose a persona, and ask a question.</p>
                <p className="mt-1 text-xs text-slate-600">Citations will appear below each answer.</p>
              </div>
            )}
            {messages.map((message) => (
              <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    message.role === "user"
                      ? "max-w-[75%] rounded-2xl bg-emerald-500 px-4 py-3 text-sm text-slate-950"
                      : "max-w-[75%] rounded-2xl bg-slate-900 px-4 py-3 text-sm text-slate-100"
                  }
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.citations && message.citations.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {message.citations.map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => handleCitationClick(c)}
                          className={
                            selectedCitation?.id === c.id
                              ? "rounded-full border border-emerald-400 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-300"
                              : "rounded-full border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[11px] text-slate-300 hover:border-emerald-400 hover:text-emerald-300"
                          }
                        >
                          [{c.id}]
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-slate-800 bg-slate-950/80 px-6 py-4">
            <div className="flex items-end gap-3">
              <div className="flex-1 rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  placeholder="Ask something about the document…"
                  rows={2}
                  className="h-16 w-full resize-none bg-transparent text-sm text-slate-50 outline-none placeholder:text-slate-500"
                />
              </div>
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputValue.trim()}
                className="inline-flex h-10 items-center justify-center rounded-full bg-emerald-500 px-6 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
              >
                Ask
              </button>
            </div>
            <p className="mt-2 text-[11px] text-slate-500">Enter to send · Shift+Enter for new line</p>
          </div>
        </section>

        {/* ── Document Viewer ── */}
        <aside className="hidden w-[28rem] flex-col bg-slate-950/90 md:flex">
          <div className="border-b border-slate-800 px-4 py-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex min-w-0 flex-col">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Document Viewer</span>
                <span className="truncate text-xs text-slate-500">{previewFileName ?? "No document uploaded"}</span>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {uploadStage === "completed" && (
                  <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400">Indexed</span>
                )}
                {uploadStage === "processing" && (
                  <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-400">Indexing…</span>
                )}
                {previewUrl && (
                  <button
                    type="button"
                    onClick={handleDeleteDocument}
                    disabled={isDeleting}
                    title="Remove document"
                    className="flex h-7 w-7 items-center justify-center rounded-full text-slate-500 hover:bg-red-500/10 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-4 w-4">
                      <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Citation passage card */}
          {selectedCitation && (
            <div className="border-b border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-emerald-300">
                    [{selectedCitation.id}] {selectedCitation.filename}
                    {selectedCitation.page_number != null && ` · page ${selectedCitation.page_number}`}
                  </p>
                  <p className="mt-1.5 line-clamp-6 text-[11px] leading-relaxed text-emerald-100/80">
                    {selectedCitation.text}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedCitation(null)}
                  className="shrink-0 text-slate-500 hover:text-slate-300"
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          {/* Document preview */}
          {!previewUrl && (
            <div className="flex flex-1 items-center justify-center text-center text-slate-500">
              <div>
                <p className="text-sm">No document uploaded yet.</p>
                <p className="mt-1 text-[11px] text-slate-600">Upload a PDF, DOCX, or TXT to preview it here.</p>
              </div>
            </div>
          )}
          {previewUrl && previewMimeType === "application/pdf" && (
            <iframe src={previewUrl} title={previewFileName ?? "Document"} className="flex-1 w-full border-0" />
          )}
          {previewUrl && previewMimeType === "text/plain" && (
            <div className="flex-1 overflow-y-auto px-4 py-4">
              <pre className="whitespace-pre-wrap break-words text-[11px] leading-relaxed text-slate-300">
                {previewText ?? "Loading…"}
              </pre>
            </div>
          )}
          {previewUrl && previewMimeType !== "application/pdf" && previewMimeType !== "text/plain" && (
            <div className="flex flex-1 items-center justify-center text-center text-slate-500">
              <div>
                <p className="text-sm">{previewFileName}</p>
                <p className="mt-1 text-[11px] text-slate-600">Preview not available for this file type.</p>
              </div>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}
