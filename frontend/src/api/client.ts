// Thin API client. Uses relative /api paths (Vite proxies them to :8000).

const BASE = "/api";

export interface ProviderStatus {
  status: string;
  provider: string;
  latency_ms?: number;
  message?: string;
}

export interface Health {
  status: string;
  environment: string;
  tts: ProviderStatus;
  stt: ProviderStatus;
  llm: ProviderStatus;
}

export async function getHealth(): Promise<Health> {
  const r = await fetch(`${BASE}/health`);
  if (!r.ok) throw new Error(`health ${r.status}`);
  return r.json();
}

export interface Msg {
  role: "user" | "assistant";
  content: string;
}

export interface ConverseResult {
  transcript: string;
  reply: string;
  audio_url: string;
  provider: string;
  model: string;
  stt_ms: number;
  llm_ms: number;
  tts_ms: number;
}

async function detail(r: Response): Promise<string> {
  try {
    const j = await r.json();
    return j.detail || `HTTP ${r.status}`;
  } catch {
    return `HTTP ${r.status}`;
  }
}

export async function converse(audio: Blob, history: Msg[]): Promise<ConverseResult> {
  const fd = new FormData();
  fd.append("audio", audio, "turn.webm");
  fd.append("history", JSON.stringify(history));
  const r = await fetch(`${BASE}/converse`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await detail(r));
  return r.json();
}

export interface ChatResult {
  text: string;
  provider: string;
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
}

export async function chat(messages: Msg[]): Promise<ChatResult> {
  const r = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!r.ok) throw new Error(await detail(r));
  return r.json();
}
