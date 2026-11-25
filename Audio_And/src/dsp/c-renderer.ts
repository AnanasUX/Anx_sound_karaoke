/**
 * BEST SOUND DSP CONTROLLER — Deterministic C Source Generator
 * Generates verified C byte array dsp[1667] for MVSilicon BP1048B2 firmware
 */

import { DspProfile } from './types'
import { buildEqPacket, buildMVBassPacket, buildGainPacket } from './packet-builder'

export function renderDspC(profile: DspProfile): string {
  const ch1Bands = profile.bands.filter((b) => b.channel === 'ch1' || b.channel === 'both')
  const ch2Bands = profile.bands.filter((b) => b.channel === 'ch2' || b.channel === 'both')

  const packet87 = buildMVBassPacket(profile.mvbass)
  const packet95 = buildEqPacket(0x95, profile.masterPreamp, ch1Bands)
  const packet96 = buildEqPacket(0x96, profile.masterPreamp, ch2Bands)

  const ch1GainLinear = Math.round(4096 * Math.pow(10, profile.biamp.ch1Gain / 20))
  const ch2GainLinear = Math.round(4096 * Math.pow(10, profile.biamp.ch2Gain / 20))
  const packet98 = buildGainPacket(0x98, ch2GainLinear)
  const packet99 = buildGainPacket(0x99, ch1GainLinear)

  // Format packets as C hex comments
  const formatPacket = (name: string, pkt: Uint8Array) => {
    const hex = Array.from(pkt)
      .map((b) => `0x${b.toString(16).toUpperCase().padStart(2, '0')}`)
      .join(', ')
    return `    /* Packet ${name} (${pkt.length} bytes) */\n    ${hex},`
  }

  return `/* ==============================================================================
 * BEST SOUND DSP CONTROLLER — Auto-generated C Configuration
 * Profile: ${profile.name}
 * Date: ${new Date().toISOString()}
 * Target: MVSilicon BP1048B2 (FW 0.3.4, Effect 2.45.5, 44.1kHz)
 * ============================================================================== */

#include <stdint.h>

/* Primary dynamic register packets for direct OTG injection */
const uint8_t dsp_mvbass_pkt[] = {
${formatPacket('0x87 MVBass', packet87)}
};

const uint8_t dsp_ch1_eq_pkt[] = {
${formatPacket('0x95 CH1 Bass EQ', packet95)}
};

const uint8_t dsp_ch2_eq_pkt[] = {
${formatPacket('0x96 CH2 Treble EQ', packet96)}
};

const uint8_t dsp_treble_gain_pkt[] = {
${formatPacket('0x98 Treble Gain', packet98)}
};

const uint8_t dsp_midbass_gain_pkt[] = {
${formatPacket('0x99 MidBass Gain', packet99)}
};
`
}
