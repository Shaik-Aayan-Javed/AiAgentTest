import { useEffect, useState } from "react";
import { getHealth, Health, ProviderStatus } from "../../api/client";

export function Header() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    const load = () => getHealth().then(setHealth).catch(() => setHealth(null));
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border px-6">
      <div className="text-sm text-muted">AI Voice Assistant</div>
      <div className="flex items-center gap-5 text-xs">
        <Pill label="STT" p={health?.stt} />
        <Pill label="LLM" p={health?.llm} />
        <Pill label="TTS" p={health?.tts} />
      </div>
    </header>
  );
}

function Pill({ label, p }: { label: string; p?: ProviderStatus }) {
  const status = p?.status ?? "unknown";
  const color =
    status === "healthy"
      ? "bg-accent"
      : status === "down"
        ? "bg-record"
        : "bg-yellow-500";
  return (
    <div className="flex items-center gap-1.5" title={p?.provider ?? label}>
      <span className={`h-2 w-2 rounded-full ${color}`} />
      <span className="text-muted">{label}</span>
    </div>
  );
}
