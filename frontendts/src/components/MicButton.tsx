import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Mic, Square } from 'lucide-react';

export type MicState = 'idle' | 'listening' | 'processing' | 'error';

export interface MicButtonProps {
  onData?: (frame: Int16Array) => void; // 16k mono PCM frames from worklet
  onStateChange?: (s: MicState) => void;
}

export function MicButton({ onData, onStateChange }: MicButtonProps) {
  const [state, setState] = useState<MicState>('idle');
  const ctxRef = useRef<AudioContext | null>(null);
  const nodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => () => void stop(), []);

  const start = useCallback(async () => {
    if (state !== 'idle') return;
    try {
      setState('processing');
      onStateChange?.('processing');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, noiseSuppression: true, echoCancellation: true, autoGainControl: true } });
      streamRef.current = stream;

      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 48000 });
      ctxRef.current = ctx;

      // Robustly resolve worklet URL in both dev (Vite) and prod (FastAPI static)
      const base = (import.meta as any).env?.BASE_URL || '/';
      const norm = (s: string) => s.replace(/\/+/g, '/');
      const candidates = [
        norm(`${base}/worklets/resampler-16k.js`),
        '/worklets/resampler-16k.js',
      ];
      let loaded = false;
      let lastErr: any = null;
      for (const url of candidates) {
        try {
          await ctx.audioWorklet.addModule(url);
          loaded = true;
          break;
        } catch (e) {
          lastErr = e;
        }
      }
      if (!loaded) {
        throw lastErr || new Error("Failed to load AudioWorklet module");
      }

      const source = ctx.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(ctx, 'resampler-16k');
      node.port.onmessage = (e: MessageEvent<Int16Array>) => {
        const frame = e.data;
        onData?.(frame);
      };

      source.connect(node);
      nodeRef.current = node;
      setState('listening');
      onStateChange?.('listening');
    } catch (e) {
      console.error(e);
      setState('error');
      onStateChange?.('error');
    }
  }, [state, onData, onStateChange]);

  const stop = useCallback(async () => {
    if (state === 'idle') return;
    setState('processing');
    onStateChange?.('processing');
    try {
      nodeRef.current?.port.postMessage({ stop: true });
      nodeRef.current?.disconnect();
      nodeRef.current = null;

      if (ctxRef.current) {
        await ctxRef.current.close();
        ctxRef.current = null;
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }

      setState('idle');
      onStateChange?.('idle');
    } catch (e) {
      console.error(e);
      setState('error');
      onStateChange?.('error');
    }
  }, [state, onStateChange]);

  return (
    <Button
      variant={state === 'listening' ? 'destructive' : 'secondary'}
      size="icon"
      onPointerDown={(e) => {
        e.preventDefault();
        start();
      }}
      onPointerUp={(e) => {
        e.preventDefault();
        stop();
      }}
      onPointerLeave={() => state === 'listening' && stop()}
      title={state === 'listening' ? '松开结束录音' : '按住说话'}
      aria-pressed={state === 'listening'}
    >
      {state === 'listening' ? <Square /> : <Mic />}
      <span className="sr-only">{state === 'listening' ? '停止' : '开始'}</span>
    </Button>
  );
}
