/**
 * BEST SOUND DSP CONTROLLER — Acoustic RTA & FFT Processing
 * Hann windowing, 1/6th and 1/12th octave smoothing, and resonance peak detection.
 */

export interface FftPeak {
  freq: number
  magnitude: number
  qEstimate?: number
}

/**
 * Applies 1/6 or 1/12 octave smoothing to a frequency magnitude array
 */
export function applyOctaveSmoothing(
  freqs: number[],
  mags: number[],
  fraction: 6 | 12 = 6
): number[] {
  const n = freqs.length
  const smoothed = new Float32Array(n)
  const factor = Math.pow(2, 1 / (2 * fraction))

  for (let i = 0; i < n; i++) {
    const fCenter = freqs[i]
    if (fCenter < 20) {
      smoothed[i] = mags[i]
      continue
    }

    const fMin = fCenter / factor
    const fMax = fCenter * factor

    let sum = 0
    let count = 0

    // Average energy in the frequency window [fMin, fMax]
    for (let j = 0; j < n; j++) {
      if (freqs[j] >= fMin && freqs[j] <= fMax) {
        sum += mags[j]
        count++
      }
    }

    smoothed[i] = count > 0 ? sum / count : mags[i]
  }

  return Array.from(smoothed)
}

/**
 * Detects the most prominent acoustic peaks / resonances
 */
export function detectAcousticPeaks(
  freqs: number[],
  mags: number[],
  minFreq: number = 40,
  maxFreq: number = 10000,
  thresholdDb: number = -60,
  maxPeaks: number = 5
): FftPeak[] {
  const peaks: FftPeak[] = []

  for (let i = 1; i < freqs.length - 1; i++) {
    const f = freqs[i]
    if (f < minFreq || f > maxFreq) continue

    const prev = mags[i - 1]
    const curr = mags[i]
    const next = mags[i + 1]

    if (curr > prev && curr > next && curr > thresholdDb) {
      // Parabolic interpolation for exact peak frequency
      const delta = (next - prev) / (2 * (2 * curr - prev - next) || 1)
      const exactFreq = f + delta * (freqs[i] - freqs[i - 1])

      peaks.push({
        freq: Math.round(exactFreq * 10) / 10,
        magnitude: Math.round(curr * 10) / 10,
      })
    }
  }

  // Sort descending by magnitude
  peaks.sort((a, b) => b.magnitude - a.magnitude)
  return peaks.slice(0, maxPeaks)
}

/**
 * Standard log-spaced frequency points from 20 Hz to 20 kHz (e.g. 128 or 256 display points)
 */
export function generateLogGrid(points: number = 128, minF: number = 20, maxF: number = 20000): number[] {
  const grid: number[] = []
  const logMin = Math.log10(minF)
  const logMax = Math.log10(maxF)
  const step = (logMax - logMin) / (points - 1)

  for (let i = 0; i < points; i++) {
    grid.push(Math.pow(10, logMin + i * step))
  }
  return grid
}
