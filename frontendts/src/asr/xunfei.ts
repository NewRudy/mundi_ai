/* Xunfei IAT (WS v2) frontend-only engine. WARNING: Embedding apiKey/apiSecret in frontend will expose secrets. */
export type XfAsrEvents = {
  onPartial?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (e: Error) => void;
};

export type XfOptions = {
  appId: string;
  apiKey: string;
  apiSecret: string;
  business?: Record<string, unknown>;
};

export class XunfeiIatEngine {
  private ws?: WebSocket;
  private started = false;
  private buf: Int16Array[] = [];
  private bufSamples = 0;
  private flushTimer?: number;
  private evts?: XfAsrEvents;
  private accText = '';
  private opts: Required<XfOptions>;

  constructor(opts: XfOptions) {
    this.opts = {
      business: { language: 'zh_cn', domain: 'iat', accent: 'mandarin', ptt: 1, vad_eos: 500 },
      ...opts,
    } as Required<XfOptions>;
  }

  async start(evts: XfAsrEvents) {
    if (this.started) return;
    this.evts = evts;
    this.accText = '';
    const url = await this.buildSignedUrl();
    this.ws = new WebSocket(url);
    this.ws.onopen = () => {
      this.started = true;
      // send start frame
      this.sendFrame(0, new Int16Array(0));
      // start periodic flush (~40ms)
      this.flushTimer = window.setInterval(() => this.flushIfNeeded(), 40);
    };
    this.ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data as string);
        if (data.code !== 0) throw new Error(`xfyun error ${data.code}: ${data.message || ''}`);
        const text = this.extractText(data);
        if (text) {
          this.accText += text;
          this.evts?.onPartial?.(this.accText);
        }
      } catch (e: any) {
        this.evts?.onError?.(e);
      }
    };
    this.ws.onerror = () => this.evts?.onError?.(new Error('WebSocket error'));
    this.ws.onclose = () => {
      if (this.flushTimer) window.clearInterval(this.flushTimer);
      if (this.accText) this.evts?.onFinal?.(this.accText);
      this.started = false;
    };
  }

  pushAudio(frame: Int16Array) {
    if (!this.started) return;
    this.buf.push(frame);
    this.bufSamples += frame.length;
    this.flushIfNeeded();
  }

  async stop() {
    if (!this.started) return;
    try {
      // flush remaining audio
      this.flush(true);
      // send end frame
      this.sendFrame(2, new Int16Array(0));
      this.ws?.close();
    } catch (e: any) {
      this.evts?.onError?.(e);
    } finally {
      if (this.flushTimer) window.clearInterval(this.flushTimer);
      this.flushTimer = undefined;
      this.started = false;
      this.buf = [];
      this.bufSamples = 0;
    }
  }

  private flushIfNeeded() {
    // target ~40ms (640 samples @16k)
    if (this.bufSamples >= 640) this.flush(false);
  }

  private flush(force: boolean) {
    if (!this.ws || (!force && this.bufSamples < 1)) return;
    const total = this.bufSamples;
    const joined = new Int16Array(total);
    let o = 0;
    for (const chunk of this.buf) {
      joined.set(chunk, o);
      o += chunk.length;
    }
    this.buf = [];
    this.bufSamples = 0;
    this.sendFrame(1, joined);
  }

  private sendFrame(status: 0 | 1 | 2, pcm: Int16Array) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const payload: any = {};
    if (status === 0) {
      payload.common = { app_id: this.opts.appId };
      payload.business = this.opts.business;
    }
    payload.data = {
      status,
      format: 'audio/L16;rate=16000',
      encoding: 'raw',
      audio: pcm && pcm.length > 0 ? this.base64FromInt16(pcm) : '',
    };
    this.ws.send(JSON.stringify(payload));
  }

  private extractText(msg: any): string {
    try {
      const ws = msg?.data?.result?.ws;
      if (!Array.isArray(ws)) return '';
      let out = '';
      for (const seg of ws) {
        if (!Array.isArray(seg.cw)) continue;
        for (const c of seg.cw) out += c.w || '';
      }
      return out;
    } catch {
      return '';
    }
  }

  private async buildSignedUrl(): Promise<string> {
    const host = 'iat-api.xfyun.cn';
    const date = new Date().toUTCString();
    const signatureOrigin = `host: ${host}\n` + `date: ${date}\n` + 'GET /v2/iat HTTP/1.1';
    const sign = await this.hmacSha256Base64(signatureOrigin, this.opts.apiSecret);
    const authorizationOrigin = `api_key="${this.opts.apiKey}",algorithm="hmac-sha256",headers="host date request-line",signature="${sign}"`;
    const url = `wss://${host}/v2/iat?authorization=${btoa(authorizationOrigin)}&date=${encodeURIComponent(date)}&host=${host}`;
    return url;
  }

  private async hmacSha256Base64(text: string, secret: string): Promise<string> {
    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    const sig = await crypto.subtle.sign('HMAC', key, enc.encode(text));
    return this.base64FromBytes(new Uint8Array(sig));
  }

  private base64FromInt16(int16: Int16Array): string {
    return this.base64FromBytes(new Uint8Array(int16.buffer, int16.byteOffset, int16.byteLength));
  }

  private base64FromBytes(bytes: Uint8Array): string {
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk) as unknown as number[]);
    }
    return btoa(binary);
  }
}
