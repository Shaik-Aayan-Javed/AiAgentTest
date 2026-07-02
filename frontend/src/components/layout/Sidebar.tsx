import { AudioLines, LayoutDashboard, Mic, UserRound, Volume2 } from "lucide-react";

export type PanelKey = "dashboard" | "live" | "tts" | "stt" | "voice";

const ITEMS: { key: PanelKey; label: string; icon: typeof Mic }[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "live", label: "Live", icon: Mic },
  { key: "tts", label: "TTS Lab", icon: Volume2 },
  { key: "stt", label: "STT Lab", icon: AudioLines },
  { key: "voice", label: "Voice Studio", icon: UserRound },
];

export function Sidebar({
  active,
  onSelect,
}: {
  active: PanelKey;
  onSelect: (k: PanelKey) => void;
}) {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface/40">
      <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-accent/20">
          <AudioLines className="h-4 w-4 text-accent" />
        </div>
        <span className="font-semibold tracking-tight">VoiceAI</span>
      </div>

      <nav className="space-y-1 p-3">
        {ITEMS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => onSelect(key)}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
              active === key
                ? "bg-accent/15 text-accent"
                : "text-muted hover:bg-surface-2 hover:text-white"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </nav>

      <div className="mt-auto p-4 text-xs text-muted/60">Prototype · Phases 1–4</div>
    </aside>
  );
}
