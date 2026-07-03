import { Loader2, Mic, Play, Square, Trash2, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  deleteVoiceSample,
  getVoiceSample,
  SampleStatus,
  saveVoiceSample,
  synthesize,
  voiceSampleUrl,
} from "../api/client";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { blobToWav } from "../lib/wav";

const SAMPLE_SCRIPT =
  "Hello, thank you for calling. I'm here to help you today. Please go ahead and " +
  "tell me what you need, and I'll do my best to assist you as quickly as possible.";

export function VoiceStudioPanel() {
  const { start, stop, error: micError } = useAudioRecorder();
  const [sample, setSample] = useState<SampleStatus | null>(null);
  const [recording, setRecording] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = () => getVoiceSample().then(setSample).catch(() => setSample(null));
  useEffect(() => {
    refresh();
  }, []);

  const onRecordClick = async () => {
    setErr(null);
    if (!recording) {
      try {
        await start();
        setRecording(true);
      } catch {
        /* micError shows it */
      }
      return;
    }
    // stop → convert → upload
    setRecording(false);
    setSaving(true);
    try {
      const webm = await stop();
      const wav = await blobToWav(webm);
      const status = await saveVoiceSample(wav);
      setSample(status);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save the recording");
    }
    setSaving(false);
  };

  const onDelete = async () => {
    await deleteVoiceSample();
    refresh();
  };

  const seconds = sample?.duration_ms ? (sample.duration_ms / 1000).toFixed(1) : null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Voice Studio</h1>
        <p className="mt-1 text-sm text-muted">
          Record a short sample of your voice — Coqui clones it so the assistant
          speaks as you.
        </p>
      </div>

      {/* Sample card */}
      <div className="rounded-xl border border-border bg-surface p-5">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">Your voice sample</div>
          {sample?.exists ? (
            <span className="flex items-center gap-1.5 text-xs text-accent">
              <span className="h-2 w-2 rounded-full bg-accent" />
              Saved · {seconds}s
            </span>
          ) : (
            <span className="text-xs text-muted">Not recorded yet</span>
          )}
        </div>

        <div className="mt-4 rounded-lg border border-border bg-surface-2 p-4 text-sm text-muted">
          <div className="mb-1 text-xs uppercase tracking-wide text-muted/60">
            Read this aloud (15–30s, quiet room, normal pace)
          </div>
          "{SAMPLE_SCRIPT}"
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={onRecordClick}
            disabled={saving}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-60 ${
              recording ? "bg-record text-white" : "bg-accent text-black"
            }`}
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : recording ? (
              <Square className="h-4 w-4" />
            ) : (
              <Mic className="h-4 w-4" />
            )}
            {saving ? "Saving…" : recording ? "Stop & save" : sample?.exists ? "Re-record" : "Record"}
          </button>

          {sample?.exists && !recording && (
            <>
              <button
                onClick={() => new Audio(voiceSampleUrl()).play().catch(() => {})}
                className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-white hover:bg-surface-2"
              >
                <Play className="h-4 w-4" /> Play sample
              </button>
              <button
                onClick={onDelete}
                className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-muted hover:text-record"
              >
                <Trash2 className="h-4 w-4" /> Delete
              </button>
            </>
          )}
        </div>

        {(err || micError) && <div className="mt-3 text-sm text-record">{err || micError}</div>}
      </div>

      <VoiceTest hasSample={!!sample?.exists} />
    </div>
  );
}

function VoiceTest({ hasSample }: { hasSample: boolean }) {
  const [text, setText] = useState("This is my own cloned voice.");
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const speak = async () => {
    if (!text.trim()) return;
    setBusy(true);
    setErr(null);
    setProvider(null);
    try {
      const res = await synthesize(text);
      setProvider(res.provider);
      await new Audio(res.audio_url).play();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Synthesis failed");
    }
    setBusy(false);
  };

  const clonedOK = provider?.startsWith("Coqui");

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Volume2 className="h-4 w-4 text-accent" /> Test the voice
      </div>

      <div className="mt-3 flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && speak()}
          className="flex-1 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <button
          onClick={speak}
          disabled={busy}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-black disabled:opacity-60"
        >
          {busy ? "…" : "Speak"}
        </button>
      </div>

      {provider && (
        <div className={`mt-3 text-xs ${clonedOK ? "text-accent" : "text-yellow-500"}`}>
          Spoken by {provider}
          {!clonedOK && " — this isn't Coqui, so it's not your cloned voice yet (see setup below)."}
        </div>
      )}
      {err && <div className="mt-3 text-sm text-record">{err}</div>}

      {!hasSample && (
        <div className="mt-3 text-xs text-muted">Record a sample above first.</div>
      )}

      <div className="mt-4 rounded-lg border border-border bg-surface-2 p-3 text-xs text-muted/80">
        <div className="mb-1 font-medium text-muted">To hear your cloned voice:</div>
        <ol className="list-decimal space-y-0.5 pl-4">
          <li>Set <code className="text-white/80">TTS_PROVIDER=coqui</code> in <code>.env</code></li>
          <li>Start Coqui: <code className="text-white/80">docker compose up -d</code> (first run downloads ~1.8GB)</li>
          <li>After saving/replacing your sample, restart it: <code className="text-white/80">docker compose restart coqui-tts</code></li>
        </ol>
      </div>
    </div>
  );
}
