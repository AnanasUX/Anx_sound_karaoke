/**
 * BEST SOUND DSP CONTROLLER — Mock DSP Transport (Hardware Simulator)
 * Allows safe desktop testing of full flash lifecycle without bricking risk.
 */

import { DspTransport } from './transport'
import { DeviceInfo, FlashProgress } from '../dsp/types'

export class MockDspTransport implements DspTransport {
  public readonly type = 'mock'
  private connected = false
  private registers: Record<string, string> = {
    '0x00': '0x30', // Type 48 (BP1048B2)
    '0x01': '0x07', // 44.1 kHz
    '0x87': '0x3F000800', // Cutoff 63Hz, intensity 8%
    '0x95': 'DEFAULT_CH1_EQ',
    '0x96': 'DEFAULT_CH2_EQ',
    '0x98': '0x7017', // Treble gain
    '0x99': '0xC012', // Mid/Bass gain
  }

  public isConnected(): boolean {
    return this.connected
  }

  public getDeviceInfo(): DeviceInfo {
    return {
      connected: this.connected,
      transportType: 'mock',
      deviceName: 'MVSilicon BP1048B2 (Virtual OTG)',
      vendorId: 0x4c4a,
      productId: 0x8888,
      firmwareType: 48,
      firmwareVersion: '0.3.4',
      effectVersion: '2.45.5',
    }
  }

  public async connect(): Promise<boolean> {
    await new Promise((r) => setTimeout(r, 400))
    this.connected = true
    return true
  }

  public async disconnect(): Promise<void> {
    this.connected = false
  }

  public async sendPacket(packet: Uint8Array): Promise<boolean> {
    if (!this.connected) return false
    // Packet must start with 0xA5 0x5A and end with 0x16
    if (packet.length < 5 || packet[0] !== 0xa5 || packet[1] !== 0x5a) {
      return false
    }
    const regId = `0x${packet[2].toString(16).toUpperCase().padStart(2, '0')}`
    this.registers[regId] = Array.from(packet.slice(5, -1))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
    return true
  }

  public async sendPackets(
    packets: Uint8Array[],
    onProgress?: (progress: FlashProgress) => void
  ): Promise<boolean> {
    if (!this.connected) return false

    const total = packets.length
    for (let i = 0; i < total; i++) {
      const pkt = packets[i]
      const ok = await this.sendPacket(pkt)
      if (!ok) return false

      if (onProgress) {
        onProgress({
          status: 'flashing',
          progress: Math.round(((i + 1) / total) * 100),
          currentPacket: i + 1,
          totalPackets: total,
          message: `Đang truyền gói ${i + 1}/${total} (Reg 0x${pkt[2].toString(16).toUpperCase()})...`,
        })
      }
      // Pacing delay (12ms)
      await new Promise((r) => setTimeout(r, 12))
    }
    return true
  }

  public async readRegisters(): Promise<Record<string, string>> {
    if (!this.connected) return {}
    await new Promise((r) => setTimeout(r, 200))
    return { ...this.registers }
  }
}
