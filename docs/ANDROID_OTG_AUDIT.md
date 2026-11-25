# ANDROID OTG & BLUETOOTH AUDIT — BEST SOUND DSP

## 1. Executive Summary
This audit reviews the physical connection, protocol, framing, and transfer mechanisms of the **BEST SOUND DSP CONTROLLER** across native Android implementations (`android_app/`) and standalone APK artifacts.

The target DSP chip is the **MVSilicon BP1048B2** (Firmware Type 48, Effect 2.45.5), operating in 2.1 Bi-Amp configuration. Communication can take place via:
1. **USB OTG (Host Mode)**: Direct Type-C cable connection from Android smartphone to the DSP board.
2. **Bluetooth RFCOMM / SPP**: Wireless serial stream using Standard Serial Port Profile (`00001101-0000-1000-8000-00805F9B34FB`).

---

## 2. Hardware Identification & USB Descriptors

### Vendor and Product IDs
- **Primary MVSilicon VID:** `0x4C4A`
- **Secondary / Generic VID:** `0x8888`
- **Product Name String Matching:** Any device matching case-insensitively `best`, `sound`, `mvsilicon`, or `audio`.

### USB Interfaces & Endpoints
- **Interface Classes:**
  - `0x03`: `USB_CLASS_HID` (Standard Human Interface Device).
  - `0xFF`: Vendor-Specific class.
- **Transfer Mechanisms:**
  - **Method A (Bulk / Interrupt OUT):** If an OUT endpoint (`USB_DIR_OUT`) is present on the claimed interface, `connection.bulkTransfer(endpointOut, data, length, 1000)` is invoked.
  - **Method B (Control Transfer Fallback):** If no dedicated bulk OUT endpoint is exposed, standard HID Set_Report control request is used:
    - `requestType`: `0x21` (`USB_TYPE_CLASS | USB_RECIP_INTERFACE`)
    - `request`: `0x09` (`SET_REPORT`)
    - `value`: `0x0200` (Report Type Output: `0x02`, Report ID: `0x00`)
    - `index`: Interface number (`activeInterface.getId()`)
    - `data`: Packet buffer.

---

## 3. Communication Protocol & Frame Framing

### Frame Structure
Every individual register command is framed as:
```
[0xA5 0x5A] [Register_ID] [Length_Low] [Length_High] [Payload...] [0x16]
```
- **Sync Header:** `0xA5 0x5A` (2 bytes)
- **Register ID:** 1 byte (e.g. `0x87` for MVBass, `0x95` for CH1 Bass EQ, `0x96` for CH2 Treble EQ, `0x98`/`0x99` for Gains)
- **Length Field:** 2 bytes (Little-Endian payload size)
- **Payload:** Biquad coefficients (Q4.27 fixed-point) or effect configuration structs
- **Sync Tail:** `0x16` (1 byte frame terminator)

### Transmission Pacing
- The MCU on the BP1048B2 board requires processing time between parameter updates to recalculate internal filter states without popping or dropping packets.
- **Enforced Delay:** Minimum **12 ms** sleep between successive frame packets.

---

## 4. APK Version History & Capabilities

| APK File | Build Type | Main Package | Key Capabilities |
| :--- | :--- | :--- | :--- |
| `BestSound_DSP_v1.0.apk` | Release | `com.bestsound.dsp` | Preset switcher (B&O, JBL, Vocal, Flat), USB OTG connection. |
| `BestSound_DSP_v2.0_Wireless.apk` | Release | `com.bestsound.dsp` | Adds Bluetooth SPP discovery and wireless profile streaming. |
| `BestSound_DSP_v3.0_PEQ_MultiBand.apk` | Debug/Release | `com.bestsound.dsp` | **Real-time 8-Band PEQ control**, dynamic register calculation (0x95 & 0x96), MVBass slider (0x87), Master Gain (0x98/0x99). |
| `MVSilicon DSP Tuner.apk` | OEM Utility | `com.mvsilicon.tuner` | OEM reference tool for BP1048 series; used to verify register IDs and protocol handshakes. |

---

## 5. Mobile Web / Next.js OTG Bridge Architecture

To connect the Next.js Mobile-First Web Application with the physical DSP board over USB OTG:
1. **WebUSB API (Chromium / Chrome Android):**
   - Directly requests `navigator.usb.requestDevice({ filters: [{ vendorId: 0x4c4a }, { vendorId: 0x8888 }] })`.
   - Claims interface `0` or `1`, executes `transferOut()` or `controlTransferOut()`.
2. **Android Webview Bridge Fallback:**
   - When hosted inside an Android WebView or PWA container, `@JavascriptInterface` bridges calls from React (`window.AndroidDsp.sendFrame(hex)`) directly into `UsbDspManager.sendPacket()`.
3. **Mock Transport (Offline/Simulator):**
   - For desktop and simulated testing, a deterministic virtual DSP state simulates read-back, checksum verification, and rollback without hardware.

---

## 6. Safety & Verification Rules for Hardware Flash
1. **Pre-check:** Read device ID (`0x00`) to confirm Type 48 (BP1048B2) before transmitting any write commands.
2. **Mandatory Backup:** Always dump current registers into a `FlashBackup` state before initiating full profile flashing.
3. **No Automatic Flashing:** Gemini RTA analysis must only suggest PEQ parameters to the UI; user must explicitly click "Apply" and confirm diff before sending over OTG.
4. **Read-Back & Rollback:** Upon transmission completion, read back registers and verify checksum. If mismatch occurs, automatically trigger rollback to the backup.
