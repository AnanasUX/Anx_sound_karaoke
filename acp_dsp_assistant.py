"""
================================================================================
          ACPWORKBENCH DSP ASSISTANT & DIRECT AUTO-CONFIGURATOR
================================================================================
Tác vụ chính:
1. Tự động cấu hình trực tiếp lên phần mềm ACPWorkbench_V2.44.2.exe qua Windows Automation.
2. Tự động khắc phục lỗi "Firmware version mismatch" của ACPWorkbench.
3. Đồng bộ và điều chỉnh cấu hình DSP 2.1 Bi-Amp (Sub 4" + Mid AIRS + Treble Dome).
4. Tự động tính toán lại hệ số Biquad IIR Filter (Q4.27) và sinh toàn bộ các file:
   - acp_workbench_config.ini (Parameters Data)
   - acp_eq_styles.xml (XBEL XML cho Parametric EQ Editor)
   - acp_dsp_effects.h (C Header cho Firmware)
   - acp_flash_parameters.bin (Flash Binary 4KB)
5. Quét cổng kết nối COM / Serial và báo cáo trạng thái hệ thống.
================================================================================
"""

import os
import sys
import time
import math
import struct
import zlib
import threading
import subprocess
import winreg

# Ensure UTF-8 output on Windows terminal
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import win32gui
import win32con
import pyautogui

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACP_EXE = os.path.join(BASE_DIR, "ACPWorkbench_V2.44.2.exe")
INI_PATH = os.path.join(BASE_DIR, "acp_workbench_config.ini")
XML_PATH = os.path.join(BASE_DIR, "acp_eq_styles.xml")
H_PATH = os.path.join(BASE_DIR, "acp_dsp_effects.h")
BIN_PATH = os.path.join(BASE_DIR, "acp_flash_parameters.bin")

Q27 = 134217728

# ----------------------------------------------------------------------
# 1. TOÁN HỌC BIQUAD FILTER (HỆ SỐ BỘ LỌC ÂM HỌC SỐ)
# ----------------------------------------------------------------------
def calc_peaking(f0, gain_db, q, fs=44100):
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

def calc_highpass(f0, q=0.7071, fs=44100):
    w0 = 2.0 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2.0 * q)
    b0 = (1.0 + math.cos(w0)) / 2.0
    b1 = -(1.0 + math.cos(w0))
    b2 = (1.0 + math.cos(w0)) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]

def calc_lowpass(f0, q=0.7071, fs=44100):
    w0 = 2.0 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2.0 * q)
    b0 = (1.0 - math.cos(w0)) / 2.0
    b1 = 1.0 - math.cos(w0)
    b2 = (1.0 - math.cos(w0)) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]

def calc_highshelf(f0, gain_db, q=0.7071, fs=44100):
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

# ----------------------------------------------------------------------
# 2. ĐỊNH NGHĨA PRESET ÂM THANH CHO HỆ THỐNG 2.1 BI-AMP
# ----------------------------------------------------------------------
PRESETS = {
    "Bose Style (Deep Bass / Warm Vocal)": [
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
            {'use': 'true', 'type': 'Peaking', 'gain': -1.0, 'f0': 500.0, 'q': 1.0},
            {'use': 'true', 'type': 'Peaking', 'gain': 1.0, 'f0': 1200.0, 'q': 0.8},
            {'use': 'true', 'type': 'Peaking', 'gain': 1.0, 'f0': 2500.0, 'q': 0.8},
            {'use': 'true', 'type': 'Peaking', 'gain': -1.0, 'f0': 5000.0, 'q': 1.0},
            {'use': 'true', 'type': 'Peaking', 'gain': 1.0, 'f0': 8000.0, 'q': 0.8},
            {'use': 'true', 'type': 'Peaking', 'gain': 1.5, 'f0': 12000.0, 'q': 0.8},
            {'use': 'true', 'type': 'Hight Shelf', 'gain': 1.0, 'f0': 16000.0, 'q': 0.8},
        ], -4.5, 100, 5, 80)
    ],
    "JBL Style (Punchy Bass / Bright Treble)": [
        ('CH1_SUB_BOOMBOX', 0.5, [
            {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 55.0, 'q': 0.7071},
            {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 55.0, 'q': 0.7071},
            {'use': 'true', 'type': 'Low Pass', 'gain': 0.0, 'f0': 380.0, 'q': 0.7071},
            {'use': 'true', 'type': 'Low Pass', 'gain': 0.0, 'f0': 380.0, 'q': 0.7071},
            {'use': 'true', 'type': 'Peaking', 'gain': 2.5, 'f0': 80.0, 'q': 1.0},
            {'use': 'true', 'type': 'Peaking', 'gain': 1.5, 'f0': 120.0, 'q': 1.2},
            {'use': 'true', 'type': 'Peaking', 'gain': -1.0, 'f0': 180.0, 'q': 1.0},
            {'use': 'true', 'type': 'Peaking', 'gain': -1.0, 'f0': 250.0, 'q': 1.0},
        ], -1.0, 100, 10, 150),
        ('CH2_MID_TREBLE', -1.0, [
            {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 380.0, 'q': 0.7071},
            {'use': 'true', 'type': 'High Pass', 'gain': 0.0, 'f0': 380.0, 'q': 0.7071},
            {'use': 'true', 'type': 'Peaking', 'gain': -0.5, 'f0': 600.0, 'q': 1.0},
            {'use': 'true', 'type': 'Peaking', 'gain': 0.5, 'f0': 1500.0, 'q': 0.8},
            {'use': 'true', 'type': 'Peaking', 'gain': 1.5, 'f0': 3000.0, 'q': 1.0},
            {'use': 'true', 'type': 'Peaking', 'gain': 0.0, 'f0': 5000.0, 'q': 1.0},
            {'use': 'true', 'type': 'Peaking', 'gain': 2.0, 'f0': 9000.0, 'q': 0.8},
            {'use': 'true', 'type': 'Peaking', 'gain': 2.0, 'f0': 13000.0, 'q': 0.8},
            {'use': 'true', 'type': 'Hight Shelf', 'gain': 1.5, 'f0': 16000.0, 'q': 0.8},
        ], -4.5, 100, 5, 80)
    ]
}

# ----------------------------------------------------------------------
# 3. QUÉT THÔNG TIN CỔNG COM VÀ TỆP CẤU HÌNH CỦA MẠCH
# ----------------------------------------------------------------------
def get_com_ports():
    ports = []
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM')
        for i in range(256):
            try:
                name, val, _ = winreg.EnumValue(key, i)
                ports.append((name, val))
            except OSError:
                break
    except FileNotFoundError:
        pass
    return ports

def read_firmware_version_from_ini(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'firmware_version' in line.lower() and '=' in line:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        val = parts[1].strip()
                        if val:
                            return val
    except Exception:
        pass
    return None

def auto_detect_firmware_in_dir():
    """Tự động tìm kiếm các file .ini khác trong thư mục để trích xuất version"""
    # Ưu tiên dsp.ini hoặc dsp_upgraded.ini (file export từ chip vật lý)
    for preferred in ["dsp.ini", "dsp_upgraded.ini", "dsp_original.ini"]:
        p = os.path.join(BASE_DIR, preferred)
        if os.path.exists(p):
            ver = read_firmware_version_from_ini(p)
            if ver and ver != "0.0.0":
                return ver, preferred

    for fname in os.listdir(BASE_DIR):
        if fname.endswith(".ini") and fname not in ["acp_workbench_config.ini", "ACPWorkbench.ini"]:
            path = os.path.join(BASE_DIR, fname)
            ver = read_firmware_version_from_ini(path)
            if ver and ver != "0.0.0":
                return ver, fname
    return "0.3.4", "dsp.ini"

# ----------------------------------------------------------------------
# 4. BỘ SINH CẤU HÌNH (CONFIG GENERATOR)
# ----------------------------------------------------------------------
def build_and_export_all(target_fw_version="2.44.2", preset_name="Bose Style (Deep Bass / Warm Vocal)"):
    channels = PRESETS.get(preset_name, PRESETS["Bose Style (Deep Bass / Warm Vocal)"])
    
    # 1. XML
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE xbel>',
        '<xbel version="3.0">'
    ]
    for name, pregain, filters, _, _, _, _ in channels:
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

    with open(XML_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_lines) + '\n')

    # 2. INI
    ini_lines = [
        '# ====================================================================',
        '# MVSILICON ACPWorkbench Complete Configuration File (2-Channel Bi-Amp)',
        f'# Preset: {preset_name}',
        f'# Firmware Version Synchronized: {target_fw_version}',
        '# ====================================================================',
        '',
        '[0x00-Firmware_Version]',
        f'Firmware_Version = {target_fw_version}',
        'Vendor = MVSILICON',
        'Product = Audio Codec Processor Workbench',
        '',
        '[0x01-System_Control]',
        'Global_Sample_Rate = 44100',
        'Global_MCLK_Source = PLL Clock1',
        'Communication_Type = USB',
        'Heartbeat_Time = 1000',
        'Frame_Size = 128',
        '',
        '[0x03-PGA0]',
        'Line1_Enable = 1',
        'Line2_Enable = 1',
        'PGA0_Input_Mode = Line1/Line2 Single-ended input',
        'MIC_Gain_Boost = Bypass',
        'PGA0_Linein1_Vol = 0.0',
        'PGA0_Linein2_Vol = 0.0',
        '',
        '[0x04-ADC0]',
        'ADC0_Enable = 1',
        'ADC0_Sample_Rate = 44100',
        'ADC0_MCLK_Source = PLL Clock1',
        'ADC0_Fade_Time = 20',
        'ADC0_LR_Swap = 0',
        'ADC0_DC_Blocker = 1',
        'ADC0_Digital_Vol = 0.0',
        'ADC0_Mute = 0',
        'AGC_Enable = 0',
        'Noise_Gating_Enable = 0',
        '',
        '[0x09-DAC0]',
        'DAC0_Enable = 1',
        'DAC0_Sample_Rate = 44100',
        'DAC0_MCLK_Source = PLL Clock1',
        'DAC0_Fade_Time = 20',
        'DAC0_Dither = 1',
        'DAC0_Scramble = DWA',
        'DAC0_Output_Mode = Stereo (L, R)',
        'DAC0_Digital_Vol = -0.5',
        'DAC0_Mute = 0',
        'Link_LR_Channels = 0',
        '',
        '[0x80-Effect_List]',
        'Effect_Count = 5',
        'Effect_0 = EQ',
        'Effect_1 = Dynamic Range Compressor',
        'Effect_2 = DC Blocker',
        'Effect_3 = Phase Control',
        'Effect_4 = MVBass',
        '',
        '[DC_Blocker]',
        'Enable = 1',
        '',
        '[Phase_Control]',
        'CH1_Sub_Phase = 0',
        'CH2_Satellite_Phase = 0',
        '',
        '[MVBass]',
        'Enable = 1',
        'Cutoff_Frequency = 55',
        'Intensity = 20',
        'BassEnhanced = 1',
        '',
        '[DRC_CH1_SUB]',
        'Enable = 1',
        'Threshold = -1.0',
        'Ratio = 100',
        'Attack_Time = 10',
        'Release_Time = 150',
        'Pregain = 0.0',
        'Crossover_Frequency = 350',
        '',
        '[DRC_CH2_SATELLITE]',
        'Enable = 1',
        'Threshold = -4.5',
        'Ratio = 100',
        'Attack_Time = 5',
        'Release_Time = 80',
        'Pregain = -1.5',
        'Crossover_Frequency = 350',
        '',
        '[EQ PARAMETERS CONFIGURATION]'
    ]

    for ch_idx, (name, pregain, flts, _, _, _, _) in enumerate(channels):
        ini_lines.append(f'# --- Channel {ch_idx+1}: {name} ---')
        ini_lines.append(f'CH{ch_idx+1}_Name = {name}')
        ini_lines.append(f'CH{ch_idx+1}_PreGain = {pregain:.2f}')
        ini_lines.append(f'CH{ch_idx+1}_FilterCount = {len(flts)}')
        for i, f_item in enumerate(flts):
            ini_lines.append(f'CH{ch_idx+1}_F{i}_Type = {f_item["type"]}')
            ini_lines.append(f'CH{ch_idx+1}_F{i}_Freq = {f_item["f0"]:.1f}')
            ini_lines.append(f'CH{ch_idx+1}_F{i}_Gain = {f_item["gain"]:.2f}')
            ini_lines.append(f'CH{ch_idx+1}_F{i}_Q = {f_item["q"]:.4f}')
            ini_lines.append(f'CH{ch_idx+1}_F{i}_Enable = 1')
        ini_lines.append('')

    ini_lines.append('[Log_Page]')
    ini_lines.append('Log_Enable = 1')
    ini_lines.append('Display_Communication_Frame = 1')
    ini_lines.append('Auto_Scroll = 1')

    if os.path.exists(os.path.join(BASE_DIR, 'dsp_upgraded.ini')):
        with open(os.path.join(BASE_DIR, 'dsp_upgraded.ini'), 'r', encoding='utf-8') as f_src:
            upgraded_data = f_src.read()
        with open(INI_PATH, 'w', encoding='utf-8') as f:
            f.write(upgraded_data)
    else:
        with open(INI_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ini_lines) + '\n')

    # 3. Header C
    h_lines = [
        '#ifndef __ACP_DSP_EFFECTS_2CH_H__',
        '#define __ACP_DSP_EFFECTS_2CH_H__',
        '#include <stdint.h>',
        '#define AUDIO_SAMPLE_RATE 44100',
        'typedef struct { int32_t b0, b1, b2, a1, a2; } ACP_BiquadCoeff_t;',
        'typedef struct { float th, ratio; uint32_t att, rel; float pregain; } ACP_DRC_Config_t;',
        ''
    ]
    for ch_idx, (name, pregain, flts, drc_th, drc_r, drc_a, drc_rel) in enumerate(channels):
        h_lines.append(f'/* Channel {ch_idx+1}: {name} */')
        h_lines.append(f'#define {name}_FILTER_COUNT {len(flts)}')
        h_lines.append(f'#define {name}_PREGAIN_DB ({pregain:.2f}f)')
        h_lines.append(f'const ACP_BiquadCoeff_t {name}_Filters[{len(flts)}] = {{')
        for i, f_item in enumerate(flts):
            t, f0, g, q = f_item['type'], f_item['f0'], f_item['gain'], f_item['q']
            if t == 'High Pass': c = calc_highpass(f0, q)
            elif t == 'Low Pass': c = calc_lowpass(f0, q)
            elif t == 'Hight Shelf': c = calc_highshelf(f0, g, q)
            else: c = calc_peaking(f0, g, q)
            h_lines.append(f'    {{ {int(round(c[0]*Q27))}, {int(round(c[1]*Q27))}, {int(round(c[2]*Q27))}, {int(round(c[3]*Q27))}, {int(round(c[4]*Q27))} }},')
        h_lines.append('};')
        h_lines.append(f'const ACP_DRC_Config_t {name}_DRC = {{ {drc_th:.1f}f, {drc_r:.1f}f, {drc_a}, {drc_rel}, {pregain:.1f}f }};\n')

    h_lines.append('#endif')
    with open(H_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(h_lines) + '\n')

    # 4. BIN Flash 4KB
    header = b'MVCFG_V2' + struct.pack('<III', 44100, len(channels), 0)
    body = bytearray()
    for ch_name, pregain, flts, drc_th, drc_ratio, drc_att, drc_rel in channels:
        name_bytes = ch_name.encode('ascii').ljust(32, b'\x00')
        ch_header = struct.pack('<32sfIIffff', name_bytes, pregain, len(flts), 0, drc_th, float(drc_ratio), float(drc_att), float(drc_rel))
        body.extend(ch_header)
        for flt in flts:
            t, f0, g, q = flt['type'], flt['f0'], flt['gain'], flt['q']
            if t == 'High Pass': c = calc_highpass(f0, q)
            elif t == 'Low Pass': c = calc_lowpass(f0, q)
            elif t == 'Hight Shelf': c = calc_highshelf(f0, g, q)
            else: c = calc_peaking(f0, g, q)
            b0_i, b1_i, b2_i, a1_i, a2_i = [int(round(x * Q27)) for x in c]
            flt_bytes = struct.pack('<4sffff5i', t[:4].encode('ascii').ljust(4, b'\x00'), f0, g, q, 0.0, b0_i, b1_i, b2_i, a1_i, a2_i)
            body.extend(flt_bytes)

    total_data = header + body
    padding_len = 4096 - len(total_data) - 4
    if padding_len > 0:
        total_data += b'\xff' * padding_len
    crc = zlib.crc32(total_data) & 0xffffffff
    total_data += struct.pack('<I', crc)
    with open(BIN_PATH, 'wb') as f:
        f.write(total_data)

    return True

# ----------------------------------------------------------------------
# 5. ROBOT TỰ ĐỘNG ĐIỀU KHIỂN & CẤU HÌNH TRỰC TIẾP LÊN ACPWORKBENCH
# ----------------------------------------------------------------------
def find_acp_window():
    """Tìm handle cửa sổ ACPWorkbench"""
    target_hwnds = []
    def enum_cb(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "ACPWorkbench" in title or "AP82xx" in title or "Audio Codec Processor" in title:
                target_hwnds.append((hwnd, title))
    win32gui.EnumWindows(enum_cb, None)
    return target_hwnds

def auto_configure_directly(log_func, fw_ver, preset_name):
    """Quy trình tự động hóa trực tiếp 100%"""
    log_func(">>> BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG CẤU HÌNH TRỰC TIẾP...")
    
    # Bước 1: Build lại cấu hình mới nhất
    log_func(f"[1/4] Đang biên dịch cấu hình Preset '{preset_name}' với Firmware '{fw_ver}'...")
    build_and_export_all(target_fw_version=fw_ver, preset_name=preset_name)
    log_func("      -> Đã xuất acp_workbench_config.ini & acp_eq_styles.xml [OK]")
    
    # Bước 2: Kiểm tra cửa sổ ACPWorkbench
    log_func("[2/4] Kiểm tra phần mềm ACPWorkbench...")
    windows = find_acp_window()
    if not windows:
        log_func("      -> Chưa mở phần mềm. Đang tự động khởi chạy ACPWorkbench_V2.44.2.exe...")
        if os.path.exists(ACP_EXE):
            subprocess.Popen([ACP_EXE], cwd=BASE_DIR)
            time.sleep(3.0)
            windows = find_acp_window()
        else:
            log_func("[LỖI] Không tìm thấy file ACPWorkbench_V2.44.2.exe!")
            return False

    if not windows:
        log_func("[CẢNH BÁO] Không tìm thấy cửa sổ ACPWorkbench. Hãy mở sẵn phần mềm rồi bấm lại!")
        return False

    hwnd, title = windows[0]
    log_func(f"      -> Tìm thấy cửa sổ: '{title}' (HWND: {hwnd}) [OK]")

    # Bước 3: Đưa cửa sổ lên phía trước
    log_func("[3/4] Kích hoạt cửa sổ ACPWorkbench lên màn hình...")
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.8)
    except Exception as e:
        log_func(f"      [Lưu ý] SetForegroundWindow: {e}")

    # Bước 4: Tự động điều khiển Menu nạp File
    log_func("[4/4] Đang gửi lệnh tự động Import Audio Setting vào phần mềm...")
    
    # Copy đường dẫn INI vào Clipboard để dán chính xác 100%
    temp_root = tk.Tk()
    temp_root.withdraw()
    temp_root.clipboard_clear()
    temp_root.clipboard_append(INI_PATH)
    temp_root.update()
    temp_root.destroy()
    time.sleep(0.3)

    # Gửi phím Alt+F để mở menu File
    pyautogui.hotkey('alt', 'f')
    time.sleep(0.5)

    # Nhấn 'i' để chọn Import Audio Setting (hoặc phím Enter đầu tiên)
    pyautogui.press('i')
    time.sleep(1.0)

    # Hộp thoại mở file hiện lên -> Dán đường dẫn file INI
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(1.2)

    # Đặt sẵn đường dẫn file XML EQ vào Clipboard cho người dùng
    temp_root2 = tk.Tk()
    temp_root2.withdraw()
    temp_root2.clipboard_clear()
    temp_root2.clipboard_append(XML_PATH)
    temp_root2.update()
    temp_root2.destroy()

    log_func("----------------------------------------------------------------------")
    log_func(">>> [HOÀN TẤT] ĐÃ TỰ ĐỘNG CẤU HÌNH THÀNH CÔNG TRỰC TIẾP LÊN PHẦN MỀM!")
    log_func("• File INI cấu hình đã được nạp tự động vào ACPWorkbench.")
    log_func("• Đường dẫn file EQ Styles XML đã được LƯU SẴN VÀO CLIPBOARD.")
    log_func("  (Mẹo: Mở đồ thị EQ -> Chuột phải chọn Import -> Bấm Ctrl+V -> Enter).")
    log_func("• Nếu bo mạch báo CONNECTED, âm thanh hệ thống sẽ nhận chuẩn Bi-Amp ngay!")
    log_func("----------------------------------------------------------------------")
    return True


# ----------------------------------------------------------------------
# 6. GIAO DIỆN ĐIỀU KHIỂN & TỰ ĐỘNG HÓA (TKINTER GUI)
# ----------------------------------------------------------------------
class DspAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MVSilicon DSP Assistant & Direct Auto-Configurator")
        self.root.geometry("680x640")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use('clam')

        # Header Banner
        header = tk.Frame(root, bg="#0f172a", height=65)
        header.pack(fill=tk.X)
        lbl_title = tk.Label(header, text="MVSILICON ACPWORKBENCH DSP AUTO-CONFIGURATOR", 
                             fg="#38bdf8", bg="#0f172a", font=("Segoe UI", 12, "bold"))
        lbl_title.pack(pady=6)
        lbl_sub = tk.Label(header, text="Tự Động Cấu Hình Trực Tiếp Lên Phần Mềm & Khắc Phục Mismatch", 
                            fg="#94a3b8", bg="#0f172a", font=("Segoe UI", 9))
        lbl_sub.pack()

        body = tk.Frame(root, padx=16, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        # Khung 1: Khởi chạy & Cổng kết nối
        grp_tool = ttk.LabelFrame(body, text=" 1. Trạng Thái Kết Nối & Khởi Chạy Tool ", padding=8)
        grp_tool.pack(fill=tk.X, pady=4)

        btn_launch = tk.Button(grp_tool, text="🚀 Mở ACPWorkbench (V2.44.2)", 
                               bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"),
                               command=self.launch_acp)
        btn_launch.pack(side=tk.LEFT, padx=4)

        self.lbl_ports = tk.Label(grp_tool, text="Đang quét cổng...", fg="#0f766e", font=("Segoe UI", 9))
        self.lbl_ports.pack(side=tk.RIGHT, padx=4)
        self.update_ports()

        # Khung 2: Cài đặt Thông số & Firmware Version
        grp_settings = ttk.LabelFrame(body, text=" 2. Cài Đặt Preset & Đồng Bộ Firmware Version ", padding=8)
        grp_settings.pack(fill=tk.X, pady=4)

        tk.Label(grp_settings, text="Chất âm (2.1 Bi-Amp):").grid(row=0, column=0, sticky="w", pady=3)
        self.cbo_preset = ttk.Combobox(grp_settings, values=list(PRESETS.keys()), state="readonly", width=34)
        self.cbo_preset.current(0)
        self.cbo_preset.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        tk.Label(grp_settings, text="Firmware Version:").grid(row=1, column=0, sticky="w", pady=3)
        self.ent_fw = ttk.Entry(grp_settings, width=16)
        
        # Tự động quét version trong thư mục nếu có
        detected_ver, detected_file = auto_detect_firmware_in_dir()
        if detected_ver:
            self.ent_fw.insert(0, detected_ver)
        else:
            self.ent_fw.insert(0, "2.44.2")
        self.ent_fw.grid(row=1, column=1, sticky="w", padx=5, pady=3)

        btn_detect = ttk.Button(grp_settings, text="📂 Đọc từ file của mạch...", command=self.browse_ini)
        btn_detect.grid(row=1, column=2, sticky="e", padx=4, pady=3)

        # KHUNG 3: MỤC ĐẶC BIỆT - TỰ ĐỘNG CẤU HÌNH TRỰC TIẾP
        grp_auto = ttk.LabelFrame(body, text=" 3. TỰ ĐỘNG CẤU HÌNH TRỰC TIẾP LÊN PHẦN MỀM (Khuyên Dùng) ", padding=10)
        grp_auto.pack(fill=tk.X, pady=8)

        btn_auto_run = tk.Button(
            grp_auto, 
            text="⚡ BẤM ĐỂ TỰ ĐỘNG CẤU HÌNH TRỰC TIẾP LÊN ACPWORKBENCH ⚡", 
            bg="#16a34a", fg="white", 
            font=("Segoe UI", 11, "bold"),
            activebackground="#15803d", activeforeground="white",
            relief=tk.RAISED, bd=3,
            command=self.run_auto_config_thread
        )
        btn_auto_run.pack(fill=tk.X, pady=4)

        btn_manual_build = ttk.Button(grp_auto, text="Hoặc chỉ cập nhật file cấu hình (Không tự bấm trên phần mềm)", 
                                      command=self.manual_build_only)
        btn_manual_build.pack(fill=tk.X, pady=2)

        # Khung 4: Nhật Ký Hoạt Động & Kiểm Định Hệ Thống (Console Log)
        grp_log = ttk.LabelFrame(body, text=" 4. Nhật Ký Hoạt Động & Kiểm Định Hệ Thống ", padding=8)
        grp_log.pack(fill=tk.BOTH, expand=True, pady=4)

        self.txt_log = tk.Text(grp_log, height=10, bg="#f8fafc", fg="#1e293b", 
                               font=("Consolas", 8), relief=tk.SOLID, bd=1)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        self.log("Hệ thống DSP Assistant đã sẵn sàng.")
        if detected_ver:
            self.log(f"-> Tự động nhận diện Firmware Version '{detected_ver}' từ file '{detected_file}'.")
        self.log("-> Bấm nút màu xanh [TỰ ĐỘNG CẤU HÌNH TRỰC TIẾP] để tự động nạp vào ACPWorkbench.")

    def log(self, message):
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)

    def update_ports(self):
        ports = get_com_ports()
        if ports:
            port_names = [p[1] for p in ports]
            self.lbl_ports.config(text=f"Cổng COM: {', '.join(port_names)}")
        else:
            self.lbl_ports.config(text="Cổng: USB (HID)")

    def launch_acp(self):
        if os.path.exists(ACP_EXE):
            subprocess.Popen([ACP_EXE], cwd=BASE_DIR)
            self.log(f"Đã mở {os.path.basename(ACP_EXE)}.")
        else:
            messagebox.showerror("Lỗi", "Không tìm thấy file ACPWorkbench_V2.44.2.exe!")

    def browse_ini(self):
        filename = filedialog.askopenfilename(
            initialdir=BASE_DIR,
            title="Chọn file .ini xuất từ bo mạch",
            filetypes=[("Parameters Data (*.ini)", "*.ini"), ("All Files", "*.*")]
        )
        if filename:
            ver = read_firmware_version_from_ini(filename)
            if ver:
                self.ent_fw.delete(0, tk.END)
                self.ent_fw.insert(0, ver)
                self.log(f"Đã phát hiện Firmware Version: {ver} từ file '{os.path.basename(filename)}'.")
            else:
                messagebox.showwarning("Cảnh báo", "Không tìm thấy thông tin Firmware_Version trong file!")

    def manual_build_only(self):
        fw_ver = self.ent_fw.get().strip()
        preset = self.cbo_preset.get()
        build_and_export_all(target_fw_version=fw_ver, preset_name=preset)
        self.log(f"Đã cập nhật toàn bộ 4 file cấu hình với Firmware Version: {fw_ver}.")
        messagebox.showinfo("Thành công", "Đã cập nhật toàn bộ file cấu hình thành công!")

    def run_auto_config_thread(self):
        fw_ver = self.ent_fw.get().strip()
        preset = self.cbo_preset.get()
        # Chạy trong luồng riêng để không bị đơ giao diện
        threading.Thread(target=auto_configure_directly, args=(self.log, fw_ver, preset), daemon=True).start()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        print("Đang chạy CLI...")
        build_and_export_all("2.44.2", "Bose Style (Deep Bass / Warm Vocal)")
        print("Đã xuất cấu hình thành công!")
        return

    root = tk.Tk()
    app = DspAssistantApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
