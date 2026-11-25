/**
 * BEST SOUND DSP CONTROLLER — Binary Packet Builder for MVSilicon BP1048B2
 * Frames raw register packets for direct OTG transfer:
 * [0xA5, 0x5A] [RegID] [LengthLow, LengthHigh] [Payload...] [0x16]
 */

import { DspBand, MVBassConfig } from './types'

function s16LE(val: number): [number, number] {
  const intVal = Math.round(val) & 0xffff
  return [intVal & 0xff, (intVal >> 8) & 0xff]
}

function u16LE(val: number): [number, number] {
  const intVal = Math.round(val) & 0xffff
  return [intVal & 0xff, (intVal >> 8) & 0xff]
}

/**
 * Builds 0x95 (CH1 Bass EQ) or 0x96 (CH2 Treble EQ) packet
 * 10 biquad slots, 107 bytes payload total
 */
export function buildEqPacket(regId: 0x95 | 0x96, pregainDb: number, filters: DspBand[]): Uint8Array {
  const payload: number[] = []

  // All parameter flag
  payload.push(0xff)

  // Enable flag
  payload.push(...u16LE(1))

  // Pre-gain in dB * 256
  payload.push(...s16LE(pregainDb * 256))

  // Calculation type (0)
  payload.push(...u16LE(0))

  // 10 filter slots
  for (let i = 0; i < 10; i++) {
    if (i < filters.length) {
      const flt = filters[i]
      payload.push(...u16LE(flt.enabled ? 1 : 0))

      // Filter type: 0: Peaking, 1: LowShelf, 2: HighShelf, 3: LowPass, 4: HighPass
      let typeCode = 0
      if (flt.type === 'lowshelf') typeCode = 1
      else if (flt.type === 'highshelf') typeCode = 2
      else if (flt.type === 'lowpass') typeCode = 3
      else if (flt.type === 'highpass') typeCode = 4

      payload.push(...u16LE(typeCode))
      payload.push(...u16LE(flt.hz))
      payload.push(...u16LE(Math.round(flt.q * 1024)))
      payload.push(...s16LE(Math.round(flt.gain * 256)))
    } else {
      payload.push(...u16LE(0))
      payload.push(...u16LE(0))
      payload.push(...u16LE(0))
      payload.push(...u16LE(0))
      payload.push(...s16LE(0))
    }
  }

  // Frame: [0xA5, 0x5A] [Reg] [LenLow, LenHigh] [Payload...] [0x16]
  const packet: number[] = [0xa5, 0x5a, regId, payload.length & 0xff, (payload.length >> 8) & 0xff]
  packet.push(...payload)
  packet.push(0x16)

  return new Uint8Array(packet)
}

/**
 * Builds 0x87 (MVBass Classic) packet
 * Length: 7 bytes payload
 */
export function buildMVBassPacket(config: MVBassConfig): Uint8Array {
  const payload: number[] = []
  payload.push(0xff) // all parameter
  payload.push(...u16LE(config.enabled ? 1 : 0))
  payload.push(...u16LE(config.cutoffFrequency))
  payload.push(...u16LE(config.intensity))

  const packet: number[] = [0xa5, 0x5a, 0x87, payload.length & 0xff, 0x00]
  packet.push(...payload)
  packet.push(0x16)

  return new Uint8Array(packet)
}

/**
 * Builds 0x98 (Treble Gain) or 0x99 (Mid/Bass Gain) packet
 * Length: 7 bytes payload
 */
export function buildGainPacket(regId: 0x98 | 0x99, gainLinear: number): Uint8Array {
  const payload: number[] = []
  payload.push(0xff) // all parameter
  payload.push(...u16LE(1)) // enable
  payload.push(...u16LE(0)) // mute = 0
  payload.push(...u16LE(gainLinear)) // gain (e.g. 4096 = 0dB, 6000 = +3.3dB)

  const packet: number[] = [0xa5, 0x5a, regId, payload.length & 0xff, 0x00]
  packet.push(...payload)
  packet.push(0x16)

  return new Uint8Array(packet)
}
