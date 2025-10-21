import { MicButton, MicState } from '@/components/MicButton';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { useMemo, useRef, useState } from 'react';
import { XunfeiIatEngine } from '@/asr/xunfei';

export default function AsrTest() {
  const [frames, setFrames] = useState<number>(0);
  const [lastDb, setLastDb] = useState<number>(-60);
  const [partial, setPartial] = useState('');
  const [finalText, setFinalText] = useState('');
  const engineRef = useRef<XunfeiIatEngine | null>(null);

  // Init engine lazily with env vars
  const ensureEngine = () => {
    if (!engineRef.current) {
      const appId = import.meta.env.VITE_XFYUN_APPID as string;
      const apiKey = import.meta.env.VITE_XFYUN_APIKEY as string;
      const apiSecret = import.meta.env.VITE_XFYUN_APISECRET as string;
      if (!appId || !apiKey || !apiSecret) {
        console.error('Missing XFYUN env: VITE_XFYUN_APPID / VITE_XFYUN_APIKEY / VITE_XFYUN_APISECRET');
      }
      engineRef.current = new XunfeiIatEngine({ appId, apiKey, apiSecret });
    }
    return engineRef.current!;
  };

  const onData = (frame: Int16Array) => {
    setFrames((n) => n + frame.length);
    ensureEngine().pushAudio(frame);
    // compute dB for UI
    let sum = 0;
    for (let i = 0; i < frame.length; i++) {
      const s = frame[i] / 32768;
      sum += s * s;
    }
    const rms = Math.sqrt(sum / frame.length) || 1e-8;
    const db = 20 * Math.log10(rms);
    setLastDb(Math.max(-60, Math.min(0, db)));
  };

  const onStateChange = async (s: MicState) => {
    if (s === 'listening') {
      await ensureEngine().start({
        onPartial: (t) => setPartial(t),
        onFinal: (t) => setFinalText(t),
        onError: (e) => console.error(e),
      });
      setPartial('');
      setFinalText('');
    }
    if (s === 'idle') {
      await ensureEngine().stop();
    }
  };

  const levelBar = useMemo(() => {
    const width = `${((lastDb + 60) / 60) * 100}%`;
    return (
      <div className="h-2 w-full bg-muted rounded">
        <div className="h-2 rounded bg-green-500 transition-all" style={{ width }} />
      </div>
    );
  }, [lastDb]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">ASR（科大讯飞 IAT via API Key，纯前端）</h1>
      <p className="text-sm text-muted-foreground">按住按钮开始录音，松开停止。需要在 .env.local 配置 VITE_XFYUN_*。</p>
      <div className="flex items-center gap-3">
        <MicButton onData={onData} onStateChange={onStateChange} />
        <div className="min-w-40 text-sm">累计样本: {frames.toLocaleString()} @16kHz</div>
      </div>
      {levelBar}
      <Card className="p-3 space-y-2">
        <div className="text-sm font-medium">增量结果</div>
        <Textarea rows={4} value={partial} readOnly />
        <div className="text-sm font-medium">最终结果</div>
        <Textarea rows={4} value={finalText} readOnly />
      </Card>
    </div>
  );
}
