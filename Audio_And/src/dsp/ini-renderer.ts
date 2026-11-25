/**
 * BEST SOUND DSP CONTROLLER — Deterministic INI Generator
 * Produces valid ACPWorkbench V2.44.2 INI configuration format matching dsp.ini
 */

import { DspProfile } from './types'

export function renderDspIni(profile: DspProfile): string {
  const lines: string[] = []

  lines.push('; ==============================================================================')
  lines.push(`; BEST SOUND DSP CONTROLLER — ${profile.name}`)
  lines.push(`; Generated: ${new Date().toISOString()}`)
  lines.push('; Hardware: MVSilicon BP1048B2 (FW 0.3.4, Effect 2.45.5, 44.1kHz)')
  lines.push('; ==============================================================================')
  lines.push('')

  lines.push('[Firmware Version]')
  lines.push('Type = 48')
  lines.push('')

  lines.push('[System Control]')
  lines.push('sr_index = 7')
  lines.push('dsp_run = 1')
  lines.push('')

  // 0x87 MVBass Classic
  lines.push('[0x87-MVBass_Classic]')
  lines.push(`enable = ${profile.mvbass.enabled ? 1 : 0}`)
  lines.push(`cutoff_frequency = ${profile.mvbass.cutoffFrequency}`)
  lines.push(`intensity = ${profile.mvbass.intensity}`)
  lines.push('')

  // 0x95 CH1 Bass EQ (Subwoofer 4")
  const ch1Bands = profile.bands.filter((b) => b.channel === 'ch1' || b.channel === 'both')
  lines.push('[0x95-EQ_Filter_Group]')
  lines.push('enable = 1')
  lines.push(`pregain = ${Math.round(profile.masterPreamp * 256)}`)
  lines.push('calculation_type = 0')
  for (let i = 0; i < 10; i++) {
    const b = ch1Bands[i]
    if (b) {
      lines.push(`filter[${i}].enable = ${b.enabled ? 1 : 0}`)
      let typeCode = 0
      if (b.type === 'lowshelf') typeCode = 1
      else if (b.type === 'highshelf') typeCode = 2
      else if (b.type === 'lowpass') typeCode = 3
      else if (b.type === 'highpass') typeCode = 4
      lines.push(`filter[${i}].type = ${typeCode}`)
      lines.push(`filter[${i}].f0 = ${b.hz}`)
      lines.push(`filter[${i}].Q = ${Math.round(b.q * 1024)}`)
      lines.push(`filter[${i}].gain = ${Math.round(b.gain * 256)}`)
    } else {
      lines.push(`filter[${i}].enable = 0`)
      lines.push(`filter[${i}].type = 0`)
      lines.push(`filter[${i}].f0 = 1000`)
      lines.push(`filter[${i}].Q = 1024`)
      lines.push(`filter[${i}].gain = 0`)
    }
  }
  lines.push('')

  // 0x96 CH2 Treble EQ (Mid AIRS + Treble Dome)
  const ch2Bands = profile.bands.filter((b) => b.channel === 'ch2' || b.channel === 'both')
  lines.push('[0x96-EQ_Filter_Group]')
  lines.push('enable = 1')
  lines.push(`pregain = ${Math.round(profile.masterPreamp * 256)}`)
  lines.push('calculation_type = 0')
  for (let i = 0; i < 10; i++) {
    const b = ch2Bands[i]
    if (b) {
      lines.push(`filter[${i}].enable = ${b.enabled ? 1 : 0}`)
      let typeCode = 0
      if (b.type === 'lowshelf') typeCode = 1
      else if (b.type === 'highshelf') typeCode = 2
      else if (b.type === 'lowpass') typeCode = 3
      else if (b.type === 'highpass') typeCode = 4
      lines.push(`filter[${i}].type = ${typeCode}`)
      lines.push(`filter[${i}].f0 = ${b.hz}`)
      lines.push(`filter[${i}].Q = ${Math.round(b.q * 1024)}`)
      lines.push(`filter[${i}].gain = ${Math.round(b.gain * 256)}`)
    } else {
      lines.push(`filter[${i}].enable = 0`)
      lines.push(`filter[${i}].type = 0`)
      lines.push(`filter[${i}].f0 = 1000`)
      lines.push(`filter[${i}].Q = 1024`)
      lines.push(`filter[${i}].gain = 0`)
    }
  }
  lines.push('')

  // 0x98 Treble SPK Gain
  const ch2GainLinear = Math.round(4096 * Math.pow(10, profile.biamp.ch2Gain / 20))
  lines.push('[0x98-Gain_Control]')
  lines.push('enable = 1')
  lines.push('mute = 0')
  lines.push(`gain = ${ch2GainLinear}`)
  lines.push('')

  // 0x99 Mid/Bass SPK Gain
  const ch1GainLinear = Math.round(4096 * Math.pow(10, profile.biamp.ch1Gain / 20))
  lines.push('[0x99-Gain_Control]')
  lines.push('enable = 1')
  lines.push('mute = 0')
  lines.push(`gain = ${ch1GainLinear}`)
  lines.push('')

  return lines.join('\n')
}
