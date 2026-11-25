# HỒ SƠ DỰ ÁN CÂN CHỈNH DSP HỆ THỐNG LOA 2.1 BI-AMP
**Dự án:** Loa Di Động Thùng 5L - Cấu Hình Boombox 4 Sub + Mid AIRS + Treble Dome  
**Phần mềm tuning:** MVSilicon ACPWorkbench (V2.44.2 / V2.21.6)  
**Tài liệu tham chiếu:** `ACPWorkbench_USER_MANUAL_Version_2.21.6.pdf`  
**Ngày cập nhật:** 16/11/2026  

---

## 1. TỔNG QUAN PHẦN CỨNG & THIẾT KẾ THÙNG LOA

### 1.1. Thể tích & Thoát âm trầm (Enclosure & Port Tuning)
* **Thể tích thùng:** Thể tích lọt lòng tổng thể **5.0 Lít**, trừ khoang củ Mid và nam châm thì thể tích khí hiệu dụng $V_b \approx \mathbf{4.5\text{ – }4.7\text{ Lít}}$.
* **Ống thông hơi (Port):**
  * Nguyên bản: Ống nhựa miệng loe $\varnothing 64\text{ mm}$, lòng trong $D \approx 50\text{ mm}$, dài $L = 73\text{ mm}$ $\rightarrow$ Nếu để nguyên sẽ bị cộng hưởng lệch lên **$105\text{ – }115\text{ Hz}$** (mất bass sâu và nguy cơ chạm coil do mất đệm khí).
  * **Giải pháp đã thực hiện:** Đã lắp **co bẻ góc 90 độ và nối dài ống lên $220\text{ – }250\text{ mm}$** chạy ép dọc theo lưng/đáy thùng.
  * **Tần số cộng hưởng thùng mục tiêu ($F_b$):** **$\approx 64\text{ – }68\text{ Hz}$** (Chuẩn âm trầm sâu, đầm, không xì gió).
  * *Lưu ý cơ học:* Đuôi ống bên trong phải cách vách thùng đối diện tối thiểu $\ge 35\text{ mm}$ để luồng khí không bị nghẽn.

### 1.2. Khoang củ loa Mid AIRS (Sub-Enclosure)
* **Bắt buộc:** Củ Mid AIRS 3 inch ($15\text{W}$) phải được đặt trong một **khoang/chén kín riêng biệt $\mathbf{0.3\text{ – }0.5\text{ Lít}}$** lót bông tiêu âm.
* *Mục đích:* Ngăn áp suất cực lớn từ củ Bass 4 inch thổi ngược làm rách/biến dạng màng loa Mid.

### 1.3. Cấu hình củ loa & Sơ đồ đấu dây (Bi-Amp 2 Kênh)
Hệ thống sử dụng mạch công suất 2 kênh (Bi-Amp / 2.1):
* **Kênh 1 (CH1 - Subwoofer):** Kéo riêng **1 củ Mid-bass Boombox 4 inch** ($4\Omega$, $40\text{W RMS}$ / $80\text{W Peak}$).
  * Đấu dây trực tiếp vào kênh 1 ampli (DSP xử lý cắt dải tần và limiter).
* **Kênh 2 (CH2 - Satellite Mid-Treble):** Kéo cụm **1 củ Mid AIRS 3 inch** ($4\Omega$, $15\text{W}$) + **1 củ Treble Dome** ($4\Omega$, $20\text{ – }30\text{W}$).
  * **QUY TẮC AN TOÀN BẮT BUỘC:** Củ Treble Dome **phải mắc nối tiếp tụ film cản $2.2\mu\text{F} – 3.3\mu\text{F}$ (MKP)** (kèm trở sứ $2\Omega – 3.3\Omega / 5\text{W}$ nếu cần hãm bớt gain) trước khi đấu song song với củ AIRS. Nếu không có tụ cản, củ Treble sẽ nhận dải trung từ 350Hz và cháy tức thì!

---

## 2. KIẾN TRÚC PHẦN MỀM & KINH NGHIỆM XỬ LÝ LỖI (ACPWORKBENCH)

### 2.1. Tool sử dụng
* Công cụ: **`ACPWorkbench_V2.44.2.exe`** (đã giải nén UPX thành `ACPWorkbench_unpacked.exe`).
* Chip hỗ trợ: Dòng chip DSP/Codec MVSilicon (Shanghai Mountain View Silicon): **BP1048B2, AP82xx, DU56x, DU26x, U1x**.

### 2.2. Xử lý lỗi "Firmware version mismatch" (Quan trọng khi Antigravity mở lại dự án)
* **Hiện tượng:** Khi vào `File -> Import Audio Setting`, phần mềm bật pop-up: `Import Registers Data: Firmware version mismatch.` và trang Audio Effect xám trắng.
* **Nguyên nhân cốt lõi:**
  1. Góc dưới bên trái đang hiển thị **`USB DISCONNECTED`**. ACPWorkbench là công cụ **Online Real-time**. Khi chưa kết nối với chip vật lý, phần mềm không có thông tin firmware nên từ chối nạp file.
  2. Số `Firmware_Version` khai báo trong tệp `.ini` không khớp với firmware nạp trong chip.
* **Quy trình xử lý chuẩn:**
  1. Cắm cáp USB (hoặc mạch nạp UART: TX-RX chéo nhau, GND chung).
  2. Vào `Settings -> Communication Type` chọn `USB (HID)` hoặc `UART` (chọn đúng COM & Baudrate).
  3. Đảm bảo góc dưới trái chuyển sang **`USB CONNECTED`** (hoặc `COMx CONNECTED` màu xanh lá). Lúc này trang `Audio Effect` sẽ tự động bung đầy đủ các khối hiệu ứng từ chip.
  4. Vào `File -> Export Audio Setting` xuất file `.ini` mẫu để đọc chính xác phiên bản firmware thực tế của mạch, sau đó điền vào `acp_workbench_config.ini` hoặc dùng `File -> Convert Audio Settings File...`.

---

## 3. BẢNG CẤU HÌNH THÔNG SỐ DSP CHI TIẾT (PRESET CHUẨN)

### 3.1. Trang Audio Module
* **PGA (Mục 5.1):** Line1/Line2 `Enable` (Single-ended input, $0.0\text{ dB}$). MIC: `Disable`.
* **ADC (Mục 5.2):** `Enable`, Sample Rate $44.1\text{ kHz}$, MCLK `PLL Clock1`, Fade Time $20\text{ ms}$, **DC Blocker: `Enable`**, AGC: `Disable`.
* **DAC (Mục 5.3):** `Enable`, Sample Rate $44.1\text{ kHz}$, **Dither: `Enable`**, Scramble: **`DWA`**, Output Mode: **`Stereo (L, R)`**, Digital Vol: $-0.5\text{ dB}$.

### 3.2. Crossover & Định tuyến 2 Kênh (Bi-Amp)
| Thông số | Kênh 1 (CH1 - SUB 4 INCH) | Kênh 2 (CH2 - SATELLITE MID-TREBLE) |
| :--- | :---: | :---: |
| **HPF (Cắt dưới)** | **$55\text{ Hz}$** (LR24 bậc 4) | **$350\text{ Hz}$** (LR24 bậc 4) |
| **LPF (Cắt trên)** | **$350\text{ Hz}$** (LR24 bậc 4) | **Bypassed / Tắt** (cho Treble lên 20kHz) |
| **Gain** | $0.0\text{ dB}$ | $-1.5\text{ dB}$ (cân bằng độ nhạy) |
| **Phase / Polarity** | $0^\circ$ | $0^\circ$ (thử đảo $180^\circ$ khi test nghe vocal) |
| **Delay** | $0.00\text{ ms}$ | $0.05\text{ ms}$ |
| **Limiter Threshold** | **$-1.0\text{ dBFS}$** ($12.65\text{V RMS}$) | **$-4.5\text{ dBFS}$** ($7.75\text{V RMS}$) |
| **Limiter Time** | Attack: $10\text{ ms}$, Release: $150\text{ ms}$ | Attack: $5\text{ ms}$, Release: $80\text{ ms}$ |

### 3.3. Bảng Cân Chỉnh Parametric EQ (PEQ)
* **Kênh 1 (SUB):**
  * `PEQ 1`: **$75\text{ Hz}$** | Gain **$+1.5\text{ dB}$** | $Q = 0.8$ *(Tạo lực đầm, nảy Boombox)*
  * `PEQ 2`: **$100\text{ Hz}$** | Gain **$+1.0\text{ dB}$** | $Q = 1.0$ *(Trống kick chắc)*
  * `PEQ 3`: **$160\text{ Hz}$** | Gain **$-1.5\text{ dB}$** | $Q = 1.0$ *(Cắt ù rền thùng 5L)*
  * `PEQ 4`: **$250\text{ Hz}$** | Gain **$-1.0\text{ dB}$** | $Q = 1.0$ *(Làm sạch dải tiếp giáp)*
* **Kênh 2 (SATELLITE MID + TREBLE):**
  * `PEQ 1 (Mid)`: **$500\text{ Hz}$** | Gain **$-1.0\text{ dB}$** | $Q = 1.0$ *(Cắt đục giọng hát)*
  * `PEQ 2 (Mid)`: **$1.200\text{ Hz}$** | Gain **$+1.0\text{ dB}$** | $Q = 0.8$ *(Làm dày giọng nam)*
  * `PEQ 3 (Mid)`: **$2.500\text{ Hz}$** | Gain **$+1.0\text{ dB}$** | $Q = 0.8$ *(Vocal nữ sáng ngọt)*
  * `PEQ 4 (Treble)`: **$5.000\text{ Hz}$** | Gain **$-1.0\text{ dB}$** | $Q = 1.0$ *(Chống chói gắt vùng giao thoa)*
  * `PEQ 5 (Treble)`: **$8.000\text{ Hz}$** | Gain **$+1.0\text{ dB}$** | $Q = 0.8$ *(Sắc nét tiếng bộ gõ)*
  * `PEQ 6 (Treble)`: **$12.000\text{ Hz}$** | Gain **$+1.5\text{ dB}$** | $Q = 0.8$ *(Tơi xốp leng keng)*
  * `PEQ 7 (Treble)`: **$16.000\text{ Hz}$** | Gain **$+1.0\text{ dB}$** | $Q = 0.8$ (**Hight Shelf** - mở rộng không gian)

### 3.4. Các hiệu ứng DSP bổ trợ
* **MVBass Classic (Mục 6.1.24):** `Enable`, Cutoff: **$55\text{ Hz}$**, Intensity: **$20\%$** (tạo âm trầm ảo cho thùng nhỏ).
* **DC Blocker (Mục 6.1.2):** `Enable`.
* **Hiệu ứng Karaoke (Echo, Reverb, Pitch, Vocal Cut):** `Disable` (khi nghe nhạc).

---

## 4. BẢN ĐỒ TỆP TRONG THƯ MỤC DỰ ÁN (`d:\Python\dsp\`)

| Tên tệp | Định dạng | Công dụng |
| :--- | :---: | :--- |
| **`acp_dsp_assistant.py`** | Python Tool | **Trợ lý tự động sửa lỗi & Điều chỉnh DSP:** Giao diện GUI hỗ trợ sửa lỗi *Firmware version mismatch*, đổi preset âm thanh, tính toán lại toàn bộ hệ số Biquad và khởi chạy ACPWorkbench. |
| **`CHAY_DSP_ASSISTANT.bat`** | Batch Script | **Nhấp đúp chuột để chạy ngay:** File chạy nhanh `acp_dsp_assistant.py` trên Windows mà không cần gõ lệnh. |
| **`acp_eq_styles.xml`** | XBEL XML | **Import vào EQ Editor:** Nhấp chuột phải trên đồ thị EQ Editor $\rightarrow$ chọn *Import EQ Parameters* để nạp ngay 2 kênh Crossover + PEQ mà không sợ lỗi firmware. |
| **`acp_workbench_config.ini`**| INI Config | **Import toàn diện:** File cấu hình toàn bộ hệ thống Audio Module, Audio Effect, DRC Limiter và Log Page qua menu *File $\rightarrow$ Import Audio Setting*. |
| **`acp_flash_parameters.bin`**| Binary 4KB | **Nạp SPI Flash:** Sector 4KB nhị phân kèm CRC32 dùng cho tính năng ghi đè bộ nhớ Flash. |
| **`acp_dsp_effects.h`** | C Header | **Nhúng Firmware C:** Mảng hệ số Biquad IIR Filter dạng số nguyên cố định Fixed-Point Q4.27 ($1 \ll 27$) cho Keil C / MVSilicon SDK. |
| **`gen_configs.py`** | Python Script | Script tự động tính toán lại toán học các hệ số biquad và sinh ra toàn bộ 3 file cấu hình trên khi có thay đổi thông số. |
| **`ACPWorkbench_V2.44.2.exe`** | Executable | Phần mềm tuning chính thức của MVSilicon (bản đóng gói UPX). |
| **`ACPWorkbench_unpacked.exe`**| Executable | Bản giải mã UPX (26MB) dùng cho phân tích kỹ thuật hoặc chạy trực tiếp. |
| **`ACPWorkbench_USER_MANUAL_Version_2.21.6.pdf`** | PDF Manual | Sách hướng dẫn sử dụng chính thức 34 trang từ hãng MVSilicon. |

---

## 5. HƯỚNG DẪN DÀNH CHO ANTIGRAVITY HOẶC KỸ SƯ KẾ THỪA DỰ ÁN

Khi mở lại dự án trên một máy tính khác:
1. **Kiểm tra trạng thái tệp:** Đọc tệp này (`README.md` hoặc `PROJECT_DSP_DOCUMENTATION.md`) để nắm toàn bộ thông số.
2. **Nếu muốn thay đổi tần số cắt hoặc EQ:** 
   * Mở file `gen_configs.py`, sửa thông số trong mảng `channels_2ch`.
   * Chạy `python gen_configs.py` $\rightarrow$ Toàn bộ hệ số Biquad Filter và 3 file export (`.xml`, `.ini`, `.h`) sẽ tự động được cập nhật lại chính xác 100%.
3. **Khi cắm mạch thật:** Luôn kiểm tra thanh trạng thái `USB CONNECTED` trước khi bấm nạp.
4. **Quy trình lưu vĩnh viễn:** Sau khi nghe thử ưng ý, vào **Downloader $\rightarrow$ Save configurations to flash** để lưu vào chip.
