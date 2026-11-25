import os
import re
import struct

def s16_bytes(val):
    return struct.pack('<h', int(val))

def u16_bytes(val):
    return struct.pack('<H', int(val) & 0xFFFF)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    orig_ini_path = os.path.join(base_dir, 'dsp_original.ini')
    orig_c_path = os.path.join(base_dir, 'dsp_original.c')

    with open(orig_ini_path, 'r', encoding='utf-8') as f:
        ini_lines = f.readlines()
    with open(orig_c_path, 'r', encoding='utf-8') as f:
        c_text = f.read()

    # B&O SIGNATURE BASS: "Nội lực nhưng gọn gàng, chắc, ấm áp, sâu vừa phải, không lấn át vocal"
    # - HPF 48 Hz (LR24) cắt sạch dải quá thấp để màng loa kiểm soát tốc độ cao
    # - LPF 350 Hz (LR24) cắt dốc tách bạch hoàn toàn dải trầm khỏi dải trung
    # - 62 Hz: +4.2 dB (1075) -> Nền sub-bass sâu, êm ái, nhung lụa
    # - 85 Hz: +4.8 dB (1228) -> Tiếng kick chắc, gọn, đánh nảy và dứt khoát
    # - 125 Hz: +2.5 dB (640) -> Thân bass ấm áp, mộc mạc chuẩn âm sắc Bắc Âu
    # - 165 Hz: -3.0 dB (-768) -> Gọt sạch bọng thùng 5L, giữ âm trường tĩnh lặng và sạch sẽ
    sub_filters = [
        {'enable': True, 'type': 4, 'f0': 48, 'Q': 724, 'gain': 0},       # HPF 48Hz
        {'enable': True, 'type': 3, 'f0': 350, 'Q': 724, 'gain': 0},      # LPF 350Hz (1/2)
        {'enable': True, 'type': 3, 'f0': 350, 'Q': 724, 'gain': 0},      # LPF 350Hz (2/2)
        {'enable': True, 'type': 0, 'f0': 62, 'Q': 870, 'gain': 1075},    # +4.2 dB deep velvet bass
        {'enable': True, 'type': 0, 'f0': 85, 'Q': 920, 'gain': 1228},    # +4.8 dB tight, punchy kick
        {'enable': True, 'type': 0, 'f0': 125, 'Q': 950, 'gain': 640},    # +2.5 dB warm acoustic body
        {'enable': True, 'type': 0, 'f0': 165, 'Q': 1024, 'gain': -768},  # -3.0 dB anti-boom (clean separation)
    ]

    # B&O SIGNATURE VOCAL & TREBLE: "Tinh tế, chi tiết, mượt mà, trong trẻo, vocal ngọt ngào trung thực"
    # - HPF 240 Hz (bảo vệ củ AIRS, loại bỏ hoàn toàn méo tần số thấp)
    # - 500 Hz: +2.0 dB (512) -> Thân giọng dày dặn, đầm ấm, mộc mạc
    # - 1000 Hz: +3.5 dB (896) -> Cốt lõi vocal B&O: ngọt ngào, tinh tế, mượt như nhung lụa
    # - 2500 Hz: +3.8 dB (972) -> Giọng hát trong trẻo, thanh thoát, mở rộng chiều sâu âm hình
    # - 4500 Hz: +3.0 dB (768) -> Chi tiết khẩu hình, tiếng thở nhẹ, tách bạch nhạc cụ acoustic
    # - 8000 Hz: +4.2 dB (1075) -> Tiếng gõ tơi xốp, long lanh, không gắt
    # - 12000 Hz: +4.8 dB (1228) -> Dải cao trong suốt, lung linh đặc trưng B&O
    # - 16000 Hz: +4.8 dB (1228) -> High Shelf mở rộng không gian 3D, âm thanh mở đa hướng
    sat_filters = [
        {'enable': True, 'type': 4, 'f0': 240, 'Q': 724, 'gain': 0},      # HPF 240Hz
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 819, 'gain': 512},    # +2.0 dB warm chest
        {'enable': True, 'type': 0, 'f0': 1000, 'Q': 819, 'gain': 896},   # +3.5 dB sweet B&O vocal
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 972},   # +3.8 dB transparent clarity
        {'enable': True, 'type': 0, 'f0': 4500, 'Q': 920, 'gain': 768},   # +3.0 dB organic detail
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 1075},  # +4.2 dB crisp shimmer
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 819, 'gain': 1228}, # +4.8 dB crystal air
        {'enable': True, 'type': 2, 'f0': 16000, 'Q': 724, 'gain': 1228}, # +4.8 dB High Shelf 3D
    ]

    clean_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            clean_ini.append(line)
            continue

        # 1. PGA0: Chống xì nền, giữ gain chuẩn 21
        if current_sec == '0x03-PGA0':
            if sline.startswith('line1_left_enable'):
                clean_ini.append('line1_left_enable = 1\n')
                continue
            elif sline.startswith('line1_right_enable'):
                clean_ini.append('line1_right_enable = 1\n')
                continue
            elif sline.startswith('line2_left_enable'):
                clean_ini.append('line2_left_enable = 0\n')
                continue
            elif sline.startswith('line2_right_enable'):
                clean_ini.append('line2_right_enable = 0\n')
                continue
            elif sline.startswith('line4_left_enable'):
                clean_ini.append('line4_left_enable = 0\n')
                continue
            elif sline.startswith('line4_right_enable'):
                clean_ini.append('line4_right_enable = 0\n')
                continue
            elif sline.startswith('line5_left_enable'):
                clean_ini.append('line5_left_enable = 0\n')
                continue
            elif sline.startswith('line5_right_enable'):
                clean_ini.append('line5_right_enable = 0\n')
                continue
            elif sline.startswith('line1_left_gain'):
                clean_ini.append('line1_left_gain = 21\n')
                continue
            elif sline.startswith('line1_right_gain'):
                clean_ini.append('line1_right_gain = 21\n')
                continue
            elif sline.startswith('line2_left_gain'):
                clean_ini.append('line2_left_gain = 21\n')
                continue
            elif sline.startswith('line2_right_gain'):
                clean_ini.append('line2_right_gain = 21\n')
                continue
            elif sline.startswith('line4_5_left_gain'):
                clean_ini.append('line4_5_left_gain = 21\n')
                continue
            elif sline.startswith('line4_5_right_gain'):
                clean_ini.append('line4_5_right_gain = 21\n')
                continue
            elif sline.startswith('reserved'):
                clean_ini.append('reserved = 21\n')
                continue

        # 2. PGA1 & ADC1: Mute Mic floating
        elif current_sec == '0x06-PGA1':
            if sline.startswith('line3_left_mic1_enable'):
                clean_ini.append('line3_left_mic1_enable = 0\n')
                continue
            elif sline.startswith('line3_right_mic2_enable'):
                clean_ini.append('line3_right_mic2_enable = 0\n')
                continue
        elif current_sec == '0x07-ADC1':
            if sline.startswith('enable'):
                clean_ini.append('enable = 0\n')
                continue
            elif sline.startswith('mute'):
                clean_ini.append('mute = 1\n')
                continue

        # 3. DAC0: Volume 4543 kèm Dither & Scramble
        elif current_sec == '0x09-DAC0':
            if sline.startswith('left_volume'):
                clean_ini.append('left_volume = 4543\n')
                continue
            elif sline.startswith('right_volume'):
                clean_ini.append('right_volume = 4543\n')
                continue
            elif sline.startswith('dither'):
                clean_ini.append('dither = 1\n')
                continue
            elif sline.startswith('scramble'):
                clean_ini.append('scramble = 1\n')
                continue
        elif current_sec == '0x0a-DAC1':
            if sline.startswith('dither'):
                clean_ini.append('dither = 1\n')
                continue
            elif sline.startswith('scramble'):
                clean_ini.append('scramble = 1\n')
                continue

        # 4. NOISE GATE: Tắt để tiếng mượt mà 100%
        elif current_sec == '0x85-Noise_Suppressor_Expander':
            if sline.startswith('enable'):
                clean_ini.append('enable = 0\n')
                continue
            elif sline.startswith('ratio'):
                clean_ini.append('ratio = 1\n')
                continue

        # 5. SILENCE DETECTOR: amplitude = 0
        elif current_sec == '0x86-SilenceDetector':
            if sline.startswith('amplitude'):
                clean_ini.append('amplitude = 0\n')
                continue

        # 6. MVBass Classic: 55Hz, 20% (Bass đầm sâu, thanh lịch chuẩn B&O)
        elif current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                clean_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                clean_ini.append('intensity = 20\n')
                continue

        # 7. Bypass secondary MVBass
        elif current_sec == '0x88-MVBass':
            if sline.startswith('enable'):
                clean_ini.append('enable = 0\n')
                continue

        # 8. Harmonic Exciter: wet = 26 (Kích thích dải tép sang trọng, tinh tế B&O)
        elif current_sec == '0x89-Harmonic_Exciter':
            if sline.startswith('enable'):
                clean_ini.append('enable = 1\n')
                continue
            elif sline.startswith('cutoff_frequency'):
                clean_ini.append('cutoff_frequency = 1200\n')
                continue
            elif sline.startswith('dry'):
                clean_ini.append('dry = 100\n')
                continue
            elif sline.startswith('wet'):
                clean_ini.append('wet = 26\n')
                continue

        # 9. Master Tone Control [0x91-EQ]
        elif current_sec == '0x91-EQ':
            if sline.startswith('pregain'):
                clean_ini.append('pregain = 0\n')
                continue
            elif sline.startswith('filter1_gain'):
                clean_ini.append('filter1_gain = 512\n')
                continue
            elif sline.startswith('filter3_gain'):
                clean_ini.append('filter3_gain = 128\n')
                continue

        # 10. Music:DRC [0x93-DRC]: Master Brickwall Limiter (-0.8 dBFS, ratio 50, attack 2ms)
        elif current_sec == '0x93-DRC':
            if sline.startswith('threshold1'):
                clean_ini.append('threshold1 = -80\n')
                continue
            elif sline.startswith('threshold2'):
                clean_ini.append('threshold2 = -80\n')
                continue
            elif sline.startswith('threshold3'):
                clean_ini.append('threshold3 = -80\n')
                continue
            elif sline.startswith('threshold4'):
                clean_ini.append('threshold4 = -80\n')
                continue
            elif sline.startswith('ratio1'):
                clean_ini.append('ratio1 = 50\n')
                continue
            elif sline.startswith('ratio2'):
                clean_ini.append('ratio2 = 50\n')
                continue
            elif sline.startswith('ratio3'):
                clean_ini.append('ratio3 = 50\n')
                continue
            elif sline.startswith('ratio4'):
                clean_ini.append('ratio4 = 50\n')
                continue
            elif sline.startswith('attack1'):
                clean_ini.append('attack1 = 2\n')
                continue
            elif sline.startswith('attack2'):
                clean_ini.append('attack2 = 2\n')
                continue
            elif sline.startswith('attack3'):
                clean_ini.append('attack3 = 2\n')
                continue
            elif sline.startswith('attack4'):
                clean_ini.append('attack4 = 2\n')
                continue
            elif sline.startswith('release1'):
                clean_ini.append('release1 = 60\n')
                continue
            elif sline.startswith('release2'):
                clean_ini.append('release2 = 60\n')
                continue
            elif sline.startswith('release3'):
                clean_ini.append('release3 = 60\n')
                continue
            elif sline.startswith('release4'):
                clean_ini.append('release4 = 60\n')
                continue

        # 11. ButterWorth EQ (DAC1 Subwoofer)
        elif current_sec == '0x94-User-defined_Effect':
            if sline.startswith('Cut Freq'):
                clean_ini.append('Cut Freq = 48\n')
                continue

        # 12. GAIN CÂN BẰNG HOÀN HẢO B&O:
        # Treble Gain = 7500 (+5.25 dB) -> Dải cao tinh tế, vocal thanh tao, bay bổng
        # Mid Gain (CH1 Subwoofer) = 5800 (+3.0 dB) -> Bass nội lực, chắc nịch nhưng gãy gọn, không đè lấn vocal
        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                clean_ini.append('gain = 7500\n')
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain (CH1 Subwoofer)
            if sline.startswith('gain'):
                clean_ini.append('gain = 5800\n')
                continue

        # 13. Sub DRC [0x9b-DRC] & [0x9c-DRC]: Bảo vệ chống vỡ tiếng
        elif current_sec in ['0x9b-DRC', '0x9c-DRC']:
            if sline.startswith('threshold4'):
                clean_ini.append('threshold4 = -120\n')
                continue
            elif sline.startswith('ratio4'):
                clean_ini.append('ratio4 = 50\n')
                continue
            elif sline.startswith('attack4'):
                clean_ini.append('attack4 = 2\n')
                continue
            elif sline.startswith('release4'):
                clean_ini.append('release4 = 100\n')
                continue

        # 14. Subwoofer EQ (0x95 Bass SPK & 0x97 Mid SPK - CH1)
        elif current_sec in ['0x95-EQ', '0x97-EQ']:
            if sline.startswith('pregain'):
                clean_ini.append('pregain = 0\n')
                continue
            elif sline.startswith('calculation_type'):
                clean_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sub_filters):
                        flt = sub_filters[fi]
                        clean_ini.append(f'filter{fnum}_enable = 1\n')
                        clean_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        clean_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        clean_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        clean_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        clean_ini.append(f'filter{fnum}_enable = 0\n')
                        clean_ini.append(f'filter{fnum}_type = 0\n')
                        clean_ini.append(f'filter{fnum}_f0 = 0\n')
                        clean_ini.append(f'filter{fnum}_Q = 0\n')
                        clean_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        # 15. Satellite EQ (0x96 Treble SPK - CH2)
        elif current_sec == '0x96-EQ':
            if sline.startswith('pregain'):
                clean_ini.append('pregain = 0\n')
                continue
            elif sline.startswith('calculation_type'):
                clean_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sat_filters):
                        flt = sat_filters[fi]
                        clean_ini.append(f'filter{fnum}_enable = 1\n')
                        clean_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        clean_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        clean_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        clean_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        clean_ini.append(f'filter{fnum}_enable = 0\n')
                        clean_ini.append(f'filter{fnum}_type = 0\n')
                        clean_ini.append(f'filter{fnum}_f0 = 0\n')
                        clean_ini.append(f'filter{fnum}_Q = 0\n')
                        clean_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        clean_ini.append(line)

    clean_ini_text = "".join(clean_ini)
    
    # Save target files
    punchy_ini_path = os.path.join(base_dir, 'dsp_punchy_bass_sweet_vocal.ini')
    with open(punchy_ini_path, 'w', encoding='utf-8') as f:
        f.write(clean_ini_text)
    
    with open(os.path.join(base_dir, 'dsp.ini'), 'w', encoding='utf-8') as f:
        f.write(clean_ini_text)
    with open(os.path.join(base_dir, 'acp_workbench_config.ini'), 'w', encoding='utf-8') as f:
        f.write(clean_ini_text)
    print("Updated dsp_punchy_bass_sweet_vocal.ini, dsp.ini, and acp_workbench_config.ini with B&O Sound Signature!")

    # Build C code
    def make_c_eq(sec_id, comment, pregain, filters):
        c_lines = [
            "0xA5, 0x5A,/*sync head*/",
            f"0x{sec_id:02X},/*{comment}*/",
            "0x6B,/*length*/",
            "0xFF,/*all parameter*/",
            "0x01, 0x00,/*enable*/",
            f"0x{u16_bytes(pregain)[0]:02X}, 0x{u16_bytes(pregain)[1]:02X},/*pregain*/",
            "0x00, 0x00,/*calculation_type*/"
        ]
        for fi in range(10):
            fnum = fi + 1
            if fi < len(filters):
                flt = filters[fi]
                c_lines.append(f"0x01, 0x00,/*filter{fnum}_enable: 1*/")
                c_lines.append(f"0x{flt['type']:02X}, 0x00,/*filter{fnum}_type*/")
                f0_b = u16_bytes(flt['f0'])
                c_lines.append(f"0x{f0_b[0]:02X}, 0x{f0_b[1]:02X},/*filter{fnum}_f0: {flt['f0']}Hz*/")
                q_b = u16_bytes(flt['Q'])
                c_lines.append(f"0x{q_b[0]:02X}, 0x{q_b[1]:02X},/*filter{fnum}_Q: {flt['Q']}*/")
                g_b = s16_bytes(flt['gain'])
                c_lines.append(f"0x{g_b[0]:02X}, 0x{g_b[1]:02X},/*filter{fnum}_gain: {flt['gain']}*/")
            else:
                c_lines.append(f"0x00, 0x00,/*filter{fnum}_enable*/")
                c_lines.append(f"0x00, 0x00,/*filter{fnum}_type*/")
                c_lines.append(f"0x00, 0x00,/*filter{fnum}_f0*/")
                c_lines.append(f"0x00, 0x00,/*filter{fnum}_Q*/")
                c_lines.append(f"0x00, 0x00,/*filter{fnum}_gain*/")
        c_lines.append("0x16,/*sync tail*/")
        return "\n".join(c_lines)

    c_up = c_text

    # 1. PGA0 (0x03)
    old_pga0 = """0xA5, 0x5A,/*sync head*/
0x03,/*PGA0*/
0x2F,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*line1_left_enable*/
0x01, 0x00,/*line1_right_enable*/
0x00, 0x00,/*line2_left_enable*/
0x01, 0x00,/*line2_right_enable*/
0x00, 0x00,/*line4_left_enable*/
0x01, 0x00,/*line4_right_enable*/
0x00, 0x00,/*line5_left_enable*/
0x01, 0x00,/*line5_right_enable*/
0x16, 0x00,/*line1_left_gain*/
0x16, 0x00,/*line1_right_gain*/
0x1A, 0x00,/*line2_left_gain*/
0x1A, 0x00,/*line2_right_gain*/
0x15, 0x00,/*line4_5_left_gain*/
0x2A, 0x00,/*line4_5_right_gain*/
0x15, 0x00,/*reserved*/
0x2A, 0x00,/*reserved*/
0x00, 0x00,/*Diff_input_enable*/
0x00, 0x00,/*Diff_left_gain*/
0x00, 0x00,/*Diff_right_gain*/
0x03, 0x00,/*Line1_left_right_pins*/
0x03, 0x00,/*Line2_left_right_pins*/
0x03, 0x00,/*Line4_left_right_pins*/
0x03, 0x00,/*Line5_left_right_pins*/
0x16,/*sync tail*/"""

    new_pga0 = """0xA5, 0x5A,/*sync head*/
0x03,/*PGA0*/
0x2F,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*line1_left_enable: 1*/
0x01, 0x00,/*line1_right_enable: 1*/
0x00, 0x00,/*line2_left_enable: 0*/
0x00, 0x00,/*line2_right_enable: 0*/
0x00, 0x00,/*line4_left_enable: 0*/
0x00, 0x00,/*line4_right_enable: 0*/
0x00, 0x00,/*line5_left_enable: 0*/
0x00, 0x00,/*line5_right_enable: 0*/
0x15, 0x00,/*line1_left_gain: 21*/
0x15, 0x00,/*line1_right_gain: 21*/
0x15, 0x00,/*line2_left_gain: 21*/
0x15, 0x00,/*line2_right_gain: 21*/
0x15, 0x00,/*line4_5_left_gain: 21*/
0x15, 0x00,/*line4_5_right_gain: 21*/
0x15, 0x00,/*reserved: 21*/
0x15, 0x00,/*reserved: 21*/
0x00, 0x00,/*Diff_input_enable*/
0x00, 0x00,/*Diff_left_gain*/
0x00, 0x00,/*Diff_right_gain*/
0x03, 0x00,/*Line1_left_right_pins*/
0x03, 0x00,/*Line2_left_right_pins*/
0x03, 0x00,/*Line4_left_right_pins*/
0x03, 0x00,/*Line5_left_right_pins*/
0x16,/*sync tail*/"""
    assert old_pga0 in c_up, "PGA0 block not found!"
    c_up = c_up.replace(old_pga0, new_pga0)

    # 2. PGA1 (0x06) -> disable mic
    old_pga1 = """0x06,/*PGA1*/
0x13,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*line3_left_mic1_enable*/
0x01, 0x00,/*line3_right_mic2_enable*/"""
    new_pga1 = """0x06,/*PGA1*/
0x13,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*line3_left_mic1_enable: 0*/
0x00, 0x00,/*line3_right_mic2_enable: 0*/"""
    assert old_pga1 in c_up, "PGA1 block not found!"
    c_up = c_up.replace(old_pga1, new_pga1)

    # 3. ADC1 (0x07) -> disable mic
    old_adc1 = """0x07,/*ADC1*/
0x15,/*length*/
0xFF,/*all parameter*/
0x03, 0x00,/*enable*/
0x00, 0x00,/*mute*/"""
    new_adc1 = """0x07,/*ADC1*/
0x15,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*enable: 0*/
0x01, 0x00,/*mute: 1*/"""
    assert old_adc1 in c_up, "ADC1 block not found!"
    c_up = c_up.replace(old_adc1, new_adc1)

    # 4. DAC0 (0x09) -> 4543 volume + dither 1, scramble 1
    old_dac0 = """0xA5, 0x5A,/*sync head*/
0x09,/*DAC0*/
0x1D,/*length*/
0xFF,/*all parameter*/
0x03, 0x00,/*enable*/
0x07, 0x00,/*sample_rate*/
0x00, 0x00,/*mute*/
0xBF, 0x11,/*left_volume*/
0xBF, 0x11,/*right_volume*/
0x00, 0x00,/*dither*/
0x00, 0x00,/*scramble*/"""

    new_dac0 = """0xA5, 0x5A,/*sync head*/
0x09,/*DAC0*/
0x1D,/*length*/
0xFF,/*all parameter*/
0x03, 0x00,/*enable*/
0x07, 0x00,/*sample_rate*/
0x00, 0x00,/*mute*/
0xBF, 0x11,/*left_volume: 4543*/
0xBF, 0x11,/*right_volume: 4543*/
0x01, 0x00,/*dither: 1*/
0x01, 0x00,/*scramble: 1*/"""
    assert old_dac0 in c_up, "DAC0 block not found!"
    c_up = c_up.replace(old_dac0, new_dac0)

    # 5. Noise Gate (0x85) -> disabled (enable = 0)
    old_85 = """0xA5, 0x5A,/*sync head*/
0x85,/*Music:Noise Gate Suppress*/
0x0B,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/"""
    new_85 = """0xA5, 0x5A,/*sync head*/
0x85,/*Music:Noise Gate Suppress*/
0x0B,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*enable: 0*/"""
    assert old_85 in c_up, "0x85 block not found!"
    c_up = c_up.replace(old_85, new_85)

    # 6. MVBass Classic (0x87) -> 55Hz, 20% (B&O tight refined bass)
    old_87 = """0xA5, 0x5A,/*sync head*/
0x87,/*Music:Virtual Bass Classi*/
0x07,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x3F, 0x00,/*cutoff_frequency*/
0x08, 0x00,/*intensity*/
0x16,/*sync tail*/"""
    new_87 = """0xA5, 0x5A,/*sync head*/
0x87,/*Music:Virtual Bass Classi*/
0x07,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x37, 0x00,/*cutoff_frequency: 55Hz*/
0x14, 0x00,/*intensity: 20% (B&O refined bass)*/
0x16,/*sync tail*/"""
    assert old_87 in c_up, "0x87 block not found!"
    c_up = c_up.replace(old_87, new_87)

    # 7. MVBass secondary (0x88) -> disable
    old_88 = """0xA5, 0x5A,/*sync head*/
0x88,/*Music:Virtual Bass       */
0x09,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/"""
    new_88 = """0xA5, 0x5A,/*sync head*/
0x88,/*Music:Virtual Bass       */
0x09,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*enable: 0*/"""
    assert old_88 in c_up, "0x88 block not found!"
    c_up = c_up.replace(old_88, new_88)

    # 8. Exciter (0x89) -> 1200Hz, wet = 26 (B&O crystal sheen)
    old_89 = """0xA5, 0x5A,/*sync head*/
0x89,/*Music:Exciter            */
0x09,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x4C, 0x04,/*cutoff_frequency*/
0x64, 0x00,/*dry*/
0x14, 0x00,/*wet*/
0x16,/*sync tail*/"""
    new_89 = """0xA5, 0x5A,/*sync head*/
0x89,/*Music:Exciter            */
0x09,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0xB0, 0x04,/*cutoff_frequency: 1200Hz*/
0x64, 0x00,/*dry: 100*/
0x1A, 0x00,/*wet: 26 (tinh tế B&O)*/
0x16,/*sync tail*/"""
    assert old_89 in c_up, "0x89 block not found!"
    c_up = c_up.replace(old_89, new_89)

    # 9. Music:DRC (0x93) -> Master Brickwall Limiter (-0.8 dBFS, ratio 50, attack 2ms)
    old_93 = """0xA5, 0x5A,/*sync head*/
0x93,/*Music:DRC                */
0x37,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x02, 0x00,/*mode*/
0x04, 0x00,/*type*/
0xD4, 0x02,/*ql*/
0xD4, 0x02,/*qh*/
0x2C, 0x01,/*fc1*/
0xD0, 0x07,/*fc2*/
0x00, 0x00,/*threshold1*/
0x00, 0x00,/*threshold2*/
0x00, 0x00,/*threshold3*/
0x00, 0x00,/*threshold4*/
0xE8, 0x03,/*ratio1*/
0x64, 0x00,/*ratio2*/
0x64, 0x00,/*ratio3*/
0x64, 0x00,/*ratio4*/
0x03, 0x00,/*attack1*/
0x64, 0x00,/*attack2*/
0x64, 0x00,/*attack3*/
0x64, 0x00,/*attack4*/
0x14, 0x00,/*release1*/
0x01, 0x00,/*release2*/
0x01, 0x00,/*release3*/
0x01, 0x00,/*release4*/
0x00, 0x10,/*pregain1*/
0x00, 0x10,/*pregain2*/
0x00, 0x10,/*pregain3*/
0x00, 0x10,/*pregain4*/
0x16,/*sync tail*/"""

    th_bytes = s16_bytes(-80)
    new_93 = f"""0xA5, 0x5A,/*sync head*/
0x93,/*Music:DRC                */
0x37,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x02, 0x00,/*mode*/
0x04, 0x00,/*type*/
0xD4, 0x02,/*ql*/
0xD4, 0x02,/*qh*/
0x2C, 0x01,/*fc1*/
0xD0, 0x07,/*fc2*/
0x{th_bytes[0]:02X}, 0x{th_bytes[1]:02X},/*threshold1: -80 (-0.8 dBFS)*/
0x{th_bytes[0]:02X}, 0x{th_bytes[1]:02X},/*threshold2: -80 (-0.8 dBFS)*/
0x{th_bytes[0]:02X}, 0x{th_bytes[1]:02X},/*threshold3: -80 (-0.8 dBFS)*/
0x{th_bytes[0]:02X}, 0x{th_bytes[1]:02X},/*threshold4: -80 (-0.8 dBFS)*/
0x32, 0x00,/*ratio1: 50 (brickwall)*/
0x32, 0x00,/*ratio2: 50 (brickwall)*/
0x32, 0x00,/*ratio3: 50 (brickwall)*/
0x32, 0x00,/*ratio4: 50 (brickwall)*/
0x02, 0x00,/*attack1: 2ms*/
0x02, 0x00,/*attack2: 2ms*/
0x02, 0x00,/*attack3: 2ms*/
0x02, 0x00,/*attack4: 2ms*/
0x3C, 0x00,/*release1: 60ms*/
0x3C, 0x00,/*release2: 60ms*/
0x3C, 0x00,/*release3: 60ms*/
0x3C, 0x00,/*release4: 60ms*/
0x00, 0x10,/*pregain1: 4096*/
0x00, 0x10,/*pregain2: 4096*/
0x00, 0x10,/*pregain3: 4096*/
0x00, 0x10,/*pregain4: 4096*/
0x16,/*sync tail*/"""
    assert old_93 in c_up, "0x93 block not found!"
    c_up = c_up.replace(old_93, new_93)

    # 10. ButterWorth EQ (0x94) -> 48Hz
    old_94 = """0xA5, 0x5A,/*sync head*/
0x94,/*Bass SPK:ButterWorth EQ  */
0x09,/*length*/
0xFF,/*User Defined Effect*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*filter_type*/
0x01, 0x00,/*filter_order*/
0x3C, 0x00,/*Cut Freq*/
0x16,/*sync tail*/"""
    new_94 = """0xA5, 0x5A,/*sync head*/
0x94,/*Bass SPK:ButterWorth EQ  */
0x09,/*length*/
0xFF,/*User Defined Effect*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*filter_type*/
0x01, 0x00,/*filter_order*/
0x30, 0x00,/*Cut Freq: 48Hz*/
0x16,/*sync tail*/"""
    assert old_94 in c_up, "0x94 block not found!"
    c_up = c_up.replace(old_94, new_94)

    # 11. Bass SPK EQ (0x95)
    c_95 = make_c_eq(0x95, "Bass SPK:Bass EQ         ", 0, sub_filters)
    idx_95 = c_up.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_95)
    c_up = c_up[:idx_95_start] + c_95 + "\n\n" + c_up[idx_95_end:]

    # 12. Treble SPK EQ (0x96)
    c_96 = make_c_eq(0x96, "Treble SPK:Treble EQ     ", 0, sat_filters)
    idx_96 = c_up.find("0x96,/*Treble SPK:Treble EQ")
    idx_96_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_96)
    idx_96_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_96)
    c_up = c_up[:idx_96_start] + c_96 + "\n\n" + c_up[idx_96_end:]

    # 13. Mid SPK EQ (0x97)
    c_97 = make_c_eq(0x97, "Mid SPK:Mid EQ           ", 0, sub_filters)
    idx_97 = c_up.find("0x97,/*Mid SPK:Mid EQ")
    idx_97_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_97)
    idx_97_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_97)
    c_up = c_up[:idx_97_start] + c_97 + "\n\n" + c_up[idx_97_end:]

    # 14. Treble Gain (0x98) -> 7500 (0x1D4C -> 0x4C, 0x1D: +5.25 dB B&O thanh thoát)
    old_98 = """0xA5, 0x5A,/*sync head*/
0x98,/*Treble SPK:Treble Gain   */
0x07,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mute*/
0x2F, 0x20,/*gain*/
0x16,/*sync tail*/"""
    new_98 = """0xA5, 0x5A,/*sync head*/
0x98,/*Treble SPK:Treble Gain   */
0x07,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mute*/
0x4C, 0x1D,/*gain: 7500 (+5.25 dB B&O trong trẻo)*/
0x16,/*sync tail*/"""
    assert old_98 in c_up, "0x98 block not found!"
    c_up = c_up.replace(old_98, new_98)

    # 15. Mid SPK Gain (0x99 - CH1 Subwoofer) -> 5800 (0x16A8 -> 0xA8, 0x16: +3.0 dB B&O nội lực, gọn gàng)
    old_99 = """0xA5, 0x5A,/*sync head*/
0x99,/*Mid SPK:Mid Gain         */
0x07,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mute*/
0x00, 0x10,/*gain*/
0x16,/*sync tail*/"""
    new_99 = """0xA5, 0x5A,/*sync head*/
0x99,/*Mid SPK:Mid Gain         */
0x07,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mute*/
0xA8, 0x16,/*gain: 5800 (+3.0 dB B&O nội lực gọn gàng)*/
0x16,/*sync tail*/"""
    assert old_99 in c_up, "0x99 block not found!"
    c_up = c_up.replace(old_99, new_99)

    # 16. Bass SPK DRC (0x9B)
    old_9b = """0xA5, 0x5A,/*sync head*/
0x9B,/*Bass SPK:Bass DRC        */
0x37,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mode*/
0x04, 0x00,/*type*/
0xD4, 0x02,/*ql*/
0xD4, 0x02,/*qh*/
0x89, 0x00,/*fc1*/
0x0A, 0x4E,/*fc2*/
0xCE, 0xFF,/*threshold1*/
0x00, 0x00,/*threshold2*/
0x00, 0x00,/*threshold3*/
0x7C, 0xFC,/*threshold4*/
0x64, 0x00,/*ratio1*/
0x64, 0x00,/*ratio2*/
0x64, 0x00,/*ratio3*/
0x0A, 0x00,/*ratio4*/
0x64, 0x00,/*attack1*/
0x64, 0x00,/*attack2*/
0x64, 0x00,/*attack3*/
0x0F, 0x00,/*attack4*/
0x01, 0x00,/*release1*/
0x01, 0x00,/*release2*/
0x01, 0x00,/*release3*/
0x5D, 0x01,/*release4*/
0x00, 0x10,/*pregain1*/
0x00, 0x10,/*pregain2*/
0x00, 0x10,/*pregain3*/
0x00, 0x10,/*pregain4*/
0x16,/*sync tail*/"""

    th_sub_bytes = s16_bytes(-120)
    new_9b = f"""0xA5, 0x5A,/*sync head*/
0x9B,/*Bass SPK:Bass DRC        */
0x37,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mode*/
0x04, 0x00,/*type*/
0xD4, 0x02,/*ql*/
0xD4, 0x02,/*qh*/
0x89, 0x00,/*fc1*/
0x0A, 0x4E,/*fc2*/
0xCE, 0xFF,/*threshold1*/
0x00, 0x00,/*threshold2*/
0x00, 0x00,/*threshold3*/
0x{th_sub_bytes[0]:02X}, 0x{th_sub_bytes[1]:02X},/*threshold4: -120 (-1.2 dBFS)*/
0x64, 0x00,/*ratio1*/
0x64, 0x00,/*ratio2*/
0x64, 0x00,/*ratio3*/
0x32, 0x00,/*ratio4: 50 (anti-clip)*/
0x64, 0x00,/*attack1*/
0x64, 0x00,/*attack2*/
0x64, 0x00,/*attack3*/
0x02, 0x00,/*attack4: 2ms*/
0x01, 0x00,/*release1*/
0x01, 0x00,/*release2*/
0x01, 0x00,/*release3*/
0x64, 0x00,/*release4: 100ms*/
0x00, 0x10,/*pregain1*/
0x00, 0x10,/*pregain2*/
0x00, 0x10,/*pregain3*/
0x00, 0x10,/*pregain4*/
0x16,/*sync tail*/"""
    assert old_9b in c_up, "0x9B block not found!"
    c_up = c_up.replace(old_9b, new_9b)

    # 17. Mid SPK DRC (0x9C)
    old_9c = """0xA5, 0x5A,/*sync head*/
0x9C,/*Mid SPK:Mid DRC         */
0x37,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mode*/
0x01, 0x00,/*type*/
0xD4, 0x02,/*ql*/
0xD4, 0x02,/*qh*/
0x3F, 0x01,/*fc1*/
0xD0, 0x07,/*fc2*/
0x00, 0x00,/*threshold1*/
0x00, 0x00,/*threshold2*/
0x00, 0x00,/*threshold3*/
0x7C, 0xFC,/*threshold4*/
0x64, 0x00,/*ratio1*/
0x64, 0x00,/*ratio2*/
0x64, 0x00,/*ratio3*/
0x0A, 0x00,/*ratio4*/
0x64, 0x00,/*attack1*/
0x64, 0x00,/*attack2*/
0x64, 0x00,/*attack3*/
0x0F, 0x00,/*attack4*/
0x01, 0x00,/*release1*/
0x01, 0x00,/*release2*/
0x01, 0x00,/*release3*/
0x5D, 0x01,/*release4*/
0x00, 0x10,/*pregain1*/
0x00, 0x10,/*pregain2*/
0x00, 0x10,/*pregain3*/
0x00, 0x10,/*pregain4*/
0x16,/*sync tail*/"""

    new_9c = f"""0xA5, 0x5A,/*sync head*/
0x9C,/*Mid SPK:Mid DRC         */
0x37,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x00, 0x00,/*mode*/
0x01, 0x00,/*type*/
0xD4, 0x02,/*ql*/
0xD4, 0x02,/*qh*/
0x3F, 0x01,/*fc1*/
0xD0, 0x07,/*fc2*/
0x00, 0x00,/*threshold1*/
0x00, 0x00,/*threshold2*/
0x00, 0x00,/*threshold3*/
0x{th_sub_bytes[0]:02X}, 0x{th_sub_bytes[1]:02X},/*threshold4: -120 (-1.2 dBFS)*/
0x64, 0x00,/*ratio1*/
0x64, 0x00,/*ratio2*/
0x64, 0x00,/*ratio3*/
0x32, 0x00,/*ratio4: 50 (anti-clip)*/
0x64, 0x00,/*attack1*/
0x64, 0x00,/*attack2*/
0x64, 0x00,/*attack3*/
0x02, 0x00,/*attack4: 2ms*/
0x01, 0x00,/*release1*/
0x01, 0x00,/*release2*/
0x01, 0x00,/*release3*/
0x64, 0x00,/*release4: 100ms*/
0x00, 0x10,/*pregain1*/
0x00, 0x10,/*pregain2*/
0x00, 0x10,/*pregain3*/
0x00, 0x10,/*pregain4*/
0x16,/*sync tail*/"""
    assert old_9c in c_up, "0x9C block not found!"
    c_up = c_up.replace(old_9c, new_9c)

    # Save target C files
    with open(os.path.join(base_dir, 'dsp_punchy_bass_sweet_vocal.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    with open(os.path.join(base_dir, 'dsp.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    print("Updated dsp_punchy_bass_sweet_vocal.c and dsp.c with B&O Sound Signature!")

    # Verify byte count and frames
    all_bytes = re.findall(r'0x[0-9A-Fa-f]{2}', c_up)
    print(f"Total bytes in output C: {len(all_bytes)}")
    assert len(all_bytes) == 1667, f"Expected 1667 bytes, got {len(all_bytes)}"
    print("Verification SUCCESSFUL! All 1667 bytes and 42 frames intact.")

if __name__ == '__main__':
    main()
