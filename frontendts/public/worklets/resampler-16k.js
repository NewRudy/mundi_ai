class Resampler16k extends AudioWorkletProcessor {
  constructor() {
    super();
    this._ratio = sampleRate / 16000; // input samples per 1 output sample
    this._carry = 0; // fractional position carried between process() calls
    this._buf = [];
  }

  _flushIfNeeded() {
    if (this._buf.length >= 160) { // ~10ms at 16k
      const frame = new Int16Array(this._buf.length);
      for (let j = 0; j < this._buf.length; j++) {
        let s = this._buf[j];
        if (s > 1) s = 1; else if (s < -1) s = -1;
        frame[j] = s < 0 ? Math.round(s * 32768) : Math.round(s * 32767);
      }
      this.port.postMessage(frame);
      this._buf.length = 0;
    }
  }

  process(inputs) {
    const input = inputs[0] && inputs[0][0];
    if (!input) return true;

    let pos = this._carry; // position in input for next output sample
    const len = input.length;

    while (pos < len) {
      const i = Math.floor(pos);
      const frac = pos - i;
      // Linear interpolation between i and i+1
      const a = input[i] || 0;
      const b = input[i + 1] || a;
      const s = a + (b - a) * frac;
      this._buf.push(s);
      this._flushIfNeeded();
      pos += this._ratio;
    }

    this._carry = pos - len; // save fractional remainder for next block
    return true;
  }
}

registerProcessor('resampler-16k', Resampler16k);
