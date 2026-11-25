# TÀI LIỆU KIỂM TOÁN VÀ PHÂN LOẠI TOÀN BỘ TÀI NGUYÊN (AUDIO_AND INVENTORY)
**Dự án:** BEST SOUND DSP CONTROLLER - Chip MVSilicon BP1048B2
**Thời gian kiểm toán:** 19/11/2026
**Người thực hiện:** Senior Audio DSP Engineer & Full-Stack Architect (Antigravity)

---

## 1. TỔNG QUAN PHÂN LOẠI
- **Tổng số file được kiểm toán:** 137 tệp tin
- **Phạm vi:** `D:\Python\dsp\` (Thư mục gốc firmware & tools), `Audio_And\` (Next.js / React UI), `android_app\` (Native Android), `peq_studio\` (Web Audio Prototype).

| Danh mục | Số lượng | Mô tả tóm tắt |
| :--- | :---: | :--- |
| **Next.js / React UI Source** | 53 | Mã nguồn giao diện chính hiện đại, Tailwind CSS v4, Payload CMS |
| **Android Source** | 14 | Mã nguồn ứng dụng Java Android (Bluetooth SPP, UsbManager OTG, 8-band PEQ) |
| **Web Audio Prototype** | 2 | Giao diện HTML5/Canvas và server Python đo RTA Web Audio |
| **ACPWorkbench INI** | 16 | Cấu hình thanh ghi MVSilicon BP1048B2 (43 sections, 864 lines) |
| **C Configuration** | 13 | Mảng nhị phân hex 1667 bytes xuất từ ACPWorkbench cho firmware |
| **Python DSP Tools** | 20 | Công cụ tính toán biquad, chuyển đổi cấu hình, tạo preset |
| **APK Builds** | 6 | Các bản build APK (3 bản BestSound native, 3 bản MVSilicon Capacitor) |
| **Header (.h) & XML (.xml)** | 2 | Cấu trúc C Fixed-point Q4.27 và XBEL XML cho ACPWorkbench EQ Editor |
| **Flash Binary (.bin)** | 1 | Sector nhị phân 4KB SPI Flash kèm CRC32 |
| **Tài liệu & Manual** | 6 | Datasheet, hướng dẫn ACPWorkbench 34 trang, Markdown documentation |
| **Executable & Launchers** | 4 | ACPWorkbench V2.44.2 exe chính hãng và các script .bat |

---

## 2. BẢNG CHI TIẾT TOÀN BỘ TỆP TIN

| STT | Đường dẫn (Path) | Loại file | Mục đích | Phiên bản | Tệp liên quan | Mức độ tin cậy | An toàn | Sử dụng |
| :-: | :--- | :--- | :--- | :--- | :--- | :-: | :-: | :-: |
| 1 | `4h5418102026.c` | Duplicate hoặc version cũ (C) | Snapshot mảng C lưu vết ngày 18/10/2026 | ACPWorkbench 2.44.2 | 4h5418102026.ini | MEDIUM | SAFE | REFERENCE ONLY |
| 2 | `4h5418102026.ini` | Duplicate hoặc version cũ (INI) | Snapshot lưu vết xuất từ máy lúc 4h54 ngày 18/10/2026 | Firmware 0.3.4 (Type 48) | 4h5418102026.c | MEDIUM | SAFE | REFERENCE ONLY |
| 3 | `ACPWorkbench.ini` | ACPWorkbench INI | File cấu hình mặc định khi ACPWorkbench lưu trạng thái hiện thời | Firmware 0.3.4 (Type 48 = BP1048B2) | ACPWorkbench_V2.44.2.exe, dsp.ini | HIGH | SAFE | YES (Golden Reference) |
| 4 | `ACPWorkbench_Tuned_2CH.ini` | ACPWorkbench INI | File cấu hình rút gọn 2 kênh (207 dòng) | Firmware 0.0.0 (Type 0) | ACPWorkbench.ini | LOW | SAFE | NO (Cấu hình thử nghiệm cũ/thiếu register) |
| 5 | `ACPWorkbench_USER_MANUAL_Version_2.21.6.pdf` | PDF/manual | Tài liệu kỹ thuật chính thức từ MVSilicon (Hướng dẫn sử dụng ACPWorkbench V2.21.6 và Datasheet) | V2.21.6 (34 trang) | ACPWorkbench_V2.44.2.exe | HIGH (Vendor Specification) | SAFE | YES (Tài liệu đối chiếu register và protocol) |
| 6 | `ACPWorkbench_V2.44.2.exe` | Executable | Phần mềm chính hãng MVSilicon ACPWorkbench (V2.44.2 UPX đóng gói & bản giải mã) | 2.44.2.0 (Win32 x86) | ACPWorkbench_USER_MANUAL_Version_2.21.6.pdf | HIGH (Vendor Official Tool) | UNSAFE (File thực thi nhị phân, không tự ý chạy trong audit) | REFERENCE ONLY (Chạy bởi người dùng qua Windows GUI) |
| 7 | `ACPWorkbench_unpacked.exe` | Executable | Phần mềm chính hãng MVSilicon ACPWorkbench (V2.44.2 UPX đóng gói & bản giải mã) | 2.44.2.0 (Win32 x86) | ACPWorkbench_USER_MANUAL_Version_2.21.6.pdf | HIGH (Vendor Official Tool) | UNSAFE (File thực thi nhị phân, không tự ý chạy trong audit) | REFERENCE ONLY (Chạy bởi người dùng qua Windows GUI) |
| 8 | `BestSound_DSP_v1.0.apk` | APK | Ứng dụng Android APK native (Java) điều khiển Bluetooth SPP / USB OTG | v1.0 | android_app/ | HIGH (Biên dịch từ source android_app/) | SAFE (Chỉ cài đặt khi người dùng yêu cầu) | YES (Build artifact chính thức) |
| 9 | `BestSound_DSP_v2.0_Wireless.apk` | APK | Ứng dụng Android APK native (Java) điều khiển Bluetooth SPP / USB OTG | v2.0_Wireless | android_app/ | HIGH (Biên dịch từ source android_app/) | SAFE (Chỉ cài đặt khi người dùng yêu cầu) | YES (Build artifact chính thức) |
| 10 | `BestSound_DSP_v3.0_PEQ_MultiBand.apk` | APK | Ứng dụng Android APK native (Java) điều khiển Bluetooth SPP / USB OTG | v3.0_PEQ_MultiBand | android_app/ | HIGH (Biên dịch từ source android_app/) | SAFE (Chỉ cài đặt khi người dùng yêu cầu) | YES (Build artifact chính thức) |
| 11 | `CHAY_DSP_ASSISTANT.bat` | Batch launcher | Script chạy nhanh trên Windows môi trường local | 1.0 | acp_dsp_assistant.py, serve_studio.py | HIGH | SAFE (Đã kiểm tra mã nguồn) | YES (Tiện ích hỗ trợ người dùng) |
| 12 | `CHAY_PEQ_RTA_STUDIO.bat` | Batch launcher | Script chạy nhanh trên Windows môi trường local | 1.0 | acp_dsp_assistant.py, serve_studio.py | HIGH | SAFE (Đã kiểm tra mã nguồn) | YES (Tiện ích hỗ trợ người dùng) |
| 13 | `MVSilicon_DSP_Tuner_v2.2_Gemini_Ini.apk` | APK | Bản APK cũ MVSilicon DSP Tuner (Capacitor/WebView) dùng tham khảo | v2.2_Gemini_Ini | MVSilicon DSP Tuner Capacitor project | MEDIUM (Bản build tham khảo lịch sử) | SAFE | REFERENCE ONLY (Chỉ dùng trích xuất tham khảo protocol) |
| 14 | `MVSilicon_DSP_Tuner_v2.3_Argon4_Ini_C.apk` | APK | Bản APK cũ MVSilicon DSP Tuner (Capacitor/WebView) dùng tham khảo | v2.3_Argon4_Ini_C | MVSilicon DSP Tuner Capacitor project | MEDIUM (Bản build tham khảo lịch sử) | SAFE | REFERENCE ONLY (Chỉ dùng trích xuất tham khảo protocol) |
| 15 | `MVSilicon_DSP_Tuner_v2.4_Bluetooth_Wizard.apk` | APK | Bản APK cũ MVSilicon DSP Tuner (Capacitor/WebView) dùng tham khảo | v2.4_Bluetooth_Wizard | MVSilicon DSP Tuner Capacitor project | MEDIUM (Bản build tham khảo lịch sử) | SAFE | REFERENCE ONLY (Chỉ dùng trích xuất tham khảo protocol) |
| 16 | `PRESET_01_BOSE_STYLE.txt` | Preset/profile (Text) hoặc Hướng dẫn | Preset mẫu phong cách Bose hoặc hướng dẫn xuất thông số | 1.0 | PROJECT_DSP_DOCUMENTATION.md | HIGH | SAFE | YES (Tài liệu tham khảo) |
| 17 | `PROJECT_DSP_DOCUMENTATION.md` | Tài liệu kỹ thuật | Hồ sơ dự án cân chỉnh loa 2.1 Bi-Amp, thể tích thùng 5L, port bass reflex, mạch bảo vệ tép | 16/11/2026 | gen_configs.py, dsp.ini, dsp.c | HIGH | SAFE | YES (Hồ sơ phần cứng chuẩn) |
| 18 | `README.md` | Tài liệu kỹ thuật | Hồ sơ dự án cân chỉnh loa 2.1 Bi-Amp, thể tích thùng 5L, port bass reflex, mạch bảo vệ tép | 16/11/2026 | gen_configs.py, dsp.ini, dsp.c | HIGH | SAFE | YES (Hồ sơ phần cứng chuẩn) |
| 19 | `README_DSP_EXPORT.txt` | Preset/profile (Text) hoặc Hướng dẫn | Preset mẫu phong cách Bose hoặc hướng dẫn xuất thông số | 1.0 | PROJECT_DSP_DOCUMENTATION.md | HIGH | SAFE | YES (Tài liệu tham khảo) |
| 20 | `a16577b54adf7ee8.pdf` | PDF/manual | Tài liệu kỹ thuật chính thức từ MVSilicon (Hướng dẫn sử dụng ACPWorkbench V2.21.6 và Datasheet) | V2.21.6 (34 trang) | ACPWorkbench_V2.44.2.exe | HIGH (Vendor Specification) | SAFE | YES (Tài liệu đối chiếu register và protocol) |
| 21 | `acp_dsp_assistant.py` | Python DSP tool | Trợ lý GUI tự tính toán hệ số Biquad, giải quyết Firmware mismatch, tạo sector Flash 4KB và gọi ACPWorkbench | 2.0 (Tkinter GUI) | CHAY_DSP_ASSISTANT.bat, ACPWorkbench_V2.44.2.exe | HIGH | UNSAFE (Có gọi subprocess.Popen để chạy EXE) | YES (Nguồn tham khảo thuật toán tính Biquad & CRC) |
| 22 | `acp_dsp_effects.h` | Header | Cấu trúc C Fixed-Point Q4.27 (biquad IIR) và DRC limiter cho Keil C firmware | SampleRate 44100 / Q4.27 (1 << 27) | gen_configs.py, acp_eq_styles.xml | HIGH | SAFE | YES (Golden Reference cho C Renderer) |
| 23 | `acp_eq_styles.xml` | XML | Định dạng XBEL XML nhập trực tiếp vào đồ thị EQ Editor của ACPWorkbench | XBEL 3.0 | acp_dsp_effects.h, acp_workbench_config.ini | HIGH | SAFE | YES (Template cho XML Export) |
| 24 | `acp_flash_parameters.bin` | Flash binary | Sector 4096 bytes (4KB) nhị phân kèm CRC32 nạp SPI Flash bộ nhớ ngoài | 4KB Sector / CRC32 | acp_dsp_assistant.py | MEDIUM (Chưa có hardware-in-the-loop verify) | UNSAFE (Có thể ghi đè SPI flash nếu nạp sai sector) | REFERENCE ONLY (Tuyệt đối không flash trực tiếp) |
| 25 | `acp_workbench_config.ini` | ACPWorkbench INI | Cấu hình 2 kênh Bi-Amp tối ưu (Sub Boombox + Mid-Treble AIRS) đang hoạt động | Firmware 0.3.4 (Type 48 = BP1048B2) | dsp.c, dsp_punchy_bass_sweet_vocal.c, acp_eq_styles.xml | HIGH (Current Production Reference) | SAFE | YES (Profile B&O 8Ω 24V Golden Reference) |
| 26 | `adjust_moderate_gain.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: adjust_moderate_gain | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 27 | `create_bass_boosted.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: create_bass_boosted | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 28 | `dsp.c` | C configuration | Mảng nhị phân hex cấu hình Bi-Amp tối ưu hiện hành (1667 bytes) | ACPWorkbench 2.44.2 / Firmware 0.3.4 | dsp.ini, dsp_punchy_bass_sweet_vocal.ini | HIGH | SAFE | YES (Golden Reference mảng byte cân chỉnh) |
| 29 | `dsp.ini` | ACPWorkbench INI | Cấu hình 2 kênh Bi-Amp tối ưu (Sub Boombox + Mid-Treble AIRS) đang hoạt động | Firmware 0.3.4 (Type 48 = BP1048B2) | dsp.c, dsp_punchy_bass_sweet_vocal.c, acp_eq_styles.xml | HIGH (Current Production Reference) | SAFE | YES (Profile B&O 8Ω 24V Golden Reference) |
| 30 | `dsp_balanced_bose.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_balanced_bose | ACPWorkbench 2.44.2 | dsp_balanced_bose.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 31 | `dsp_balanced_bose.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_balanced_bose | Firmware 0.3.4 (Type 48) | dsp_balanced_bose.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 32 | `dsp_bass_boosted.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_bass_boosted | ACPWorkbench 2.44.2 | dsp_bass_boosted.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 33 | `dsp_bass_boosted.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_bass_boosted | Firmware 0.3.4 (Type 48) | dsp_bass_boosted.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 34 | `dsp_clean_no_noise.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_clean_no_noise | ACPWorkbench 2.44.2 | dsp_clean_no_noise.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 35 | `dsp_clean_no_noise.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_clean_no_noise | Firmware 0.3.4 (Type 48) | dsp_clean_no_noise.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 36 | `dsp_master_ultimate.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_master_ultimate | ACPWorkbench 2.44.2 | dsp_master_ultimate.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 37 | `dsp_master_ultimate.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_master_ultimate | Firmware 0.3.4 (Type 48) | dsp_master_ultimate.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 38 | `dsp_original.c` | Original/restore (C) | Mảng nhị phân hex 1667 bytes cấu hình gốc xuất từ ACPWorkbench | ACPWorkbench 2.44.2 / Firmware 0.3.4 | dsp_original.ini | HIGH (Factory Golden Reference) | SAFE | YES (Golden Reference mảng byte gốc) |
| 39 | `dsp_original.ini` | Original/restore (INI) | Cấu hình gốc nhà máy trích xuất từ mạch nguyên bản Best Sound T1V2 | Firmware 0.3.4 (Type 48 = BP1048B2) | dsp_original.c, dsp_restore_original.c | HIGH (Factory Golden Reference) | SAFE | YES (Mốc khôi phục gốc / Safe Rollback) |
| 40 | `dsp_punchy_bass_sweet_vocal.c` | C configuration | Mảng nhị phân hex cấu hình Bi-Amp tối ưu hiện hành (1667 bytes) | ACPWorkbench 2.44.2 / Firmware 0.3.4 | dsp.ini, dsp_punchy_bass_sweet_vocal.ini | HIGH | SAFE | YES (Golden Reference mảng byte cân chỉnh) |
| 41 | `dsp_punchy_bass_sweet_vocal.ini` | ACPWorkbench INI | Cấu hình 2 kênh Bi-Amp tối ưu (Sub Boombox + Mid-Treble AIRS) đang hoạt động | Firmware 0.3.4 (Type 48 = BP1048B2) | dsp.c, dsp_punchy_bass_sweet_vocal.c, acp_eq_styles.xml | HIGH (Current Production Reference) | SAFE | YES (Profile B&O 8Ω 24V Golden Reference) |
| 42 | `dsp_punchy_bass_sweet_vocal_haynhat.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_punchy_bass_sweet_vocal_haynhat | ACPWorkbench 2.44.2 | dsp_punchy_bass_sweet_vocal_haynhat.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 43 | `dsp_punchy_bass_sweetan.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_punchy_bass_sweetan | Firmware 0.3.4 (Type 48) | dsp_punchy_bass_sweetan.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 44 | `dsp_restore_original.c` | Original/restore (C) | Mảng nhị phân hex 1667 bytes cấu hình gốc xuất từ ACPWorkbench | ACPWorkbench 2.44.2 / Firmware 0.3.4 | dsp_original.ini | HIGH (Factory Golden Reference) | SAFE | YES (Golden Reference mảng byte gốc) |
| 45 | `dsp_restore_original.ini` | Original/restore (INI) | Cấu hình gốc nhà máy trích xuất từ mạch nguyên bản Best Sound T1V2 | Firmware 0.3.4 (Type 48 = BP1048B2) | dsp_original.c, dsp_restore_original.c | HIGH (Factory Golden Reference) | SAFE | YES (Mốc khôi phục gốc / Safe Rollback) |
| 46 | `dsp_smooth_no_stutter.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_smooth_no_stutter | ACPWorkbench 2.44.2 | dsp_smooth_no_stutter.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 47 | `dsp_smooth_no_stutter.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_smooth_no_stutter | Firmware 0.3.4 (Type 48) | dsp_smooth_no_stutter.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 48 | `dsp_upgraded.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_upgraded | ACPWorkbench 2.44.2 | dsp_upgraded.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 49 | `dsp_upgraded.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_upgraded | Firmware 0.3.4 (Type 48) | dsp_upgraded.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 50 | `dsp_warm_bass_bright_treble.c` | Preset/profile (C) | Mảng nhị phân hex cấu hình cho profile dsp_warm_bass_bright_treble | ACPWorkbench 2.44.2 | dsp_warm_bass_bright_treble.ini | HIGH | SAFE | YES (Golden Reference mảng byte) |
| 51 | `dsp_warm_bass_bright_treble.ini` | Preset/profile (INI) | Preset cấu hình âm thanh: dsp_warm_bass_bright_treble | Firmware 0.3.4 (Type 48) | dsp_warm_bass_bright_treble.c | HIGH | SAFE | YES (Nguồn dữ liệu profile cục bộ) |
| 52 | `fix_noise_punchy_bass_sweet_vocal.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: fix_noise_punchy_bass_sweet_vocal | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 53 | `gen_configs.py` | Python DSP tool | Script tính toán công thức biquad và sinh 3 file: XML, INI, C Header | 1.0 | acp_eq_styles.xml, acp_workbench_config.ini, acp_dsp_effects.h | HIGH | SAFE (Thuần toán học và ghi file config) | YES (Cốt lõi thuật toán Biquad RBJ) |
| 54 | `tune_8ohm_24v_profile.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_8ohm_24v_profile | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 55 | `tune_anti_hiss_punchy_sweet.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_anti_hiss_punchy_sweet | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 56 | `tune_balanced.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_balanced | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 57 | `tune_bo_signature.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_bo_signature | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 58 | `tune_clean_no_noise.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_clean_no_noise | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 59 | `tune_jbl_boombox_profile.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_jbl_boombox_profile | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 60 | `tune_master_ultimate.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_master_ultimate | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 61 | `tune_midbass_ts_profile.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_midbass_ts_profile | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 62 | `tune_punchy_sweet.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_punchy_sweet | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 63 | `tune_smooth_no_stutter.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_smooth_no_stutter | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 64 | `tune_warm_bright.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: tune_warm_bright | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 65 | `upgrade_brighter_treble.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: upgrade_brighter_treble | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 66 | `upgrade_dsp.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: upgrade_dsp | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 67 | `upgrade_jbl_deep_punchy_bass.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: upgrade_jbl_deep_punchy_bass | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 68 | `upgrade_ultimate_punchy_sweet.py` | Python DSP tool | Script điều chỉnh/tạo profile DSP: upgrade_ultimate_punchy_sweet | 1.0 | dsp_original.ini, dsp_original.c | HIGH | SAFE (Chỉ đọc/ghi file INI và C cục bộ) | YES (Nguồn trích xuất thông số profile chuẩn) |
| 69 | `android_app\build.gradle` | Android source | Cấu hình build hệ thống Gradle cho ứng dụng Android native | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 70 | `android_app\gradle.properties` | Android source | Cấu hình build hệ thống Gradle cho ứng dụng Android native | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 71 | `android_app\local.properties` | Android source | Cấu hình build hệ thống Gradle cho ứng dụng Android native | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 72 | `android_app\settings.gradle` | Android source | Cấu hình build hệ thống Gradle cho ứng dụng Android native | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 73 | `android_app\app\build.gradle` | Android source | Cấu hình build hệ thống Gradle cho ứng dụng Android native | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 74 | `android_app\app\src\main\AndroidManifest.xml` | Android source | Khai báo quyền USB Host (OTG), Bluetooth Classic/BLE và Activity chính | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 75 | `android_app\app\src\main\java\com\bestsound\dsp\BluetoothDspManager.java` | Android source | Quản lý kết nối Bluetooth SPP RFCOMM socket và truyền gói lệnh DSP nhị phân | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 76 | `android_app\app\src\main\java\com\bestsound\dsp\DspProfiles.java` | Android source | Thư viện mảng nhị phân profile và các hàm đóng gói (frame builder) cho Sub/Treble/MVBass/PEQ 8 band | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 77 | `android_app\app\src\main\java\com\bestsound\dsp\MainActivity.java` | Android source | Activity điều khiển chính: quản lý kết nối Bluetooth, USB OTG, 8 thanh trượt PEQ và giao diện người dùng | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 78 | `android_app\app\src\main\java\com\bestsound\dsp\UsbDspManager.java` | Android source | Quản lý kết nối USB OTG Host (UsbManager, UsbDeviceConnection, Bulk/Control transfers) | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 79 | `android_app\app\src\main\res\layout\activity_main.xml` | Android source | Giao diện layout XML hoặc định nghĩa tài nguyên màu sắc/chuỗi/theme | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 80 | `android_app\app\src\main\res\values\colors.xml` | Android source | Giao diện layout XML hoặc định nghĩa tài nguyên màu sắc/chuỗi/theme | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 81 | `android_app\app\src\main\res\values\strings.xml` | Android source | Giao diện layout XML hoặc định nghĩa tài nguyên màu sắc/chuỗi/theme | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 82 | `android_app\app\src\main\res\values\themes.xml` | Android source | Giao diện layout XML hoặc định nghĩa tài nguyên màu sắc/chuỗi/theme | SDK 35 / MinSdk 26 | android_app/ | HIGH | SAFE | YES |
| 83 | `peq_studio\index.html` | Web Application Prototype | Ứng dụng phòng thu PEQ & Acoustic RTA độc lập (Web Audio API, Canvas 2D 60fps, RBJ Biquad, RTA Mic FFT, Signal Gen) | 3.0 | serve_studio.py, CHAY_PEQ_RTA_STUDIO.bat | HIGH | SAFE | YES (Nền tảng thuật toán Web Audio và RTA) |
| 84 | `peq_studio\serve_studio.py` | Python Local Server | Máy chủ HTTP cục bộ mở phòng thu trên trình duyệt PC và cung cấp link Wi-Fi cho điện thoại | 1.0 | index.html | HIGH | SAFE | YES |
| 85 | `Audio_And\.gitattributes` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: .gitattributes | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 86 | `Audio_And\.gitignore` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: .gitignore | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 87 | `Audio_And\.mise.toml` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: .mise.toml | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 88 | `Audio_And\AGENTS.md` | Tài liệu kỹ thuật / Quy tắc dự án | Hướng dẫn vòng đời phát triển Next.js/Payload, quản lý routing, styling Tailwind v4 và verify deploy | 1.0 | Audio_And/ | HIGH | SAFE | YES (Quy tắc phát triển Next.js) |
| 89 | `Audio_And\CLAUDE.md` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: CLAUDE.md | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 90 | `Audio_And\figma-image-loader.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: figma-image-loader.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 91 | `Audio_And\next.config.ts` | Next.js / Payload CMS / React Source | Cấu hình build TypeScript, Next.js và dependencies | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 92 | `Audio_And\oxfmt.config.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: oxfmt.config.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 93 | `Audio_And\package.json` | Next.js / Payload CMS / React Source | Cấu hình build TypeScript, Next.js và dependencies | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 94 | `Audio_And\pnpm-lock.yaml` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: pnpm-lock.yaml | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 95 | `Audio_And\pnpm-workspace.yaml` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: pnpm-workspace.yaml | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 96 | `Audio_And\postcss.config.mjs` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: postcss.config.mjs | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 97 | `Audio_And\tsconfig.json` | Next.js / Payload CMS / React Source | Cấu hình build TypeScript, Next.js và dependencies | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 98 | `Audio_And\.figma\README.md` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: README.md | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 99 | `Audio_And\.figma\make\analyze-routes` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: analyze-routes | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 100 | `Audio_And\.figma\make\deploy` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: deploy | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 101 | `Audio_And\.figma\make\deploy-preview` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: deploy-preview | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 102 | `Audio_And\.figma\make\deploy.json` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: deploy.json | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 103 | `Audio_And\.figma\make\dev` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: dev | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 104 | `Audio_And\.figma\make\dev.json` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: dev.json | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 105 | `Audio_And\.figma\make\format` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: format | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 106 | `Audio_And\.figma\make\install` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: install | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 107 | `Audio_And\.figma\make\langserver` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: langserver | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 108 | `Audio_And\.figma\make\payload.json` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: payload.json | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 109 | `Audio_And\.figma\make\site.json` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: site.json | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 110 | `Audio_And\.figma\make\template-transition.json` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: template-transition.json | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 111 | `Audio_And\docs\GEMINI_OTG_HANDOFF.md` | Tài liệu kỹ thuật / Handoff | Quy định kiến trúc phân tích Gemini qua Argon Browser và pipeline nạp flash OTG an toàn | 1.0 | Audio_And/ | HIGH (Architecture Contract) | SAFE | YES (Ràng buộc kiến trúc bắt buộc) |
| 112 | `Audio_And\public\favicon.svg` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: favicon.svg | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 113 | `Audio_And\src\payload-types.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: payload-types.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 114 | `Audio_And\src\payload.config.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: payload.config.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 115 | `Audio_And\src\app\(frontend)\layout.tsx` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: layout.tsx | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 116 | `Audio_And\src\app\(frontend)\not-found.tsx` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: not-found.tsx | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 117 | `Audio_And\src\app\(frontend)\page.tsx` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: page.tsx | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 118 | `Audio_And\src\app\(frontend)\styles.css` | Next.js / Payload CMS / React Source | Định nghĩa màu sắc CSS tokens, theme tối studio, kiểu dáng slider và responsive mobile/desktop | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 119 | `Audio_And\src\app\(frontend)\.figma\make\[asset]\route.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: route.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 120 | `Audio_And\src\app\(payload)\custom.css` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: custom.css | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 121 | `Audio_And\src\app\(payload)\layout.tsx` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: layout.tsx | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 122 | `Audio_And\src\app\(payload)\admin\importMap.js` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: importMap.js | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 123 | `Audio_And\src\app\(payload)\admin\logout\route.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: route.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 124 | `Audio_And\src\app\(payload)\admin\[[...segments]]\not-found.tsx` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: not-found.tsx | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 125 | `Audio_And\src\app\(payload)\admin\[[...segments]]\page.tsx` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: page.tsx | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 126 | `Audio_And\src\app\(payload)\api\graphql\route.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: route.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 127 | `Audio_And\src\app\(payload)\api\graphql-playground\route.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: route.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 128 | `Audio_And\src\app\(payload)\api\[...slug]\route.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: route.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 129 | `Audio_And\src\collections\Admins.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: Admins.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 130 | `Audio_And\src\collections\Folders.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: Folders.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 131 | `Audio_And\src\collections\Media.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: Media.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 132 | `Audio_And\src\collections\Tags.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: Tags.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 133 | `Audio_And\src\components\AiCalibrationPanel.tsx` | Next.js / Payload CMS / React Source | Component cân chỉnh âm học AI & OTG Programmer (RTA, mục tiêu âm học, kết nối Argon Gemini, xuất INI/C, nạp OTG) | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH (Primary AI/OTG Target) | SAFE | YES (Component cốt lõi cần nâng cấp) |
| 134 | `Audio_And\src\components\DspController.tsx` | Next.js / Payload CMS / React Source | Component giao diện chính BEST SOUND DSP CONTROLLER (Studio Dark theme, Spectrum, 8 PEQ faders, MVBass, Bi-Amp, Presets, Bottom Nav) | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH (Primary UI Target) | SAFE | YES (Component cốt lõi cần nâng cấp) |
| 135 | `Audio_And\src\lib\make-custom-code.tsx` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: make-custom-code.tsx | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 136 | `Audio_And\src\lib\make-site-settings.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: make-site-settings.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |
| 137 | `Audio_And\src\lib\payload.ts` | Next.js / Payload CMS / React Source | Source code phụ trợ / cấu hình / schema: payload.ts | Next.js 16.4.2 / React 19.3.1 / Tailwind v4 | Audio_And/ | HIGH | SAFE | YES (Target Project UI) |

---

## 3. KẾT LUẬN VÀ PHÁT HIỆN QUAN TRỌNG TỪ AUDIT

1. **Source of Truth cho cấu hình DSP:**
   - Cặp file `dsp_original.ini` và `dsp_original.c` (MD5 khớp 100% với `dsp_restore_original.*`) là cấu hình xuất xưởng gốc của bo mạch Best Sound T1V2 (Firmware Type 48 = BP1048B2, Version 0.3.4, Effect 2.45.5).
   - Cặp file `dsp.ini` và `dsp.c` (MD5 khớp 100% với `dsp_punchy_bass_sweet_vocal.*` và `acp_workbench_config.ini`) là cấu hình Bi-Amp tối ưu hiện thời được tune bởi `tune_8ohm_24v_profile.py`.
2. **Bản chất của file `.c`:**
   - File `.c` trong project này **không phải mã nguồn thuật toán C thông thường**, mà là một mảng nhị phân đóng gói `const unsigned char dsp[1667]` gồm 43 frame giao tiếp USB/UART chuẩn MVSilicon (bắt đầu bằng `0xA5 0x5A`, mã hiệu lệnh, chiều dài payload, dữ liệu thanh ghi và kết thúc bằng `0x16`).
   - Mảng byte trong `DspProfiles.java` của Android app lấy trực tiếp từ mảng `dsp[]` trong file `.c` này.
3. **Mã nguồn Android và Giao tiếp OTG:**
   - Đã kiểm toán toàn bộ thư mục `android_app/`: Chứa mã nguồn Android Native Java sạch 100%, không dùng thư viện ngoài.
   - Giao tiếp USB Host OTG sử dụng `android.hardware.usb.UsbManager`, tìm kiếm VID `0x4C4A` / `0x8888` hoặc thiết bị có tên MVSilicon/Audio/Best Sound.
   - Giao tiếp hỗ trợ 2 chế độ: Bulk OUT transfer (Endpoint OUT) và HID Control Transfer (`0x21`, `0x09`, Set_Report `0x0200`).
4. **Quy tắc an toàn phần cứng:**
   - File `acp_flash_parameters.bin` (4KB) là sector raw flash. Tuyệt đối không tự ý flash đè lên SPI flash của chip khi chưa có tính năng read-back verify và backup an toàn.
   - Các file `.exe` (ACPWorkbench V2.44.2) không được tự động thực thi trong môi trường tự động hóa headless.
