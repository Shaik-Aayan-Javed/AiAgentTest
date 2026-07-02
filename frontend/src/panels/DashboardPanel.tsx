import { useEffect, useState } from "react";
import { chat, getHealth, Health, ProviderStatus } from "../api/client";

export function DashboardPanel() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatusCard title="Speech-to-Text" p={health?.stt} />
        <StatusCard title="Brain (LLM)" p={health?.llm} />
        <StatusCard title="Text-to-Speech" p={health?.tts} />
      </div>

      <QuickAsk />
    </div>
  );
}

function StatusCard({ title, p }: { title: string; p?: ProviderStatus }) {
  const status = p?.status ?? "…";
  const color =
    status === "healthy" ? "bg-accent" : status === "down" ? "bg-record" : "bg-yellow-500";
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="text-sm text-muted">{title}</div>
      <div className="mt-2 flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
        <span className="font-medium">{p?.provider ?? "—"}</span>
      </div>
      {p?.message && <div className="mt-1 text-xs text-muted/70">{p.message}</div>}
    </div>
  );
}

function QuickAsk() {
  const [text, setText] = useState("");
  const [reply, setReply] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const ask = async () => {
    if (!text.trim()) return;
    setBusy(true);
    setReply(null);
    try {
      const r = await chat([{ role: "user", content: text }]);
      setReply(`${r.text}\n\n— ${r.provider}/${r.model} · ${r.latency_ms} ms`);
    } catch (e) {
      setReply(`Error: ${e instanceof Error ? e.message : "failed"}`);
    }
    setBusy(false);
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-2 text-sm text-muted">Quick ask (text)</div>
      <div className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask the brain anything…"
          className="flex-1 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <button
          onClick={ask}
          disabled={busy}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-black disabled:opacity-60"
        >
          {busy ? "…" : "Ask"}
        </button>
      </div>
      {reply && <pre className="mt-3 whitespace-pre-wrap text-sm text-white/90">{reply}</pre>}
    </div>
  );
}
