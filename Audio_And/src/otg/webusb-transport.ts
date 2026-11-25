/**
 * BEST SOUND DSP CONTROLLER — WebUSB OTG Transport
 * Interfaces with physical MVSilicon BP1048B2 over WebUSB (Chrome Android OTG)
 */

import { DspTransport } from './transport'
import { DeviceInfo, FlashProgress } from '../dsp/types'

export class WebUsbDspTransport implements DspTransport {
  public readonly type = 'usb_otg'
  private device: USBDevice | null = null
  private interfaceNumber = 0
  private endpointOutNumber = 1

  public isConnected(): boolean {
    return this.device !== null && this.device.opened
  }

  public getDeviceInfo(): DeviceInfo {
    return {
      connected: this.isConnected(),
      transportType: 'usb_otg',
      deviceName: this.device?.productName || 'MVSilicon BP1048B2',
      vendorId: this.device?.vendorId,
      productId: this.device?.productId,
      firmwareType: 48,
    }
  }

  public async connect(): Promise<boolean> {
    if (typeof navigator === 'undefined' || !navigator.usb) {
      console.warn('WebUSB không khả dụng trên trình duyệt này.')
      return false
    }

    try {
      this.device = await navigator.usb.requestDevice({
        filters: [{ vendorId: 0x4c4a }, { vendorId: 0x8888 }],
      })

      await this.device.open()
      if (this.device.configuration === null) {
        await this.device.selectConfiguration(1)
      }

      // Claim first available interface
      if (this.device.configuration?.interfaces.length) {
        const intf = this.device.configuration.interfaces[0]
        this.interfaceNumber = intf.interfaceNumber
        await this.device.claimInterface(this.interfaceNumber)

        const outEp = intf.alternate.endpoints.find((e) => e.direction === 'out')
        if (outEp) {
          this.endpointOutNumber = outEp.endpointNumber
        }
      }

      return true
    } catch (err) {
      console.error('Lỗi kết nối WebUSB:', err)
      this.device = null
      return false
    }
  }

  public async disconnect(): Promise<void> {
    if (this.device && this.device.opened) {
      try {
        await this.device.releaseInterface(this.interfaceNumber)
        await this.device.close()
      } catch (ignored) {}
    }
    this.device = null
  }

  public async sendPacket(packet: Uint8Array): Promise<boolean> {
    if (!this.isConnected() || !this.device) return false

    try {
      // Primary: Bulk/Interrupt OUT transfer
      const res = await this.device.transferOut(this.endpointOutNumber, packet)
      if (res.status === 'ok') return true

      // Fallback: HID Set_Report Control Transfer (0x21, 0x09)
      const ctrlRes = await this.device.controlTransferOut(
        {
          requestType: 'class',
          recipient: 'interface',
          request: 0x09, // SET_REPORT
          value: 0x0200, // Report type Output (0x02), Report ID 0x00
          index: this.interfaceNumber,
        },
        packet
      )
      return ctrlRes.status === 'ok'
    } catch (err) {
      console.error('Lỗi gửi gói WebUSB:', err)
      return false
    }
  }

  public async sendPackets(
    packets: Uint8Array[],
    onProgress?: (progress: FlashProgress) => void
  ): Promise<boolean> {
    if (!this.isConnected()) return false

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
          message: `Đang nạp gói ${i + 1}/${total}...`,
        })
      }
      // Mandatory pacing delay (12ms)
      await new Promise((r) => setTimeout(r, 12))
    }
    return true
  }

  public async readRegisters(): Promise<Record<string, string>> {
    // In WebUSB, reading registers requires control transfer or bulk in
    return {}
  }
}
