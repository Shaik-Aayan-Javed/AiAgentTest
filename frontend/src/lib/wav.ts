// Convert a recorded audio Blob (webm/opus from MediaRecorder) into a mono
// 16-bit PCM WAV Blob — the format Coqui wants for voice cloning.
//
// Done client-side via the Web Audio API so there's no fragile server-side
// audio conversion: decode → downmix to mono → resample → encode WAV.

export async function blobToWav(blob: Blob, targetRate = 24000): Promise<Blob> {
  const arrayBuf = await blob.arrayBuffer();
  const ctx = new AudioContext();
  try {
    const audioBuf = await ctx.decodeAudioData(arrayBuf);
    const wav = encodeWav(audioBuf, targetRate);
    return new Blob([wav], { type: "audio/wav" });
  } finally {
    ctx.close();
  }
}

function encodeWav(buffer: AudioBuffer, targetRate: number): ArrayBuffer {
  const channels = buffer.numberOfChannels;

  // Downmix to mono.
  const length = buffer.length;
  const mono = new Float32Array(length);
  for (let c = 0; c < channels; c++) {
    const data = buffer.getChannelData(c);
    for (let i = 0; i < length; i++) mono[i] += data[i] / channels;
  }

  const samples = resample(mono, buffer.sampleRate, targetRate);

  const bytesPerSample = 2;
  const dataSize = samples.length * bytesPerSample;
  const out = new ArrayBuffer(44 + dataSize);
  const view = new DataView(out);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true); // subchunk1 size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, targetRate, true);
  view.setUint32(28, targetRate * bytesPerSample, true); // byte rate
  view.setUint16(32, bytesPerSample, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return out;
}

function resample(data: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return data;
  const ratio = from / to;
  const newLength = Math.round(data.length / ratio);
  const out = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const idx = i * ratio;
    const i0 = Math.floor(idx);
    const i1 = Math.min(i0 + 1, data.length - 1);
    const frac = idx - i0;
    out[i] = data[i0] * (1 - frac) + data[i1] * frac;
  }
  return out;
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
}
