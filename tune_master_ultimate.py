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

    # BASS: "khoẻ, đầm nảy, ấm, sạch, kiểm soát chặt"
    # - HPF 52 Hz (LR24) cuts 50Hz hum, protects 4" sub below Fb
    # - LPF 380 Hz (LR24) steep 24dB/oct cutoff, keeps bass tight
    # - 65 Hz: +2.5 dB (640) -> Sub-bass deep rumble
    # - 85 Hz: +3.0 dB (768) -> Solid, punchy kick punch
    # - 120 Hz: +1.5 dB (384) -> Warm, thick bass body
    # - 160 Hz: -2.5 dB (-640) -> Anti-boom (cancels 5L box cavity resonance)
    sub_filters = [
        {'enable': True, 'type': 4, 'f0': 52, 'Q': 724, 'gain': 0},       # HPF 52Hz (clean 50Hz hum cut)
        {'enable': True, 'type': 3, 'f0': 380, 'Q': 724, 'gain': 0},      # LPF 380Hz (1/2)
        {'enable': True, 'type': 3, 'f0': 380, 'Q': 724, 'gain': 0},      # LPF 380Hz (2/2)
        {'enable': True, 'type': 0, 'f0': 65, 'Q': 870, 'gain': 640},     # +2.5 dB deep foundation
        {'enable': True, 'type': 0, 'f0': 85, 'Q': 870, 'gain': 768},     # +3.0 dB punchy kick
        {'enable': True, 'type': 0, 'f0': 120, 'Q': 920, 'gain': 384},    # +1.5 dB warm body
        {'enable': True, 'type': 0, 'f0': 160, 'Q': 1024, 'gain': -640},  # -2.5 dB clean anti-boom
    ]

    # MID & TREBLE: "tiếng ngọt sáng, lung linh, leng keng, không chói, không xì"
    # - HPF 240 Hz (protects Mid AIRS, retains full warm vocal chest body)
    # - 500 Hz: +2.0 dB (512) -> Warm vocal presence
    # - 1000 Hz: +2.5 dB (640) -> Sweet, intimate vocal core ("tiếng ngọt")
    # - 2500 Hz: +3.0 dB (768) -> Bright, soaring vocal projection ("tiếng sáng")
    # - 4000 Hz: +2.2 dB (563) -> Articulation, breathiness, diction
    # - 8000 Hz: +3.2 dB (819) -> Crisp metallic snap
    # - 12000 Hz: +3.8 dB (973) -> Silky, shimmering sheen
    # - 16000 Hz: High Shelf +3.5 dB (896) -> Airy acoustic space
    sat_filters = [
        {'enable': True, 'type': 4, 'f0': 240, 'Q': 724, 'gain': 0},      # HPF 240Hz
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 819, 'gain': 512},    # +2.0 dB warm body
        {'enable': True, 'type': 0, 'f0': 1000, 'Q': 819, 'gain': 640},   # +2.5 dB sweet vocal
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 768},   # +3.0 dB bright vocal
        {'enable': True, 'type': 0, 'f0': 4000, 'Q': 920, 'gain': 563},   # +2.2 dB diction
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 819},   # +3.2 dB crisp
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 819, 'gain': 973},  # +3.8 dB silky air
        {'enable': True, 'type': 2, 'f0': 16000, 'Q': 724, 'gain': 896},  # +3.5 dB High Shelf
    ]

    master_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            master_ini.append(line)
            continue

        # 1. Disable open floating MIC pins to stop hardware hum/hiss
        if current_sec == '0x06-PGA1':
            if sline.startswith('line3_left_mic1_enable'):
                master_ini.append('line3_left_mic1_enable = 0\n')
                continue
            elif sline.startswith('line3_right_mic2_enable'):
                master_ini.append('line3_right_mic2_enable = 0\n')
                continue
        elif current_sec == '0x07-ADC1':
            if sline.startswith('enable'):
                master_ini.append('enable = 0\n')
                continue
            elif sline.startswith('mute'):
                master_ini.append('mute = 1\n')
                continue

        # 2. DAC Dither & Scramble DWA on DAC0 and DAC1
        elif current_sec == '0x09-DAC0':
            if sline.startswith('dither'):
                master_ini.append('dither = 1\n')
                continue
            elif sline.startswith('scramble'):
                master_ini.append('scramble = 1\n')
                continue
        elif current_sec == '0x0a-DAC1':
            if sline.startswith('dither'):
                master_ini.append('dither = 1\n')
                continue
            elif sline.startswith('scramble'):
                master_ini.append('scramble = 1\n')
                continue

        # 3. Noise Gate: Disabled (enable=0) for 100% continuous, smooth playback without stuttering
        elif current_sec == '0x85-Noise_Suppressor_Expander':
            if sline.startswith('enable'):
                master_ini.append('enable = 0\n')
                continue
            elif sline.startswith('ratio'):
                master_ini.append('ratio = 1\n')
                continue

        # 4. Silence Detector: amplitude = 0 (no cutting off)
        elif current_sec == '0x86-SilenceDetector':
            if sline.startswith('amplitude'):
                master_ini.append('amplitude = 0\n')
                continue

        # 5. MVBass Classic: 55Hz, 16% (solid, deep psychoacoustic enhancement)
        elif current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                master_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                master_ini.append('intensity = 16\n')
                continue

        # 6. Bypass secondary MVBass to keep bass clean & single-source
        elif current_sec == '0x88-MVBass':
            if sline.startswith('enable'):
                master_ini.append('enable = 0\n')
                continue

        # 7. Harmonic Exciter: wet = 18 (silky high-end sparkle, completely clean)
        elif current_sec == '0x89-Harmonic_Exciter':
            if sline.startswith('wet'):
                master_ini.append('wet = 18\n')
                continue
            elif sline.startswith('cutoff_frequency'):
                master_ini.append('cutoff_frequency = 1200\n')
                continue

        # 8. Master Tone Control [0x91-EQ]
        elif current_sec == '0x91-EQ':
            if sline.startswith('pregain'):
                master_ini.append('pregain = 0\n')
                continue
            elif sline.startswith('filter1_gain'):
                master_ini.append('filter1_gain = 512\n') # +2.0 dB at 60Hz
                continue
            elif sline.startswith('filter3_gain'):
                master_ini.append('filter3_gain = 128\n') # +0.5 dB at 1400Hz
                continue

        # 9. ButterWorth EQ (DAC1 Subwoofer)
        elif current_sec == '0x94-User-defined_Effect':
            if sline.startswith('Cut Freq'):
                master_ini.append('Cut Freq = 52\n')
                continue

        # 10. Gains: Treble Gain = 7500 (+5.2 dB), Sub Gain = 4096 (0 dB)
        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                master_ini.append('gain = 7500\n') # Ideal acoustic sensitivity balance
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain (CH1 Subwoofer)
            if sline.startswith('gain'):
                master_ini.append('gain = 4096\n') # 0.0 dB
                continue

        # 11. DRC Limiter: -1.5 dBFS for clean maximum volume
        elif current_sec == '0x9b-DRC': # Bass SPK:Bass DRC
            if sline.startswith('threshold4'):
                master_ini.append('threshold4 = -150\n')
                continue
            elif sline.startswith('attack4'):
                master_ini.append('attack4 = 10\n')
                continue
            elif sline.startswith('release4'):
                master_ini.append('release4 = 150\n')
                continue

        # 12. Subwoofer EQ (0x95 Bass SPK & 0x97 Mid SPK - CH1)
        elif current_sec in ['0x95-EQ', '0x97-EQ']:
            if sline.startswith('pregain'):
                master_ini.append('pregain = 0\n')
                continue
            elif sline.startswith('calculation_type'):
                master_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sub_filters):
                        flt = sub_filters[fi]
                        master_ini.append(f'filter{fnum}_enable = 1\n')
                        master_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        master_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        master_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        master_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        master_ini.append(f'filter{fnum}_enable = 0\n')
                        master_ini.append(f'filter{fnum}_type = 0\n')
                        master_ini.append(f'filter{fnum}_f0 = 0\n')
                        master_ini.append(f'filter{fnum}_Q = 0\n')
                        master_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        # 13. Satellite EQ (0x96 Treble SPK - CH2)
        elif current_sec == '0x96-EQ':
            if sline.startswith('pregain'):
                master_ini.append('pregain = 128\n') # +0.5 dB
                continue
            elif sline.startswith('calculation_type'):
                master_ini.append('calculation_type = 0\n')
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(sat_filters):
                        flt = sat_filters[fi]
                        master_ini.append(f'filter{fnum}_enable = 1\n')
                        master_ini.append(f'filter{fnum}_type = {flt["type"]}\n')
                        master_ini.append(f'filter{fnum}_f0 = {flt["f0"]}\n')
                        master_ini.append(f'filter{fnum}_Q = {flt["Q"]}\n')
                        master_ini.append(f'filter{fnum}_gain = {flt["gain"]}\n')
                    else:
                        master_ini.append(f'filter{fnum}_enable = 0\n')
                        master_ini.append(f'filter{fnum}_type = 0\n')
                        master_ini.append(f'filter{fnum}_f0 = 0\n')
                        master_ini.append(f'filter{fnum}_Q = 0\n')
                        master_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue

        master_ini.append(line)

    master_ini_text = "".join(master_ini)
    with open(os.path.join(base_dir, 'dsp_master_ultimate.ini'), 'w', encoding='utf-8') as f:
        f.write(master_ini_text)
    with open(os.path.join(base_dir, 'dsp.ini'), 'w', encoding='utf-8') as f:
        f.write(master_ini_text)
    with open(os.path.join(base_dir, 'acp_workbench_config.ini'), 'w', encoding='utf-8') as f:
        f.write(master_ini_text)
    print("Created dsp_master_ultimate.ini, updated dsp.ini and acp_workbench_config.ini")

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

    # 1. 0x06 (PGA1) -> disable mic
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
    c_up = c_up.replace(old_pga1, new_pga1)

    # 2. 0x07 (ADC1) -> disable mic
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
    c_up = c_up.replace(old_adc1, new_adc1)

    # 3. 0x09 (DAC0) -> dither 1, scramble 1
    old_dac0 = """0xBF, 0x11,/*right_volume*/
0x00, 0x00,/*dither*/
0x00, 0x00,/*scramble*/"""
    new_dac0 = """0xBF, 0x11,/*right_volume*/
0x01, 0x00,/*dither: 1*/
0x01, 0x00,/*scramble: 1*/"""
    c_up = c_up.replace(old_dac0, new_dac0)

    # 4. 0x85 (Noise Gate -> disabled enable = 0)
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
0x00, 0x00,/*enable: 0 (disabled for 100% smooth playback)*/
0x9C, 0xE6,/*threshold*/
0x01, 0x00,/*ratio*/
0x05, 0x00,/*attack*/
0xA0, 0x00,/*release*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_85, new_85)

    # 5. 0x87 (MVBass Classic -> 55Hz, 16%)
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
0x10, 0x00,/*intensity: 16% (deep, firm bass)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_87, new_87)

    # 6. 0x88 (MVBass secondary -> disable)
    old_88 = """0xA5, 0x5A,/*sync head*/
0x88,/*Music:Virtual Bass       */
0x09,/*length*/
0xFF,/*all parameter*/
0x01, 0x00,/*enable*/"""
    new_88 = """0xA5, 0x5A,/*sync head*/
0x88,/*Music:Virtual Bass       */
0x09,/*length*/
0xFF,/*all parameter*/
0x00, 0x00,/*enable: 0 (bypassed)*/"""
    c_up = c_up.replace(old_88, new_88)

    # 7. 0x89 (Exciter -> wet = 18)
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
0x12, 0x00,/*wet: 18 (silky high-end sheen)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_89, new_89)

    # 8. 0x94 (ButterWorth EQ -> 52Hz)
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
0x34, 0x00,/*Cut Freq: 52Hz*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_94, new_94)

    # 9. 0x95 (Bass SPK EQ -> sub_filters)
    c_95 = make_c_eq(0x95, "Bass SPK:Bass EQ         ", 0, sub_filters)
    idx_95 = c_up.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_95)
    c_up = c_up[:idx_95_start] + c_95 + "\n\n" + c_up[idx_95_end:]

    # 10. 0x96 (Treble SPK EQ -> sat_filters, pregain = 128)
    c_96 = make_c_eq(0x96, "Treble SPK:Treble EQ     ", 128, sat_filters)
    idx_96 = c_up.find("0x96,/*Treble SPK:Treble EQ")
    idx_96_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_96)
    idx_96_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_96)
    c_up = c_up[:idx_96_start] + c_96 + "\n\n" + c_up[idx_96_end:]

    # 11. 0x97 (Mid SPK EQ - CH1 Subwoofer -> sub_filters)
    c_97 = make_c_eq(0x97, "Mid SPK:Mid EQ           ", 0, sub_filters)
    idx_97 = c_up.find("0x97,/*Mid SPK:Mid EQ")
    idx_97_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_97)
    idx_97_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_97)
    c_up = c_up[:idx_97_start] + c_97 + "\n\n" + c_up[idx_97_end:]

    # 12. 0x98 (Treble Gain -> 7500 = 0x1D4C)
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
0x4C, 0x1D,/*gain: 7500 (+5.2 dB perfectly balanced)*/
0x16,/*sync tail*/"""
    c_up = c_up.replace(old_98, new_98)

    with open(os.path.join(base_dir, 'dsp_master_ultimate.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    with open(os.path.join(base_dir, 'dsp.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    print("Created dsp_master_ultimate.c and updated dsp.c")

if __name__ == '__main__':
    main()
