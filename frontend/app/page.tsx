"use client";

import { useEffect, useState } from "react";

type PersonaOption = "sarcastic" | "technical";

type ChatMessageRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatMessageRole;
  content: string;
  citationIds?: string[];
  costUsd?: number;
  latencyMs?: number;
};

type UploadStage = "idle" | "uploading" | "processing" | "completed";

export default function Page() {
  const [persona, setPersona] = useState<PersonaOption>("technical");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [uploadStage, setUploadStage] = useState<UploadStage>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadTaskId, setUploadTaskId] = useState<string | null>(null);
  const [uploadStep, setUploadStep] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [latestCostUsd, setLatestCostUsd] = useState<number | null>(null);
  const [latestLatencyMs, setLatestLatencyMs] = useState<number | null>(null);

  function handlePersonaChange(value: PersonaOption) {
    setPersona(value);
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    const formData = new FormData();
    formData.append("file", file);

    setUploadError(null);
    setUploadStage("uploading");
    setUploadProgress(5);
    setUploadStep("uploading");

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/ingest/upload`, {
        method: "POST",
        headers: {
          "X-User-ID": "demo-user-1",
        },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        const message = data && typeof data.detail === "string" ? data.detail : "Upload failed";
        setUploadError(message);
        setUploadStage("idle");
        setUploadProgress(0);
        setUploadStep(null);
        return;
      }

      const data = (await response.json()) as { task_id: string };
      setUploadTaskId(data.task_id);
      setUploadStage("processing");
      setUploadProgress(10);
      setUploadStep("pending");
    } catch (error) {
      setUploadError("Network error during upload");
      setUploadStage("idle");
      setUploadProgress(0);
      setUploadStep(null);
    }
  }

  useEffect(() => {
    if (!uploadTaskId) {
      return;
    }
    let isCancelled = false;
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    async function fetchStatus() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/ingest/status/${uploadTaskId}`);
        if (!response.ok) {
          return;
        }
        const data = (await response.json()) as {
          status: string;
          step: string | null;
          progress: number;
          error: string | null;
        };
        if (isCancelled) {
          return;
        }
        setUploadStep(data.step);
        setUploadProgress(data.progress);
        if (data.status === "processing" || data.status === "pending") {
          setUploadStage("processing");
        } else if (data.status === "completed") {
          setUploadStage("completed");
          setUploadTaskId(null);
        } else if (data.status === "failed") {
          setUploadStage("idle");
          setUploadTaskId(null);
          setUploadError(data.error ?? "Ingestion failed");
        }
      } catch {
      }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);

    return () => {
      isCancelled = true;
      clearInterval(interval);
    };
  }, [uploadTaskId]);

  function handleSend() {
    if (!inputValue.trim()) {
      return;
    }
    const idBase = String(Date.now());
    const userMessage: ChatMessage = {
      id: `${idBase}-user`,
      role: "user",
      content: inputValue,
    };
    const assistantMessage: ChatMessage = {
      id: `${idBase}-assistant`,
      role: "assistant",
      content:
        persona === "sarcastic"
          ? "Sample sarcastic answer with citation [1]."
          : "Sample highly technical answer with citation [1].",
      citationIds: ["1"],
      costUsd: 0.01,
      latencyMs: 1500,
    };
    setMessages((previous) => [...previous, userMessage, assistantMessage]);
    setInputValue("");
    setSelectedCitationId("1");
    setLatestCostUsd(assistantMessage.costUsd ?? null);
    setLatestLatencyMs(assistantMessage.latencyMs ?? null);
  }

  function handleCitationClick(citationId: string) {
    setSelectedCitationId(citationId);
  }

  return (
    <main className="flex min-h-screen flex-col bg-slate-950 text-slate-50">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex flex-col">
          <span className="text-xs uppercase tracking-wide text-slate-400">
            Enterprise RAG
          </span>
          <span className="text-lg font-semibold text-slate-50">
            Observability-first RAG Workbench
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <div className="flex flex-col items-end">
            <span className="font-medium text-slate-200">Persona</span>
            <div className="mt-1 inline-flex gap-1 rounded-full bg-slate-900 p-1">
              <button
                type="button"
                className={
                  persona === "sarcastic"
                    ? "rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-950"
                    : "rounded-full px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
                }
                onClick={() => handlePersonaChange("sarcastic")}
              >
                Sarcastic
              </button>
              <button
                type="button"
                className={
                  persona === "technical"
                    ? "rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-950"
                    : "rounded-full px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
                }
                onClick={() => handlePersonaChange("technical")}
              >
                Extremely Technical
              </button>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1 md:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-[11px] uppercase tracking-wide">
              Live Evaluation Enabled
            </span>
          </div>
        </div>
      </header>

      <section className="flex flex-1 flex-row overflow-hidden">
        <aside className="flex w-full max-w-xs flex-col border-r border-slate-800 bg-slate-950/40">
          <div className="border-b border-slate-800 px-4 py-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Upload
            </span>
            <p className="mt-1 text-xs text-slate-400">
              Upload a complex technical PDF to demonstrate ingestion.
            </p>
            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/40 px-4 py-5 text-center text-xs text-slate-300 hover:border-emerald-500 hover:bg-slate-900/70">
              <span className="text-sm font-medium text-slate-100">
                Drop the PDF here or click to select
              </span>
              <span className="mt-1 text-[11px] text-slate-500">
                Supports PDF, DOCX, TXT
              </span>
              <input
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                className="hidden"
                onChange={handleFileChange}
              />
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
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-500">
                <span>Dense + Sparse Index</span>
                <span>RBAC Scope: user_id</span>
              </div>
              {uploadError && (
                <div className="text-[11px] text-red-400">
                  {uploadError}
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-1 flex-col justify-between px-4 py-4 text-xs text-slate-300">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Live Config
              </span>
              <p className="mt-1 text-xs text-slate-400">
                Persona controls the prompt orchestrated by the graph.
              </p>
              <div className="mt-3 space-y-1 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">Persona</span>
                  <span className="text-[11px] font-medium text-emerald-400">
                    {persona === "sarcastic" ? "Sarcastic" : "Extremely technical"}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500">
                  This information will be sent as an instruction to the LLM.
                </p>
              </div>
            </div>
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Last interaction
              </span>
              <div className="mt-2 space-y-1 text-[11px] text-slate-300">
                <div className="flex justify-between">
                  <span>Latency</span>
                  <span>
                    {latestLatencyMs != null ? `${latestLatencyMs / 1000}s` : "–"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Cost</span>
                  <span>
                    {latestCostUsd != null ? `$${latestCostUsd.toFixed(4)}` : "–"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col border-r border-slate-800 bg-slate-950/60">
          <div className="flex items-center justify-between border-b border-slate-800 px-6 py-3">
            <div className="flex flex-col">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Chat
              </span>
              <span className="text-xs text-slate-500">
                Ask anything about your technical PDF.
              </span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-400">
              <span>Hybrid Search + Rerank</span>
              <span className="h-1 w-1 rounded-full bg-slate-600" />
              <span>Top 5 chunks</span>
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
            {messages.length === 0 && (
              <div className="mt-16 text-center text-sm text-slate-500">
                <p>Upload a PDF, choose a persona, and ask a hard question.</p>
                <p className="mt-1 text-xs text-slate-600">
                  The answer will appear here, with clickable citations.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                <div
                  className={
                    message.role === "user"
                      ? "max-w-[75%] rounded-2xl bg-emerald-500 px-4 py-3 text-sm text-slate-950"
                      : "max-w-[75%] rounded-2xl bg-slate-900 px-4 py-3 text-sm text-slate-100"
                  }
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.citationIds && message.citationIds.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {message.citationIds.map((citationId) => (
                        <button
                          key={citationId}
                          type="button"
                          onClick={() => handleCitationClick(citationId)}
                          className={
                            selectedCitationId === citationId
                              ? "rounded-full border border-emerald-400 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-300"
                              : "rounded-full border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[11px] text-slate-300 hover:border-emerald-400 hover:text-emerald-300"
                          }
                        >
                          [{citationId}]
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
                  onChange={(event) => setInputValue(event.target.value)}
                  placeholder="Ask something specific about the document. For example: 'Explain the consensus algorithm described in section 4.'"
                  rows={2}
                  className="h-16 w-full resize-none bg-transparent text-sm text-slate-50 outline-none placeholder:text-slate-500"
                />
              </div>
              <button
                type="button"
                onClick={handleSend}
                className="inline-flex h-10 items-center justify-center rounded-full bg-emerald-500 px-6 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
                disabled={!inputValue.trim()}
              >
                Ask
              </button>
            </div>
            <div className="mt-2 flex justify-between text-[11px] text-slate-500">
              <span>Responses are instrumented with Langfuse for cost and latency metrics.</span>
              <span>Streaming and the real RAG graph will be wired to the backend.</span>
            </div>
          </div>
        </section>

        <aside className="hidden w-[28rem] flex-col bg-slate-950/90 md:flex">
          <div className="border-b border-slate-800 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Document Viewer
                </span>
                <span className="text-xs text-slate-500">
                  Click a citation to navigate to the relevant passage.
                </span>
              </div>
              <div className="rounded-full border border-slate-800 bg-slate-900/70 px-3 py-1 text-[11px] text-slate-300">
                Citation [{selectedCitationId ?? "–"}]
              </div>
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4 text-xs text-slate-300">
            {selectedCitationId == null && (
              <div className="mt-16 text-center text-slate-500">
                <p>Click a citation [1], [2], [3] in the model answer.</p>
                <p className="mt-1 text-[11px] text-slate-600">
                  Here you will see the PDF opened, with the text used by RAG highlighted.
                </p>
              </div>
            )}
            {selectedCitationId != null && (
              <div className="space-y-3">
                <div className="rounded-xl border border-emerald-500/60 bg-emerald-500/5 px-3 py-2">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-emerald-300">
                    <span>Citation [{selectedCitationId}]</span>
                    <span>Page 12</span>
                  </div>
                  <p className="mt-2 text-xs text-emerald-100">
                    This block simulates the exact PDF passage used as context by the RAG graph,
                    with visual highlight to demonstrate alignment between answer and source.
                  </p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    Analytics
                  </span>
                  <div className="mt-2 space-y-1 text-[11px]">
                    <div className="flex justify-between">
                      <span>Latency</span>
                      <span>
                        {latestLatencyMs != null ? `${latestLatencyMs / 1000}s` : "–"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Cost</span>
                      <span>
                        {latestCostUsd != null ? `$${latestCostUsd.toFixed(4)}` : "–"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Tokens in/out</span>
                      <span>simulated</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}

