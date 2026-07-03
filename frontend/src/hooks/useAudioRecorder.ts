import { useCallback, useRef, useState } from "react";

/**
 * Records the microphone via the browser MediaRecorder API.
 * start() asks for mic permission and begins; stop() resolves with the audio Blob.
 */
export function useAudioRecorder() {
  const [isRecording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const rec = new MediaRecorder(stream);
      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      rec.start();
      recorderRef.current = rec;
      setRecording(true);
    } catch {
      setError("Microphone access denied or unavailable.");
      throw new Error("mic-unavailable");
    }
  }, []);

  const stop = useCallback((): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      const rec = recorderRef.current;
      // Guard: nothing recording, or already stopped → resolve with what we have
      // rather than throwing InvalidStateError or hanging forever.
      if (!rec || rec.state === "inactive") {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        setRecording(false);
        return resolve(new Blob(chunksRef.current, { type: "audio/webm" }));
      }
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: rec.mimeType || "audio/webm",
        });
        streamRef.current?.getTracks().forEach((t) => t.stop());
        setRecording(false);
        resolve(blob);
      };
      try {
        rec.stop();
      } catch (e) {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        setRecording(false);
        reject(e);
      }
    });
  }, []);

  return { isRecording, error, start, stop };
}
