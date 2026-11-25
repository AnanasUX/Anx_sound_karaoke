/**
 * BEST SOUND DSP CONTROLLER — Acoustic Test Signal Generator
 * Generates calibrated pink noise, logarithmic sine sweeps, and single-tone test bursts.
 */

export class TestSignalGenerator {
  private ctx: AudioContext | null = null
  private activeSource: AudioNode | null = null
  private gainNode: GainNode | null = null

  private initContext() {
    if (!this.ctx || this.ctx.state === 'closed') {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      this.ctx = new AudioCtx()
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume()
    }
  }

  public stop() {
    if (this.activeSource) {
      try {
        if ('stop' in this.activeSource && typeof (this.activeSource as AudioScheduledSourceNode).stop === 'function') {
          (this.activeSource as AudioScheduledSourceNode).stop()
        }
        this.activeSource.disconnect()
      } catch (ignored) {}
      this.activeSource = null
    }
    if (this.gainNode) {
      this.gainNode.disconnect()
      this.gainNode = null
    }
  }

  /**
   * Plays continuous pink noise (equal energy per octave)
   * Uses Paul Kellet's filtered white noise algorithm
   */
  public playPinkNoise(levelDbFS: number = -12.0) {
    this.stop()
    this.initContext()
    if (!this.ctx) return

    const bufferSize = this.ctx.sampleRate * 2 // 2-second looped buffer
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate)
    const output = buffer.getChannelData(0)

    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0

    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1
      b0 = 0.99886 * b0 + white * 0.0555179
      b1 = 0.99332 * b1 + white * 0.0750759
      b2 = 0.96900 * b2 + white * 0.1538520
      b3 = 0.86650 * b3 + white * 0.3104856
      b4 = 0.55000 * b4 + white * 0.5329522
      b5 = -0.7616 * b5 - white * 0.0168980
      output[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11
      b6 = white * 0.115926
    }

    const whiteNoise = this.ctx.createBufferSource()
    whiteNoise.buffer = buffer
    whiteNoise.loop = true

    this.gainNode = this.ctx.createGain()
    const linearGain = Math.pow(10, Math.min(0, levelDbFS) / 20)
    this.gainNode.gain.setValueAtTime(linearGain, this.ctx.currentTime)

    whiteNoise.connect(this.gainNode)
    this.gainNode.connect(this.ctx.destination)

    whiteNoise.start()
    this.activeSource = whiteNoise
  }

  /**
   * Plays a calibrated logarithmic sine sweep from 20 Hz to 20,000 Hz
   */
  public playSineSweep(durationSec: number = 5.0, levelDbFS: number = -12.0, onComplete?: () => void) {
    this.stop()
    this.initContext()
    if (!this.ctx) return

    const osc = this.ctx.createOscillator()
    this.gainNode = this.ctx.createGain()
    const linearGain = Math.pow(10, Math.min(0, levelDbFS) / 20)
    this.gainNode.gain.setValueAtTime(linearGain, this.ctx.currentTime)

    const startTime = this.ctx.currentTime + 0.05
    const endTime = startTime + durationSec

    osc.type = 'sine'
    osc.frequency.setValueAtTime(20, startTime)
    osc.frequency.exponentialRampToValueAtTime(20000, endTime)

    osc.connect(this.gainNode)
    this.gainNode.connect(this.ctx.destination)

    osc.onended = () => {
      this.activeSource = null
      if (onComplete) onComplete()
    }

    osc.start(startTime)
    osc.stop(endTime)
    this.activeSource = osc
  }

  /**
   * Plays a single test tone (e.g. 60Hz Sub, 1kHz Mid, 10kHz Treble)
   */
  public playTone(freqHz: number, levelDbFS: number = -12.0) {
    this.stop()
    this.initContext()
    if (!this.ctx) return

    const osc = this.ctx.createOscillator()
    this.gainNode = this.ctx.createGain()
    const linearGain = Math.pow(10, Math.min(0, levelDbFS) / 20)
    this.gainNode.gain.setValueAtTime(linearGain, this.ctx.currentTime)

    osc.type = 'sine'
    osc.frequency.setValueAtTime(freqHz, this.ctx.currentTime)

    osc.connect(this.gainNode)
    this.gainNode.connect(this.ctx.destination)

    osc.start()
    this.activeSource = osc
  }

  public isPlaying(): boolean {
    return this.activeSource !== null
  }
}

export const signalGenerator = new TestSignalGenerator()
