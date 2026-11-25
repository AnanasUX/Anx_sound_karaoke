/**
 * BEST SOUND DSP CONTROLLER — Safety Limits and Normalization Rules
 * Prevents speaker damage, DSP digital clipping, and invalid parameter injection.
 */

import { DspBand, MVBassConfig, BiAmpConfig } from './types'

export const DSP_LIMITS = {
  // Master Preamp
  PREAMP_MIN_DB: -18.0,
  PREAMP_MAX_DB: 6.0,
  PREAMP_DEFAULT_DB: 0.0,

  // PEQ Band Gain
  GAIN_MIN_DB: -12.0,
  GAIN_MAX_DB: 6.0,
  GAIN_DISPLAY_MIN: -18.0,
  GAIN_DISPLAY_MAX: 18.0,

  // PEQ Q Factor
  Q_MIN: 0.2,
  Q_MAX: 12.0,
  Q_DEFAULT: 1.0,

  // Frequency range in Hz
  FREQ_MIN_HZ: 20,
  FREQ_MAX_HZ: 20000,

  // MVBass limits
  MVBASS_INTENSITY_MIN: 0,
  MVBASS_INTENSITY_MAX: 100,
  MVBASS_CUTOFF_MIN_HZ: 40,
  MVBASS_CUTOFF_MAX_HZ: 200,

  // Bi-Amp digital gain
  BIAMP_GAIN_MIN_DB: -24.0,
  BIAMP_GAIN_MAX_DB: 12.0,

  // Maximum allowed total sum boost across all bands to avoid distortion
  MAX_ALLOWED_HEADROOM_BOOST_DB: 14.0,
} as const

export function clamp(value: number, min: number, max: number): number {
  if (isNaN(value)) return min
  return Math.min(Math.max(value, min), max)
}

export function validateBand(band: Partial<DspBand>): DspBand {
  const hz = clamp(band.hz ?? 1000, DSP_LIMITS.FREQ_MIN_HZ, DSP_LIMITS.FREQ_MAX_HZ)
  const gain = clamp(band.gain ?? 0, DSP_LIMITS.GAIN_MIN_DB, DSP_LIMITS.GAIN_MAX_DB)
  const q = clamp(band.q ?? 1.0, DSP_LIMITS.Q_MIN, DSP_LIMITS.Q_MAX)

  return {
    id: band.id ?? 1,
    name: band.name ?? `Band ${band.id ?? 1}`,
    hz: Math.round(hz),
    gain: Math.round(gain * 10) / 10,
    q: Math.round(q * 100) / 100,
    type: band.type ?? 'peaking',
    enabled: band.enabled ?? true,
    channel: band.channel ?? 'both',
    color: band.color ?? '#00E5FF',
    desc: band.desc,
  }
}

export function validateMVBass(config: Partial<MVBassConfig>): MVBassConfig {
  return {
    enabled: config.enabled ?? true,
    cutoffFrequency: clamp(
      config.cutoffFrequency ?? 75,
      DSP_LIMITS.MVBASS_CUTOFF_MIN_HZ,
      DSP_LIMITS.MVBASS_CUTOFF_MAX_HZ
    ),
    intensity: clamp(
      config.intensity ?? 65,
      DSP_LIMITS.MVBASS_INTENSITY_MIN,
      DSP_LIMITS.MVBASS_INTENSITY_MAX
    ),
  }
}

export function validateBiAmp(config: Partial<BiAmpConfig>): BiAmpConfig {
  return {
    ch1Gain: clamp(config.ch1Gain ?? 0.0, DSP_LIMITS.BIAMP_GAIN_MIN_DB, DSP_LIMITS.BIAMP_GAIN_MAX_DB),
    ch2Gain: clamp(config.ch2Gain ?? 0.0, DSP_LIMITS.BIAMP_GAIN_MIN_DB, DSP_LIMITS.BIAMP_GAIN_MAX_DB),
    crossoverFreq: config.crossoverFreq ?? 2500,
  }
}

/**
 * Calculates recommended auto-headroom attenuation based on the highest positive peak
 */
export function calculateAutoHeadroom(bands: DspBand[]): number {
  const maxGain = bands
    .filter((b) => b.enabled)
    .reduce((acc, curr) => Math.max(acc, curr.gain), 0)

  if (maxGain > 0) {
    // Attenuate preamp by max positive gain to guarantee zero digital clipping
    return Math.max(DSP_LIMITS.PREAMP_MIN_DB, -maxGain)
  }
  return 0.0
}
