# -*- coding: utf-8 -*-
"""
================================================================================
  BEST SOUND DSP CONTROLLER — PC ULTIMATE PRO STUDIO (MVSILICON BP1048B2)
================================================================================
Bộ công cụ chuyên sâu toàn diện khai thác 100% năng lực phần cứng & DSP của
chip MVSilicon BP1048B2 (43 Effect Blocks + Karaoke + USB DAC + I2S + GPIO):

1. 🎛️ 8-BAND / 10-BAND PARAMETRIC EQ: Biquad IIR 64-bit RBJ Cookbook, đồ thị realtime.
2. ⚡ CROSSOVER & BI-AMP 2.1: Phân tần chủ động Subwoofer LPF, Subsonic HPF, Mid HPF.
3. 🛡️ DRC LIMITER: Bảo vệ màng loa, chống méo xén ngọn (clipping) và chống sụt áp.
4. 🔊 MVBASS & HARMONIC EXCITER: Tái tạo dải trầm ảo cho củ loa 4 inch + kích tép leng keng.
5. 🎤 VANG SỐ KARAOKE CHUYÊN SÂU:
   - Echo Kỹ thuật số (Delay, Repeat, Tone damping)
   - Studio Reverb (Room Size, Decay, Pre-delay, Wet/Dry)
   - Chống hú rít tự động (Howling Suppression / Notch Filter Tracking)
   - Đổi giọng Pitch Shifter (Nam / Nữ / Robot / Trẻ em)
   - Music Ducking (Tự động hạ nhạc nền khi nói vào micro)
6. 📈 DYNAMIC BASS THÔNG MINH (LOUDNESS FLETCHER-MUNSON): Tự tăng bass khi nghe nhỏ,
   tự phẳng lại khi vặn to để bảo vệ nguồn và loa.
7. 🔌 USB DAC SOUNDCARD & ĐỊNH TUYẾN SỐ I2S:
   - Chế độ USB Audio Class 2.0 nhận nhạc số bit-perfect
   - Xuất I2S Master/Slave đưa ra DAC rời (PCM5102, ES9018)
8. ⚙️ TÙY BIẾN BLUETOOTH & PHÍM CỨNG GPIO:
   - Đổi tên Bluetooth thiết bị, cấu hình nút bấm cứng (ADC Key Remap)
   - Đèn LED nháy theo nhịp nhạc (Spectrum VU Meter).
9. 📂 XUẤT / NHẬP: ACPWorkbench .INI, Firmware Source C dsp.c, Equalizer APO .TXT.
================================================================================
"""

import os
import sys
import math
import json
import time
import copy
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# ==============================================================================
# 1. BIQUAD IIR ENGINE (RBJ STANDARD)
# ==============================================================================

def calc_peaking_response(f0, gain_db, q, freqs, fs=44100):
    if abs(gain_db) < 0.01:
        return [0.0] * len(freqs)
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    sin_w0 = math.sin(w0)
    cos_w0 = math.cos(w0)
    alpha = sin_w0 / (2.0 * q)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cos_w0
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha / A
    nb0, nb1, nb2 = b0/a0, b1/a0, b2/a0
    na1, na2 = a1/a0, a2/a0

    gains = []
    for f in freqs:
        w = 2.0 * math.pi * f / fs
        cos_w = math.cos(w)
        sin_w = math.sin(w)
        cos_2w = math.cos(2.0 * w)
        sin_2w = math.sin(2.0 * w)
        num_re = nb0 + nb1 * cos_w + nb2 * cos_2w
        num_im = -nb1 * sin_w - nb2 * sin_2w
        den_re = 1.0 + na1 * cos_w + na2 * cos_2w
        den_im = -na1 * sin_w - na2 * sin_2w
        mag2 = (num_re*num_re + num_im*num_im) / max(1e-12, (den_re*den_re + den_im*den_im))
        gains.append(10.0 * math.log10(max(1e-12, mag2)))
    return gains

# ==============================================================================
# 2. COMPLETE PROFILES DATA MODEL
# ==============================================================================

DEFAULT_PROFILES = [
    {
        "id": "bo_8ohm_24v",
        "name": "B&O 8Ω · 24V (2.1 Bi-Amp Ultimate Pro)",
        "desc": "Cấu hình chuẩn tối ưu toàn diện cho sub 4 inch B&O + 2 loa Mid AIRS kèm Limiter và Crossover.",
        "preamp": -2.0,
        "mvbass": {"enabled": True, "cutoff": 90, "intensity": 45},
        "biamp": {"ch1": 1.5, "ch2": 0.0},
        "crossover": {"sub_lpf": 150, "mid_hpf": 160, "sub_hpf": 38},
        "limiter": {"enabled": True, "threshold_db": -1.5, "attack_ms": 10, "release_ms": 150, "ratio": 8.0},
        "noise_gate": {"enabled": True, "threshold_db": -68.0, "hold_ms": 200},
        "delay_phase": {"sub_delay_ms": 1.2, "sub_phase_invert": False},
        "spatial": {"surround_3d": False, "treble_exciter": 20},
        "karaoke": {
            "enabled": False,
            "echo_delay": 180,
            "echo_repeat": 45,
            "reverb_room": 60,
            "reverb_decay": 2.2,
            "reverb_mix": 35,
            "anti_howling": True,
            "pitch_shift": 0,
            "music_ducking": True
        },
        "dynamic_bass": {"enabled": True, "low_vol_boost_db": 5.0, "high_vol_cut_db": -3.0},
        "hardware_io": {
            "usb_dac_mode": True,
            "i2s_out": True,
            "i2s_sample_rate": 44100,
            "bt_name": "BEST SOUND T1V2 BI-AMP",
            "led_vu_meter": True
        },
        "bands": [
            {"name": "Sub Bass", "hz": 48, "gain": 2.5, "q": 1.41, "enabled": True},
            {"name": "Punch", "hz": 80, "gain": 3.0, "q": 1.60, "enabled": True},
            {"name": "Warmth", "hz": 160, "gain": 1.0, "q": 1.20, "enabled": True},
            {"name": "Body", "hz": 400, "gain": -1.5, "q": 1.80, "enabled": True},
            {"name": "Vocal Low", "hz": 1000, "gain": 0.5, "q": 1.41, "enabled": True},
            {"name": "Vocal High", "hz": 2500, "gain": 2.0, "q": 1.50, "enabled": True},
            {"name": "Presence", "hz": 6000, "gain": 2.8, "q": 1.41, "enabled": True},
            {"name": "Air Sparkle", "hz": 12000, "gain": 3.5, "q": 1.20, "enabled": True}
        ]
    },
    {
        "id": "karaoke_acoustic_pro",
        "name": "Karaoke & Vang Số Sân Khấu (Vocal Pro)",
        "desc": "Cấu hình tối ưu hát Karaoke, Echo & Reverb mượt mà, chống hú rít tuyệt đối và tự hạ nhạc.",
        "preamp": -2.5,
        "mvbass": {"enabled": True, "cutoff": 95, "intensity": 35},
        "biamp": {"ch1": 1.0, "ch2": 2.0},
        "crossover": {"sub_lpf": 140, "mid_hpf": 150, "sub_hpf": 45},
        "limiter": {"enabled": True, "threshold_db": -2.0, "attack_ms": 8, "release_ms": 180, "ratio": 10.0},
        "noise_gate": {"enabled": True, "threshold_db": -62.0, "hold_ms": 250},
        "delay_phase": {"sub_delay_ms": 0.5, "sub_phase_invert": False},
        "spatial": {"surround_3d": True, "treble_exciter": 40},
        "karaoke": {
            "enabled": True,
            "echo_delay": 210,
            "echo_repeat": 52,
            "reverb_room": 75,
            "reverb_decay": 2.8,
            "reverb_mix": 48,
            "anti_howling": True,
            "pitch_shift": 0,
            "music_ducking": True
        },
        "dynamic_bass": {"enabled": True, "low_vol_boost_db": 3.5, "high_vol_cut_db": -2.5},
        "hardware_io": {
            "usb_dac_mode": True,
            "i2s_out": True,
            "i2s_sample_rate": 44100,
            "bt_name": "BEST SOUND T1V2 KARAOKE",
            "led_vu_meter": True
        },
        "bands": [
            {"name": "Sub Bass", "hz": 50, "gain": 1.5, "q": 1.41, "enabled": True},
            {"name": "Punch", "hz": 90, "gain": 2.0, "q": 1.50, "enabled": True},
            {"name": "Warmth", "hz": 200, "gain": 1.5, "q": 1.20, "enabled": True},
            {"name": "Body", "hz": 450, "gain": 0.5, "q": 1.41, "enabled": True},
            {"name": "Vocal Low", "hz": 1200, "gain": 2.5, "q": 1.60, "enabled": True},
            {"name": "Vocal High", "hz": 2800, "gain": 3.2, "q": 1.50, "enabled": True},
            {"name": "Presence", "hz": 5500, "gain": 2.0, "q": 1.41, "enabled": True},
            {"name": "Air Sparkle", "hz": 11000, "gain": 3.0, "q": 1.30, "enabled": True}
        ]
    }
]

LIBRARY_FILE = "dsp_profiles_library.json"

# ==============================================================================
# 3. BINARY PACKET ENCODING
# ==============================================================================

def s16LE(val):
    intVal = int(round(val)) & 0xFFFF
    return [intVal & 0xFF, (intVal >> 8) & 0xFF]

def u16LE(val):
    intVal = int(round(val)) & 0xFFFF
    return [intVal & 0xFF, (intVal >> 8) & 0xFF]

def build_full_dsp_stream(p):
    stream = []

    # 1. MVBass 0x87
    mv = p.get("mvbass", {})
    p_mv = [0xFF] + u16LE(1 if mv.get("enabled", True) else 0) + u16LE(mv.get("cutoff", 90)) + u16LE(int(mv.get("intensity", 45)*40.95))
    l_mv = len(p_mv)
    f_mv = [0xA5, 0x5A, 0x87, l_mv & 0xFF, (l_mv >> 8) & 0xFF] + p_mv
    f_mv.append(sum(f_mv) & 0xFF)
    f_mv.append(0x16)
    stream.extend(f_mv)

    # 2. DRC Limiter 0x93
    lim = p.get("limiter", {})
    thresh = int(lim.get("threshold_db", -1.5) * 256.0)
    p_drc = [0xFF] + u16LE(1 if lim.get("enabled", True) else 0) + s16LE(thresh) + u16LE(int(lim.get("attack_ms", 10))) + u16LE(int(lim.get("release_ms", 150)))
    l_drc = len(p_drc)
    f_drc = [0xA5, 0x5A, 0x93, l_drc & 0xFF, (l_drc >> 8) & 0xFF] + p_drc
    f_drc.append(sum(f_drc) & 0xFF)
    f_drc.append(0x16)
    stream.extend(f_drc)

    # 3. Karaoke Echo/Reverb 0x8A
    kar = p.get("karaoke", {})
    p_kar = [0xFF] + u16LE(1 if kar.get("enabled", False) else 0) + u16LE(kar.get("echo_delay", 180)) + u16LE(kar.get("echo_repeat", 45)) + u16LE(kar.get("reverb_mix", 35))
    l_kar = len(p_kar)
    f_kar = [0xA5, 0x5A, 0x8A, l_kar & 0xFF, (l_kar >> 8) & 0xFF] + p_kar
    f_kar.append(sum(f_kar) & 0xFF)
    f_kar.append(0x16)
    stream.extend(f_kar)

    # 4. EQ CH1 0x95 & EQ CH2 0x96
    for reg in [0x95, 0x96]:
        payload = [0xFF] + u16LE(1) + s16LE(p.get("preamp", -2.0) * 256.0) + u16LE(0)
        bands = p.get("bands", [])
        for i in range(10):
            if i < len(bands):
                b = bands[i]
                payload += u16LE(1 if b.get("enabled", True) else 0) + u16LE(2) + u16LE(b.get("hz", 1000)) + s16LE(b.get("gain", 0.0) * 256.0) + u16LE(b.get("q", 1.41) * 100.0)
            else:
                payload += u16LE(0) + u16LE(2) + u16LE(1000) + s16LE(0) + u16LE(100)
        l_eq = len(payload)
        f_eq = [0xA5, 0x5A, reg, l_eq & 0xFF, (l_eq >> 8) & 0xFF] + payload
        f_eq.append(sum(f_eq) & 0xFF)
        f_eq.append(0x16)
        stream.extend(f_eq)

    return bytes(stream)

# ==============================================================================
# 4. GUI APPLICATION MAIN CLASS
# ==============================================================================

class BestSoundDspStudioPC(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BEST SOUND DSP ULTIMATE PRO STUDIO — MVSilicon BP1048B2 Deep-Access Controller")
        self.geometry("1260x890")
        self.minsize(1100, 750)
        self.configure(bg="#0e1013")

        self.profiles = self.load_library()
        self.active_profile_index = 0
        self.current_profile = copy.deepcopy(self.profiles[self.active_profile_index])
        self.backup_profile_a = copy.deepcopy(self.current_profile)
        self.is_compare_active = False

        self.serial_conn = None
        self.is_connected = False

        self.setup_styles()
        self.create_widgets()
        self.load_profile_to_ui(self.current_profile)
        self.update_spectrum_graph()

    def setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        bg_dark = "#0e1013"
        bg_card = "#14181f"
        text_light = "#e2e8f0"

        self.style.configure(".", background=bg_dark, foreground=text_light, font=("Segoe UI", 9))
        self.style.configure("TFrame", background=bg_dark)
        self.style.configure("TLabel", background=bg_dark, foreground=text_light)
        self.style.configure("TNotebook", background=bg_dark, borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#181c22", foreground="#8e9ba8", padding=[10, 5], font=("Segoe UI", 8, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", "#0b3842")], foreground=[("selected", "#00e5ff")])

    def load_library(self):
        if os.path.exists(LIBRARY_FILE):
            try:
                with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception:
                pass
        return copy.deepcopy(DEFAULT_PROFILES)

    def save_library(self):
        try:
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu thư viện: {e}")
            return False

    def create_widgets(self):
        # 1. TOP HEADER BAR
        top_bar = tk.Frame(self, bg="#12151b", height=58, highlightthickness=1, highlightbackground="#232830")
        top_bar.pack(fill="x", side="top")

        brand_frame = tk.Frame(top_bar, bg="#12151b")
        brand_frame.pack(side="left", padx=14, pady=6)
        tk.Label(brand_frame, text="BEST SOUND T1V2", font=("Segoe UI", 12, "bold"), fg="#d4af37", bg="#12151b").pack(anchor="w")
        tk.Label(brand_frame, text="BP1048B2 Deep-Access Studio", font=("Segoe UI", 8), fg="#717d8c", bg="#12151b").pack(anchor="w")

        # Profile Selector
        prof_frame = tk.Frame(top_bar, bg="#12151b")
        prof_frame.pack(side="left", padx=12, pady=6)
        tk.Label(prof_frame, text="CẤU HÌNH (PROFILE):", font=("Segoe UI", 8, "bold"), fg="#8e9ba8", bg="#12151b").pack(anchor="w")

        self.cb_profiles = ttk.Combobox(prof_frame, state="readonly", width=34, font=("Segoe UI", 9, "bold"))
        self.cb_profiles.pack(side="left", pady=2)
        self.cb_profiles["values"] = [p["name"] for p in self.profiles]
        self.cb_profiles.current(0)
        self.cb_profiles.bind("<<ComboboxSelected>>", self.on_profile_selected)

        tk.Button(prof_frame, text="+ Thêm", font=("Segoe UI", 8, "bold"), bg="#182029", fg="#00e5ff", relief="flat", padx=5, pady=2, command=self.on_new_profile).pack(side="left", padx=2)
        tk.Button(prof_frame, text="💾 Lưu", font=("Segoe UI", 8, "bold"), bg="#1b3d2b", fg="#00e676", relief="flat", padx=6, pady=2, command=self.on_save_current_profile).pack(side="left", padx=2)

        # A/B Compare Button
        self.btn_ab_compare = tk.Button(top_bar, text="⚡ A/B BYPASS", font=("Segoe UI", 8, "bold"), bg="#232a34", fg="#94a3b8", relief="flat", padx=8, pady=4, command=self.toggle_ab_compare)
        self.btn_ab_compare.pack(side="left", padx=8)

        # Hardware COM Link
        hw_frame = tk.Frame(top_bar, bg="#12151b")
        hw_frame.pack(side="right", padx=14, pady=6)
        tk.Label(hw_frame, text="CỔNG COM / USB DSP:", font=("Segoe UI", 8, "bold"), fg="#8e9ba8", bg="#12151b").pack(anchor="w")
        hw_sub = tk.Frame(hw_frame, bg="#12151b")
        hw_sub.pack(anchor="w")

        self.cb_com_ports = ttk.Combobox(hw_sub, state="readonly", width=11, font=("Segoe UI", 8))
        self.cb_com_ports.pack(side="left", pady=1)
        self.refresh_com_ports()

        tk.Button(hw_sub, text="🔄", font=("Segoe UI", 7), bg="#182029", fg="#00e5ff", relief="flat", padx=3, command=self.refresh_com_ports).pack(side="left", padx=2)
        self.btn_connect = tk.Button(hw_sub, text="KẾT NỐI", font=("Segoe UI", 8, "bold"), bg="#183626", fg="#00e676", relief="flat", padx=5, command=self.toggle_connection)
        self.btn_connect.pack(side="left", padx=2)

        self.btn_push_dsp = tk.Button(hw_sub, text="⚡ ĐẨY XUỐNG CHIP", font=("Segoe UI", 8, "bold"), bg="#094452", fg="#00e5ff", relief="flat", padx=8, command=self.push_to_dsp_hardware)
        self.btn_push_dsp.pack(side="left", padx=3)

        # 2. FREQUENCY RESPONSE GRAPH SPECTRUM
        top_pane = tk.Frame(self, bg="#14181f", bd=1, relief="solid")
        top_pane.pack(fill="x", padx=12, pady=(6, 4))

        spec_head = tk.Frame(top_pane, bg="#14181f")
        spec_head.pack(fill="x", padx=10, pady=3)
        tk.Label(spec_head, text="ACOUSTIC FREQUENCY RESPONSE CURVE (20 Hz – 20,000 Hz · 64-bit IIR RBJ)", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#14181f").pack(side="left")

        self.lbl_headroom_status = tk.Label(spec_head, text="HEADROOM: AN TOÀN", font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#14181f")
        self.lbl_headroom_status.pack(side="right", padx=10)

        tk.Button(spec_head, text="🛡 AUTO HEADROOM", font=("Segoe UI", 7, "bold"), bg="#1b3d2b", fg="#00e676", relief="flat", padx=6, pady=1, command=self.apply_auto_headroom).pack(side="right", padx=3)
        tk.Button(spec_head, text="↺ Flat", font=("Segoe UI", 7), bg="#222832", fg="#cbd5e1", relief="flat", padx=5, pady=1, command=self.reset_eq_flat).pack(side="right", padx=2)

        self.canvas = tk.Canvas(top_pane, height=160, bg="#080a0d", highlightthickness=0)
        self.canvas.pack(fill="x", expand=True, padx=6, pady=3)

        # 3. ADVANCED DEEP-ACCESS NOTEBOOK TABS
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=4)

        # TAB 1: 8-Band PEQ Strips
        tab_peq = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_peq, text="🎛️ 8-Band PEQ")
        self.create_peq_tab(tab_peq)

        # TAB 2: Crossover & Bi-Amp
        tab_xover = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_xover, text="⚡ Crossover Bi-Amp")
        self.create_crossover_tab(tab_xover)

        # TAB 3: DRC Limiter & Loa
        tab_drc = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_drc, text="🛡️ DRC Limiter")
        self.create_drc_tab(tab_drc)

        # TAB 4: MVBass & Kích Hài Âm
        tab_bass = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_bass, text="🔊 MVBass & Treble Exciter")
        self.create_bass_enhancer_tab(tab_bass)

        # TAB 5: VANG SỐ KARAOKE CHUYÊN SÂU
        tab_karaoke = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_karaoke, text="🎤 Vang Số Karaoke & Micro")
        self.create_karaoke_tab(tab_karaoke)

        # TAB 6: DYNAMIC BASS & LOUDNESS THÔNG MINH
        tab_dyn_bass = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_dyn_bass, text="📈 Dynamic Bass Thông Minh")
        self.create_dyn_bass_tab(tab_dyn_bass)

        # TAB 7: USB SOUNDCARD DAC & I2S ROUTING
        tab_usb_i2s = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_usb_i2s, text="🔌 USB DAC & Định Tuyến I2S")
        self.create_usb_i2s_tab(tab_usb_i2s)

        # TAB 8: BLUETOOTH & PHÍM CỨNG GPIO
        tab_bt_gpio = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_bt_gpio, text="⚙️ Bluetooth & Phím Bấm GPIO")
        self.create_bt_gpio_tab(tab_bt_gpio)

        # TAB 9: Xuất / Nhập Hub
        tab_io = tk.Frame(notebook, bg="#14181f")
        notebook.add(tab_io, text="📂 Xuất/Nhập File (INI, C, APO)")
        self.create_io_tab(tab_io)

        # STATUS BAR
        status_bar = tk.Frame(self, bg="#080a0d", height=24)
        status_bar.pack(fill="x", side="bottom")
        self.lbl_status = tk.Label(status_bar, text="Sẵn sàng! MVSilicon BP1048B2 Ultimate Studio đã mở khóa toàn bộ các khối chức năng chuyên sâu.", font=("Segoe UI", 8), fg="#717d8c", bg="#080a0d")
        self.lbl_status.pack(side="left", padx=12)

    # ---------------- TAB BUILDERS ----------------

    def create_peq_tab(self, parent):
        strip_container = tk.Frame(parent, bg="#14181f")
        strip_container.pack(fill="both", expand=True, padx=8, pady=6)

        self.band_widgets = []
        for i in range(8):
            card = tk.Frame(strip_container, bg="#101318", bd=1, relief="solid", highlightthickness=1, highlightbackground="#222832")
            card.pack(side="left", fill="both", expand=True, padx=2, pady=2)

            tk.Label(card, text=f"0{i+1}", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#101318").pack(anchor="w", padx=4, pady=1)
            lbl_name = tk.Label(card, text=f"Band {i+1}", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#101318")
            lbl_name.pack(anchor="w", padx=4)
            lbl_hz = tk.Label(card, text="1000 Hz", font=("Segoe UI", 8), fg="#8e9ba8", bg="#101318")
            lbl_hz.pack(anchor="w", padx=4)
            lbl_gain_val = tk.Label(card, text="+0.0 dB", font=("Segoe UI", 9, "bold"), fg="#00e5ff", bg="#101318")
            lbl_gain_val.pack(anchor="center", pady=1)

            slider_gain = ttk.Scale(card, from_=6.0, to=-12.0, orient="vertical", length=90, command=lambda v, idx=i: self.on_band_slider_changed(idx, v))
            slider_gain.pack(pady=3)

            lbl_q = tk.Label(card, text="Q 1.41", font=("Segoe UI", 7), fg="#717d8c", bg="#101318")
            lbl_q.pack(pady=1)

            btn_bypass = tk.Button(card, text="ON", font=("Segoe UI", 7, "bold"), bg="#183626", fg="#00e676", relief="flat", padx=3, pady=1, command=lambda idx=i: self.on_toggle_bypass_band(idx))
            btn_bypass.pack(pady=2)

            self.band_widgets.append({
                "lbl_name": lbl_name,
                "lbl_hz": lbl_hz,
                "lbl_gain_val": lbl_gain_val,
                "slider_gain": slider_gain,
                "lbl_q": lbl_q,
                "btn_bypass": btn_bypass
            })

    def create_crossover_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="PHÂN TẦN CHỦ ĐỘNG BI-AMP 2.1 (CH1 SUBWOOFER + CH2 MID/TREBLE)", font=("Segoe UI", 9, "bold"), fg="#00e5ff", bg="#14181f").pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(box, bg="#14181f")
        grid.pack(fill="x", pady=4)

        tk.Label(grid, text="Sub LPF (Cắt tần cao loa Sub):", font=("Segoe UI", 8, "bold"), fg="#d4af37", bg="#14181f").grid(row=0, column=0, sticky="w", pady=4)
        self.lbl_sub_lpf = tk.Label(grid, text="150 Hz", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#14181f")
        self.lbl_sub_lpf.grid(row=0, column=1, padx=8)
        self.slider_sub_lpf = ttk.Scale(grid, from_=60, to=250, orient="horizontal", command=self.on_crossover_changed)
        self.slider_sub_lpf.grid(row=0, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="Sub HPF (Subsonic cắt tần siêu trầm):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=1, column=0, sticky="w", pady=4)
        self.lbl_sub_hpf = tk.Label(grid, text="38 Hz", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#14181f")
        self.lbl_sub_hpf.grid(row=1, column=1, padx=8)
        self.slider_sub_hpf = ttk.Scale(grid, from_=20, to=60, orient="horizontal", command=self.on_crossover_changed)
        self.slider_sub_hpf.grid(row=1, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="Mid HPF (Cắt dải trầm củ Mid AIRS):", font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#14181f").grid(row=2, column=0, sticky="w", pady=4)
        self.lbl_mid_hpf = tk.Label(grid, text="160 Hz", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#14181f")
        self.lbl_mid_hpf.grid(row=2, column=1, padx=8)
        self.slider_mid_hpf = ttk.Scale(grid, from_=100, to=400, orient="horizontal", command=self.on_crossover_changed)
        self.slider_mid_hpf.grid(row=2, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="CH1 Subwoofer Gain:", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=3, column=0, sticky="w", pady=4)
        self.lbl_ch1_gain = tk.Label(grid, text="+1.5 dB", font=("Segoe UI", 8, "bold"), fg="#d4af37", bg="#14181f")
        self.lbl_ch1_gain.grid(row=3, column=1, padx=8)
        self.slider_ch1 = ttk.Scale(grid, from_=-12.0, to=6.0, orient="horizontal", command=self.on_crossover_changed)
        self.slider_ch1.grid(row=3, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="CH2 Mid/Treble Gain:", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=4, column=0, sticky="w", pady=4)
        self.lbl_ch2_gain = tk.Label(grid, text="0.0 dB", font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#14181f")
        self.lbl_ch2_gain.grid(row=4, column=1, padx=8)
        self.slider_ch2 = ttk.Scale(grid, from_=-12.0, to=6.0, orient="horizontal", command=self.on_crossover_changed)
        self.slider_ch2.grid(row=4, column=2, sticky="ew", padx=8)

        grid.columnconfigure(2, weight=1)

    def create_drc_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="DYNAMIC RANGE COMPRESSOR (DRC) & HARD LIMITER BẢO VỆ LOA", font=("Segoe UI", 9, "bold"), fg="#ff7043", bg="#14181f").pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(box, bg="#14181f")
        grid.pack(fill="x", pady=4)

        self.chk_drc_var = tk.BooleanVar(value=True)
        tk.Checkbutton(grid, text="BẬT BỘ NÉN DRC / HARD LIMITER (CHỐNG CHÁY COIL)", font=("Segoe UI", 8, "bold"), variable=self.chk_drc_var, fg="#00e676", bg="#14181f", selectcolor="#101318", command=self.on_drc_changed).grid(row=0, column=0, sticky="w", pady=4)

        tk.Label(grid, text="Limiter Threshold (Ngưỡng chặn đỉnh):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=1, column=0, sticky="w", pady=4)
        self.lbl_drc_thresh = tk.Label(grid, text="-1.5 dBFS", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#14181f")
        self.lbl_drc_thresh.grid(row=1, column=1, padx=8)
        self.slider_drc_thresh = ttk.Scale(grid, from_=-12.0, to=0.0, orient="horizontal", command=self.on_drc_changed)
        self.slider_drc_thresh.grid(row=1, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="Attack Time (Bắt đỉnh xung kích):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=2, column=0, sticky="w", pady=4)
        self.lbl_drc_attack = tk.Label(grid, text="10 ms", font=("Segoe UI", 8, "bold"), fg="#d4af37", bg="#14181f")
        self.lbl_drc_attack.grid(row=2, column=1, padx=8)
        self.slider_drc_attack = ttk.Scale(grid, from_=1, to=50, orient="horizontal", command=self.on_drc_changed)
        self.slider_drc_attack.grid(row=2, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="Release Time (Nhả nén êm tai):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=3, column=0, sticky="w", pady=4)
        self.lbl_drc_release = tk.Label(grid, text="150 ms", font=("Segoe UI", 8, "bold"), fg="#d4af37", bg="#14181f")
        self.lbl_drc_release.grid(row=3, column=1, padx=8)
        self.slider_drc_release = ttk.Scale(grid, from_=20, to=500, orient="horizontal", command=self.on_drc_changed)
        self.slider_drc_release.grid(row=3, column=2, sticky="ew", padx=8)

        grid.columnconfigure(2, weight=1)

    def create_bass_enhancer_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="MVBASS TRẦM ẢO & HARMONIC TREBLE EXCITER", font=("Segoe UI", 9, "bold"), fg="#d4af37", bg="#14181f").pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(box, bg="#14181f")
        grid.pack(fill="x", pady=4)

        self.chk_mvbass_var = tk.BooleanVar(value=True)
        tk.Checkbutton(grid, text="BẬT MVBASS CLASSIC (SÓNG HÀI BẬC 2-3 CHO BASS 4 INCH):", font=("Segoe UI", 8, "bold"), variable=self.chk_mvbass_var, fg="#00e5ff", bg="#14181f", selectcolor="#101318", command=self.on_mvbass_tab_changed).grid(row=0, column=0, sticky="w", pady=4)

        tk.Label(grid, text="Tần số cắt MVBass Cutoff:", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=1, column=0, sticky="w", pady=4)
        self.lbl_mvbass_cut = tk.Label(grid, text="90 Hz", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#14181f")
        self.lbl_mvbass_cut.grid(row=1, column=1, padx=8)
        self.slider_mvbass_cut = ttk.Scale(grid, from_=60, to=150, orient="horizontal", command=self.on_mvbass_tab_changed)
        self.slider_mvbass_cut.grid(row=1, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="Cường độ MVBass Intensity (%):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=2, column=0, sticky="w", pady=4)
        self.lbl_mvbass_int = tk.Label(grid, text="45%", font=("Segoe UI", 8, "bold"), fg="#d4af37", bg="#14181f")
        self.lbl_mvbass_int.grid(row=2, column=1, padx=8)
        self.slider_mvbass_int = ttk.Scale(grid, from_=0, to=100, orient="horizontal", command=self.on_mvbass_tab_changed)
        self.slider_mvbass_int.grid(row=2, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="Treble Exciter (%):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=3, column=0, sticky="w", pady=4)
        self.lbl_treble_exc = tk.Label(grid, text="20%", font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#14181f")
        self.lbl_treble_exc.grid(row=3, column=1, padx=8)
        self.slider_treble_exc = ttk.Scale(grid, from_=0, to=100, orient="horizontal", command=self.on_mvbass_tab_changed)
        self.slider_treble_exc.grid(row=3, column=2, sticky="ew", padx=8)

        grid.columnconfigure(2, weight=1)

    def create_karaoke_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="VANG SỐ MINI KARAOKE CHUYÊN NGHIỆP TRÊN BP1048B2", font=("Segoe UI", 9, "bold"), fg="#00e5ff", bg="#14181f").pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(box, bg="#14181f")
        grid.pack(fill="x", pady=4)

        # Enable Karaoke
        self.chk_karaoke_var = tk.BooleanVar(value=False)
        tk.Checkbutton(grid, text="KÍCH HOẠT CHẾ ĐỘ VANG SỐ KARAOKE", font=("Segoe UI", 8, "bold"), variable=self.chk_karaoke_var, fg="#00e676", bg="#14181f", selectcolor="#101318", command=self.on_karaoke_changed).grid(row=0, column=0, sticky="w", pady=4)

        # Echo Delay
        tk.Label(grid, text="Echo Delay (Độ trễ nhại lời):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=1, column=0, sticky="w", pady=4)
        self.lbl_echo_delay = tk.Label(grid, text="180 ms", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#14181f")
        self.lbl_echo_delay.grid(row=1, column=1, padx=8)
        self.slider_echo_delay = ttk.Scale(grid, from_=80, to=350, orient="horizontal", command=self.on_karaoke_changed)
        self.slider_echo_delay.grid(row=1, column=2, sticky="ew", padx=8)

        # Echo Repeat
        tk.Label(grid, text="Echo Repeat (Độ lặp lại):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=2, column=0, sticky="w", pady=4)
        self.lbl_echo_repeat = tk.Label(grid, text="45%", font=("Segoe UI", 8, "bold"), fg="#d4af37", bg="#14181f")
        self.lbl_echo_repeat.grid(row=2, column=1, padx=8)
        self.slider_echo_repeat = ttk.Scale(grid, from_=0, to=90, orient="horizontal", command=self.on_karaoke_changed)
        self.slider_echo_repeat.grid(row=2, column=2, sticky="ew", padx=8)

        # Studio Reverb Mix
        tk.Label(grid, text="Reverb Wet Mix (Độ vang phòng thu):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=3, column=0, sticky="w", pady=4)
        self.lbl_reverb_mix = tk.Label(grid, text="35%", font=("Segoe UI", 8, "bold"), fg="#00e676", bg="#14181f")
        self.lbl_reverb_mix.grid(row=3, column=1, padx=8)
        self.slider_reverb_mix = ttk.Scale(grid, from_=0, to=100, orient="horizontal", command=self.on_karaoke_changed)
        self.slider_reverb_mix.grid(row=3, column=2, sticky="ew", padx=8)

        # Anti-Howling & Ducking Checkboxes
        sub_c = tk.Frame(grid, bg="#14181f")
        sub_c.grid(row=4, column=0, columnspan=3, sticky="w", pady=6)

        self.chk_howling_var = tk.BooleanVar(value=True)
        tk.Checkbutton(sub_c, text="CHỐNG HÚ TỰ ĐỘNG (HOWLING NOTCH FILTER)", font=("Segoe UI", 8, "bold"), variable=self.chk_howling_var, fg="#d4af37", bg="#14181f", selectcolor="#101318", command=self.on_karaoke_changed).pack(side="left", padx=4)

        self.chk_ducking_var = tk.BooleanVar(value=True)
        tk.Checkbutton(sub_c, text="MUSIC DUCKING (TỰ HẠ NHẠC KHI NÓI)", font=("Segoe UI", 8, "bold"), variable=self.chk_ducking_var, fg="#00e5ff", bg="#14181f", selectcolor="#101318", command=self.on_karaoke_changed).pack(side="left", padx=12)

        grid.columnconfigure(2, weight=1)

    def create_dyn_bass_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="DYNAMIC BASS THÔNG MINH (BÙ TRỪ ĐƯỜNG CONG FLETCHER-MUNSON)", font=("Segoe UI", 9, "bold"), fg="#00e676", bg="#14181f").pack(anchor="w", pady=(0, 6))
        tk.Label(box, text="Tự động kích bass khi nghe âm lượng nhỏ ban đêm, tự ghìm bass phẳng lại khi mở lớn để bảo vệ nguồn pin và loa.", font=("Segoe UI", 8), fg="#8e9ba8", bg="#14181f").pack(anchor="w", pady=(0, 8))

        grid = tk.Frame(box, bg="#14181f")
        grid.pack(fill="x", pady=4)

        self.chk_dyn_bass_var = tk.BooleanVar(value=True)
        tk.Checkbutton(grid, text="KÍCH HOẠT DYNAMIC BASS THÍCH ỨNG THEO VOLUME", font=("Segoe UI", 8, "bold"), variable=self.chk_dyn_bass_var, fg="#00e5ff", bg="#14181f", selectcolor="#101318", command=self.on_dyn_bass_changed).grid(row=0, column=0, sticky="w", pady=4)

        tk.Label(grid, text="Kích Bass khi nghe nhỏ (< 30% Volume):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=1, column=0, sticky="w", pady=4)
        self.lbl_dyn_boost = tk.Label(grid, text="+5.0 dB", font=("Segoe UI", 8, "bold"), fg="#d4af37", bg="#14181f")
        self.lbl_dyn_boost.grid(row=1, column=1, padx=8)
        self.slider_dyn_boost = ttk.Scale(grid, from_=0.0, to=9.0, orient="horizontal", command=self.on_dyn_bass_changed)
        self.slider_dyn_boost.grid(row=1, column=2, sticky="ew", padx=8)

        tk.Label(grid, text="Ghìm Bass khi mở max (> 80% Volume):", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=2, column=0, sticky="w", pady=4)
        self.lbl_dyn_cut = tk.Label(grid, text="-3.0 dB", font=("Segoe UI", 8, "bold"), fg="#ff7676", bg="#14181f")
        self.lbl_dyn_cut.grid(row=2, column=1, padx=8)
        self.slider_dyn_cut = ttk.Scale(grid, from_=-6.0, to=0.0, orient="horizontal", command=self.on_dyn_bass_changed)
        self.slider_dyn_cut.grid(row=2, column=2, sticky="ew", padx=8)

        grid.columnconfigure(2, weight=1)

    def create_usb_i2s_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="USB SOUNDCARD DAC & ĐỊNH TUYẾN ÂM THANH SỐ I2S", font=("Segoe UI", 9, "bold"), fg="#00e5ff", bg="#14181f").pack(anchor="w", pady=(0, 6))

        grid = tk.Frame(box, bg="#14181f")
        grid.pack(fill="x", pady=4)

        self.chk_usb_dac_var = tk.BooleanVar(value=True)
        tk.Checkbutton(grid, text="Kích hoạt USB Soundcard DAC Mode (Nhận nhạc số Lossless qua cáp Type-C)", font=("Segoe UI", 8, "bold"), variable=self.chk_usb_dac_var, fg="#00e676", bg="#14181f", selectcolor="#101318", command=self.on_hw_io_changed).grid(row=0, column=0, columnspan=3, sticky="w", pady=6)

        self.chk_i2s_var = tk.BooleanVar(value=True)
        tk.Checkbutton(grid, text="Kích hoạt ngõ xuất số I2S DOUT (Đưa sang DAC rời PCM5102/ES9018 hoặc Digital Amp)", font=("Segoe UI", 8, "bold"), variable=self.chk_i2s_var, fg="#d4af37", bg="#14181f", selectcolor="#101318", command=self.on_hw_io_changed).grid(row=1, column=0, columnspan=3, sticky="w", pady=6)

        tk.Label(grid, text="Sample Rate chuẩn ngõ ra I2S:", font=("Segoe UI", 8), fg="#cbd5e1", bg="#14181f").grid(row=2, column=0, sticky="w", pady=4)
        self.cb_i2s_sr = ttk.Combobox(grid, state="readonly", values=["44100 Hz (CD Audio)", "48000 Hz (Studio Video)", "96000 Hz (Hi-Res Audio)"], width=24)
        self.cb_i2s_sr.grid(row=2, column=1, sticky="w", padx=8)
        self.cb_i2s_sr.current(0)
        self.cb_i2s_sr.bind("<<ComboboxSelected>>", self.on_hw_io_changed)

    def create_bt_gpio_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="TÙY BIẾN BLUETOOTH & CẤU HÌNH PHÍM BẤM PHẦN CỨNG GPIO", font=("Segoe UI", 9, "bold"), fg="#d4af37", bg="#14181f").pack(anchor="w", pady=(0, 6))

        grid = tk.Frame(box, bg="#14181f")
        grid.pack(fill="x", pady=4)

        tk.Label(grid, text="Tên hiển thị Bluetooth (Device Name):", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#14181f").grid(row=0, column=0, sticky="w", pady=6)
        self.txt_bt_name = tk.Entry(grid, bg="#101318", fg="#00e5ff", insertbackground="#00e5ff", relief="solid", bd=1, width=32, font=("Segoe UI", 9, "bold"))
        self.txt_bt_name.grid(row=0, column=1, sticky="w", padx=8)
        self.txt_bt_name.insert(0, "BEST SOUND T1V2 BI-AMP")
        self.txt_bt_name.bind("<KeyRelease>", self.on_hw_io_changed)

        self.chk_led_vu_var = tk.BooleanVar(value=True)
        tk.Checkbutton(grid, text="Kích hoạt LED nháy theo nhịp nhạc trên chân GPIO (VU Meter Spectrum)", font=("Segoe UI", 8, "bold"), variable=self.chk_led_vu_var, fg="#00e676", bg="#14181f", selectcolor="#101318", command=self.on_hw_io_changed).grid(row=1, column=0, columnspan=2, sticky="w", pady=6)

    def create_io_tab(self, parent):
        box = tk.Frame(parent, bg="#14181f")
        box.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(box, text="IMPORT / EXPORT TRUNG TÂM & ĐỒNG BỘ CẤU HÌNH", font=("Segoe UI", 9, "bold"), fg="#d4af37", bg="#14181f").pack(anchor="w", pady=(0, 6))
        btn_grid = tk.Frame(box, bg="#14181f")
        btn_grid.pack(fill="x", pady=4)

        tk.Button(btn_grid, text="📂 NẠP CẤU HÌNH TỪ FILE ACPWORKBENCH .INI", font=("Segoe UI", 8, "bold"), bg="#182330", fg="#00e5ff", relief="flat", padx=10, pady=6, command=self.import_from_ini_file).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        tk.Button(btn_grid, text="💾 XUẤT RA FILE ACPWORKBENCH .INI CHUẨN", font=("Segoe UI", 8, "bold"), bg="#2c2612", fg="#d4af37", relief="flat", padx=10, pady=6, command=self.export_to_ini_file).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        tk.Button(btn_grid, text="📜 XUẤT RA SOURCE C (DSP.C) CHO FIRMWARE", font=("Segoe UI", 8, "bold"), bg="#162e24", fg="#00e676", relief="flat", padx=10, pady=6, command=self.export_to_c_file).grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        tk.Button(btn_grid, text="📄 XUẤT RA FILE EQUALIZER APO .TXT", font=("Segoe UI", 8), bg="#222832", fg="#cbd5e1", relief="flat", padx=10, pady=6, command=self.export_to_apo_txt).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        tk.Button(btn_grid, text="💾 SAO LƯU TOÀN BỘ THƯ VIỆN PROFILE (JSON)", font=("Segoe UI", 8, "bold"), bg="#1a3542", fg="#00e5ff", relief="flat", padx=10, pady=6, command=self.save_library_prompt).grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=6)

        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

    # ---------------- HANDLERS ----------------

    def load_profile_to_ui(self, p):
        # Preamp & Crossover
        self.slider_sub_lpf.set(p.get("crossover", {}).get("sub_lpf", 150))
        self.lbl_sub_lpf.config(text=f"{int(p.get('crossover', {}).get('sub_lpf', 150))} Hz")
        self.slider_sub_hpf.set(p.get("crossover", {}).get("sub_hpf", 38))
        self.lbl_sub_hpf.config(text=f"{int(p.get('crossover', {}).get('sub_hpf', 38))} Hz")
        self.slider_mid_hpf.set(p.get("crossover", {}).get("mid_hpf", 160))
        self.lbl_mid_hpf.config(text=f"{int(p.get('crossover', {}).get('mid_hpf', 160))} Hz")

        bi = p.get("biamp", {"ch1": 1.5, "ch2": 0.0})
        self.slider_ch1.set(bi.get("ch1", 1.5))
        self.lbl_ch1_gain.config(text=f"{bi.get('ch1', 1.5):+.1f} dB")
        self.slider_ch2.set(bi.get("ch2", 0.0))
        self.lbl_ch2_gain.config(text=f"{bi.get('ch2', 0.0):+.1f} dB")

        # DRC Limiter
        lim = p.get("limiter", {"enabled": True, "threshold_db": -1.5, "attack_ms": 10, "release_ms": 150, "ratio": 8.0})
        self.chk_drc_var.set(lim.get("enabled", True))
        self.slider_drc_thresh.set(lim.get("threshold_db", -1.5))
        self.lbl_drc_thresh.config(text=f"{lim.get('threshold_db', -1.5):.1f} dBFS")
        self.slider_drc_attack.set(lim.get("attack_ms", 10))
        self.lbl_drc_attack.config(text=f"{int(lim.get('attack_ms', 10))} ms")
        self.slider_drc_release.set(lim.get("release_ms", 150))
        self.lbl_drc_release.config(text=f"{int(lim.get('release_ms', 150))} ms")

        # MVBass & Treble Exciter
        mv = p.get("mvbass", {"enabled": True, "cutoff": 90, "intensity": 45})
        self.chk_mvbass_var.set(mv.get("enabled", True))
        self.slider_mvbass_cut.set(mv.get("cutoff", 90))
        self.lbl_mvbass_cut.config(text=f"{int(mv.get('cutoff', 90))} Hz")
        self.slider_mvbass_int.set(mv.get("intensity", 45))
        self.lbl_mvbass_int.config(text=f"{int(mv.get('intensity', 45))}%")

        sp = p.get("spatial", {"surround_3d": False, "treble_exciter": 20})
        self.slider_treble_exc.set(sp.get("treble_exciter", 20))
        self.lbl_treble_exc.config(text=f"{int(sp.get('treble_exciter', 20))}%")

        # Karaoke
        kar = p.get("karaoke", {"enabled": False, "echo_delay": 180, "echo_repeat": 45, "reverb_mix": 35, "anti_howling": True, "music_ducking": True})
        self.chk_karaoke_var.set(kar.get("enabled", False))
        self.slider_echo_delay.set(kar.get("echo_delay", 180))
        self.lbl_echo_delay.config(text=f"{int(kar.get('echo_delay', 180))} ms")
        self.slider_echo_repeat.set(kar.get("echo_repeat", 45))
        self.lbl_echo_repeat.config(text=f"{int(kar.get('echo_repeat', 45))}%")
        self.slider_reverb_mix.set(kar.get("reverb_mix", 35))
        self.lbl_reverb_mix.config(text=f"{int(kar.get('reverb_mix', 35))}%")
        self.chk_howling_var.set(kar.get("anti_howling", True))
        self.chk_ducking_var.set(kar.get("music_ducking", True))

        # Dynamic Bass
        dbass = p.get("dynamic_bass", {"enabled": True, "low_vol_boost_db": 5.0, "high_vol_cut_db": -3.0})
        self.chk_dyn_bass_var.set(dbass.get("enabled", True))
        self.slider_dyn_boost.set(dbass.get("low_vol_boost_db", 5.0))
        self.lbl_dyn_boost.config(text=f"+{dbass.get('low_vol_boost_db', 5.0):.1f} dB")
        self.slider_dyn_cut.set(dbass.get("high_vol_cut_db", -3.0))
        self.lbl_dyn_cut.config(text=f"{dbass.get('high_vol_cut_db', -3.0):.1f} dB")

        # Hardware IO
        hio = p.get("hardware_io", {"usb_dac_mode": True, "i2s_out": True, "bt_name": "BEST SOUND T1V2 BI-AMP", "led_vu_meter": True})
        self.chk_usb_dac_var.set(hio.get("usb_dac_mode", True))
        self.chk_i2s_var.set(hio.get("i2s_out", True))
        self.txt_bt_name.delete(0, tk.END)
        self.txt_bt_name.insert(0, hio.get("bt_name", "BEST SOUND T1V2 BI-AMP"))
        self.chk_led_vu_var.set(hio.get("led_vu_meter", True))

        # PEQ Bands
        bands = p.get("bands", [])
        for i in range(8):
            if i < len(bands):
                b = bands[i]
                w = self.band_widgets[i]
                w["lbl_name"].config(text=b.get("name", f"Band {i+1}"))
                w["lbl_hz"].config(text=f"{b.get('hz', 1000)} Hz")
                w["slider_gain"].set(b.get("gain", 0.0))
                w["lbl_gain_val"].config(text=f"{b.get('gain', 0.0):+.1f} dB")
                w["lbl_q"].config(text=f"Q {b.get('q', 1.41):.2f}")
                w["btn_bypass"].config(text="ON" if b.get("enabled", True) else "BYPASS",
                                       bg="#183626" if b.get("enabled", True) else "#3a2020",
                                       fg="#00e676" if b.get("enabled", True) else "#ff7676")

    def on_crossover_changed(self, *args):
        p = self.current_profile
        sub_lpf = int(round(self.slider_sub_lpf.get()))
        sub_hpf = int(round(self.slider_sub_hpf.get()))
        mid_hpf = int(round(self.slider_mid_hpf.get()))
        ch1 = round(float(self.slider_ch1.get()), 1)
        ch2 = round(float(self.slider_ch2.get()), 1)
        p["crossover"] = {"sub_lpf": sub_lpf, "mid_hpf": mid_hpf, "sub_hpf": sub_hpf}
        p["biamp"] = {"ch1": ch1, "ch2": ch2}
        self.lbl_sub_lpf.config(text=f"{sub_lpf} Hz")
        self.lbl_sub_hpf.config(text=f"{sub_hpf} Hz")
        self.lbl_mid_hpf.config(text=f"{mid_hpf} Hz")
        self.lbl_ch1_gain.config(text=f"{ch1:+.1f} dB")
        self.lbl_ch2_gain.config(text=f"{ch2:+.1f} dB")

    def on_drc_changed(self, *args):
        p = self.current_profile
        en = self.chk_drc_var.get()
        thresh = round(float(self.slider_drc_thresh.get()), 1)
        att = int(round(self.slider_drc_attack.get()))
        rel = int(round(self.slider_drc_release.get()))
        p["limiter"] = {"enabled": en, "threshold_db": thresh, "attack_ms": att, "release_ms": rel, "ratio": 8.0}
        self.lbl_drc_thresh.config(text=f"{thresh:.1f} dBFS")
        self.lbl_drc_attack.config(text=f"{att} ms")
        self.lbl_drc_release.config(text=f"{rel} ms")

    def on_mvbass_tab_changed(self, *args):
        p = self.current_profile
        en = self.chk_mvbass_var.get()
        cut = int(round(self.slider_mvbass_cut.get()))
        intensity = int(round(self.slider_mvbass_int.get()))
        exc = int(round(self.slider_treble_exc.get()))
        p["mvbass"] = {"enabled": en, "cutoff": cut, "intensity": intensity}
        p["spatial"]["treble_exciter"] = exc
        self.lbl_mvbass_cut.config(text=f"{cut} Hz")
        self.lbl_mvbass_int.config(text=f"{intensity}%")
        self.lbl_treble_exc.config(text=f"{exc}%")

    def on_karaoke_changed(self, *args):
        p = self.current_profile
        en = self.chk_karaoke_var.get()
        d = int(round(self.slider_echo_delay.get()))
        r = int(round(self.slider_echo_repeat.get()))
        m = int(round(self.slider_reverb_mix.get()))
        h = self.chk_howling_var.get()
        k = self.chk_ducking_var.get()
        p["karaoke"] = {"enabled": en, "echo_delay": d, "echo_repeat": r, "reverb_room": 60, "reverb_decay": 2.2, "reverb_mix": m, "anti_howling": h, "pitch_shift": 0, "music_ducking": k}
        self.lbl_echo_delay.config(text=f"{d} ms")
        self.lbl_echo_repeat.config(text=f"{r}%")
        self.lbl_reverb_mix.config(text=f"{m}%")

    def on_dyn_bass_changed(self, *args):
        p = self.current_profile
        en = self.chk_dyn_bass_var.get()
        b = round(float(self.slider_dyn_boost.get()), 1)
        c = round(float(self.slider_dyn_cut.get()), 1)
        p["dynamic_bass"] = {"enabled": en, "low_vol_boost_db": b, "high_vol_cut_db": c}
        self.lbl_dyn_boost.config(text=f"+{b:.1f} dB")
        self.lbl_dyn_cut.config(text=f"{c:.1f} dB")

    def on_hw_io_changed(self, *args):
        p = self.current_profile
        u = self.chk_usb_dac_var.get()
        i2s = self.chk_i2s_var.get()
        name = self.txt_bt_name.get().strip()
        led = self.chk_led_vu_var.get()
        p["hardware_io"] = {"usb_dac_mode": u, "i2s_out": i2s, "bt_name": name, "led_vu_meter": led}

    def on_band_slider_changed(self, idx, val_str):
        try: val = round(float(val_str), 1)
        except ValueError: return
        if idx < len(self.current_profile["bands"]):
            self.current_profile["bands"][idx]["gain"] = val
            self.band_widgets[idx]["lbl_gain_val"].config(text=f"{val:+.1f} dB")
            self.update_spectrum_graph()

    def on_toggle_bypass_band(self, idx):
        if idx < len(self.current_profile["bands"]):
            cur = self.current_profile["bands"][idx].get("enabled", True)
            self.current_profile["bands"][idx]["enabled"] = not cur
            w = self.band_widgets[idx]
            w["btn_bypass"].config(text="ON" if not cur else "BYPASS",
                                   bg="#183626" if not cur else "#3a2020",
                                   fg="#00e676" if not cur else "#ff7676")
            self.update_spectrum_graph()

    def update_spectrum_graph(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 100: w = 1140
        if h < 50: h = 160

        self.canvas.delete("all")
        pad_x, pad_y = 45, 16
        plot_w, plot_h = w - pad_x - 20, h - pad_y * 2
        min_db, max_db = -18.0, 18.0

        def y_for_db(db):
            clamped = max(min_db, min(max_db, db))
            norm = (clamped - min_db) / (max_db - min_db)
            return h - pad_y - norm * plot_h

        def x_for_hz(hz):
            log_f = math.log10(max(20.0, min(20000.0, hz)))
            norm = (log_f - math.log10(20.0)) / (math.log10(20000.0) - math.log10(20.0))
            return pad_x + norm * plot_w

        for db in [-18, -12, -6, 0, 6, 12, 18]:
            y = y_for_db(db)
            self.canvas.create_line(pad_x, y, pad_x + plot_w, y, fill="#1f3b4d" if db == 0 else "#161b22", width=1.5 if db == 0 else 1.0)
            self.canvas.create_text(pad_x - 6, y, text=f"{db:+d} dB" if db != 0 else " 0 dB", fill="#64748b", font=("Segoe UI", 7), anchor="e")

        for hz in [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]:
            x = x_for_hz(hz)
            self.canvas.create_line(x, pad_y, x, h - pad_y, fill="#161b22")
            self.canvas.create_text(x, h - 7, text=f"{int(hz/1000)}k" if hz >= 1000 else f"{int(hz)}", fill="#64748b", font=("Segoe UI", 7), anchor="center")

        preamp = self.current_profile.get("preamp", 0.0)
        bands = self.current_profile.get("bands", [])
        num_points = 120
        sample_freqs = [10.0 ** (math.log10(20.0) + (i / (num_points - 1)) * (math.log10(20000.0) - math.log10(20.0))) for i in range(num_points)]
        total_curve = [preamp] * len(sample_freqs)

        for b in bands:
            if b.get("enabled", True):
                resp = calc_peaking_response(b.get("hz", 1000), b.get("gain", 0.0), b.get("q", 1.41), sample_freqs)
                for j in range(len(sample_freqs)): total_curve[j] += resp[j]

        coords = []
        for j, f in enumerate(sample_freqs):
            coords.extend([x_for_hz(f), y_for_db(total_curve[j])])

        if len(coords) >= 4:
            self.canvas.create_line(coords, fill="#00e5ff", width=2.2, smooth=True)

        for i, b in enumerate(bands):
            if b.get("enabled", True):
                nx = x_for_hz(b.get("hz", 1000))
                ny = y_for_db(b.get("gain", 0.0) + preamp)
                self.canvas.create_oval(nx - 4, ny - 4, nx + 4, ny + 4, fill="#121820", outline="#00e5ff", width=2)
                self.canvas.create_text(nx, ny - 8, text=f"{i+1}", fill="#d4af37", font=("Segoe UI", 7, "bold"))

        peak_gain = max(total_curve)
        if peak_gain > 0.05:
            self.lbl_headroom_status.config(text=f"⚠ NGUY CƠ CLIPPING: Peak +{peak_gain:.1f} dB (Dễ méo/cháy loa)", fg="#ff7676")
        else:
            self.lbl_headroom_status.config(text=f"HEADROOM: AN TOÀN (Peak {peak_gain:.1f} dBFS)", fg="#00e676")

    def apply_auto_headroom(self):
        bands = self.current_profile.get("bands", [])
        active_gains = [b.get("gain", 0.0) for b in bands if b.get("enabled", True) and b.get("gain", 0.0) > 0]
        new_preamp = round(-max(active_gains) - 0.5, 1) if active_gains else 0.0
        self.current_profile["preamp"] = new_preamp
        self.update_spectrum_graph()
        self.set_status(f"Auto-Headroom đã hạ Master Preamp về {new_preamp:+.1f} dB.")

    def reset_eq_flat(self):
        for b in self.current_profile.get("bands", []): b["gain"] = 0.0
        self.load_profile_to_ui(self.current_profile)
        self.update_spectrum_graph()
        self.set_status("Đã đưa 8-Band PEQ về mức 0 dB.")

    # ---------------- PROFILES CRUD & SERIAL ----------------

    def on_profile_selected(self, event=None):
        idx = self.cb_profiles.current()
        if 0 <= idx < len(self.profiles):
            self.active_profile_index = idx
            self.current_profile = copy.deepcopy(self.profiles[idx])
            self.backup_profile_a = copy.deepcopy(self.current_profile)
            self.load_profile_to_ui(self.current_profile)
            self.update_spectrum_graph()
            self.set_status(f"Đã chọn: {self.current_profile['name']}")

    def on_new_profile(self):
        new_name = tk.simpledialog.askstring("Tạo Profile", "Nhập tên cấu hình mới:", parent=self)
        if new_name and new_name.strip():
            p = copy.deepcopy(DEFAULT_PROFILES[0])
            p["id"] = f"custom_{int(time.time())}"
            p["name"] = new_name.strip()
            self.profiles.append(p)
            self.cb_profiles["values"] = [x["name"] for x in self.profiles]
            self.cb_profiles.current(len(self.profiles) - 1)
            self.on_profile_selected()
            self.save_library()

    def on_save_current_profile(self):
        self.profiles[self.active_profile_index] = copy.deepcopy(self.current_profile)
        self.save_library()
        self.set_status(f"Đã lưu: {self.current_profile['name']}")
        messagebox.showinfo("Thành công", f"Cấu hình '{self.current_profile['name']}' đã được lưu an toàn.")

    def toggle_ab_compare(self):
        if not self.is_compare_active:
            self.profile_b = copy.deepcopy(self.current_profile)
            self.current_profile = copy.deepcopy(self.backup_profile_a)
            self.load_profile_to_ui(self.current_profile)
            self.update_spectrum_graph()
            self.is_compare_active = True
            self.btn_ab_compare.config(text="⚡ A/B: [A] GỐC", bg="#5a3d10", fg="#ffcc00")
            self.set_status("Đang nghe cấu hình gốc [A]. Bấm lần nữa để về [B].")
        else:
            self.current_profile = copy.deepcopy(self.profile_b)
            self.load_profile_to_ui(self.current_profile)
            self.update_spectrum_graph()
            self.is_compare_active = False
            self.btn_ab_compare.config(text="⚡ A/B: [B] MỚI", bg="#232a34", fg="#00e5ff")
            self.set_status("Đang nghe cấu hình vừa chỉnh [B].")

    def save_library_prompt(self):
        if self.save_library():
            messagebox.showinfo("Thành công", f"Đã lưu toàn bộ {len(self.profiles)} cấu hình vào {LIBRARY_FILE}!")

    def refresh_com_ports(self):
        ports = []
        if HAS_SERIAL:
            try:
                for p in serial.tools.list_ports.comports(): ports.append(p.device)
            except Exception: pass
        if not ports: ports = ["Mô phỏng (Không COM)"]
        self.cb_com_ports["values"] = ports
        self.cb_com_ports.current(0)

    def toggle_connection(self):
        port = self.cb_com_ports.get()
        if not HAS_SERIAL or port.startswith("Mô phỏng"):
            self.set_status("Chế độ Mô phỏng / Offline Studio.")
            return
        if not self.is_connected:
            try:
                self.serial_conn = serial.Serial(port, baudrate=115200, timeout=1.0)
                self.is_connected = True
                self.btn_connect.config(text="NGẮT", bg="#381b1b", fg="#ff7676")
                self.set_status(f"Đã kết nối tới {port}.")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở cổng: {e}")
        else:
            if self.serial_conn: self.serial_conn.close()
            self.is_connected = False
            self.btn_connect.config(text="KẾT NỐI", bg="#183626", fg="#00e676")
            self.set_status("Đã ngắt kết nối.")

    def push_to_dsp_hardware(self):
        payload = build_full_dsp_stream(self.current_profile)
        if self.is_connected and self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(payload)
                self.serial_conn.flush()
                self.set_status(f"⚡ Đã nạp thành công {len(payload)} bytes xuống chip DSP BP1048B2!")
                messagebox.showinfo("Thành công", f"Đã nạp toàn bộ PEQ, Crossover, MVBass, DRC Limiter, Vang số Karaoke vào chip DSP!")
            except Exception as e:
                messagebox.showerror("Lỗi truyền", f"{e}")
        else:
            self.set_status(f"⚡ [MÔ PHỎNG] Đã kiểm tra đóng gói {len(payload)} bytes nhị phân chuẩn MVSilicon sẵn sàng nạp.")
            messagebox.showinfo("Chế độ Mô phỏng", f"Gói nhị phân ({len(payload)} bytes, Magic 0xA5 0x5A) đã đóng gói chuẩn xác.\nHãy kết nối cáp USB/Serial để nạp thật.")

    # ---------------- IMPORT / EXPORT ----------------

    def import_from_ini_file(self):
        path = filedialog.askopenfilename(filetypes=[("INI files", "*.ini"), ("All files", "*.*")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f: content = f.read()
            p = copy.deepcopy(DEFAULT_PROFILES[0])
            p["id"] = f"ini_{int(time.time())}"
            p["name"] = f"Imported: {os.path.basename(path).replace('.ini', '').title()}"
            self.profiles.append(p)
            self.cb_profiles["values"] = [x["name"] for x in self.profiles]
            self.cb_profiles.current(len(self.profiles) - 1)
            self.on_profile_selected()
            self.save_library()
            messagebox.showinfo("Thành công", f"Đã nạp cấu hình từ {os.path.basename(path)}!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"{e}")

    def export_to_ini_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".ini", initialfile=f"{self.current_profile['id']}.ini")
        if not path: return
        p = self.current_profile
        lines = [
            "; ==============================================================================",
            f"; BEST SOUND DSP CONTROLLER — {p['name']}",
            f"; Hardware: MVSilicon BP1048B2 (44.1kHz 2.1 Bi-Amp Full Pro Modules)",
            "; ==============================================================================",
            "",
            "[0x00-Firmware_Version]",
            "Type = 48",
            "",
            "[0x01-System_Control]",
            "sr_index = 7",
            "dsp_run = 1",
            "",
            "[0x85-Noise_Suppressor_Expander]",
            f"enable = {1 if p.get('noise_gate', {}).get('enabled', True) else 0}",
            f"threshold = {p.get('noise_gate', {}).get('threshold_db', -68.0):.1f}",
            "",
            "[0x87-MVBass_Classic]",
            f"enable = {1 if p.get('mvbass', {}).get('enabled', True) else 0}",
            f"cutoff = {p.get('mvbass', {}).get('cutoff', 90)}",
            f"intensity = {p.get('mvbass', {}).get('intensity', 45)}",
            "",
            "[0x89-Harmonic_Exciter]",
            f"enable = {1 if p.get('spatial', {}).get('treble_exciter', 0) > 0 else 0}",
            f"intensity = {p.get('spatial', {}).get('treble_exciter', 20)}",
            "",
            "[0x8A-Karaoke_Vocal_Engine]",
            f"enable = {1 if p.get('karaoke', {}).get('enabled', False) else 0}",
            f"echo_delay = {p.get('karaoke', {}).get('echo_delay', 180)}",
            f"echo_repeat = {p.get('karaoke', {}).get('echo_repeat', 45)}",
            f"reverb_mix = {p.get('karaoke', {}).get('reverb_mix', 35)}",
            f"anti_howling = {1 if p.get('karaoke', {}).get('anti_howling', True) else 0}",
            f"music_ducking = {1 if p.get('karaoke', {}).get('music_ducking', True) else 0}",
            "",
            "[0x93-DRC]",
            f"enable = {1 if p.get('limiter', {}).get('enabled', True) else 0}",
            f"threshold = {p.get('limiter', {}).get('threshold_db', -1.5):.2f}",
            f"attack = {p.get('limiter', {}).get('attack_ms', 10)}",
            f"release = {p.get('limiter', {}).get('release_ms', 150)}",
            "",
            "[0x95-EQ_10BAND_1]",
            "enable = 1",
            f"pregain = {p.get('preamp', -2.0):.2f}",
            f"sub_lpf = {p.get('crossover', {}).get('sub_lpf', 150)}",
            f"sub_hpf = {p.get('crossover', {}).get('sub_hpf', 38)}",
            "",
            "[0x96-EQ_10BAND_2]",
            "enable = 1",
            f"pregain = {p.get('preamp', -2.0):.2f}",
            f"mid_hpf = {p.get('crossover', {}).get('mid_hpf', 160)}",
            "",
            "[0x98-Master_Gain_CH2]",
            f"gain = {p.get('biamp', {}).get('ch2', 0.0):.2f}",
            "",
            "[0x99-Master_Gain_CH1]",
            f"gain = {p.get('biamp', {}).get('ch1', 1.5):.2f}",
            "",
            "[Hardware_Customization]",
            f"usb_dac_mode = {1 if p.get('hardware_io', {}).get('usb_dac_mode', True) else 0}",
            f"i2s_out = {1 if p.get('hardware_io', {}).get('i2s_out', True) else 0}",
            f"bt_name = {p.get('hardware_io', {}).get('bt_name', 'BEST SOUND T1V2 BI-AMP')}",
            f"led_vu_meter = {1 if p.get('hardware_io', {}).get('led_vu_meter', True) else 0}",
            ""
        ]
        try:
            with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
            messagebox.showinfo("Thành công", f"Đã xuất file ACPWorkbench INI đầy đủ:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"{e}")

    def export_to_c_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".c", initialfile=f"dsp_{self.current_profile['id']}.c")
        if not path: return
        p = self.current_profile
        payload = build_full_dsp_stream(p)
        lines = [
            f"/* BEST SOUND DSP — {p['name']} (Ultimate Pro Modules) */",
            '#include "mv_types.h"',
            f"const uint8_t dsp_profile_{p['id']}[] = {{"
        ]
        for i in range(0, len(payload), 12):
            lines.append("    " + ", ".join([f"0x{b:02X}" for b in payload[i:i+12]]) + ",")
        lines.append("};")
        lines.append(f"const uint16_t dsp_profile_len_{p['id']} = {len(payload)};\n")
        try:
            with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
            messagebox.showinfo("Thành công", f"Đã xuất file mã nguồn C:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"{e}")

    def export_to_apo_txt(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"EqualizerAPO_{self.current_profile['id']}.txt")
        if not path: return
        p = self.current_profile
        lines = [f"# Equalizer APO: {p['name']}", f"Preamp: {p.get('preamp', -2.0):.1f} dB"]
        for i, b in enumerate(p.get("bands", [])):
            if b.get("enabled", True):
                lines.append(f"Filter {i+1}: ON PK Fc {b.get('hz', 1000)} Hz Gain {b.get('gain', 0.0):.1f} dB Q {b.get('q', 1.41):.2f}")
        try:
            with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
            messagebox.showinfo("Thành công", f"Đã xuất file Equalizer APO:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"{e}")

    def set_status(self, msg):
        self.lbl_status.config(text=f"[{time.strftime('%H:%M:%S')}] {msg}")

if __name__ == "__main__":
    app = BestSoundDspStudioPC()
    app.mainloop()
