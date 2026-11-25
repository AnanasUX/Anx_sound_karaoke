# BẢNG ĐỐI CHIẾU VÀ ÁNH XẠ PROFILE DSP (DSP PROFILE MAPPING)
**Dự án:** BEST SOUND DSP CONTROLLER - Chip MVSilicon BP1048B2
**Thời gian cập nhật:** 19/11/2026
**Mục tiêu:** Xác định nguồn chân lý (Source of Truth) cho từng cấu hình âm thanh, thông số bộ lọc, crossover, DRC và register map.

---

## 1. THÔNG SỐ PHẦN CỨNG & HỆ THỐNG GỐC

- **Chipset:** MVSilicon BP1048B2 (Shanghai Mountain View Silicon Co., Ltd.)
- **Firmware Type:** `48` (`0x30` = BP1048B2)
- **Firmware Version:** `0.3.4` (Internal code: `0x00, 0x03, 0x04`)
- **Effect Version:** `2.45.5` (Internal code: `0x02, 0x2D, 0x05`)
- **Sample Rate:** `44.1 kHz` (Register 0x01 system_sr_index = `7`)
- **Bit Depth:** 24-bit (32-bit internal fixed-point DSP accumulator)
- **Cấu hình phần cứng loa (Hardware Topology):**
  - Cấu hình: 2 Kênh Bi-Amp (Active 2.1)
  - **Kênh 1 (CH1 - Subwoofer):** Củ loa Subwoofer 4 inch 40W RMS / 80W Peak (8Ω / 4Ω)
    - Cắt tần số dưới (HPF): 55 Hz (Bậc 4 Linkwitz-Riley 24dB/oct)
    - Cắt tần số trên (LPF): 350 Hz (Bậc 4 Linkwitz-Riley 24dB/oct)
    - Register: `0x95-EQ` (Bass EQ), `0x99-Gain_Control` (Mid/Bass SPK Volume)
  - **Kênh 2 (CH2 - Satellite Mid-Treble):** Củ Mid AIRS 3 inch 15W + Củ Treble Dome 20-30W (có tụ cản bảo vệ 2.2µF - 3.3µF)
    - Cắt tần số dưới (HPF): 350 Hz (Bậc 4 Linkwitz-Riley 24dB/oct)
    - Cắt tần số trên (LPF): Bypassed (cho tép vươn tới 20kHz)
    - Register: `0x96-EQ` (Treble EQ), `0x98-Gain_Control` (Treble SPK Volume)
- **Bảo vệ màng loa (DRC Limiter):** Register `0x93-DRC` (Attack 5-10ms, Release 80-150ms)

---

## 2. MA TRẬN ÁNH XẠ CHI TIẾT TỪNG PROFILE

### 2.1. B&O 8Ω · 24V (Signature / Punchy Bass Sweet Vocal)
* **File nguồn INI:** `dsp_punchy_bass_sweet_vocal.ini`, `dsp.ini`, `acp_workbench_config.ini`
* **File nguồn C:** `dsp_punchy_bass_sweet_vocal.c`, `dsp.c`
* **Script khởi tạo:** `tune_8ohm_24v_profile.py`, `tune_bo_signature.py`
* **Trạng thái:** **VERIFIED (Source of Truth cho cấu hình hiện hành)**
* **Thông số chi tiết:**
  - **Master Preamp:** -1.5 dB
  - **CH1 Bass Digital Gain (0x99):** `7200` (+4.9 dB)
  - **CH2 Treble Digital Gain (0x98):** `8000` (+5.8 dB)
  - **MVBass (0x87):** Enable = 1 | Cutoff = **58 Hz** | Intensity = **28%**
  - **8 Dải PEQ chính trên màn hình điện thoại:**
    1. Band 1 (`62 Hz`): Gain = **+5.5 dB**, Q = 0.85 (Deep Sub Boombox)
    2. Band 2 (`85 Hz`): Gain = **+6.2 dB**, Q = 0.90 (Trống kick punchy)
    3. Band 3 (`125 Hz`): Gain = **+3.2 dB**, Q = 0.95 (Mid-bass đầy đặn)
    4. Band 4 (`165 Hz`): Gain = **-3.5 dB**, Q = 1.20 (Cắt triệt để ù rền cộng hưởng thùng 5L)
    5. Band 5 (`500 Hz`): Gain = **+2.2 dB**, Q = 0.80 (Cắt đục, ấm giọng)
    6. Band 6 (`1.0 kHz`): Gain = **+3.5 dB**, Q = 0.80 (Vocal nam rõ nét)
    7. Band 7 (`2.5 kHz`): Gain = **+3.8 dB**, Q = 0.80 (Vocal nữ bay bổng)
    8. Band 8 (`8.0 kHz`): Gain = **+5.0 dB**, Q = 0.80 (Tép dome leng keng)

### 2.2. JBL Boombox (Heavy Kick & High Energy EDM)
* **File nguồn INI:** `dsp_punchy_bass_sweetan.ini`
* **Script khởi tạo:** `tune_jbl_boombox_profile.py`, `upgrade_jbl_deep_punchy_bass.py`
* **Trạng thái:** **VERIFIED**
* **Thông số chi tiết:**
  - **Master Preamp:** -2.8 dB
  - **CH1 Bass Digital Gain (0x99):** `8000` (+5.8 dB)
  - **CH2 Treble Digital Gain (0x98):** `7500` (+5.2 dB)
  - **MVBass (0x87):** Enable = 1 | Cutoff = **65 Hz** | Intensity = **40%**
  - **8 Dải PEQ:**
    1. `62 Hz`: +6.8 dB
    2. `85 Hz`: +7.5 dB
    3. `125 Hz`: +4.5 dB
    4. `165 Hz`: -4.2 dB
    5. `500 Hz`: +0.5 dB
    6. `1.0 kHz`: +1.8 dB
    7. `2.5 kHz`: +3.4 dB
    8. `8.0 kHz`: +4.2 dB

### 2.3. Sweet Vocal (Acoustic, Bolero, Nhạc Vàng)
* **File nguồn INI:** `dsp_punchy_bass_sweetan.ini`
* **Script khởi tạo:** `tune_punchy_sweet.py`, `upgrade_ultimate_punchy_sweet.py`
* **Trạng thái:** **VERIFIED**
* **Thông số chi tiết:**
  - **Master Preamp:** -1.2 dB
  - **CH1 Bass Digital Gain (0x99):** `6000` (+3.3 dB)
  - **CH2 Treble Digital Gain (0x98):** `8500` (+6.3 dB)
  - **MVBass (0x87):** Enable = 1 | Cutoff = **55 Hz** | Intensity = **18%**
  - **8 Dải PEQ:**
    1. `62 Hz`: +2.4 dB
    2. `85 Hz`: +1.8 dB
    3. `125 Hz`: +1.2 dB
    4. `165 Hz`: -2.5 dB
    5. `500 Hz`: +3.8 dB (Độ dày giọng hát)
    6. `1.0 kHz`: +4.6 dB (Ngọt ngào, tiến về phía trước)
    7. `2.5 kHz`: +5.2 dB (Chi tiết nhạc cụ mộc, ngân nga)
    8. `8.0 kHz`: +3.3 dB

### 2.4. Flat Reference (Kiểm Âm Tiêu Chuẩn 0 dB)
* **File nguồn:** Nguồn chuẩn mực âm học lý thuyết
* **Trạng thái:** **VERIFIED**
* **Thông số chi tiết:**
  - **Master Preamp:** 0.0 dB
  - **CH1 Bass Digital Gain (0x99):** `4096` (0.0 dB)
  - **CH2 Treble Digital Gain (0x98):** `4096` (0.0 dB)
  - **MVBass (0x87):** Bypassed (Intensity = 0%)
  - **Tất cả 8 dải PEQ:** Gain = **0.0 dB** (Phẳng tuyệt đối)

### 2.5. Original / Restore Original (Khôi Phục Gốc Xuất Xưởng)
* **File nguồn INI:** `dsp_original.ini`, `dsp_restore_original.ini`
* **File nguồn C:** `dsp_original.c`, `dsp_restore_original.c`
* **Trạng thái:** **VERIFIED (Factory Safe Rollback Anchor)**
* **Thông số chi tiết:**
  - **CH1 Bass Digital Gain (0x99):** `4096` (0.0 dB)
  - **CH2 Treble Digital Gain (0x98):** `8239` (+6.07 dB)
  - **MVBass (0x87):** Cutoff = 63 Hz, Intensity = 8%
  - **PEQ 0x95 & 0x96:** Toàn bộ filter cân chỉnh thêm đều tắt (0.0 dB)

### 2.6. Các profile phụ trợ đã kiểm toán
1. **Clean No Noise:** `dsp_clean_no_noise.ini` / `.c` (Hạ gain tép xuống 6800 để triệt tiêu tiếng xì nền hiss).
2. **Smooth No Stutter:** `dsp_smooth_no_stutter.ini` / `.c` (Tối ưu buffer DAC và PGA để chống giật âm khi nhận Bluetooth yếu).
3. **Warm Bass Bright Treble:** `dsp_warm_bass_bright_treble.ini` / `.c` (Âm trầm ấm áp 65Hz +2.0dB, tép sáng 8kHz +4.0dB).
4. **Master Ultimate:** `dsp_master_ultimate.ini` / `.c` (Cân bằng năng lượng tối đa giữa lực bass và chi tiết tép dome).

---

## 3. BẢNG TỔNG HỢP MATRIX GIÁ TRỊ PEQ 8 BĂNG CHO UI

| Tên Profile | 62Hz (Sub) | 85Hz (Kick) | 125Hz (MidB) | 165Hz (AntiBoom) | 500Hz (VocalB) | 1kHz (LeadM) | 2.5kHz (Clarity) | 8kHz (Treble) | Preamp | MVBass (Hz/%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **B&O 8Ω · 24V** | +5.5 | +6.2 | +3.2 | -3.5 | +2.2 | +3.5 | +3.8 | +5.0 | -1.5 dB | 58Hz / 28% |
| **JBL Boombox** | +6.8 | +7.5 | +4.5 | -4.2 | +0.5 | +1.8 | +3.4 | +4.2 | -2.8 dB | 65Hz / 40% |
| **Sweet Vocal** | +2.4 | +1.8 | +1.2 | -2.5 | +3.8 | +4.6 | +5.2 | +3.3 | -1.2 dB | 55Hz / 18% |
| **Flat Reference** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 dB | 0Hz / 0% |
| **Original Reset** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 dB | 63Hz / 8% |
