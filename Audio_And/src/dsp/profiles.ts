/**
 * BEST SOUND DSP CONTROLLER — Verified Audio Profiles & State Manager
 * Fully grounded in docs/DSP_PROFILE_MAPPING.md and golden register tables.
 */

import { DspProfile, DspBand } from './types'
import { validateBand, validateMVBass, validateBiAmp } from './limits'

export const STANDARD_BANDS_TEMPLATE: Omit<DspBand, 'gain'>[] = [
  {
    id: 1,
    name: 'Sub',
    hz: 62,
    q: 0.8,
    type: 'peaking',
    enabled: true,
    channel: 'ch1',
    color: '#00E5FF',
    desc: 'Deep sub-bass extension (CH1 Woofer)',
  },
  {
    id: 2,
    name: 'Kick',
    hz: 85,
    q: 1.1,
    type: 'peaking',
    enabled: true,
    channel: 'ch1',
    color: '#30D9F0',
    desc: 'Punch & impact (CH1 Woofer)',
  },
  {
    id: 3,
    name: 'Mid-Bass',
    hz: 125,
    q: 1.3,
    type: 'peaking',
    enabled: true,
    channel: 'ch1',
    color: '#5AC9E0',
    desc: 'Low-end body (CH1 Woofer)',
  },
  {
    id: 4,
    name: 'Anti-Boom',
    hz: 165,
    q: 2.4,
    type: 'peaking',
    enabled: true,
    channel: 'ch1',
    color: '#FF8A3D',
    desc: 'Controls 5L box resonance (CH1 Woofer)',
  },
  {
    id: 5,
    name: 'Vocal Body',
    hz: 500,
    q: 1.2,
    type: 'peaking',
    enabled: true,
    channel: 'ch2',
    color: '#6BE2CC',
    desc: 'Warmth for Mid AIRS (CH2)',
  },
  {
    id: 6,
    name: 'Lead Mid',
    hz: 1000,
    q: 1.4,
    type: 'peaking',
    enabled: true,
    channel: 'ch2',
    color: '#78D4F2',
    desc: 'Clarity and presence (CH2)',
  },
  {
    id: 7,
    name: 'Vocal Clarity',
    hz: 2500,
    q: 1.8,
    type: 'peaking',
    enabled: true,
    channel: 'ch2',
    color: '#B4A7FF',
    desc: 'Upper midrange brilliance (CH2)',
  },
  {
    id: 8,
    name: 'Treble Air',
    hz: 8000,
    q: 0.9,
    type: 'highshelf',
    enabled: true,
    channel: 'ch2',
    color: '#D4AF37',
    desc: 'Silk dome tweeter shimmer (CH2)',
  },
]

function createBands(gains: number[]): DspBand[] {
  return STANDARD_BANDS_TEMPLATE.map((template, idx) =>
    validateBand({
      ...template,
      gain: gains[idx] ?? 0.0,
    })
  )
}

export const VERIFIED_PROFILES: DspProfile[] = [
  {
    id: 'bo-8ohm-24v',
    name: 'B&O 8Ω · 24V Signature',
    category: 'curated',
    tag: 'STUDIO SIGNATURE',
    accent: '#D4AF37',
    description:
      'Chữ ký âm thanh Bang & Olufsen: Bass đầm sâu, mid mộc ngọt ngào, treble dome tơi nhuyễn không chói.',
    masterPreamp: -1.5,
    mvbass: validateMVBass({ enabled: true, cutoffFrequency: 75, intensity: 75 }),
    biamp: validateBiAmp({ ch1Gain: 0.0, ch2Gain: 0.5, crossoverFreq: 2500 }),
    bands: createBands([5.5, 6.2, 3.2, -3.5, 2.2, 3.5, 3.8, 5.0]),
    verified: true,
    sourceFile: 'tune_bo_signature.py / ACPWorkbench_Tuned_2CH.ini',
  },
  {
    id: 'jbl-boombox',
    name: 'JBL Boombox Party',
    category: 'curated',
    tag: 'HIGH ENERGY',
    accent: '#FF8A3D',
    description:
      'Năng lượng cực đại cho nhạc EDM, Remix, Dance. Đẩy mạnh sub 62Hz và kick 85Hz, MVBass 85% uy lực.',
    masterPreamp: -2.0,
    mvbass: validateMVBass({ enabled: true, cutoffFrequency: 65, intensity: 85 }),
    biamp: validateBiAmp({ ch1Gain: 1.0, ch2Gain: -0.5, crossoverFreq: 2400 }),
    bands: createBands([6.8, 7.5, 4.5, -4.2, 0.5, 1.8, 3.4, 4.2]),
    verified: true,
    sourceFile: 'tune_jbl_boombox_profile.py',
  },
  {
    id: 'sweet-vocal',
    name: 'Sweet Vocal & Bolero',
    category: 'curated',
    tag: 'VOCAL FOCUS',
    accent: '#B4A7FF',
    description:
      'Tối ưu cho nhạc Trữ tình, Bolero, Acoustic. Dải trung 500Hz-2.5kHz dày dặn, giảm bass tránh ù giọng.',
    masterPreamp: -1.0,
    mvbass: validateMVBass({ enabled: true, cutoffFrequency: 85, intensity: 45 }),
    biamp: validateBiAmp({ ch1Gain: -1.0, ch2Gain: 1.5, crossoverFreq: 2600 }),
    bands: createBands([2.4, 1.8, 1.2, -2.5, 3.8, 4.6, 5.2, 3.3]),
    verified: true,
    sourceFile: 'tune_sweet_vocal.py / dsp_punchy_bass_sweet_vocal.ini',
  },
  {
    id: 'clean-no-noise',
    name: 'Clean Studio (No Hiss)',
    category: 'curated',
    tag: 'AUDIOPHILE CLEAN',
    accent: '#30D9F0',
    description:
      'Cân chỉnh gain thận trọng loại bỏ triệt để tiếng xì nền (hiss) và hiện tượng nghẽn limiter ở mức âm lượng cao.',
    masterPreamp: -0.5,
    mvbass: validateMVBass({ enabled: true, cutoffFrequency: 80, intensity: 55 }),
    biamp: validateBiAmp({ ch1Gain: 0.0, ch2Gain: 0.0, crossoverFreq: 2500 }),
    bands: createBands([3.0, 3.5, 1.5, -2.0, 1.0, 2.0, 2.5, 3.0]),
    verified: true,
    sourceFile: 'tune_clean_no_noise.py / dsp_clean_no_noise.ini',
  },
  {
    id: 'flat-reference',
    name: 'Flat Reference (Zero EQ)',
    category: 'curated',
    tag: 'CALIBRATION BASE',
    accent: '#00E5FF',
    description:
      'Điểm xuất phát trung tính hoàn toàn (0.0 dB all bands, MVBass bypass) phục vụ đo đáp tuyến phòng với RTA.',
    masterPreamp: 0.0,
    mvbass: validateMVBass({ enabled: false, cutoffFrequency: 75, intensity: 0 }),
    biamp: validateBiAmp({ ch1Gain: 0.0, ch2Gain: 0.0, crossoverFreq: 2500 }),
    bands: createBands([0, 0, 0, 0, 0, 0, 0, 0]),
    verified: true,
    sourceFile: 'dsp_restore_original.ini / dsp.ini',
  },
]

export interface ProfileDiff {
  bandDiffs: Array<{
    id: number
    name: string
    hz: number
    oldGain: number
    newGain: number
    deltaGain: number
  }>
  mvbassDiff?: {
    oldIntensity: number
    newIntensity: number
    oldCutoff: number
    newCutoff: number
  }
  preampDiff?: {
    oldPreamp: number
    newPreamp: number
  }
}

export function computeProfileDiff(current: DspProfile, proposed: DspProfile): ProfileDiff {
  const bandDiffs = current.bands.map((currBand, idx) => {
    const propBand = proposed.bands[idx] ?? currBand
    return {
      id: currBand.id,
      name: currBand.name,
      hz: currBand.hz,
      oldGain: currBand.gain,
      newGain: propBand.gain,
      deltaGain: Math.round((propBand.gain - currBand.gain) * 10) / 10,
    }
  })

  return {
    bandDiffs,
    mvbassDiff: {
      oldIntensity: current.mvbass.intensity,
      newIntensity: proposed.mvbass.intensity,
      oldCutoff: current.mvbass.cutoffFrequency,
      newCutoff: proposed.mvbass.cutoffFrequency,
    },
    preampDiff: {
      oldPreamp: current.masterPreamp,
      newPreamp: proposed.masterPreamp,
    },
  }
}
