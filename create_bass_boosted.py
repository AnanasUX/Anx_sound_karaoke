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
        ini_text = f.read()

    with open(orig_c_path, 'r', encoding='utf-8') as f:
        c_text = f.read()

    # 1. Create dsp_restore_original.ini and dsp_restore_original.c
    with open(os.path.join(base_dir, 'dsp_restore_original.ini'), 'w', encoding='utf-8') as f:
        f.write(ini_text)
    with open(os.path.join(base_dir, 'dsp_restore_original.c'), 'w', encoding='utf-8') as f:
        f.write(c_text)
    print("Created dsp_restore_original.ini and dsp_restore_original.c")

    # 2. Build dsp_bass_boosted.ini
    # In this configuration:
    # - Mid SPK (DAC0 Left / CH1 Subwoofer Boombox 4"):
    #   Filter 1: High Pass, 45 Hz, Q=724, gain=0 (protect below 45Hz)
    #   Filter 2: Low Pass, 500 Hz, Q=724, gain=0 (cut high mids from sub)
    #   Filter 3: Low Pass, 500 Hz, Q=724, gain=0 (2nd order -> 24dB/oct at 500Hz)
    #   Filter 4: Peaking, 65 Hz, gain=+3.0 dB (768), Q=0.8 (819) -> Deep sub bass
    #   Filter 5: Peaking, 85 Hz, gain=+2.5 dB (640), Q=0.8 (819) -> Punchy bass
    #   Filter 6: Peaking, 100 Hz, gain=+2.0 dB (512), Q=1.0 (1024) -> Solid kick
    #   Filter 7: Peaking, 160 Hz, gain=-1.5 dB (-384), Q=1.0 (1024) -> Cut box boom
    #   pregain = 256 (+1dB)
    #   Mid Gain = 4096 (0dB, full sub output)
    #
    # - Bass SPK (DAC1 Subwoofer):
    #   Same powerful sub tuning so both outputs have massive bass!
    #   0x94 Butterworth: bypass / Cut Freq = 500 (LPF) or Cut Freq = 45 (HPF)
    #   Bass EQ (0x95): same 7 filters
    #   pregain = 256
    #
    # - Treble SPK (DAC0 Right / CH2 Mid AIRS + Treble Dome):
    #   Filter 1: High Pass, 350 Hz, Q=724, gain=0 (protect Mid AIRS + Treble)
    #   Filter 2: Peaking, 500 Hz, gain=-1.0 dB (-256), Q=1.0 (1024) (cut mud)
    #   Filter 3: Peaking, 1200 Hz, gain=+1.0 dB (256), Q=0.8 (819) (warm vocal)
    #   Filter 4: Peaking, 2500 Hz, gain=+1.0 dB (256), Q=0.8 (819) (female vocal)
    #   Filter 5: Peaking, 5000 Hz, gain=-1.0 dB (-256), Q=1.0 (1024) (anti-harsh)
    #   Filter 6: Peaking, 8000 Hz, gain=+1.0 dB (256), Q=0.8 (819) (crisp)
    #   Filter 7: Peaking, 12000 Hz, gain=+1.5 dB (384), Q=0.8 (819) (air)
    #   Filter 8: Hight Shelf, 16000 Hz, gain=+1.0 dB (256), Q=0.8 (819)
    #   Treble Gain = 4096 (0dB balanced)
    #
    # - Master effects:
    #   0x87 MVBass_Classic: cutoff = 55, intensity = 20
    #   0x91 Bass-Mid-Treb: keep 60Hz +3dB boost (filter1_gain = 768)

    sub_filters = [
        {'enable': True, 'type': 4, 'f0': 45, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 500, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 500, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 0, 'f0': 65, 'Q': 819, 'gain': 768},
        {'enable': True, 'type': 0, 'f0': 85, 'Q': 819, 'gain': 640},
        {'enable': True, 'type': 0, 'f0': 100, 'Q': 1024, 'gain': 512},
        {'enable': True, 'type': 0, 'f0': 160, 'Q': 1024, 'gain': -384},
    ]

    sat_filters = [
        {'enable': True, 'type': 4, 'f0': 350, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 1024, 'gain': -256},
        {'enable': True, 'type': 0, 'f0': 1200, 'Q': 819, 'gain': 256},
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 256},
        {'enable': True, 'type': 0, 'f0': 5000, 'Q': 1024, 'gain': -256},
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 256},
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 819, 'gain': 384},
        {'enable': True, 'type': 2, 'f0': 16000, 'Q': 819, 'gain': 256},
    ]

    with open(orig_ini_path, 'r', encoding='utf-8') as f:
        ini_lines = f.readlines()

    boosted_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            boosted_ini.append(line)
            continue

        if current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                boosted_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                boosted_ini.append('intensity = 20\n')
                continue

        elif current_sec == '0x94-User-defined_Effect': # ButterWorth EQ
            if sline.startswith('Cut Freq'):
                boosted_ini.append('Cut Freq = 45\n') # High-pass protection at 45Hz
                continue

        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                boosted_ini.append('gain = 4096\n') # 0 dB
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain (CH1 Subwoofer)
            if sline.startswith('gain'):
                boosted_ini.append('gain = 4096\n') # 0 dB full sub power
                continue

        elif current_sec in ['0x95-EQ', '0x97-EQ']: # Subwoofer channels (Bass SPK and Mid SPK)
            if sline.startswith('pregain'):
                boosted_ini.append('pregain = 256\n') # +1.0 dB
                continue
            elif sline.startswith('calculation_type'):
                boosted_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sub_filters):
                        flt = sub_filters[fi]
                        boosted_ini.append(f'filter{fnum}_enable = 1\n')
                        boosted_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        boosted_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        boosted_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        boosted_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        boosted_ini.append(f'filter{fnum}_enable = 0\n')
                        boosted_ini.append(f'filter{fnum}_type = 0\n')
                        boosted_ini.append(f'filter{fnum}_f0 = 0\n')
                        boosted_ini.append(f'filter{fnum}_Q = 0\n')
                        boosted_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        elif current_sec == '0x96-EQ': # Satellite channel (Treble SPK / CH2)
            if sline.startswith('pregain'):
                boosted_ini.append('pregain = 0\n')
                continue
            elif sline.startswith('calculation_type'):
                boosted_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sat_filters):
                        flt = sat_filters[fi]
                        boosted_ini.append(f'filter{fnum}_enable = 1\n')
                        boosted_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        boosted_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        boosted_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        boosted_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        boosted_ini.append(f'filter{fnum}_enable = 0\n')
                        boosted_ini.append(f'filter{fnum}_type = 0\n')
                        boosted_ini.append(f'filter{fnum}_f0 = 0\n')
                        boosted_ini.append(f'filter{fnum}_Q = 0\n')
                        boosted_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        boosted_ini.append(line)

    boosted_ini_text = "".join(boosted_ini)
    with open(os.path.join(base_dir, 'dsp_bass_boosted.ini'), 'w', encoding='utf-8') as f:
        f.write(boosted_ini_text)
    # Also update dsp.ini with this bass boosted version
    with open(os.path.join(base_dir, 'dsp.ini'), 'w', encoding='utf-8') as f:
        f.write(boosted_ini_text)
    print("Created dsp_bass_boosted.ini and updated dsp.ini")

    # 3. Build C code for dsp_bass_boosted.c
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

    # Replace 0x87 (MVBass Classic)
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
0x14, 0x00,/*intensity: 20%*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_87, new_87)

    # Replace 0x94
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
0x2D, 0x00,/*Cut Freq: 45Hz*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_94, new_94)

    # Replace 0x95 (Bass SPK EQ)
    c_95 = make_c_eq(0x95, "Bass SPK:Bass EQ         ", 256, sub_filters)
    idx_95 = c_up.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_95)
    c_up = c_up[:idx_95_start] + c_95 + "\n\n" + c_up[idx_95_end:]

    # Replace 0x96 (Treble SPK EQ)
    c_96 = make_c_eq(0x96, "Treble SPK:Treble EQ     ", 0, sat_filters)
    idx_96 = c_up.find("0x96,/*Treble SPK:Treble EQ")
    idx_96_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_96)
    idx_96_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_96)
    c_up = c_up[:idx_96_start] + c_96 + "\n\n" + c_up[idx_96_end:]

    # Replace 0x97 (Mid SPK EQ - CH1 Subwoofer)
    c_97 = make_c_eq(0x97, "Mid SPK:Mid EQ           ", 256, sub_filters)
    idx_97 = c_up.find("0x97,/*Mid SPK:Mid EQ")
    idx_97_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_97)
    idx_97_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_97)
    c_up = c_up[:idx_97_start] + c_97 + "\n\n" + c_up[idx_97_end:]

    # Replace 0x98 (Treble Gain: set to 4096 / 0dB)
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
0x00, 0x10,/*gain: 4096 (0 dB)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_98, new_98)

    with open(os.path.join(base_dir, 'dsp_bass_boosted.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    with open(os.path.join(base_dir, 'dsp.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    print("Created dsp_bass_boosted.c and updated dsp.c")

if __name__ == '__main__':
    main()
