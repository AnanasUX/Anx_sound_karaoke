# Gemini Argon Browser Calibration & MVSilicon OTG — Antigravity Handoff

## 1. Phạm vi đã chốt

Tích hợp AI chỉ dùng **Gemini đang chạy trong trình duyệt Argon**.

Không sử dụng:

- Gemini API hoặc Google AI Studio.
- API key hay biến môi trường cho Gemini.
- Next.js route/proxy gọi Gemini.
- Backend request đến Gemini.
- Cookie, token hoặc mật khẩu của người dùng.

Giao diện hiện tại chỉ mô phỏng:

1. Kết nối phiên Argon Browser.
2. Chuẩn bị dữ liệu RTA.
3. Chọn mục tiêu cân chỉnh.
4. Đồng bộ yêu cầu sang tab Gemini trong Argon.
5. Nhận kết quả JSON về ứng dụng.
6. Tạo bản xem trước `.ini` và `.c`.
7. Mô phỏng nạp cấu hình qua OTG.

Chưa có browser bridge hoặc giao tiếp phần cứng thật. Các file tải từ UI là prototype và không được nạp vào mạch.

Ngoài Argon, người dùng có thể chọn **Cấu hình có sẵn**. Nhánh này hoạt động cục bộ, không mở Gemini và không yêu cầu kết nối Argon.

Thư viện prototype hiện có:

- B&O 8Ω · 24V.
- JBL Boombox.
- Sweet Vocal.
- Flat Reference.

Khi chọn một profile, UI cập nhật trực tiếp 8 band PEQ rồi chuyển sang bước kiểm tra artifact. Antigravity phải giữ profile trong code hoặc một signed local bundle; không tải profile từ nguồn không tin cậy.

## 2. Nguyên tắc hoạt động

Người dùng tự đăng nhập Gemini trong trình duyệt Argon. Ứng dụng không đọc hoặc xử lý thông tin đăng nhập.

```text
Best Sound DSP UI
  │
  ├─ tạo Analysis Package: RTA + target + hardware profile
  ▼
Argon Browser Bridge
  ├─ yêu cầu người dùng xác nhận
  ├─ mở/chọn tab Gemini đã đăng nhập
  ├─ đưa prompt + Analysis Package vào Gemini
  ├─ chờ Gemini trả JSON
  └─ validate envelope rồi chuyển JSON về DSP UI
          │
          ▼
Local validators + deterministic file renderer
          │
          ▼
Android OTG bridge → MVSilicon BP1048B2
```

Gemini chỉ đề xuất dữ liệu PEQ. Gemini không được tạo lệnh USB, register write, binary firmware hoặc mã được thực thi trực tiếp.

## 3. Giới hạn kỹ thuật của browser integration

Website không thể tự đọc hay điều khiển DOM của tab Gemini khác origin do Same-Origin Policy. Antigravity cần một thành phần chính thức do Argon cung cấp hoặc browser extension/content script được người dùng cài và cấp quyền.

Thứ tự ưu tiên:

1. **Argon native browser-agent bridge** nếu Argon có contract chính thức.
2. **Argon extension/content script** với quyền origin tối thiểu.
3. **Clipboard/file handoff có xác nhận thủ công** nếu không có bridge chính thức.

Không dùng scraping ẩn, đánh cắp cookie, remote debugging mở công khai hoặc bypass chính sách trình duyệt.

## 4. State machine kết nối Argon

```text
disconnected
  -> requesting_connection
  -> awaiting_user_approval
  -> connected
  -> preparing_analysis
  -> awaiting_gemini
  -> result_received
  -> result_validated
  -> disconnected / expired
```

Khi bấm **Connect Argon Browser**:

1. App tạo `sessionId`, nonce dùng một lần, origin và protocol version.
2. Bridge hiển thị cửa sổ xác nhận.
3. Người dùng chọn tab Gemini đang đăng nhập.
4. Bridge trả capability envelope.
5. App chỉ báo Connected sau khi origin, nonce và protocol đều hợp lệ.

Không tự reconnect âm thầm vào tab Gemini cũ.

## 5. Bridge envelope

Message từ app:

```json
{
  "source": "best-sound-dsp",
  "type": "ARGON_CONNECT_REQUEST",
  "protocolVersion": 1,
  "sessionId": "uuid",
  "nonce": "cryptographically-random-value",
  "requestedCapabilities": ["gemini-tab-handoff", "structured-result"]
}
```

Acknowledgement:

```json
{
  "source": "gemini-argon-bridge",
  "type": "ARGON_CONNECT_RESULT",
  "protocolVersion": 1,
  "sessionId": "uuid",
  "nonce": "same-random-value",
  "approved": true,
  "capabilities": ["gemini-tab-handoff", "structured-result"]
}
```

Yêu cầu:

- Kiểm tra `event.origin` và `event.source`.
- Nonce dùng một lần, ngẫu nhiên và có thời hạn.
- Không dùng wildcard `postMessage("*")` trong production.
- Strict allowlist cho message type.
- Giới hạn kích thước message.
- Không nhận executable text hoặc HTML.
- Xóa session khi tab đóng, timeout hoặc người dùng disconnect.

Nếu Argon có SDK chính thức, dùng SDK đó thay vì tự tạo `postMessage`.

## 6. Analysis Package gửi sang Gemini

```json
{
  "schemaVersion": 1,
  "measurementId": "client-session-uuid",
  "hardware": {
    "chip": "BP1048B2",
    "boardProfile": "best-sound-t1v2",
    "sampleRate": 44100,
    "bitDepth": 24,
    "channels": 2
  },
  "speaker": {
    "type": "diy-2-way",
    "impedanceOhm": 8,
    "supplyVoltage": 24,
    "hasBiAmp": true
  },
  "microphone": {
    "name": "UMIK-1",
    "splCalibrated": true,
    "calibrationApplied": true
  },
  "measurement": {
    "fftSize": 16384,
    "smoothing": "1/12",
    "window": "hann",
    "durationMs": 10000,
    "noiseFloorDb": -58.4,
    "frequenciesHz": [20, 25, 31.5, 40, 50, 63, 80, 100],
    "levelsDb": [-11.2, -9.4, -6.1, -2.7, 1.8, 4.2, 3.1, 0.8]
  },
  "currentPeq": [
    {
      "band": 1,
      "enabled": true,
      "type": "bell",
      "frequencyHz": 62,
      "gainDb": 5.5,
      "q": 0.8
    }
  ],
  "target": {
    "preset": "balanced",
    "maxBoostDb": 6,
    "maxCutDb": -12,
    "maxBands": 8
  }
}
```

Validation trước khi gửi:

- `frequenciesHz` và `levelsDb` cùng số phần tử.
- Tối thiểu 32, tối đa 4096 bin.
- Tần số tăng dần, hữu hạn, trong 20–20.000 Hz.
- Hardware profile nằm trong allowlist.
- Analysis Package tối đa 256 KB.
- Không có dữ liệu cá nhân hoặc thông tin đăng nhập.

## 7. Prompt cho Gemini trong Argon

Bridge tạo prompt cố định; chỉ Analysis Package và target là dữ liệu động.

```text
You are an acoustic DSP calibration assistant for an MVSilicon BP1048B2
speaker controller.

Analyze the attached RTA package and propose at most 8 safe PEQ bands.
Return JSON only, following the supplied result schema.

Never return executable code, USB commands, register writes, binary data,
shell commands, HTML, or configuration-file text.

Prefer cuts for narrow resonances. Avoid aggressive boosts. Respect the
frequency, gain, Q, headroom, sample-rate, and band limits in the package.
State uncertainty when measurement quality is insufficient.
```

Không cho Gemini thay đổi schema hoặc hardware limits.

## 8. Result Package trả về app

```json
{
  "schemaVersion": 1,
  "measurementId": "client-session-uuid",
  "summary": "string",
  "measurementQuality": {
    "score": 0.86,
    "warnings": []
  },
  "recommendation": {
    "preampDb": -3,
    "estimatedHeadroomDb": 6,
    "bands": [
      {
        "band": 1,
        "enabled": true,
        "type": "bell",
        "frequencyHz": 165,
        "gainDb": -3.5,
        "q": 2.4,
        "reason": "Reduce cabinet resonance",
        "confidence": 0.88
      }
    ]
  }
}
```

Bridge chỉ lấy fenced JSON hoặc structured result. Không inject HTML của Gemini vào app.

Sau khi nhận:

1. Parse bằng strict schema.
2. Từ chối field lạ.
3. So khớp `measurementId`.
4. Clamp và kiểm tra mọi số.
5. Sort/dedupe band.
6. Chạy response simulator cục bộ.
7. Kiểm tra headroom.
8. Hiển thị preview để người dùng duyệt.

## 9. Quy tắc DSP an toàn

Giới hạn khởi điểm, cần xác nhận lại bằng MVSilicon SDK:

| Thuộc tính  |      Giới hạn |
| ----------- | ------------: |
| Frequency   |  20–20.000 Hz |
| Gain        | -12 đến +6 dB |
| Q           |        0.2–12 |
| Số band     |      Tối đa 8 |
| Auto preamp |  -18 đến 0 dB |

Không auto-correct:

- Vùng dưới tuning frequency của bass-reflex.
- Null sâu do triệt tiêu phòng.
- Measurement có noise floor cao.
- Microphone chưa calibration.
- Tín hiệu clipping.

## 10. Sinh `.ini` và `.c`

Gemini không được viết file trực tiếp. App hoặc trusted local module render file từ Result Package đã validate.

### `.ini`

```ini
[Project]
FormatVersion=1
Chip=BP1048B2
BoardProfile=best-sound-t1v2
SampleRate=44100

[Preamp]
GainDb=-3.0

[PEQ.1]
Enabled=true
Type=BELL
FrequencyHz=165.0
GainDb=-3.5
Q=2.40
```

Yêu cầu:

- Locale, field order và số thập phân cố định.
- Có format version và hash của recommendation chuẩn hóa.
- Không chèn free text của Gemini vào field thực thi.

### `.c`

```c
/* Generated file. Review before production use. */
#include "bestsound_bp1048b2_profile.h"

const BestSoundPeqBand kBestSoundPeqBands[8] = {
  { true, BESTSOUND_FILTER_BELL, 165.0f, -3.5f, 2.40f },
};
```

Yêu cầu:

- Render từ template nội bộ.
- Compile trong CI.
- Golden tests cho mỗi format version.
- Không dùng identifier, include hoặc macro do Gemini tạo.
- Đây là source artifact, không phải binary flash trực tiếp.

## 11. OTG và giới hạn nền tảng

WebUSB yêu cầu secure context, user gesture và quyền thiết bị. Hỗ trợ tốt hơn trên Chromium Android; iOS Safari không hỗ trợ đầy đủ.

Khuyến nghị production:

```text
React UI
  -> Android native / Capacitor bridge
  -> Android UsbManager
  -> vendor protocol adapter
  -> BP1048B2 programming transport
```

Antigravity cần:

- MVSilicon BP1048B2 SDK/programming guide.
- VID/PID của USB bridge.
- Endpoint/interface descriptors.
- Register map và memory layout.
- Bootloader sequence.
- Erase/write page size.
- CRC/checksum algorithm.
- Firmware compatibility matrix.

Không suy đoán các giá trị này từ tên chip.

## 12. Flash pipeline

```text
1. User taps Connect
2. Request USB permission
3. Read device identity
4. Match VID/PID + chip + board revision
5. Read firmware/sample rate/current profile
6. Backup current configuration
7. Validate profile against detected hardware
8. Ask for final confirmation
9. Enter programming mode
10. Write staged blocks
11. Verify checksum/read-back
12. Reboot DSP
13. Read active profile
14. Mark success only after match
15. Offer rollback
```

Không auto-flash ngay khi Argon trả Result Package.

## 13. UI integration points

Component:

```text
src/components/AiCalibrationPanel.tsx
```

Thay các phần prototype:

- `setArgonConnected(true)`: thay bằng Argon bridge handshake thật.
- `rtaSummary`: thay bằng measurement thật.
- `generateFiles()`: gửi Analysis Package qua Argon và chờ Result Package.
- `downloadPrototype()`: render từ dữ liệu đã validate.
- `setOtgConnected()`: thay bằng WebUSB/native bridge.
- `startFlash()`: thay bằng OTG state machine thật.

Không thêm Gemini API route hoặc API key.

### Cấu hình có sẵn

`readyProfiles` là thư viện profile cục bộ gồm metadata và 8 giá trị gain. Khi triển khai chính thức:

- Bổ sung frequency, Q, filter type, preamp và hardware compatibility cho từng profile.
- Có `profileVersion`, `boardProfile`, `sampleRate` và checksum.
- Validate profile giống Result Package của Argon.
- Không cho áp dụng nếu chip, board revision hoặc sample rate không tương thích.
- Luôn hiển thị preview trước khi nạp OTG.

## 14. Fallback khi không có Argon bridge

1. App tạo `bestsound-analysis.json`.
2. App tạo prompt có checksum.
3. Người dùng tải file và đưa thủ công vào Gemini.
4. Gemini trả Result Package JSON.
5. Người dùng import JSON về app.
6. App validate schema và checksum.

Fallback này không tự động nhưng không cần API và không vi phạm cross-origin restrictions.

## 15. Test plan

### Browser bridge

- Origin sai.
- Nonce sai, hết hạn hoặc replay.
- Tab Gemini đóng giữa phiên.
- Người dùng đăng xuất.
- Bridge thiếu capability.
- Message quá kích thước.
- Malformed JSON hoặc HTML injection.
- Result Package của measurement cũ.

### DSP/OTG

- Gain/Q/frequency clamp.
- Headroom calculation.
- INI/C golden files.
- Unsupported board/sample rate.
- USB permission denied.
- Device removed trong lúc write.
- Verify mismatch.
- Rollback thành công/thất bại.
- Hardware-in-the-loop trên từng board revision.

## 16. Definition of Done

- [ ] Không có Gemini API hoặc API key trong code.
- [ ] Người dùng tự đăng nhập Gemini trong Argon.
- [ ] Bridge không đọc hoặc lưu cookie/token.
- [ ] Origin, source, nonce và protocol version được xác thực.
- [ ] Analysis Package và Result Package có strict schema.
- [ ] Kết quả Argon luôn qua local validator.
- [ ] Gemini không tạo code/USB command trực tiếp.
- [ ] `.ini` renderer có version và golden tests.
- [ ] `.c` renderer compile được trong CI.
- [ ] Protocol OTG dựa trên SDK chính thức.
- [ ] Có allowlist VID/PID/chip/board/firmware.
- [ ] Backup trước erase/write.
- [ ] Checksum và read-back verify.
- [ ] Rollback đã được test.
- [ ] Android OTG được test trên thiết bị thật.
- [ ] UI chỉ gỡ nhãn prototype sau khi toàn bộ điều kiện trên đạt.
