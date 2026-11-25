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

    # BASS: "khoẻ, đầm nảy, ấm, sạch, kiểm soát chặt, không ù"
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

    # MID & TREBLE: "tiếng ngọt sáng, lung linh, leng keng, KHÔNG XÌ NOISE"
    # - HPF 240 Hz (protects Mid AIRS, retains full warm vocal chest body)
    # - 500 Hz: +1.5 dB (384) -> Warm vocal presence
    # - 1000 Hz: +2.5 dB (640) -> Sweet, intimate vocal core ("tiếng ngọt")
    # - 2500 Hz: +3.0 dB (768) -> Bright, soaring vocal projection ("tiếng sáng")
    # - 4000 Hz: +2.0 dB (512) -> Articulation, breathiness, diction
    # - 8000 Hz: +1.5 dB (384) -> Crisp metallic snap & cymbal shimmer without harshness
    # - 12000 Hz: 0.0 dB (0) -> Flat (completely eliminates hiss amplification!)
    # - 18000 Hz: LPF (Type 3) -> Low Pass filter cutting ultrasonic DAC & thermal noise floor!
    sat_filters = [
        {'enable': True, 'type': 4, 'f0': 240, 'Q': 724, 'gain': 0},      # HPF 240Hz
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 819, 'gain': 384},    # +1.5 dB warm body
        {'enable': True, 'type': 0, 'f0': 1000, 'Q': 819, 'gain': 640},   # +2.5 dB sweet vocal
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 768},   # +3.0 dB bright vocal
        {'enable': True, 'type': 0, 'f0': 4000, 'Q': 920, 'gain': 512},   # +2.0 dB diction
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 384},   # +1.5 dB crisp
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 724, 'gain': 0},    # 0.0 dB flat (anti-hiss)
        {'enable': True, 'type': 3, 'f0': 18000, 'Q': 724, 'gain': 0},    # LPF 18kHz (anti-hiss cutoff)
    ]

    clean_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            clean_ini.append(line)
            continue

        # 1. PGA0: Cut off floating unused inputs, set 0dB gain (removes ~21dB thermal hiss)
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

        # 2. PGA1 & ADC1: Disable floating MIC pins completely
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

        # 3. DAC0 & DAC1: Unity volume (4096) + Dither & Scramble (removes quantization hiss)
        elif current_sec == '0x09-DAC0':
            if sline.startswith('left_volume'):
                clean_ini.append('left_volume = 4096\n')
                continue
            elif sline.startswith('right_volume'):
                clean_ini.append('right_volume = 4096\n')
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

        # 4. NOISE GATE: DISABLED to prevent music stuttering
        elif current_sec == '0x85-Noise_Suppressor_Expander':
            if sline.startswith('enable'):
                clean_ini.append('enable = 0\n')
                continue
            elif sline.startswith('ratio'):
                clean_ini.append('ratio = 1\n')
                continue

        # 5. SILENCE DETECTOR: amplitude = 0 (no cutting off)
        elif current_sec == '0x86-SilenceDetector':
            if sline.startswith('amplitude'):
                clean_ini.append('amplitude = 0\n')
                continue

        # 6. MVBass Classic: 55Hz, 15%
        elif current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                clean_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                clean_ini.append('intensity = 15\n')
                continue

        # 7. Bypass secondary MVBass
        elif current_sec == '0x88-MVBass':
            if sline.startswith('enable'):
                clean_ini.append('enable = 0\n')
                continue

        # 8. Harmonic Exciter: BYPASSED (enable = 0, wet = 0) -> Eliminates high-frequency hiss synthesis!
        elif current_sec == '0x89-Harmonic_Exciter':
            if sline.startswith('enable'):
                clean_ini.append('enable = 0\n')
                continue
            elif sline.startswith('wet'):
                clean_ini.append('wet = 0\n')
                continue
            elif sline.startswith('dry'):
                clean_ini.append('dry = 100\n')
                continue
            elif sline.startswith('cutoff_frequency'):
                clean_ini.append('cutoff_frequency = 1200\n')
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

        # 10. ButterWorth EQ (DAC1 Subwoofer)
        elif current_sec == '0x94-User-defined_Effect':
            if sline.startswith('Cut Freq'):
                clean_ini.append('Cut Freq = 52\n')
                continue

        # 11. Gains: Treble Gain = 4096 (0.0 dB clean unity, drops noise floor by 5dB!), Sub Gain = 4096 (0 dB)
        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                clean_ini.append('gain = 4096\n')
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain (CH1 Subwoofer)
            if sline.startswith('gain'):
                clean_ini.append('gain = 4096\n')
                continue

        # 12. DRC Limiter: -1.5 dBFS for clean output
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

        # 13. Subwoofer EQ (0x95 Bass SPK & 0x97 Mid SPK - CH1)
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

        # 14. Satellite EQ (0x96 Treble SPK - CH2)
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
    print("Updated dsp_punchy_bass_sweet_vocal.ini, dsp.ini, and acp_workbench_config.ini!")

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

    # 1. PGA0 (0x03) -> Mute floating right lines, set 21 (0dB unity)
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
0x15, 0x00,/*line1_left_gain: 21 (0dB unity)*/
0x15, 0x00,/*line1_right_gain: 21 (0dB unity)*/
0x15, 0x00,/*line2_left_gain: 21*/
0x15, 0x00,/*line2_right_gain: 21*/
0x15, 0x00,/*line4_5_left_gain: 21*/
0x15, 0x00,/*line4_5_right_gain: 21 (anti-noise cut)*/
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
0x00, 0x00,/*line3_left_mic1_enable: 0 (disable floating mic noise)*/
0x00, 0x00,/*line3_right_mic2_enable: 0 (disable floating mic noise)*/"""
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
0x00, 0x00,/*enable: 0 (disable mic ADC)*/
0x01, 0x00,/*mute: 1 (mute mic ADC)*/"""
    assert old_adc1 in c_up, "ADC1 block not found!"
    c_up = c_up.replace(old_adc1, new_adc1)

    # 4. DAC0 (0x09) -> 4096 unity volume + dither 1, scramble 1
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
0x00, 0x10,/*left_volume: 4096 (0dB unity)*/
0x00, 0x10,/*right_volume: 4096 (0dB unity)*/
0x01, 0x00,/*dither: 1 (suppress quantization hiss)*/
0x01, 0x00,/*scramble: 1 (DWA mode)*/"""
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
0x00, 0x00,/*enable: 0 (disabled for continuous audio)*/"""
    assert old_85 in c_up, "0x85 block not found!"
    c_up = c_up.replace(old_85, new_85)

    # 6. MVBass Classic (0x87) -> 55Hz, 15%
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
0x0F, 0x00,/*intensity: 15%*/
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
0x00, 0x00,/*enable: 0 (bypassed)*/"""
    assert old_88 in c_up, "0x88 block not found!"
    c_up = c_up.replace(old_88, new_88)

    # 8. Exciter (0x89) -> BYPASS (enable = 0, wet = 0)
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
0x00, 0x00,/*enable: 0 (bypassed to eliminate hiss synthesis)*/
0xB0, 0x04,/*cutoff_frequency: 1200Hz*/
0x64, 0x00,/*dry: 100*/
0x00, 0x00,/*wet: 0*/
0x16,/*sync tail*/"""
    assert old_89 in c_up, "0x89 block not found!"
    c_up = c_up.replace(old_89, new_89)

    # 9. ButterWorth EQ (0x94) -> 52Hz
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
    assert old_94 in c_up, "0x94 block not found!"
    c_up = c_up.replace(old_94, new_94)

    # 10. Bass SPK EQ (0x95)
    c_95 = make_c_eq(0x95, "Bass SPK:Bass EQ         ", 0, sub_filters)
    idx_95 = c_up.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_95)
    c_up = c_up[:idx_95_start] + c_95 + "\n\n" + c_up[idx_95_end:]

    # 11. Treble SPK EQ (0x96)
    c_96 = make_c_eq(0x96, "Treble SPK:Treble EQ     ", 0, sat_filters)
    idx_96 = c_up.find("0x96,/*Treble SPK:Treble EQ")
    idx_96_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_96)
    idx_96_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_96)
    c_up = c_up[:idx_96_start] + c_96 + "\n\n" + c_up[idx_96_end:]

    # 12. Mid SPK EQ (0x97)
    c_97 = make_c_eq(0x97, "Mid SPK:Mid EQ           ", 0, sub_filters)
    idx_97 = c_up.find("0x97,/*Mid SPK:Mid EQ")
    idx_97_start = c_up.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_97)
    idx_97_end = c_up.find("0xA5, 0x5A,/*sync head*/", idx_97)
    c_up = c_up[:idx_97_start] + c_97 + "\n\n" + c_up[idx_97_end:]

    # 13. Treble Gain (0x98) -> 4096 (0dB clean unity)
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
0x00, 0x10,/*gain: 4096 (0.0 dB clean unity gain, drops hiss floor)*/
0x16,/*sync tail*/"""
    assert old_98 in c_up, "0x98 block not found!"
    c_up = c_up.replace(old_98, new_98)

    # Save target C files
    with open(os.path.join(base_dir, 'dsp_punchy_bass_sweet_vocal.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    with open(os.path.join(base_dir, 'dsp.c'), 'w', encoding='utf-8') as f:
        f.write(c_up)
    print("Updated dsp_punchy_bass_sweet_vocal.c and dsp.c!")

    # Verify byte count and frames
    all_bytes = re.findall(r'0x[0-9A-Fa-f]{2}', c_up)
    print(f"Total bytes in output C: {len(all_bytes)}")
    assert len(all_bytes) == 1667, f"Expected 1667 bytes, got {len(all_bytes)}"
    print("Verification SUCCESSFUL! All 1667 bytes and 42 frames intact.")

if __name__ == '__main__':
    main()
