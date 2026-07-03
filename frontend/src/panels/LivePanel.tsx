import { motion } from "framer-motion";
import { Loader2, Mic, Square } from "lucide-react";
import { useRef, useState } from "react";
import { converse, Msg } from "../api/client";
import { useAudioRecorder } from "../hooks/useAudioRecorder";

type Status = "idle" | "recording" | "thinking" | "speaking";

const STATUS_LABEL: Record<Status, string> = {
  idle: "Tap to talk",
  recording: "Listening… tap to send",
  thinking: "Thinking…",
  speaking: "Speaking…",
};

export function LivePanel() {
  const { start, stop, error: micError } = useAudioRecorder();
  const [status, setStatus] = useState<Status>("idle");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [meta, setMeta] = useState<{ provider: string; model: string; ms: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleClick = async () => {
    setErr(null);

    if (status === "idle") {
      try {
        await start();
        setStatus("recording");
      } catch {
        /* mic error surfaced via micError */
      }
      return;
    }

    if (status === "recording") {
      try {
        const blob = await stop();
        setStatus("thinking");
        const res = await converse(blob, messages);
        setMessages((m) => [
          ...m,
          { role: "user", content: res.transcript },
          { role: "assistant", content: res.reply },
        ]);
        setMeta({
          provider: res.provider,
          model: res.model,
          ms: res.stt_ms + res.llm_ms + res.tts_ms,
        });

        setStatus("speaking");
        const audio = new Audio(res.audio_url);
        audioRef.current = audio;
        audio.onended = () => setStatus("idle");
        audio.onerror = () => setStatus("idle");
        await audio.play().catch(() => setStatus("idle"));
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Something went wrong");
        setStatus("idle");
      }
    }
  };

  const busy = status === "thinking";
  const recording = status === "recording";

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center">
      {/* conversation */}
      <div className="mb-10 min-h-[140px] w-full space-y-3">
        {messages.length === 0 && (
          <p className="mt-10 text-center text-sm text-muted">
            Tap the mic and ask something — you'll hear the answer spoken back.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user" ? "bg-accent/15 text-white" : "bg-surface-2 text-white/90"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
      </div>

      {/* mic button */}
      <motion.button
        onClick={handleClick}
        disabled={busy}
        whileTap={{ scale: 0.94 }}
        className={`relative grid h-28 w-28 place-items-center rounded-full transition-colors disabled:opacity-70 ${
          recording ? "bg-record" : "bg-accent"
        }`}
        aria-label={STATUS_LABEL[status]}
      >
        {recording && (
          <motion.span
            className="absolute inset-0 rounded-full bg-record"
            animate={{ scale: [1, 1.4], opacity: [0.5, 0] }}
            transition={{ repeat: Infinity, duration: 1.4, ease: "easeOut" }}
          />
        )}
        {busy ? (
          <Loader2 className="h-9 w-9 animate-spin text-black" />
        ) : recording ? (
          <Square className="h-8 w-8 text-white" />
        ) : (
          <Mic className="h-9 w-9 text-black" />
        )}
      </motion.button>

      <div className="mt-5 h-5 text-sm text-muted">{STATUS_LABEL[status]}</div>

      {meta && !recording && (
        <div className="mt-1 text-xs text-muted/70">
          {meta.provider} · {meta.model} · {meta.ms} ms
        </div>
      )}

      {(err || micError) && (
        <div className="mt-4 rounded-lg border border-record/40 bg-record/10 px-4 py-2 text-sm text-record">
          {err || micError}
        </div>
      )}
    </div>
  );
}
