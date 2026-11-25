/**
 * BEST SOUND DSP CONTROLLER — Core Domain Models & Types
 * Target Chip: MVSilicon BP1048B2 (Firmware Type 48, Effect 2.45.5)
 */

export type FilterType = 'peaking' | 'lowshelf' | 'highshelf' | 'lowpass' | 'highpass' | 'notch'

export interface DspBand {
  id: number // 1 to 8 (or 1 to 10)
  name: string // 'Sub', 'Kick', 'Mid-Bass', etc.
  hz: number // Center frequency in Hz (20 to 20000)
  gain: number // Gain in dB (-12.0 to +6.0, display range -18 to +18)
  q: number // Quality factor Q (0.2 to 12.0)
  type: FilterType
  enabled: boolean
  channel: 'ch1' | 'ch2' | 'both'
  color: string
  desc?: string
}

export interface MVBassConfig {
  enabled: boolean
  cutoffFrequency: number // 40 Hz to 200 Hz (default ~75Hz)
  intensity: number // 0% to 100% (default 40-75%)
}

export interface BiAmpConfig {
  ch1Gain: number // Bass digital gain in dB (-24.0 to +12.0)
  ch2Gain: number // Treble digital gain in dB (-24.0 to +12.0)
  crossoverFreq?: number // Acoustic or electronic crossover point (~2500 Hz)
}

export interface LimiterConfig {
  enabled: boolean
  threshold: number // dBFS (-24 to 0)
  attack: number // ms
  release: number // ms
  ratio: number // 1.0 to 20.0
}

export interface DspProfile {
  id: string
  name: string
  category: 'curated' | 'user' | 'ai_generated' | 'backup'
  description: string
  tag: string
  accent: string
  masterPreamp: number // Master gain in dB (-18.0 to +6.0)
  mvbass: MVBassConfig
  biamp: BiAmpConfig
  limiter?: LimiterConfig
  bands: DspBand[]
  checksum?: string
  sourceFile?: string
  verified: boolean
  createdAt?: string
}

export interface RtaMeasurement {
  id: string
  timestamp: number
  sampleRate: number
  fftSize: number
  frequencies: number[]
  magnitudes: number[] // Live SPL/dBFS levels
  peaks: Array<{ freq: number; magnitude: number }>
  avgLevel: number
  targetCurve?: 'flat' | 'harman' | 'bass_heavy' | 'sweet_vocal'
}

export interface DeviceInfo {
  connected: boolean
  transportType: 'usb_otg' | 'bluetooth_spp' | 'mock'
  deviceName: string
  vendorId?: number
  productId?: number
  firmwareType?: number // 48 = BP1048B2
  firmwareVersion?: string // e.g. "0.3.4"
  effectVersion?: string // e.g. "2.45.5"
}

export interface FlashBackup {
  id: string
  timestamp: string
  profileName: string
  registers: Record<string, string> // hex strings of registers
  rawBytes: number[] // Complete frame stream
  checksum: string
}

export type FlashStatus =
  | 'idle'
  | 'checking'
  | 'backing_up'
  | 'flashing'
  | 'verifying'
  | 'rebooting'
  | 'verified'
  | 'rolling_back'
  | 'error'

export interface FlashProgress {
  status: FlashStatus
  progress: number // 0 to 100
  currentPacket: number
  totalPackets: number
  message: string
  errorMessage?: string
}

export interface GeminiHandoffPackage {
  measurementId: string
  nonce: string
  timestamp: string
  deviceContext: {
    chip: 'BP1048B2'
    firmwareType: 48
    sampleRate: 44100
    speakerLayout: '2.1 Bi-Amp (Sub 4" + Mid AIRS + Treble Dome)'
    enclosureVolume: '5L'
  }
  currentSettings: {
    masterPreamp: number
    mvbass: MVBassConfig
    biamp: BiAmpConfig
    bands: Array<{
      id: number
      name: string
      hz: number
      gain: number
      q: number
    }>
  }
  measurementSummary: {
    avgLevel: number
    resonancePeaks: Array<{ freq: number; magnitude: number }>
    lowFreqRollOff: number
    highFreqResponse: number
    targetGoal: string
  }
}

export interface GeminiResultPackage {
  measurementId: string
  nonce: string
  proposedBands: Array<{
    id: number
    gain: number
    q?: number
    hz?: number
  }>
  proposedMvbass?: {
    intensity?: number
    cutoffFrequency?: number
  }
  proposedPreamp?: number
  reasoning: string
  confidenceScore: number
}
