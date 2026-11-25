import os
import math
import struct
import zlib

def biquad_peaking(f0, gain_db, q, fs=44100):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2.0 * q)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * math.cos(w0)
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha / A
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]

def biquad_highpass(f0, q=0.7071, fs=44100):
    w0 = 2.0 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2.0 * q)
    b0 = (1.0 + math.cos(w0)) / 2.0
    b1 = -(1.0 + math.cos(w0))
    b2 = (1.0 + math.cos(w0)) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]

def biquad_lowpass(f0, q=0.7071, fs=44100):
    w0 = 2.0 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2.0 * q)
    b0 = (1.0 - math.cos(w0)) / 2.0
    b1 = 1.0 - math.cos(w0)
    b2 = (1.0 - math.cos(w0)) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]

def biquad_highshelf(f0, gain_db, q=0.7071, fs=44100):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2.0 * q)
    cos_w0 = math.cos(w0)
    sqrt_A = math.sqrt(A)
    b0 =    A*( (A+1) + (A-1)*cos_w0 + 2*sqrt_A*alpha )
    b1 = -2*A*( (A-1) + (A+1)*cos_w0 )
    b2 =    A*( (A+1) + (A-1)*cos_w0 - 2*sqrt_A*alpha )
    a0 =        (A+1) - (A-1)*cos_w0 + 2*sqrt_A*alpha
    a1 =    2*( (A-1) - (A+1)*cos_w0 )
    a2 =        (A+1) - (A-1)*cos_w0 - 2*sqrt_A*alpha
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]

# 2 CHANNELS:
# CH1: SUB 4" Boombox (40W)
# CH2: SATELLITE MID-TREBLE (AIRS 15W + Treble Dome 20-30W)
channels_2ch = [
    ('CH1_SUB_BOOMBOX', 0.0, [
        {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 55.0, 'q': 0.7071},
        {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 55.0, 'q': 0.7071},
        {'use': 'true', 'type': 'Low Pass', 'gain': 0.0, 'f0': 350.0, 'q': 0.7071},
        {'use': 'true', 'type': 'Low Pass', 'gain': 0.0, 'f0': 350.0, 'q': 0.7071},
        {'use': 'true', 'type': 'Peaking', 'gain': 1.5, 'f0': 75.0, 'q': 0.8},
        {'use': 'true', 'type': 'Peaking', 'gain': 1.0, 'f0': 100.0, 'q': 1.0},
        {'use': 'true', 'type': 'Peaking', 'gain': -1.5, 'f0': 160.0, 'q': 1.0},
        {'use': 'true', 'type': 'Peaking', 'gain': -1.0, 'f0': 250.0, 'q': 1.0},
    ], -1.0, 100, 10, 150),
    ('CH2_MID_TREBLE', -1.5, [
        {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 350.0, 'q': 0.7071},
        {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 350.0, 'q': 0.7071},
        # Mid tuning for AIRS
        {'use': 'true', 'type': 'Peaking', 'gain': -1.0, 'f0': 500.0, 'q': 1.0},
        {'use': 'true', 'type': 'Peaking', 'gain': 1.0, 'f0': 1200.0, 'q': 0.8},
        {'use': 'true', 'type': 'Peaking', 'gain': 1.0, 'f0': 2500.0, 'q': 0.8},
        # Treble tuning for Dome Tweeter
        {'use': 'true', 'type': 'Peaking', 'gain': -1.0, 'f0': 5000.0, 'q': 1.0},
        {'use': 'true', 'type': 'Peaking', 'gain': 1.0, 'f0': 8000.0, 'q': 0.8},
        {'use': 'true', 'type': 'Peaking', 'gain': 1.5, 'f0': 12000.0, 'q': 0.8},
        {'use': 'true', 'type': 'Hight Shelf', 'gain': 1.0, 'f0': 16000.0, 'q': 0.8},
    ], -4.5, 100, 5, 80)
]

# 1. Generate XML
xml_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<!DOCTYPE xbel>',
    '<xbel version="3.0">'
]
for name, pregain, filters, _, _, _, _ in channels_2ch:
    xml_lines.append('    <folder folded="no">')
    xml_lines.append(f'        <title>EQ_EFFECT_STYLE_{name}</title>')
    xml_lines.append(f'        <bookmark href="eq_effect_style_name"><title>{name}</title></bookmark>')
    xml_lines.append(f'        <bookmark href="pre_gain"><title>{pregain:.6f}</title></bookmark>')
    xml_lines.append(f'        <bookmark href="preset_filters_size"><title>{len(filters)}</title></bookmark>')
    for i, flt in enumerate(filters):
        logf0 = math.log10(flt['f0'])
        xml_lines.append('        <folder folded="no">')
        xml_lines.append(f'            <title>preset_filter[{i}]</title>')
        xml_lines.append(f'            <bookmark href="useFlag"><title>{flt["use"]}</title></bookmark>')
        xml_lines.append(f'            <bookmark href="filter_type"><title>{flt["type"]}</title></bookmark>')
        xml_lines.append(f'            <bookmark href="dBgain"><title>{flt["gain"]:.6f}</title></bookmark>')
        xml_lines.append(f'            <bookmark href="f0"><title>{flt["f0"]:.6f}</title></bookmark>')
        xml_lines.append(f'            <bookmark href="logf0"><title>{logf0:.6f}</title></bookmark>')
        xml_lines.append(f'            <bookmark href="Q"><title>{flt["q"]:.6f}</title></bookmark>')
        xml_lines.append('        </folder>')
    xml_lines.append('    </folder>')
xml_lines.append('</xbel>')

with open('acp_eq_styles.xml', 'w', encoding='utf-8') as f:
    f.write('\n'.join(xml_lines) + '\n')
print('Generated acp_eq_styles.xml (2-channel Bi-Amp)')

# 2. Generate INI
# Sync with actual hardware parameters from dsp_upgraded.ini (Firmware 0.3.4, Type 48, Effect 2.45.5)
if os.path.exists('dsp_upgraded.ini'):
    with open('dsp_upgraded.ini', 'r', encoding='utf-8') as f:
        ini_content = f.read()
    with open('acp_workbench_config.ini', 'w', encoding='utf-8') as f:
        f.write(ini_content)
    print('Synchronized acp_workbench_config.ini from dsp_upgraded.ini (Hardware Best Sound T1V2 FW 0.3.4)')


# 3. Generate C Header
Q27 = 134217728
h_lines = [
    '#ifndef __ACP_DSP_EFFECTS_2CH_H__',
    '#define __ACP_DSP_EFFECTS_2CH_H__',
    '#include <stdint.h>',
    '#define AUDIO_SAMPLE_RATE 44100',
    'typedef struct { int32_t b0, b1, b2, a1, a2; } ACP_BiquadCoeff_t;',
    'typedef struct { float th, ratio; uint32_t att, rel; float pregain; } ACP_DRC_Config_t;',
    ''
]
for ch_idx, (name, pregain, flts, drc_th, drc_r, drc_a, drc_rel) in enumerate(channels_2ch):
    h_lines.append(f'/* Channel {ch_idx+1}: {name} */')
    h_lines.append(f'#define {name}_FILTER_COUNT {len(flts)}')
    h_lines.append(f'#define {name}_PREGAIN_DB ({pregain:.2f}f)')
    h_lines.append(f'const ACP_BiquadCoeff_t {name}_Filters[{len(flts)}] = {{')
    for i, f_item in enumerate(flts):
        t, f0, g, q = f_item['type'], f_item['f0'], f_item['gain'], f_item['q']
        if t == 'High Pass': c = biquad_highpass(f0, q)
        elif t == 'Low Pass': c = biquad_lowpass(f0, q)
        elif t == 'Hight Shelf': c = biquad_highshelf(f0, g, q)
        else: c = biquad_peaking(f0, g, q)
        h_lines.append(f'    {{ {int(round(c[0]*Q27))}, {int(round(c[1]*Q27))}, {int(round(c[2]*Q27))}, {int(round(c[3]*Q27))}, {int(round(c[4]*Q27))} }},')
    h_lines.append('};')
    h_lines.append(f'const ACP_DRC_Config_t {name}_DRC = {{ {drc_th:.1f}f, {drc_r:.1f}f, {drc_a}, {drc_rel}, {pregain:.1f}f }};\n')

h_lines.append('#endif')
with open('acp_dsp_effects.h', 'w', encoding='utf-8') as f:
    f.write('\n'.join(h_lines) + '\n')
print('Generated acp_dsp_effects.h (2-channel Bi-Amp)')
