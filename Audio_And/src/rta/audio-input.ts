/**
 * BEST SOUND DSP CONTROLLER — Microphone RTA Capture
 * Captures real acoustic measurement from the device microphone via Web Audio API.
 */

import { applyOctaveSmoothing, detectAcousticPeaks, FftPeak } from './fft'

export interface RtaFrame {
  frequencies: number[]
  magnitudes: number[]
  peaks: FftPeak[]
  avgLevelDb: number
}

export class RealMicrophoneRta {
  private ctx: AudioContext | null = null
  private stream: MediaStream | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private analyser: AnalyserNode | null = null
  private animationId: number | null = null
  private isRunning: boolean = false
  private callback: ((frame: RtaFrame) => void) | null = null

  public async start(onFrame: (frame: RtaFrame) => void): Promise<boolean> {
    if (this.isRunning) return true

    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      this.ctx = new AudioCtx()
      if (this.ctx.state === 'suspended') {
        await this.ctx.resume()
      }

      // Request raw, unadulterated microphone stream (disable AGC and noise suppression for acoustic calibration)
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      })

      this.sourceNode = this.ctx.createMediaStreamSource(this.stream)
      this.analyser = this.ctx.createAnalyser()
      this.analyser.fftSize = 4096
      this.analyser.smoothingTimeConstant = 0.8
      this.analyser.minDecibels = -100
      this.analyser.maxDecibels = -10

      this.sourceNode.connect(this.analyser)
      this.callback = onFrame
      this.isRunning = true

      this.processLoop()
      return true
    } catch (err) {
      console.error('Microphone access failed:', err)
      this.stop()
      return false
    }
  }

  private processLoop = () => {
    if (!this.isRunning || !this.analyser || !this.ctx) return

    const bufferLength = this.analyser.frequencyBinCount
    const dataArray = new Float32Array(bufferLength)
    this.analyser.getFloatFrequencyData(dataArray)

    const nyquist = this.ctx.sampleRate / 2
    const freqs: number[] = new Array(bufferLength)
    const mags: number[] = new Array(bufferLength)

    let totalEnergy = 0
    let validCount = 0

    for (let i = 0; i < bufferLength; i++) {
      const f = (i * nyquist) / bufferLength
      const m = dataArray[i]
      freqs[i] = f
      mags[i] = m

      if (f >= 40 && f <= 15000 && isFinite(m)) {
        totalEnergy += m
        validCount++
      }
    }

    const avgLevel = validCount > 0 ? totalEnergy / validCount : -70
    const smoothedMags = applyOctaveSmoothing(freqs, mags, 6)
    const peaks = detectAcousticPeaks(freqs, smoothedMags, 40, 10000, -75, 4)

    if (this.callback) {
      this.callback({
        frequencies: freqs,
        magnitudes: smoothedMags,
        peaks,
        avgLevelDb: Math.round(avgLevel * 10) / 10,
      })
    }

    this.animationId = requestAnimationFrame(this.processLoop)
  }

  public stop() {
    this.isRunning = false
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect()
      this.sourceNode = null
    }
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop())
      this.stream = null
    }
    if (this.ctx && this.ctx.state !== 'closed') {
      this.ctx.close().catch(() => {})
      this.ctx = null
    }
    this.callback = null
  }

  public active(): boolean {
    return this.isRunning
  }
}

export const micRta = new RealMicrophoneRta()
