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

    # BASS: Clean, punchy, warm, NO 50Hz HUM ("Hết ù")
    # HPF 55 Hz (LR24) cuts 50Hz mains hum and DC ground loop
    sub_filters = [
        {'enable': True, 'type': 4, 'f0': 55, 'Q': 724, 'gain': 0},       # HPF 55Hz cuts 50Hz AC hum
        {'enable': True, 'type': 3, 'f0': 380, 'Q': 724, 'gain': 0},      # LPF 380Hz
        {'enable': True, 'type': 3, 'f0': 380, 'Q': 724, 'gain': 0},      # LPF 380Hz
        {'enable': True, 'type': 0, 'f0': 70, 'Q': 870, 'gain': 563},     # +2.2 dB punch
        {'enable': True, 'type': 0, 'f0': 85, 'Q': 870, 'gain': 640},     # +2.5 dB solid kick
        {'enable': True, 'type': 0, 'f0': 120, 'Q': 920, 'gain': 256},    # +1.0 dB warm
        {'enable': True, 'type': 0, 'f0': 160, 'Q': 1024, 'gain': -640},  # -2.5 dB anti-boom 5L
    ]

    # MID & TREBLE: Sweet, bright vocal, NO HISS ("Hết xì")
    # Tamed ultra-highs above 14kHz to not amplify noise floor, boosted speech clarity
    sat_filters = [
        {'enable': True, 'type': 4, 'f0': 250, 'Q': 724, 'gain': 0},      # HPF 250Hz protect mid
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 819, 'gain': 512},    # +2.0 dB warm body
        {'enable': True, 'type': 0, 'f0': 1000, 'Q': 819, 'gain': 563},   # +2.2 dB sweet vocal
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 768},   # +3.0 dB bright vocal
        {'enable': True, 'type': 0, 'f0': 4000, 'Q': 920, 'gain': 640},   # +2.5 dB vocal presence
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 640},   # +2.5 dB crisp cymbal
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 819, 'gain': 512},  # +2.0 dB airy
        {'enable': True, 'type': 2, 'f0': 16000, 'Q': 724, 'gain': 384},  # +1.5 dB High Shelf gentle air
    ]

    clean_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            clean_ini.append(line)
            continue

        # 1. Disable floating MIC inputs to eliminate open-pin noise & hum
        if current_sec == '0x06-PGA1':
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

        # 2. DAC Dither & Scramble to remove DAC quantization hiss
        elif current_sec == '0x09-DAC0':
            if sline.startswith('dither'):
                clean_ini.append('dither = 1\n')
                continue
            elif sline.startswith('scramble'):
                clean_ini.append('scramble = 1\n')
                continue

        # 3. Noise Suppressor Expander: Active noise gate to kill background hiss & hum during silence
        elif current_sec == '0x85-Noise_Suppressor_Expander':
            if sline.startswith('threshold'):
                clean_ini.append('threshold = -5800\n') # -58 dBFS threshold
                continue
            elif sline.startswith('ratio'):
                clean_ini.append('ratio = 20\n') # 20:1 expansion ratio (silences hiss)
                continue
            elif sline.startswith('attack'):
                clean_ini.append('attack = 5\n')
                continue
            elif sline.startswith('release'):
                clean_ini.append('release = 120\n')
                continue

        # 4. Harmonic Exciter: Lower wet to 15 so it doesn't amplify hiss
        elif current_sec == '0x89-Harmonic_Exciter':
            if sline.startswith('wet'):
                clean_ini.append('wet = 15\n')
                continue

        # 5. MVBass Classic: 55Hz, 12%
        elif current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                clean_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                clean_ini.append('intensity = 12\n')
                continue

        elif current_sec == '0x94-User-defined_Effect': # ButterWorth EQ (DAC1 Sub)
            if sline.startswith('Cut Freq'):
                clean_ini.append('Cut Freq = 55\n')
                continue

        # 6. Gain Controls: Controlled Treble gain (6800) so it doesn't boost thermal noise
        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                clean_ini.append('gain = 6800\n') # ~ +4.4 dB (clean, no hiss)
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain (CH1 Subwoofer)
            if sline.startswith('gain'):
                clean_ini.append('gain = 4096\n') # 0.0 dB
                continue

        elif current_sec == '0x9b-DRC': # Bass SPK:Bass DRC
            if sline.startswith('threshold4'):
                clean_ini.append('threshold4 = -150\n')
                continue
            elif sline.startswith('attack4'):
                clean_ini.append('attack4 = 10\n')
                continue
            elif sline.startswith('release4'):
                clean_ini.append('release4 = 150\n')
                continue

        # 7. Subwoofer EQ
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

        # 8. Satellite EQ: Pregain 0dB, sweet vocal, bright treble without hiss
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
    with open(os.path.join(base_dir, 'dsp_clean_no_noise.ini'), 'w', encoding='utf-8') as f:
        f.write(clean_ini_text)
    with open(os.path.join(base_dir, 'dsp.ini'), 'w', encoding='utf-8') as f:
        f.write(clean_ini_text)
    with open(os.path.join(base_dir, 'acp_workbench_config.ini'), 'w', encoding='utf-8') as f:
        f.write(clean_ini_text)
    print("Created dsp_clean_no_noise.ini, updated dsp.ini and acp_workbench_config.ini")

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

    # Replace 0x06 (PGA1) line3_left_mic1_enable = 0, line3_right_mic2_enable = 0
    old_pga1 = """0x06,/*PGA1*/
0x13,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*line3_left_mic1_enable*/
0x01, 0x00,/*line3_right_mic2_enable*/"""
    new_pga1 = """0x06,/*PGA1*/
0x13,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*line3_left_mic1_enable: 0 (disable floating mic noise)*/
0x00, 0x00,/*line3_right_mic2_enable: 0 (disable floating mic noise)*/"""
    c_up = c_up.replace(old_pga1, new_pga1)

    # Replace 0x07 (ADC1) enable = 0, mute = 1
    old_adc1 = """0x07,/*ADC1*/
0x15,/*length*/
0xFF,/*all parameter*/
0x03, 0x00,/*enable*/
0x00, 0x00,/*mute*/"""
    new_adc1 = """0x07,/*ADC1*/
0x15,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*enable: 0 (disable mic ADC)*/
0x01, 0x00,/*mute: 1 (mute mic ADC)*/"""
    c_up = c_up.replace(old_adc1, new_adc1)

    # Replace 0x09 (DAC0) dither = 1, scramble = 1
    old_dac0 = """0xBF, 0x11,/*right_volume*/
0x00, 0x00,/*dither*/
0x00, 0x00,/*scramble*/"""
    new_dac0 = """0xBF, 0x11,/*right_volume*/
0x01, 0x00,/*dither: 1 (suppress quantization hiss)*/
0x01, 0x00,/*scramble: 1 (DWA mode)*/"""
    c_up = c_up.replace(old_dac0, new_dac0)

    # Replace 0x85 (Noise Suppressor Expander: threshold = -5800, ratio = 20)
    # -5800 = 0xE958 in 16-bit signed -> 0x58, 0xE9
    old_85 = """0xA5, 0x5A,/*sync head*/
0x85,/*Music:Noise Gate Suppress*/
0x0B,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x9C, 0xE6,/*threshold*/
0x01, 0x00,/*ratio*/
0x05, 0x00,/*attack*/
0xA0, 0x00,/*release*/
0x16,/*sync tail*/"""
    new_85 = """0xA5, 0x5A,/*sync head*/
0x85,/*Music:Noise Gate Suppress*/
0x0B,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/
0x58, 0xE9,/*threshold: -5800 (-58 dBFS)*/
0x14, 0x00,/*ratio: 20 (20:1 expander silences hiss & hum)*/
0x05, 0x00,/*attack: 5ms*/
0x78, 0x00,/*release: 120ms*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_85, new_85)

    # Replace 0x87 (MVBass Classic) -> 55Hz, 12%
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
0x0C, 0x00,/*intensity: 12% (natural warm bass)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_87, new_87)

    # Replace 0x89 (Harmonic Exciter wet = 15)
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
0x0F, 0x00,/*wet: 15 (clean, no hiss floor)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_89, new_89)

    # Replace 0x94 (ButterWorth EQ) -> 55Hz
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
0x37, 0x00,/*Cut Freq: 55Hz*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_94, new_94)

    # Replace 0x95 (Bass SPK EQ) -> Pregain = 0
    c_95 = make_c_eq(0x95, "Bass SPK:Bass EQ         ", 0, sub_filters)
    idx_95 = c_up.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_95)
    c_up = c_up[:idx_95_start] + c_95 + "\n\n" + c_up[idx_95_end:]

    # Replace 0x96 (Treble SPK EQ) -> Pregain = 0
    c_96 = make_c_eq(0x96, "Treble SPK:Treble EQ     ", 0, sat_filters)
    idx_96 = c_up.find("0x96,/*Treble SPK:Treble EQ")
    idx_96_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_96)
    idx_96_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_96)
    c_up = c_up[:idx_96_start] + c_96 + "\n\n" + c_up[idx_96_end:]

    # Replace 0x97 (Mid SPK EQ - CH1 Subwoofer) -> Pregain = 0
    c_97 = make_c_eq(0x97, "Mid SPK:Mid EQ           ", 0, sub_filters)
    idx_97 = c_up.find("0x97,/*Mid SPK:Mid EQ")
    idx_97_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_97)
    idx_97_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_97)
    c_up = c_up[:idx_97_start] + c_97 + "\n\n" + c_up[idx_97_end:]

    # Replace 0x98 (Treble Gain -> 6800 = 0x1A90)
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
0x90, 0x1A,/*gain: 6800 (+4.4 dB clean, no hiss)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_98, new_98)

    with open(os.path.join(base_dir, 'dsp_clean_no_noise.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    with open(os.path.join(base_dir, 'dsp.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    print("Created dsp_clean_no_noise.c and updated dsp.c")

if __name__ == '__main__':
    main()
