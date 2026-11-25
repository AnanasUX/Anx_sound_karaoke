# BẢN ĐỒ TOÀN BỘ CÁC MODULE & THÔNG SỐ CẤU HÌNH TRÊN CHIP MVSILICON BP1048B2

**Dòng chip:** MVSilicon BP1048B2 (32-bit DSP Dual-Core, 288MHz, 32-bit/64-bit Fixed/Floating Processing)  
**Phần mềm chính hãng:** ACPWorkbench V2.44.2 / V2.21.6  
**Số lượng khối chức năng (Effect Blocks):** 43 khối độc lập  

---

## 1. KHỐI PHẦN CỨNG NGOẠI VI & ĐẦU VÀO/ĐẦU RA (HARDWARE I/O)

| Mã Khối (ID) | Tên Module | Chức năng & Thông số cấu hình |
| :--- | :--- | :--- |
| `0x03` & `0x06` | **PGA0 / PGA1 (Programmable Gain Amp)** | Khuếch đại tiền khuếch đại analog cho Mic/AUX ngõ vào từ `0 dB` đến `+36 dB` (bước 1 dB). |
| `0x04` & `0x07` | **ADC0 / ADC1** | Cấu hình tần số lấy mẫu (Sample Rate 44.1k/48k), bộ lọc High-Pass chống trôi một chiều (DC offset filter). |
| `0x05` & `0x08` | **AGC0 / AGC1 (Auto Gain Control)** | Tự động cân bằng mức tín hiệu vào Mic: chống vỡ tiếng khi nói to, bù âm lượng khi nói nhỏ. |
| `0x09` & `0x0A` | **DAC0 / DAC1** | Âm lượng giải mã analog ngõ ra, Dither giảm méo lượng tử hóa, Soft-Mute chống nổ khi bật nguồn. |
| `0x0B` & `0x0C` | **I2S0 / I2S1** | Giao tiếp âm thanh số Master/Slave (16-bit, 24-bit, 32-bit), kết nối chip Bluetooth ngoài hoặc USB Codec. |
| `0x0D` | **SPDIF** | Ngõ vào/ra cáp quang (Optical) và đồng trục (Coaxial) chuẩn âm thanh số PCM stereo. |
| `0x0E` & `0x0F` | **GPIO Config & Output** | Cấu hình chân điều khiển LED hiển thị trạng thái, chân đóng ngắt Relay bảo vệ loa, chân MUTE ampli công suất. |

---

## 2. KHỐI LỌC TẦN SỐ & PHÂN TẦN CHỦ ĐỘNG (CROSSOVER & EQUALIZERS)

| Mã Khối (ID) | Tên Module | Chức năng & Thông số cấu hình |
| :--- | :--- | :--- |
| `0x95` | **EQ_10BAND_1 (Kênh 1 - Subwoofer)** | **Phân tần & PEQ cho dải trầm:**<br>• **Subsonic HPF (30Hz - 50Hz):** Cắt tần số siêu trầm vô ích, bảo vệ cuộn coil và màng loa không bị dập đáy.<br>• **Subwoofer LPF (80Hz - 200Hz):** Cắt tần số cao của loa Sub.<br>• **10-Band Biquad PEQ:** Freq, Gain, Q-factor, Filter Type. |
| `0x96` | **EQ_10BAND_2 (Kênh 2 - Mid/Treble)** | **Phân tần & PEQ cho dải trung cao:**<br>• **Satellite HPF (120Hz - 300Hz):** Ngăn dải trầm lọt vào củ Mid AIRS (chống rách màng củ Mid).<br>• **10-Band Biquad PEQ:** Căn chỉnh chi tiết độ trong và độ ngọt của giọng hát. |
| `0x8D` – `0x91`, `0x97` | **Pre-EQ & Post-EQ Banks** | Các bộ lọc EQ trung gian trước và sau khi phối trộn tín hiệu từ các nguồn Bluetooth, USB, Aux. |

---

## 3. KHỐI NÉN ĐỘNG HỌC & BẢO VỆ LOA (DRC & HARD LIMITER)

| Mã Khối (ID) | Tên Module | Chức năng & Thông số cấu hình |
| :--- | :--- | :--- |
| `0x93`, `0x9B`, `0x9C` | **Dynamic Range Compressor (DRC) / Limiter** | **Khối bảo vệ loa quan trọng nhất:**<br>• **Threshold (Ngưỡng chặn, ví dụ -1.5 dBFS đến 0 dBFS):** Khi tín hiệu vượt ngưỡng, mạch nén tự động hạ gain $\rightarrow$ **chống 100% Clipping méo tiếng và cháy coil**.<br>• **Attack Time (1ms - 50ms):** Thời gian phản ứng chặn đứng sóng đỉnh tức thời.<br>• **Release Time (50ms - 500ms):** Tốc độ hồi phục âm lượng mượt mà, không giật tiếng.<br>• **Ratio (2:1 đến $\infty:1$):** Tỷ lệ nén (từ nén nhẹ tới chặn đứng Hard Limiter).<br>• **Knee (Soft / Hard Knee):** Độ mềm mại tại điểm bắt đầu nén. |

---

## 4. KHỐI TÁI TẠO TRẦM ẢO & KÍCH HÀI ÂM (BASS & TREBLE SYNTH)

| Mã Khối (ID) | Tên Module | Chức năng & Thông số cấu hình |
| :--- | :--- | :--- |
| `0x87` | **MVBass Classic** | **Thuật toán trầm ảo độc quyền MVSilicon:** Tái tạo cảm giác bass sâu 40Hz - 50Hz cho loa cỡ nhỏ 3-4 inch bằng cách sinh sóng hài bậc 2 và 3.<br>• **Cutoff:** Tần số giới hạn (60Hz - 160Hz).<br>• **Intensity:** Cường độ trầm ảo (0% - 100%). |
| `0x88` | **MVBass Advanced** | Bản nâng cấp hỗ trợ chỉnh tỷ lệ hòa trộn tín hiệu gốc/tín hiệu ảo (Dry/Wet Blend). |
| `0x89` | **Harmonic Exciter** | **Kích thích hài âm dải cao:** Làm cho tiếng ca sĩ và nhạc cụ tách bạch, trong trẻo, leng keng mà không bị gắt tai. |

---

## 5. KHỐI KHỬ NHIỄU & TIẾT KIỆM NĂNG LƯỢNG (NOISE GATE & SILENCE)

| Mã Khối (ID) | Tên Module | Chức năng & Thông số cấu hình |
| :--- | :--- | :--- |
| `0x85` | **Noise Suppressor / Expander (Noise Gate)** | **Triệt tiêu tiếng xì rè nền:** Khi người dùng dừng nhạc hoặc trong các khoảng lặng, cổng tự động dập mức tín hiệu về $-\infty\text{ dB}$, giúp nền âm tĩnh tuyệt đối, sạch tiếng 100%. |
| `0x86` | **Silence Detector** | Tự động phát hiện khi không có âm thanh trong một khoảng thời gian cài đặt để đưa mạch vào trạng thái tiết kiệm điện (Sleep/Standby) hoặc tự ngắt nguồn. |

---

## 6. KHỐI CĂN CHỈNH TRỄ & PHA (TIME ALIGNMENT & PHASE)

| Mã Khối (ID) | Tên Module | Chức năng & Thông số cấu hình |
| :--- | :--- | :--- |
| `0x8B` & `0x9D` | **PCM Delay (Time Alignment)** | **Độ trễ tín hiệu số:** Điều chỉnh trễ từ $0.1\text{ ms}$ đến $50\text{ ms}$. Dùng để đồng bộ thời gian âm thanh giữa loa Subwoofer và loa vệ tinh tới tai người nghe, triệt tiêu hiện tượng lệch pha gây hụt bass. |
| `0x9A` | **Phase Control** | Đảo pha $0^\circ / 180^\circ$ hoặc dịch pha liên tục để sóng âm từ loa sub cộng hưởng tối đa với loa mid. |
| `0x80` | **3D Stereo Soundstage Widener** | Mở rộng không gian trường âm sân khấu ảo (3D Surround). |

---

## 7. KHỐI XỬ LÝ MICRO & KARAOKE (VOCAL ENGINE)

| Chức năng | Thông số cấu hình |
| :--- | :--- |
| **Echo & Reverb Engine** | Thời gian nhại (Delay ms), số lần lặp (Repeat), thời gian vang vọng phòng lớn/nhỏ (Reverb Decay/Room Size). |
| **Anti-Howling / Feedback Suppressor** | Bộ triệt tiêu tiếng hú rít micro tự động (dò và đặt bộ lọc Notch Filter tự động tại tần số đang cộng hưởng hú). |
| **Pitch Shifter / Voice Changer** | Nâng hạ tone bài hát ($\pm 6$ bán âm) và giả lập giọng nói nam, nữ, trẻ em, robot. |
| **Vocal Cut (Tách lời ca sĩ)** | Thuật toán triệt tiêu giọng hát ở giữa để biến bài hát thông thường thành bài hát Karaoke. |
