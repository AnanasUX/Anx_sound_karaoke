/**
 * BEST SOUND DSP CONTROLLER — OTG Hardware Transport Interface
 */

import { DeviceInfo, FlashProgress } from '../dsp/types'

export interface DspTransport {
  readonly type: 'usb_otg' | 'bluetooth_spp' | 'mock'
  isConnected(): boolean
  getDeviceInfo(): DeviceInfo
  connect(): Promise<boolean>
  disconnect(): Promise<void>
  sendPacket(packet: Uint8Array): Promise<boolean>
  sendPackets(
    packets: Uint8Array[],
    onProgress?: (progress: FlashProgress) => void
  ): Promise<boolean>
  readRegisters(): Promise<Record<string, string>>
}
