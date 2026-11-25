import os
import shutil
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

    # BASS: "khoẻ ấm kiểm soát gain"
    # - HPF 48 Hz (LR24)
    # - LPF 400 Hz (LR24)
    # - PEQ 65 Hz: +2.0 dB (512) -> Khoẻ, sâu
    # - PEQ 85 Hz: +2.0 dB (512) -> Nảy, đầm
    # - PEQ 120 Hz: +1.5 dB (384) -> Ấm áp
    # - PEQ 160 Hz: -2.5 dB (-640) -> Triệt tiêu ù rền thùng 5L
    # - PEQ 250 Hz: -1.0 dB (-256)
    sub_filters = [
        {'enable': True, 'type': 4, 'f0': 48, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 400, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 400, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 0, 'f0': 65, 'Q': 819, 'gain': 512},    # +2.0 dB
        {'enable': True, 'type': 0, 'f0': 85, 'Q': 819, 'gain': 512},    # +2.0 dB
        {'enable': True, 'type': 0, 'f0': 120, 'Q': 920, 'gain': 384},   # +1.5 dB warm
        {'enable': True, 'type': 0, 'f0': 160, 'Q': 1024, 'gain': -640}, # -2.5 dB clean anti-boom
    ]

    # TREBLE: "sáng hơn nữa"
    # - HPF 250 Hz
    # - 500 Hz: +1.5 dB (384)
    # - 1200 Hz: +1.5 dB (384)
    # - 2500 Hz: +2.0 dB (512)
    # - 5000 Hz: +2.0 dB (512) -> Sáng rõ
    # - 8000 Hz: +3.5 dB (896) -> Sắc nét
    # - 12000 Hz: +4.0 dB (1024) -> Tơi xốp
    # - 16000 Hz: High Shelf +4.5 dB (1152) -> Sáng bừng, leng keng, không gian rộng mở
    sat_filters = [
        {'enable': True, 'type': 4, 'f0': 250, 'Q': 724, 'gain': 0},      # HPF 250Hz
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 819, 'gain': 384},    # +1.5 dB
        {'enable': True, 'type': 0, 'f0': 1200, 'Q': 819, 'gain': 384},   # +1.5 dB
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 512},   # +2.0 dB
        {'enable': True, 'type': 0, 'f0': 5000, 'Q': 920, 'gain': 512},   # +2.0 dB bright presence
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 896},   # +3.5 dB crisp cymbal
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 819, 'gain': 1024}, # +4.0 dB airy sparkle
        {'enable': True, 'type': 2, 'f0': 16000, 'Q': 724, 'gain': 1152}, # +4.5 dB High Shelf open space
    ]

    tuned_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            tuned_ini.append(line)
            continue

        if current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                tuned_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                tuned_ini.append('intensity = 15\n') # 15% warm and firm
                continue

        elif current_sec == '0x89-Harmonic_Exciter': # Exciter for extra treble sparkle
            if sline.startswith('wet'):
                tuned_ini.append('wet = 35\n') # Add harmonic brilliance
                continue

        elif current_sec == '0x94-User-defined_Effect': # ButterWorth EQ
            if sline.startswith('Cut Freq'):
                tuned_ini.append('Cut Freq = 48\n')
                continue

        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                tuned_ini.append('gain = 8239\n') # +6.0 dB full gain for brilliant highs
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain (CH1 Subwoofer)
            if sline.startswith('gain'):
                tuned_ini.append('gain = 4096\n') # 0.0 dB controlled gain
                continue

        elif current_sec == '0x9b-DRC': # Bass SPK:Bass DRC
            if sline.startswith('threshold4'):
                tuned_ini.append('threshold4 = -150\n') # -1.5 dBFS controlled limiter
                continue
            elif sline.startswith('attack4'):
                tuned_ini.append('attack4 = 10\n') # 10 ms
                continue
            elif sline.startswith('release4'):
                tuned_ini.append('release4 = 150\n') # 150 ms
                continue

        elif current_sec in ['0x95-EQ', '0x97-EQ']: # Subwoofer channels (Bass SPK and Mid SPK)
            if sline.startswith('pregain'):
                tuned_ini.append('pregain = 0\n') # 0 dB controlled pregain
                continue
            elif sline.startswith('calculation_type'):
                tuned_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sub_filters):
                        flt = sub_filters[fi]
                        tuned_ini.append(f'filter{fnum}_enable = 1\n')
                        tuned_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        tuned_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        tuned_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        tuned_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        tuned_ini.append(f'filter{fnum}_enable = 0\n')
                        tuned_ini.append(f'filter{fnum}_type = 0\n')
                        tuned_ini.append(f'filter{fnum}_f0 = 0\n')
                        tuned_ini.append(f'filter{fnum}_Q = 0\n')
                        tuned_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        elif current_sec == '0x96-EQ': # Satellite channel (Treble SPK / CH2)
            if sline.startswith('pregain'):
                tuned_ini.append('pregain = 384\n') # +1.5 dB pregain for extra sparkle
                continue
            elif sline.startswith('calculation_type'):
                tuned_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sat_filters):
                        flt = sat_filters[fi]
                        tuned_ini.append(f'filter{fnum}_enable = 1\n')
                        tuned_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        tuned_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        tuned_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        tuned_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        tuned_ini.append(f'filter{fnum}_enable = 0\n')
                        tuned_ini.append(f'filter{fnum}_type = 0\n')
                        tuned_ini.append(f'filter{fnum}_f0 = 0\n')
                        tuned_ini.append(f'filter{fnum}_Q = 0\n')
                        tuned_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        tuned_ini.append(line)

    tuned_ini_text = "".join(tuned_ini)
    with open(os.path.join(base_dir, 'dsp_warm_bass_bright_treble.ini'), 'w', encoding='utf-8') as f:
        f.write(tuned_ini_text)
    with open(os.path.join(base_dir, 'dsp.ini'), 'w', encoding='utf-8') as f:
        f.write(tuned_ini_text)
    with open(os.path.join(base_dir, 'acp_workbench_config.ini'), 'w', encoding='utf-8') as f:
        f.write(tuned_ini_text)
    print("Created dsp_warm_bass_bright_treble.ini, updated dsp.ini and acp_workbench_config.ini")

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

    # Replace 0x87 (MVBass Classic) -> 55Hz, 15%
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
0x0F, 0x00,/*intensity: 15% (warm & firm)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_87, new_87)

    # Replace 0x89 (Harmonic Exciter wet = 35)
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
0x4C, 0x04,/*cutoff_frequency*/
0x64, 0x00,/*dry*/
0x23, 0x00,/*wet: 35 (sparkling treble)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_89, new_89)

    # Replace 0x94 (ButterWorth EQ) -> 48Hz
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
    c_up = c_up.replace(old_94, new_94)

    # Replace 0x95 (Bass SPK EQ)
    c_95 = make_c_eq(0x95, "Bass SPK:Bass EQ         ", 0, sub_filters)
    idx_95 = c_up.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_95)
    c_up = c_up[:idx_95_start] + c_95 + "\n\n" + c_up[idx_95_end:]

    # Replace 0x96 (Treble SPK EQ) -> Pregain = 384 (+1.5 dB)
    c_96 = make_c_eq(0x96, "Treble SPK:Treble EQ     ", 384, sat_filters)
    idx_96 = c_up.find("0x96,/*Treble SPK:Treble EQ")
    idx_96_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_96)
    idx_96_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_96)
    c_up = c_up[:idx_96_start] + c_96 + "\n\n" + c_up[idx_96_end:]

    # Replace 0x97 (Mid SPK EQ - CH1 Subwoofer)
    c_97 = make_c_eq(0x97, "Mid SPK:Mid EQ           ", 0, sub_filters)
    idx_97 = c_up.find("0x97,/*Mid SPK:Mid EQ")
    idx_97_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_97)
    idx_97_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_97)
    c_up = c_up[:idx_97_start] + c_97 + "\n\n" + c_up[idx_97_end:]

    # Treble Gain: Keep 8239
    # Mid Gain: 4096 (0 dB)

    with open(os.path.join(base_dir, 'dsp_warm_bass_bright_treble.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    with open(os.path.join(base_dir, 'dsp.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    print("Created dsp_warm_bass_bright_treble.c and updated dsp.c")

if __name__ == '__main__':
    main()
