import os
import shutil
import struct

def s16_bytes(val):
    return struct.pack('<h', int(val))

def u16_bytes(val):
    return struct.pack('<H', int(val) & 0xFFFF)

def build_eq_payload(pregain, filters):
    # filters is a list of up to 10 dicts: {'enable': bool, 'type': int, 'f0': int, 'Q': int, 'gain': int}
    payload = bytearray()
    payload.append(0xFF) # all parameter
    payload.extend(u16_bytes(1)) # enable
    payload.extend(s16_bytes(pregain)) # pregain
    payload.extend(u16_bytes(0)) # calculation_type

    for i in range(10):
        if i < len(filters):
            flt = filters[i]
            payload.extend(u16_bytes(1 if flt['enable'] else 0))
            payload.extend(u16_bytes(flt['type']))
            payload.extend(u16_bytes(flt['f0']))
            payload.extend(u16_bytes(flt['Q']))
            payload.extend(s16_bytes(flt['gain']))
        else:
            payload.extend(u16_bytes(0))
            payload.extend(u16_bytes(0))
            payload.extend(u16_bytes(0))
            payload.extend(u16_bytes(0))
            payload.extend(s16_bytes(0))
    return payload

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dsp_c_path = os.path.join(base_dir, 'dsp.c')
    dsp_ini_path = os.path.join(base_dir, 'dsp.ini')

    # Read original dsp.c
    with open(dsp_c_path, 'r', encoding='utf-8') as f:
        c_content = f.read()

    # Define Upgraded Filters
    # 1. Bass SPK EQ (0x95):
    # Filter 1: High Pass, 55Hz, Q=724, gain=0
    # Filter 2: Low Pass, 350Hz, Q=724, gain=0
    # Filter 3: Low Pass, 350Hz, Q=724, gain=0
    # Filter 4: Peaking, 75Hz, gain=+1.5dB (384), Q=0.8 (819)
    # Filter 5: Peaking, 100Hz, gain=+1.0dB (256), Q=1.0 (1024)
    # Filter 6: Peaking, 160Hz, gain=-1.5dB (-384), Q=1.0 (1024)
    # Filter 7: Peaking, 250Hz, gain=-1.0dB (-256), Q=1.0 (1024)
    bass_filters = [
        {'enable': True, 'type': 4, 'f0': 55, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 350, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 3, 'f0': 350, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 0, 'f0': 75, 'Q': 819, 'gain': 384},
        {'enable': True, 'type': 0, 'f0': 100, 'Q': 1024, 'gain': 256},
        {'enable': True, 'type': 0, 'f0': 160, 'Q': 1024, 'gain': -384},
        {'enable': True, 'type': 0, 'f0': 250, 'Q': 1024, 'gain': -256},
    ]

    # 2. Mid SPK EQ (0x97):
    # Filter 1: High Pass, 350Hz, Q=724, gain=0
    # Filter 2: High Pass, 350Hz, Q=724, gain=0
    # Filter 3: Peaking, 500Hz, gain=-1.0dB (-256), Q=1.0 (1024)
    # Filter 4: Peaking, 1200Hz, gain=+1.0dB (256), Q=0.8 (819)
    # Filter 5: Peaking, 2500Hz, gain=+1.0dB (256), Q=0.8 (819)
    mid_filters = [
        {'enable': True, 'type': 4, 'f0': 350, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 4, 'f0': 350, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 0, 'f0': 500, 'Q': 1024, 'gain': -256},
        {'enable': True, 'type': 0, 'f0': 1200, 'Q': 819, 'gain': 256},
        {'enable': True, 'type': 0, 'f0': 2500, 'Q': 819, 'gain': 256},
    ]

    # 3. Treble SPK EQ (0x96):
    # Filter 1: High Pass, 350Hz, Q=724, gain=0
    # Filter 2: Peaking, 5000Hz, gain=-1.0dB (-256), Q=1.0 (1024)
    # Filter 3: Peaking, 8000Hz, gain=+1.0dB (256), Q=0.8 (819)
    # Filter 4: Peaking, 12000Hz, gain=+1.5dB (384), Q=0.8 (819)
    # Filter 5: Hight Shelf, 16000Hz, gain=+1.0dB (256), Q=0.8 (819)
    treble_filters = [
        {'enable': True, 'type': 4, 'f0': 350, 'Q': 724, 'gain': 0},
        {'enable': True, 'type': 0, 'f0': 5000, 'Q': 1024, 'gain': -256},
        {'enable': True, 'type': 0, 'f0': 8000, 'Q': 819, 'gain': 256},
        {'enable': True, 'type': 0, 'f0': 12000, 'Q': 819, 'gain': 384},
        {'enable': True, 'type': 2, 'f0': 16000, 'Q': 819, 'gain': 256},
    ]

    # Parse and update dsp.ini
    with open(dsp_ini_path, 'r', encoding='utf-8') as f:
        ini_lines = f.readlines()

    updated_ini = []
    current_sec = ""
    for line in ini_lines:
        sline = line.strip()
        if sline.startswith('[') and sline.endswith(']'):
            current_sec = sline[1:-1]
            updated_ini.append(line)
            continue

        if current_sec == '0x87-MVBass_Classic':
            if sline.startswith('cutoff_frequency'):
                updated_ini.append('cutoff_frequency = 55\n')
                continue
            elif sline.startswith('intensity'):
                updated_ini.append('intensity = 20\n')
                continue

        elif current_sec == '0x94-User-defined_Effect': # Bass SPK:ButterWorth EQ
            if sline.startswith('Cut Freq'):
                updated_ini.append('Cut Freq = 55\n')
                continue

        elif current_sec == '0x98-Gain_Control': # Treble SPK:Treble Gain
            if sline.startswith('gain'):
                updated_ini.append('gain = 3444\n') # -1.5 dB balanced
                continue

        elif current_sec == '0x99-Gain_Control': # Mid SPK:Mid Gain
            if sline.startswith('gain'):
                updated_ini.append('gain = 3444\n') # -1.5 dB balanced
                continue

        elif current_sec == '0x9b-DRC': # Bass SPK:Bass DRC
            if sline.startswith('threshold4'):
                updated_ini.append('threshold4 = -100\n') # -1.0 dBFS Limiter
                continue
            elif sline.startswith('attack4'):
                updated_ini.append('attack4 = 10\n') # 10 ms
                continue
            elif sline.startswith('release4'):
                updated_ini.append('release4 = 150\n') # 150 ms
                continue

        elif current_sec == '0x9c-DRC': # Mid SPK:Mid DRC
            if sline.startswith('threshold4'):
                updated_ini.append('threshold4 = -450\n') # -4.5 dBFS Limiter
                continue
            elif sline.startswith('attack4'):
                updated_ini.append('attack4 = 5\n') # 5 ms
                continue
            elif sline.startswith('release4'):
                updated_ini.append('release4 = 80\n') # 80 ms
                continue

        elif current_sec in ['0x95-EQ', '0x96-EQ', '0x97-EQ']:
            # Skip old filter lines, we will emit them when section starts
            if sline.startswith('pregain'):
                updated_ini.append('pregain = 0\n')
                continue
            elif sline.startswith('calculation_type'):
                updated_ini.append('calculation_type = 0\n')
                # Now write the 10 filters for this section
                flts = bass_filters if current_sec == '0x95-EQ' else (treble_filters if current_sec == '0x96-EQ' else mid_filters)
                for fi in range(10):
                    fnum = fi + 1
                    if fi < len(flts):
                        fitem = flts[fi]
                        updated_ini.append(f'filter{fnum}_enable = 1\n')
                        updated_ini.append(f'filter{fnum}_type = {fitem["type"]}\n')
                        updated_ini.append(f'filter{fnum}_f0 = {fitem["f0"]}\n')
                        updated_ini.append(f'filter{fnum}_Q = {fitem["Q"]}\n')
                        updated_ini.append(f'filter{fnum}_gain = {fitem["gain"]}\n')
                    else:
                        updated_ini.append(f'filter{fnum}_enable = 0\n')
                        updated_ini.append(f'filter{fnum}_type = 0\n')
                        updated_ini.append(f'filter{fnum}_f0 = 0\n')
                        updated_ini.append(f'filter{fnum}_Q = 0\n')
                        updated_ini.append(f'filter{fnum}_gain = 0\n')
                continue
            elif sline.startswith('filter'):
                continue # skipped because written above

        updated_ini.append(line)

    upgraded_ini_content = "".join(updated_ini)
    with open(dsp_ini_path, 'w', encoding='utf-8') as f:
        f.write(upgraded_ini_content)
    with open(os.path.join(base_dir, 'dsp_upgraded.ini'), 'w', encoding='utf-8') as f:
        f.write(upgraded_ini_content)
    print("Updated dsp.ini and created dsp_upgraded.ini")

    # Also update acp_workbench_config.ini to match the 100% compatible structure
    with open(os.path.join(base_dir, 'acp_workbench_config.ini'), 'w', encoding='utf-8') as f:
        f.write(upgraded_ini_content)
    print("Synchronized acp_workbench_config.ini with hardware firmware version 0.3.4")

    # Now generate the updated dsp.c with exact frame bytes
    # Function to format an effect block in C array syntax
    def format_c_block(sec_id_hex, comment, payload_bytes):
        lines = []
        lines.append("0xA5, 0x5A,/*sync head*/")
        lines.append(f"{sec_id_hex},/*{comment}*/")
        lines.append(f"0x{len(payload_bytes):02X},/*length*/")
        # Format payload bytes in pairs or groups
        i = 0
        while i < len(payload_bytes):
            if i == 0 and payload_bytes[0] == 0xFF:
                lines.append("0xFF,/*all parameter*/")
                i += 1
            else:
                b1 = payload_bytes[i]
                b2 = payload_bytes[i+1] if i + 1 < len(payload_bytes) else None
                if b2 is not None:
                    lines.append(f"0x{b1:02X}, 0x{b2:02X},")
                    i += 2
                else:
                    lines.append(f"0x{b1:02X},")
                    i += 1
        lines.append("0x16,/*sync tail*/\n")
        return "\n".join(lines)

    # Let's rebuild the C code by replacing the blocks in dsp_original.c
    with open(os.path.join(base_dir, 'dsp_original.c'), 'r', encoding='utf-8') as f:
        orig_c = f.read()

    # 1. Replace 0x87 MVBass_Classic
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
    orig_c = orig_c.replace(old_87, new_87)

    # 2. Replace 0x94 ButterWorth EQ
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
    orig_c = orig_c.replace(old_94, new_94)

    # 3. Build new C text for 0x95 (Bass EQ)
    c_lines_95 = [
        "0xA5, 0x5A,/*sync head*/",
        "0x95,/*Bass SPK:Bass EQ         */",
        "0x6B,/*length*/",
        "0xFF,/*all parameter*/",
        "0x01, 0x00,/*enable*/",
        "0x00, 0x00,/*pregain: 0 dB*/",
        "0x00, 0x00,/*calculation_type*/"
    ]
    filter_names_95 = [
        "HPF 55Hz LR24 (1/2)",
        "LPF 350Hz LR24 (1/2)",
        "LPF 350Hz LR24 (2/2)",
        "PEQ 75Hz +1.5dB Q0.8",
        "PEQ 100Hz +1.0dB Q1.0",
        "PEQ 160Hz -1.5dB Q1.0",
        "PEQ 250Hz -1.0dB Q1.0",
        "Unused",
        "Unused",
        "Unused"
    ]
    for fi in range(10):
        fnum = fi + 1
        name = filter_names_95[fi]
        if fi < len(bass_filters):
            flt = bass_filters[fi]
            c_lines_95.append(f"0x01, 0x00,/*filter{fnum}_enable: 1 ({name})*/")
            c_lines_95.append(f"0x{flt['type']:02X}, 0x00,/*filter{fnum}_type*/")
            f0_b = u16_bytes(flt['f0'])
            c_lines_95.append(f"0x{f0_b[0]:02X}, 0x{f0_b[1]:02X},/*filter{fnum}_f0: {flt['f0']}Hz*/")
            q_b = u16_bytes(flt['Q'])
            c_lines_95.append(f"0x{q_b[0]:02X}, 0x{q_b[1]:02X},/*filter{fnum}_Q: {flt['Q']}*/")
            g_b = s16_bytes(flt['gain'])
            c_lines_95.append(f"0x{g_b[0]:02X}, 0x{g_b[1]:02X},/*filter{fnum}_gain: {flt['gain']}*/")
        else:
            c_lines_95.append(f"0x00, 0x00,/*filter{fnum}_enable*/")
            c_lines_95.append(f"0x00, 0x00,/*filter{fnum}_type*/")
            c_lines_95.append(f"0x00, 0x00,/*filter{fnum}_f0*/")
            c_lines_95.append(f"0x00, 0x00,/*filter{fnum}_Q*/")
            c_lines_95.append(f"0x00, 0x00,/*filter{fnum}_gain*/")
    c_lines_95.append("0x16,/*sync tail*/")
    new_95_str = "\n".join(c_lines_95)

    # 4. Build new C text for 0x96 (Treble EQ)
    c_lines_96 = [
        "0xA5, 0x5A,/*sync head*/",
        "0x96,/*Treble SPK:Treble EQ     */",
        "0x6B,/*length*/",
        "0xFF,/*all parameter*/",
        "0x01, 0x00,/*enable*/",
        "0x00, 0x00,/*pregain: 0 dB*/",
        "0x00, 0x00,/*calculation_type*/"
    ]
    filter_names_96 = [
        "HPF 350Hz Protected",
        "PEQ 5000Hz -1.0dB Q1.0 Anti-harsh",
        "PEQ 8000Hz +1.0dB Q0.8 Crisp",
        "PEQ 12000Hz +1.5dB Q0.8 Air",
        "High Shelf 16000Hz +1.0dB Space",
        "Unused",
        "Unused",
        "Unused",
        "Unused",
        "Unused"
    ]
    for fi in range(10):
        fnum = fi + 1
        name = filter_names_96[fi]
        if fi < len(treble_filters):
            flt = treble_filters[fi]
            c_lines_96.append(f"0x01, 0x00,/*filter{fnum}_enable: 1 ({name})*/")
            c_lines_96.append(f"0x{flt['type']:02X}, 0x00,/*filter{fnum}_type*/")
            f0_b = u16_bytes(flt['f0'])
            c_lines_96.append(f"0x{f0_b[0]:02X}, 0x{f0_b[1]:02X},/*filter{fnum}_f0: {flt['f0']}Hz*/")
            q_b = u16_bytes(flt['Q'])
            c_lines_96.append(f"0x{q_b[0]:02X}, 0x{q_b[1]:02X},/*filter{fnum}_Q: {flt['Q']}*/")
            g_b = s16_bytes(flt['gain'])
            c_lines_96.append(f"0x{g_b[0]:02X}, 0x{g_b[1]:02X},/*filter{fnum}_gain: {flt['gain']}*/")
        else:
            c_lines_96.append(f"0x00, 0x00,/*filter{fnum}_enable*/")
            c_lines_96.append(f"0x00, 0x00,/*filter{fnum}_type*/")
            c_lines_96.append(f"0x00, 0x00,/*filter{fnum}_f0*/")
            c_lines_96.append(f"0x00, 0x00,/*filter{fnum}_Q*/")
            c_lines_96.append(f"0x00, 0x00,/*filter{fnum}_gain*/")
    c_lines_96.append("0x16,/*sync tail*/")
    new_96_str = "\n".join(c_lines_96)

    # 5. Build new C text for 0x97 (Mid EQ)
    c_lines_97 = [
        "0xA5, 0x5A,/*sync head*/",
        "0x97,/*Mid SPK:Mid EQ           */",
        "0x6B,/*length*/",
        "0xFF,/*all parameter*/",
        "0x01, 0x00,/*enable*/",
        "0x00, 0x00,/*pregain: 0 dB*/",
        "0x00, 0x00,/*calculation_type*/"
    ]
    filter_names_97 = [
        "HPF 350Hz LR24 (1/2) Protect AIRS",
        "HPF 350Hz LR24 (2/2) Protect AIRS",
        "PEQ 500Hz -1.0dB Q1.0 Clear Vocal",
        "PEQ 1200Hz +1.0dB Q0.8 Warm Body",
        "PEQ 2500Hz +1.0dB Q0.8 Clarity",
        "Unused",
        "Unused",
        "Unused",
        "Unused",
        "Unused"
    ]
    for fi in range(10):
        fnum = fi + 1
        name = filter_names_97[fi]
        if fi < len(mid_filters):
            flt = mid_filters[fi]
            c_lines_97.append(f"0x01, 0x00,/*filter{fnum}_enable: 1 ({name})*/")
            c_lines_97.append(f"0x{flt['type']:02X}, 0x00,/*filter{fnum}_type*/")
            f0_b = u16_bytes(flt['f0'])
            c_lines_97.append(f"0x{f0_b[0]:02X}, 0x{f0_b[1]:02X},/*filter{fnum}_f0: {flt['f0']}Hz*/")
            q_b = u16_bytes(flt['Q'])
            c_lines_97.append(f"0x{q_b[0]:02X}, 0x{q_b[1]:02X},/*filter{fnum}_Q: {flt['Q']}*/")
            g_b = s16_bytes(flt['gain'])
            c_lines_97.append(f"0x{g_b[0]:02X}, 0x{g_b[1]:02X},/*filter{fnum}_gain: {flt['gain']}*/")
        else:
            c_lines_97.append(f"0x00, 0x00,/*filter{fnum}_enable*/")
            c_lines_97.append(f"0x00, 0x00,/*filter{fnum}_type*/")
            c_lines_97.append(f"0x00, 0x00,/*filter{fnum}_f0*/")
            c_lines_97.append(f"0x00, 0x00,/*filter{fnum}_Q*/")
            c_lines_97.append(f"0x00, 0x00,/*filter{fnum}_gain*/")
    c_lines_97.append("0x16,/*sync tail*/")
    new_97_str = "\n".join(c_lines_97)

    # Replace 0x95 in orig_c
    idx_95 = orig_c.find("0x95,/*Bass SPK:Bass EQ")
    idx_95_start = orig_c.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_95)
    idx_95_end = orig_c.find("0xA5, 0x5A,/*sync head*/", idx_95)
    orig_c = orig_c[:idx_95_start] + new_95_str + "\n\n" + orig_c[idx_95_end:]

    # Replace 0x96 in orig_c
    idx_96 = orig_c.find("0x96,/*Treble SPK:Treble EQ")
    idx_96_start = orig_c.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_96)
    idx_96_end = orig_c.find("0xA5, 0x5A,/*sync head*/", idx_96)
    orig_c = orig_c[:idx_96_start] + new_96_str + "\n\n" + orig_c[idx_96_end:]

    # Replace 0x97 in orig_c
    idx_97 = orig_c.find("0x97,/*Mid SPK:Mid EQ")
    idx_97_start = orig_c.rfind("0xA5, 0x5A,/*sync head*/", 0, idx_97)
    idx_97_end = orig_c.find("0xA5, 0x5A,/*sync head*/", idx_97)
    orig_c = orig_c[:idx_97_start] + new_97_str + "\n\n" + orig_c[idx_97_end:]

    # 6. Replace 0x98 (Treble Gain) & 0x99 (Mid Gain)
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
0x74, 0x0D,/*gain: 3444 (-1.5 dB)*/
0x16,/*sync tail*/"""
    orig_c = orig_c.replace(old_98, new_98)

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
0x74, 0x0D,/*gain: 3444 (-1.5 dB)*/
0x16,/*sync tail*/"""
    orig_c = orig_c.replace(old_99, new_99)

    # 7. Replace 0x9B (Bass DRC) Limiter parameters
    old_9b = """0x7C, 0xFC,/*threshold4*/
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
0x5D, 0x01,/*release4*/"""

    new_9b = """0x9C, 0xFF,/*threshold4: -100 (-1.0 dBFS)*/
0x64, 0x00,/*ratio1*/
0x64, 0x00,/*ratio2*/
0x64, 0x00,/*ratio3*/
0x0A, 0x00,/*ratio4*/
0x64, 0x00,/*attack1*/
0x64, 0x00,/*attack2*/
0x64, 0x00,/*attack3*/
0x0A, 0x00,/*attack4: 10ms*/
0x01, 0x00,/*release1*/
0x01, 0x00,/*release2*/
0x01, 0x00,/*release3*/
0x96, 0x00,/*release4: 150ms*/"""

    # Check 0x9B context
    idx_9b = orig_c.find("0x9B,/*Bass SPK:Bass DRC")
    if idx_9b != -1:
        part_9b = orig_c[idx_9b:idx_9b+450]
        if old_9b in part_9b:
            orig_c = orig_c[:idx_9b] + part_9b.replace(old_9b, new_9b) + orig_c[idx_9b+450:]

    # 8. Replace 0x9C (Mid DRC) Limiter parameters
    new_9c = """0x3E, 0xFE,/*threshold4: -450 (-4.5 dBFS)*/
0x64, 0x00,/*ratio1*/
0x64, 0x00,/*ratio2*/
0x64, 0x00,/*ratio3*/
0x0A, 0x00,/*ratio4*/
0x64, 0x00,/*attack1*/
0x64, 0x00,/*attack2*/
0x64, 0x00,/*attack3*/
0x05, 0x00,/*attack4: 5ms*/
0x01, 0x00,/*release1*/
0x01, 0x00,/*release2*/
0x01, 0x00,/*release3*/
0x50, 0x00,/*release4: 80ms*/"""

    idx_9c = orig_c.find("0x9C,/*Mid SPK:Mid DRC")
    if idx_9c != -1:
        part_9c = orig_c[idx_9c:idx_9c+450]
        if old_9b in part_9c:
            orig_c = orig_c[:idx_9c] + part_9c.replace(old_9b, new_9c) + orig_c[idx_9c+450:]

    # Write upgraded dsp.c
    with open(dsp_c_path, 'w', encoding='utf-8') as f:
        f.write(orig_c)
    with open(os.path.join(base_dir, 'dsp_upgraded.c'), 'w', encoding='utf-8') as f:
        f.write(orig_c)
    print("Updated dsp.c and created dsp_upgraded.c")

if __name__ == '__main__':
    main()
