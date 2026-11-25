================================================================================
             HỆ THỐNG FILE EXPORT CẤU HÌNH DSP CHO ACPWORKBENCH
         DỰ ÁN: LOA 3 ĐƯỜNG TIẾNG MONO (BOOMBOX 4 + AIRS 3" + TREBLE DOME)
================================================================================

Tất cả các file cấu hình đã được tự động tính toán, biên dịch và xuất ra sẵn:

1. acp_eq_styles.xml (13 KB):
   - Định dạng: XBEL XML chuẩn của Parametric Equalizer Editor (Chương 9 trong Manual).
   - Chức năng: Chứa toàn bộ 3 Styles EQ và phân tần Crossover của 3 kênh.
   - Cách dùng: Trong cửa sổ EQ Editor của ACPWorkbench, nhấp chuột phải chọn 
     "Import EQ Parameters" (hoặc chọn tệp XML này).

2. acp_workbench_config.ini (4 KB):
   - Định dạng: Tệp thông số INI (Parameters Data).
   - Chức năng: Lưu trữ toàn bộ cấu hình DAC, Global Sample Rate, danh sách Effect 
     (EQ, Dynamic Range Compressor, Pregain, Phase).
   - Cách dùng: Vào menu chính của ACPWorkbench: File -> Import Audio Setting 
     và chọn file này.

3. acp_flash_parameters.bin (4 KB = 4096 bytes):
   - Định dạng: Flash Binary File (Sector 4KB chuẩn SPI Flash, kèm mã kiểm tra CRC32).
   - Chức năng: Dùng để nạp thẳng vào bộ nhớ SPI Flash của chip MVSilicon.
   - Cách dùng: Vào Downloader -> Firmware Upgrader hoặc nạp qua công cụ Flash Programmer 
     để chip tự động chạy khi khởi động mà không cần PC.

4. acp_dsp_effects.h (4.3 KB):
   - Định dạng: C Header File mã nguồn C.
   - Chức năng: Đã tính toán sẵn toàn bộ hệ số Biquad IIR Filter (Fixed-Point Q4.27) 
     và struct DRC Limiter.
   - Cách dùng: Dành cho lập trình viên nhúng trực tiếp vào dự án firmware Keil C 
     / Eclipse của chip MVSilicon.

5. PRESET_01_BOSE_STYLE.txt (5.2 KB):
   - Bản ghi chép thông số kỹ thuật dạng bảng trực quan, quy trình test 4 bước.
================================================================================
