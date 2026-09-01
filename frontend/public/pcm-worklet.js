/* AudioWorklet: raw Float32 PCM capture.
 *
 * WHY NOT MediaRecorder: it hands you a WebM/Opus container you then have to decode
 * server-side -- hours of pain for nothing. AudioWorklet gives raw samples directly.
 *
 * Buffers to exactly 1.0 s at the context rate, then posts a Float32Array to the main
 * thread, which resamples to 16 kHz and ships it over the WebSocket.
 */
class PCMWorklet extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.target = (options.processorOptions && options.processorOptions.frameSamples) || sampleRate;
    this.buf = new Float32Array(this.target);
    this.n = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    for (let i = 0; i < ch.length; i++) {
      this.buf[this.n++] = ch[i];
      if (this.n >= this.target) {
        this.port.postMessage(this.buf.slice(0));
        this.n = 0;
      }
    }
    return true;
  }
}
registerProcessor('pcm-worklet', PCMWorklet);
