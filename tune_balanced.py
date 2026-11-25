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

    # Balanced Subwoofer filters (Clean, tight bass, not boomy, no rumble)
    # LPF at 380 Hz (LR24), HPF at 50 Hz (LR24)
    # Moderate boost: +1.0dB at 75Hz, +0.5dB at 100Hz, -2.0dB at 160Hz (box boom reduction)
    sub_filters = [
        {'enable': True, 'type': 4, 'f0': 50, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 380, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 380, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 0, 'f0': 75, 'Q': 819, 'gain': 256},    # +1.0 dB
        {'enable': True, 'type': 0, 'f0': 100, 'Q': 1024, 'gain': 128},  # +0.5 dB
        {'enable': True, 'type': 0, 'f0': 160, 'Q': 1024, 'gain': -512}, # -2.0 dB anti-boom
        {'enable': True, 'type': 0, 'f0': 250, 'Q': 1024, 'gain': -256}, # -1.0 dB
    ]

    # Vivid Mid & Treble filters (Warm vocal, clear presence, sparkling treble)
    # HPF at 250 Hz (so Mid AIRS reproduces warm, full-bodied vocals)
    # Boosted presence and highs to match the hardware's acoustic sensitivity
    sat_filters = [
        {'enable': True, 'type': 4, 'f0': 250, 'Q': 724, 'gain': 0},      # HPF 250Hz protect mid
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 819, 'gain': 512},    # +2.0 dB warm vocal body
        {'enable': True, 'type': 0, 'f0': 1200, 'Q': 819, 'gain': 512},   # +2.0 dB male vocal clarity
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 640},   # +2.5 dB female vocal / melody
        {'enable': True, 'type': 0, 'f0': 5000, 'Q': 1024, 'gain': 256},  # +1.0 dB vocal presence
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 512},   # +2.0 dB crisp percussions
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 819, 'gain': 640},  # +2.5 dB airy treble
        {'enable': True, 'type': 2, 'f0': 16000, 'Q': 819, 'gain': 512},  # +2.0 dB High Shelf space
    ]

    balanced_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            balanced_ini.append(line)
            continue

        if current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                balanced_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                balanced_ini.append('intensity = 10\n') # reduced from 20 to 10 for gentle bass
                continue

        elif current_sec == '0x94-User-defined_Effect': # ButterWorth EQ (DAC1 Sub)
            if sline.startswith('Cut Freq'):
                balanced_ini.append('Cut Freq = 50\n')
                continue

        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                balanced_ini.append('gain = 8239\n') # Restore +6dB full gain for Mid/Treble
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain (CH1 Subwoofer)
            if sline.startswith('gain'):
                balanced_ini.append('gain = 3600\n') # Slightly reduced sub gain (-1.1 dB) so bass is gentle
                continue

        elif current_sec in ['0x95-EQ', '0x97-EQ']: # Subwoofer channels (Bass SPK and Mid SPK)
            if sline.startswith('pregain'):
                balanced_ini.append('pregain = 0\n') # 0 dB pregain (reduced bass)
                continue
            elif sline.startswith('calculation_type'):
                balanced_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sub_filters):
                        flt = sub_filters[fi]
                        balanced_ini.append(f'filter{fnum}_enable = 1\n')
                        balanced_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        balanced_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        balanced_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        balanced_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        balanced_ini.append(f'filter{fnum}_enable = 0\n')
                        balanced_ini.append(f'filter{fnum}_type = 0\n')
                        balanced_ini.append(f'filter{fnum}_f0 = 0\n')
                        balanced_ini.append(f'filter{fnum}_Q = 0\n')
                        balanced_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        elif current_sec == '0x96-EQ': # Satellite channel (Treble SPK / CH2)
            if sline.startswith('pregain'):
                balanced_ini.append('pregain = 256\n') # +1.0 dB pregain for crisp vocal
                continue
            elif sline.startswith('calculation_type'):
                balanced_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sat_filters):
                        flt = sat_filters[fi]
                        balanced_ini.append(f'filter{fnum}_enable = 1\n')
                        balanced_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        balanced_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        balanced_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        balanced_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        balanced_ini.append(f'filter{fnum}_enable = 0\n')
                        balanced_ini.append(f'filter{fnum}_type = 0\n')
                        balanced_ini.append(f'filter{fnum}_f0 = 0\n')
                        balanced_ini.append(f'filter{fnum}_Q = 0\n')
                        balanced_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        balanced_ini.append(line)

    balanced_ini_text = "".join(balanced_ini)
    with open(os.path.join(base_dir, 'dsp_balanced_bose.ini'), 'w', encoding='utf-8') as f:
        f.write(balanced_ini_text)
    with open(os.path.join(base_dir, 'dsp.ini'), 'w', encoding='utf-8') as f:
        f.write(balanced_ini_text)
    with open(os.path.join(base_dir, 'acp_workbench_config.ini'), 'w', encoding='utf-8') as f:
        f.write(balanced_ini_text)
    print("Created dsp_balanced_bose.ini, updated dsp.ini and acp_workbench_config.ini")

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

    # Replace 0x87 (MVBass Classic) -> 55Hz, 10%
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
0x0A, 0x00,/*intensity: 10% (moderate bass)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_87, new_87)

    # Replace 0x94 (ButterWorth EQ) -> 50Hz
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
0x32, 0x00,/*Cut Freq: 50Hz*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_94, new_94)

    # Replace 0x95 (Bass SPK EQ)
    c_95 = make_c_eq(0x95, "Bass SPK:Bass EQ         ", 0, sub_filters)
    idx_95 = c_up.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_95)
    c_up = c_up[:idx_95_start] + c_95 + "\n\n" + c_up[idx_95_end:]

    # Replace 0x96 (Treble SPK EQ)
    c_96 = make_c_eq(0x96, "Treble SPK:Treble EQ     ", 256, sat_filters)
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

    # Keep 0x98 (Treble Gain) at 8239 (original full gain)
    # Set 0x99 (Mid Gain - Subwoofer) to 3600 (-1.1dB) so sub is softer and balanced
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
0x10, 0x0E,/*gain: 3600 (-1.1 dB)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_99, new_99)

    with open(os.path.join(base_dir, 'dsp_balanced_bose.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    with open(os.path.join(base_dir, 'dsp.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    print("Created dsp_balanced_bose.c and updated dsp.c")

if __name__ == '__main__':
    main()
