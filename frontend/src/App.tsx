import { useState } from "react";
import { Header } from "./components/layout/Header";
import { PanelKey, Sidebar } from "./components/layout/Sidebar";
import { DashboardPanel } from "./panels/DashboardPanel";
import { LivePanel } from "./panels/LivePanel";

const LABELS: Record<PanelKey, string> = {
  dashboard: "Dashboard",
  live: "Live",
  tts: "TTS Lab",
  stt: "STT Lab",
  voice: "Voice Studio",
};

export default function App() {
  const [panel, setPanel] = useState<PanelKey>("live");

  return (
    <div className="flex h-full">
      <Sidebar active={panel} onSelect={setPanel} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          {panel === "live" && <LivePanel />}
          {panel === "dashboard" && <DashboardPanel />}
          {panel !== "live" && panel !== "dashboard" && <ComingSoon name={LABELS[panel]} />}
        </main>
      </div>
    </div>
  );
}

function ComingSoon({ name }: { name: string }) {
  return (
    <div className="mx-auto mt-24 max-w-md text-center">
      <div className="text-lg font-medium">{name}</div>
      <p className="mt-2 text-sm text-muted">
        This panel is coming next. The Live panel already does the full
        speech-to-speech loop — try it.
      </p>
    </div>
  );
}
