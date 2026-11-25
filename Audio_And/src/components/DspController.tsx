'use client'

import { useEffect, useMemo, useState } from 'react'
import AICalibrationPanel from '@/components/AiCalibrationPanel'
import { DspProfile, DspBand } from '../dsp/types'
import { VERIFIED_PROFILES, STANDARD_BANDS_TEMPLATE } from '../dsp/profiles'
import { calculateAutoHeadroom, validateBand, validateMVBass, validateBiAmp } from '../dsp/limits'
import { renderDspIni } from '../dsp/ini-renderer'
import { renderDspC } from '../dsp/c-renderer'
import { micRta, RtaFrame } from '../rta/audio-input'
import { signalGenerator } from '../rta/signals'
import { FftPeak } from '../rta/fft'
import { DspFlashStateMachine } from '../otg/state-machine'
import { MockDspTransport } from '../otg/mock-transport'
import { WebUsbDspTransport } from '../otg/webusb-transport'

type IconName =
  | 'bluetooth'
  | 'usb'
  | 'power'
  | 'mic'
  | 'shield'
  | 'save'
  | 'download'
  | 'wave'
  | 'spark'
  | 'chevron'
  | 'home'
  | 'equalizer'
  | 'device'

const iconPaths: Record<IconName, React.ReactNode> = {
  bluetooth: <path d="m7 7 10 10-5 4V3l5 4L7 17" />,
  usb: (
    <path d="M12 2v14m0-14 3 3m-3-3L9 5m3 11-4-4m4 4 4-4M8 12H5v5m11-5h3v5M5 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm14 0v4h-4v-4h4Z" />
  ),
  power: <path d="M12 2v10m6.4-6.4a9 9 0 1 1-12.8 0" />,
  mic: (
    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Zm-7 9v1a7 7 0 0 0 14 0v-1M12 19v3m-4 0h8" />
  ),
  shield: <path d="M12 2 4 5v6c0 5.2 3.4 9 8 11 4.6-2 8-5.8 8-11V5l-8-3Zm-3 10 2 2 4-5" />,
  save: <path d="M5 3h12l3 3v15H4V3h1Zm2 0v6h9V3M8 21v-7h8v7" />,
  download: <path d="M12 3v12m0 0 5-5m-5 5-5-5M4 21h16" />,
  wave: <path d="M3 12h2l2-7 4 14 3-10 3 6h4" />,
  spark: (
    <path d="m12 2 1.4 5.1L18 9l-4.6 1.9L12 16l-1.4-5.1L6 9l4.6-1.9L12 2Zm6 13 .7 2.3L21 18l-2.3.7L18 21l-.7-2.3L15 18l2.3-.7L18 15Z" />
  ),
  chevron: <path d="m9 18 6-6-6-6" />,
  home: <path d="m3 11 9-8 9 8v10h-6v-6H9v6H3V11Z" />,
  equalizer: <path d="M4 21V10m0-4V3m8 18v-6m0-4V3m8 18V9m0-4V3M1 10h6m2 5h6m2-6h6" />,
  device: (
    <path d="M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm3 17h4M9 5h6" />
  ),
}

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {iconPaths[name]}
    </svg>
  )
}

function Toggle({
  on,
  onChange,
  label,
  icon,
}: {
  on: boolean
  onChange: () => void
  label: string
  icon?: IconName
}) {
  return (
    <button className={`toggle-control ${on ? 'on' : ''}`} onClick={onChange} aria-pressed={on}>
      {icon && <Icon name={icon} size={15} />}
      <span>{label}</span>
      <span className="switch">
        <span />
      </span>
    </button>
  )
}

function Spectrum({
  bands,
  rta,
  liveRtaMags,
  bypass,
  compact = false,
}: {
  bands: DspBand[]
  rta: boolean
  liveRtaMags: number[]
  bypass: boolean
  compact?: boolean
}) {
  const width = 1000
  const height = compact ? 240 : 370
  const padX = compact ? 25 : 52
  const padY = compact ? 20 : 32
  const xForHz = (hz: number) => padX + ((Math.log10(hz) - Math.log10(20)) / 3) * (width - padX * 2)
  const yForGain = (gain: number) => height / 2 - (gain / 18) * (height / 2 - padY)

  const response = useMemo(() => {
    const pts = Array.from({ length: 160 }, (_, i) => {
      const logHz = Math.log10(20) + (i / 159) * 3
      const hz = 10 ** logHz
      const gain = bypass
        ? 0
        : bands.reduce((sum, b) => {
            if (!b.enabled) return sum
            const distance = Math.log2(hz / b.hz)
            return sum + b.gain * Math.exp(-distance * distance * b.q * 1.5)
          }, 0)
      return `${xForHz(hz)},${yForGain(Math.max(-17, Math.min(17, gain)))}`
    })
    return pts.join(' ')
  }, [bands, bypass, height])

  const octaveLines = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
  const dbLines = [-18, -12, -6, 0, 6, 12, 18]

  // Render live microphone RTA curve if available, or static fallback curve
  const rtaPoints = useMemo(() => {
    if (liveRtaMags.length > 50) {
      const pts = Array.from({ length: 120 }, (_, i) => {
        const logHz = Math.log10(20) + (i / 119) * 3
        const hz = 10 ** logHz
        // map frequency to FFT bin
        const binIdx = Math.min(liveRtaMags.length - 1, Math.round((hz / 22050) * liveRtaMags.length))
        const rawDb = liveRtaMags[binIdx] ?? -80
        // normalize -90..-10 dBFS to visual +/- 15 dB
        const visualGain = ((rawDb + 55) / 35) * 12
        return `${xForHz(hz)},${yForGain(Math.max(-17, Math.min(17, visualGain)))}`
      })
      return pts.join(' ')
    }
    return null
  }, [liveRtaMags, height])

  const staticRtaPath = `M ${padX} ${height * 0.67} C 120 ${height * 0.6}, 145 ${height * 0.33}, 205 ${height * 0.48} S 300 ${height * 0.78}, 370 ${height * 0.55} S 455 ${height * 0.28}, 520 ${height * 0.5} S 635 ${height * 0.74}, 710 ${height * 0.42} S 815 ${height * 0.36}, ${width - padX} ${height * 0.6}`

  return (
    <svg
      className="spectrum"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Real-time parametric equalizer response"
    >
      <defs>
        <linearGradient id="cyanFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#00e5ff" stopOpacity=".23" />
          <stop offset="1" stopColor="#00e5ff" stopOpacity="0" />
        </linearGradient>
        <filter id="cyanGlow">
          <feGaussianBlur stdDeviation="5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="amberGlow">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width={width} height={height} fill="#0b0e12" />
      {dbLines.map((db) => (
        <g key={db}>
          <line
            x1={padX}
            x2={width - padX}
            y1={yForGain(db)}
            y2={yForGain(db)}
            className={db === 0 ? 'zero-line' : 'grid-line'}
          />
          {!compact && (
            <text x="10" y={yForGain(db) + 4} className="axis-label">
              {db > 0 ? `+${db}` : db}
            </text>
          )}
        </g>
      ))}
      {octaveLines.map((hz) => (
        <g key={hz}>
          <line
            x1={xForHz(hz)}
            x2={xForHz(hz)}
            y1={padY}
            y2={height - padY}
            className="grid-line"
          />
          <text x={xForHz(hz)} y={height - 8} textAnchor="middle" className="axis-label">
            {hz >= 1000 ? `${hz / 1000}k` : hz}
          </text>
        </g>
      ))}
      {rta && (
        rtaPoints ? (
          <polyline
            points={rtaPoints}
            fill="none"
            stroke="#ffb300"
            strokeWidth="2.2"
            opacity=".85"
            filter="url(#amberGlow)"
          />
        ) : (
          <path
            d={staticRtaPath}
            fill="none"
            stroke="#ffb300"
            strokeWidth="2.2"
            opacity=".72"
            filter="url(#amberGlow)"
          />
        )
      )}
      <polyline
        points={`${response} ${width - padX},${height / 2} ${padX},${height / 2}`}
        fill="url(#cyanFill)"
        opacity={bypass ? 0.2 : 1}
        suppressHydrationWarning
      />
      <polyline
        points={response}
        fill="none"
        stroke="#00e5ff"
        strokeWidth={compact ? 3 : 3.5}
        opacity={bypass ? 0.25 : 1}
        filter="url(#cyanGlow)"
        suppressHydrationWarning
      />
      {!bypass &&
        bands.map((band, index) => (
          <g key={band.name} transform={`translate(${xForHz(band.hz)}, ${yForGain(band.gain)})`}>
            <circle r={compact ? 12 : 14} fill="#10161b" stroke={band.color} strokeWidth="3" />
            <circle r={compact ? 7 : 8} fill={band.color} opacity=".22" />
            <text textAnchor="middle" dominantBaseline="central" className="node-label">
              {index + 1}
            </text>
          </g>
        ))}
    </svg>
  )
}

function ValueSlider({
  value,
  min,
  max,
  step = 0.1,
  onChange,
  accent = '#00e5ff',
  label,
}: {
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
  accent?: string
  label: string
}) {
  const progress = ((value - min) / (max - min)) * 100
  return (
    <input
      aria-label={label}
      className="precision-slider"
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      style={{ '--progress': `${progress}%`, '--accent': accent } as React.CSSProperties}
    />
  )
}

export default function App() {
  // Master Profile State
  const [profile, setProfile] = useState<DspProfile>(VERIFIED_PROFILES[0])
  const [activePreset, setActivePreset] = useState(VERIFIED_PROFILES[0].name)
  const [baselineProfile, setBaselineProfile] = useState<DspProfile>(VERIFIED_PROFILES[0])

  // Audio Processing and Measurement State
  const [rta, setRta] = useState(true)
  const [liveRtaMags, setLiveRtaMags] = useState<number[]>([])
  const [livePeaks, setLivePeaks] = useState<FftPeak[]>([])
  const [avgLevelDb, setAvgLevelDb] = useState(-54.2)
  const [bypass, setBypass] = useState(false)
  const [headroom, setHeadroom] = useState(true)
  const [muted, setMuted] = useState(false)
  const [isABComparing, setIsABComparing] = useState(false)

  // Test Signals
  const [activeSignal, setActiveSignal] = useState<'none' | 'pink' | 'sweep' | 'tone'>('none')
  const [signalLevel, setSignalLevel] = useState(-12)

  // Hardware Flash & Status
  const [saved, setSaved] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const [mobileStudio, setMobileStudio] = useState(false)
  const [mobileTab, setMobileTab] = useState('home')

  // Real Microphone RTA Hook
  useEffect(() => {
    if (rta) {
      micRta.start((frame: RtaFrame) => {
        setLiveRtaMags(frame.magnitudes)
        setLivePeaks(frame.peaks)
        setAvgLevelDb(frame.avgLevelDb)
      }).catch((err) => console.warn('Microphone RTA start error:', err))
    } else {
      micRta.stop()
      setLiveRtaMags([])
    }
    return () => {
      micRta.stop()
    }
  }, [rta])

  // Stop test signals on unmount
  useEffect(() => {
    return () => {
      signalGenerator.stop()
    }
  }, [])

  // Auto-Headroom adjustment
  const handleAutoHeadroom = () => {
    const recommendedPreamp = calculateAutoHeadroom(profile.bands)
    setProfile((prev) => ({
      ...prev,
      masterPreamp: recommendedPreamp,
    }))
    setHeadroom(true)
  }

  const setBandGain = (index: number, gain: number) => {
    setProfile((prev) => {
      const updated = prev.bands.map((b, i) => (i === index ? { ...b, gain } : b))
      return { ...prev, bands: updated }
    })
    setActivePreset('Custom')
  }

  const applyPreset = (presetName: string) => {
    const found = VERIFIED_PROFILES.find((p) => p.name.includes(presetName) || p.id.includes(presetName))
    if (found) {
      setProfile(found)
      setBaselineProfile(found)
      setActivePreset(found.name)
    }
  }

  const toggleAB = () => {
    if (isABComparing) {
      // Revert to tweaked profile
      setIsABComparing(false)
      setBypass(false)
    } else {
      // Toggle to baseline
      setIsABComparing(true)
      setBypass(true)
    }
  }

  const playPinkNoise = () => {
    if (activeSignal === 'pink') {
      signalGenerator.stop()
      setActiveSignal('none')
    } else {
      signalGenerator.playPinkNoise(signalLevel)
      setActiveSignal('pink')
    }
  }

  const playSineSweep = () => {
    if (activeSignal === 'sweep') {
      signalGenerator.stop()
      setActiveSignal('none')
    } else {
      signalGenerator.playSineSweep(5.0, signalLevel, () => setActiveSignal('none'))
      setActiveSignal('sweep')
    }
  }

  const playSingleTone = (hz: number) => {
    signalGenerator.playTone(hz, signalLevel)
    setActiveSignal('tone')
  }

  const stopSignals = () => {
    signalGenerator.stop()
    setActiveSignal('none')
  }

  const downloadConfig = (format: 'ini' | 'c' | 'txt') => {
    let content = ''
    let filename = ''
    if (format === 'ini') {
      content = renderDspIni(profile)
      filename = `${profile.id}.ini`
    } else if (format === 'c') {
      content = renderDspC(profile)
      filename = `${profile.id}.c`
    } else {
      content = `# Equalizer APO Configuration\n# Profile: ${profile.name}\nPreamp: ${profile.masterPreamp} dB\n` +
        profile.bands
          .map((b) => `Filter ${b.id}: ON PK Fc ${b.hz} Hz Gain ${b.gain} dB Q ${b.q}`)
          .join('\n')
      filename = `${profile.id}_apo.txt`
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const flashToHardware = async () => {
    const transport = new MockDspTransport()
    const sm = new DspFlashStateMachine(transport)
    setSaved(true)
    await sm.executeFlashPipeline(profile, () => {})
    window.setTimeout(() => setSaved(false), 2000)
  }

  const navigateMobile = (tab: string, sectionId: string) => {
    setMobileTab(tab)
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <main
      className={`app-shell ${muted ? 'is-muted' : ''} ${mobileStudio ? 'mobile-studio-open' : ''}`}
    >
      <header className="topbar">
        <div className="mobile-sensor-zone" aria-hidden="true">
          <span />
        </div>
        <div className="brand">
          <div className="brand-mark">
            <span />
            <span />
            <span />
          </div>
          <div>
            <div className="brand-title">
              BEST SOUND <strong>T1V2</strong>
            </div>
            <div className="brand-sub">
              MVSilicon BP1048B2 <span>DSP CONTROLLER</span>
            </div>
          </div>
        </div>
        <div className="project-meta">
          <span>PROJECT</span>
          <strong>2.1 Bi-Amp (5L Sub 4" + Mid AIRS)</strong>
        </div>
        <div className="format-meta">
          <span>DEVICE FORMAT</span>
          <strong>
            44.1 kHz <i /> 24-bit
          </strong>
        </div>
        <div className="cpu-meter">
          <div>
            <span>DSP</span>
            <strong>38%</strong>
          </div>
          <div className="meter-track">
            <i style={{ width: '38%' }} />
          </div>
        </div>
        <button className="connection-pill" aria-label="Connected via USB OTG">
          <span className="live-dot" />
          <Icon name="usb" size={16} />
          <span>
            <small>OTG READY</small>BP1048B2
          </span>
          <Icon name="chevron" size={14} />
        </button>
        <button
          className={`mute-button ${muted ? 'active' : ''}`}
          onClick={() => {
            setMuted(!muted)
            if (!muted) stopSignals()
          }}
          aria-pressed={muted}
        >
          <Icon name="power" size={17} />
          <span>{muted ? 'UNMUTE' : 'MUTE'}</span>
        </button>
        <button
          className={`save-button ${saved ? 'saved' : ''}`}
          onClick={flashToHardware}
        >
          <Icon name="save" size={16} /> {saved ? 'SAVED (OTG)' : 'SAVE TO FLASH'}
        </button>
      </header>

      <section className="workspace">
        <aside className="left-rail">
          <div className="rail-heading">
            <span>SIGNAL PATH</span>
            <i>LIVE</i>
          </div>
          {[
            'USB OTG / BT INPUT',
            'MASTER PRE-AMP',
            'PARAMETRIC EQ (8-BAND)',
            'MVBASS HARMONIC SYNTH',
            '2.1 BI-AMP OUTPUT',
          ].map((item, i) => (
            <button key={item} className={`path-item ${i === 2 ? 'active' : ''}`}>
              <span className="path-number">0{i + 1}</span>
              <span>{item}</span>
              <i />
            </button>
          ))}
          <div className="output-meter">
            <div className="rail-heading">
              <span>OUTPUT</span>
              <strong>{avgLevelDb.toFixed(1)} dBFS</strong>
            </div>
            <div className="stereo-bars">
              {[...Array(16)].map((_, i) => (
                <i key={`l${i}`} className={i < 11 ? 'lit' : ''} />
              ))}
              {[...Array(16)].map((_, i) => (
                <i key={`r${i}`} className={i < 10 ? 'lit' : ''} />
              ))}
            </div>
            <div className="lr-label">
              <span>L</span>
              <span>R</span>
            </div>
          </div>
          <div className="device-card">
            <span className="device-icon">
              <Icon name="usb" size={21} />
            </span>
            <div>
              <small>HARDWARE</small>
              <strong>BP1048B2</strong>
              <em>Firmware Type 48</em>
            </div>
          </div>
        </aside>

        <div className="main-panel">
          <div className="mobile-only mobile-head" id="app-home">
            <div className="eyebrow">
              <span className="live-dot" /> LIVE DSP SESSION
            </div>
            <div className="mobile-title-line">
              <div>
                <h1>Parametric EQ</h1>
                <p>8-band precision acoustic tuning · 2.1 Bi-Amp</p>
              </div>
              <span className="mobile-profile-badge">
                <small>ACTIVE PROFILE</small>
                {activePreset}
              </span>
            </div>
          </div>

          <section className="mobile-only mobile-mode-rack" aria-label="Quick processing modes">
            <div className="mode-rack-head">
              <div>
                <span>PROCESSING MODES</span>
                <small>Tap a module to toggle</small>
              </div>
              <strong>
                <i /> DSP LIVE
              </strong>
            </div>
            <div className="mode-switches">
              <button
                className={profile.mvbass.enabled ? 'active warm' : ''}
                onClick={() =>
                  setProfile((prev) => ({
                    ...prev,
                    mvbass: { ...prev.mvbass, enabled: !prev.mvbass.enabled },
                  }))
                }
                aria-pressed={profile.mvbass.enabled}
              >
                <span>BSS</span>
                <i>
                  <b />
                </i>
                <small>MVBASS</small>
              </button>
              <button
                className={!bypass ? 'active' : ''}
                onClick={toggleAB}
                aria-pressed={!bypass}
              >
                <span>PEQ</span>
                <i>
                  <b />
                </i>
                <small>8-BAND EQ</small>
              </button>
              <button
                className={rta ? 'active' : ''}
                onClick={() => setRta(!rta)}
                aria-pressed={rta}
              >
                <span>RTA</span>
                <i>
                  <b />
                </i>
                <small>MIC FFT</small>
              </button>
            </div>
            <div className="mode-rack-footer">
              <span>
                <i className={headroom ? 'active' : ''} />
                AUTO HEADROOM
              </span>
              <span>
                <i className={!muted ? 'active' : ''} />
                OUTPUT READY
              </span>
              <span>
                <i className={activePreset.includes('Flat') ? '' : 'active'} />
                PROFILE SYNC
              </span>
            </div>
          </section>

          <section className="analyzer-card">
            <div className="panel-header">
              <div>
                <span className="section-kicker">LIVE ANALYZER</span>
                <h1>Acoustic Response</h1>
              </div>
              <div className="legend">
                <span>
                  <i className="cyan" /> PEQ COMPOSITE
                </span>
                <span>
                  <i className="amber" /> MIC RTA {rta ? '(LIVE)' : '(PAUSED)'}
                </span>
              </div>
              <div className="analyzer-stats">
                <span>
                  PEAK<strong>{livePeaks[0] ? `${livePeaks[0].freq} Hz` : '-3.8 dBFS'}</strong>
                </span>
                <span>
                  AVG<strong>{avgLevelDb.toFixed(1)} dBFS</strong>
                </span>
              </div>
            </div>
            <div className="graph-wrap">
              <div className="graph-unit">dB</div>
              <Spectrum
                bands={profile.bands}
                rta={rta}
                liveRtaMags={liveRtaMags}
                bypass={bypass}
                compact
              />
              <div className="mobile-hud">
                <span>BAND 04 (ANTI-BOOM)</span>
                <strong>165 Hz</strong>
                <em>{profile.bands[3]?.gain.toFixed(1)} dB</em>
                <small>Q {profile.bands[3]?.q.toFixed(2)}</small>
              </div>
            </div>
            <div className="graph-toolbar">
              <Toggle on={bypass} onChange={toggleAB} label={isABComparing ? 'COMPARING B' : 'A/B BYPASS'} />
              <Toggle
                on={headroom}
                onChange={handleAutoHeadroom}
                label="AUTO HEADROOM"
                icon="shield"
              />
              <Toggle on={rta} onChange={() => setRta(!rta)} label="MIC RTA" icon="mic" />
            </div>
          </section>

          <section className="control-row">
            <div className="preamp-card">
              <div className="control-label">
                <span>MASTER PRE-AMP</span>
                <strong>
                  {profile.masterPreamp > 0 ? '+' : ''}
                  {profile.masterPreamp.toFixed(1)} <small>dB</small>
                </strong>
              </div>
              <ValueSlider
                value={profile.masterPreamp}
                min={-18}
                max={6}
                onChange={(val) => setProfile((p) => ({ ...p, masterPreamp: val }))}
                label="Master pre-amp gain"
              />
              <div className="range-label">
                <span>-18</span>
                <span>0</span>
                <span>+6 dB</span>
              </div>
            </div>
            <div className="preset-card">
              <div className="control-label">
                <span>VERIFIED PRESETS</span>
                <small>1-TAP HARDWARE VOICING</small>
              </div>
              <div className="preset-list">
                {VERIFIED_PROFILES.map((p) => (
                  <button
                    key={p.id}
                    className={activePreset === p.name ? 'active' : ''}
                    onClick={() => applyPreset(p.name)}
                  >
                    {p.name.split(' ')[0]}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="peq-section" id="app-eq">
            <div className="section-title-row">
              <div>
                <span className="section-kicker">CHANNEL STRIP</span>
                <h2>Precision PEQ Bands</h2>
              </div>
              <div className="section-status">
                <span className="live-dot" /> REAL-TIME HARDWARE SYNC
              </div>
            </div>
            <p className="mobile-only fader-hint">Drag to tune · Double-tap a band to reset to 0dB</p>
            <div className="mobile-band-grid">
              {profile.bands.map((band, index) => (
                <article
                  className={`band-card ${index === 3 ? 'resonance' : ''}`}
                  key={band.name}
                  onDoubleClick={() => setBandGain(index, 0)}
                >
                  <div className="band-card-head">
                    <span className="band-index" style={{ color: band.color }}>
                      0{index + 1}
                    </span>
                    <span className="band-enabled">
                      <i style={{ background: band.color }} /> ON
                    </span>
                  </div>
                  <div className="band-name">{band.name}</div>
                  <div className="band-freq">{band.hz} Hz</div>
                  <div
                    className="band-value"
                    style={{ color: index === 3 ? '#ff8a3d' : band.color }}
                  >
                    {band.gain > 0 ? '+' : ''}
                    {band.gain.toFixed(1)} <small>dB</small>
                  </div>
                  <ValueSlider
                    value={band.gain}
                    min={-12}
                    max={6}
                    onChange={(value) => setBandGain(index, value)}
                    accent={band.color}
                    label={`${band.name} gain`}
                  />
                  <div className="band-scale">
                    <span>-12</span>
                    <i>0</i>
                    <span>+6</span>
                  </div>
                </article>
              ))}
            </div>

            <div className="peq-table">
              <div className="peq-table-head">
                <span>BAND</span>
                <span>ENABLE</span>
                <span>FILTER TYPE</span>
                <span>FREQUENCY</span>
                <span>GAIN</span>
                <span>Q FACTOR</span>
                <span>DESCRIPTION</span>
              </div>
              {profile.bands.map((band, index) => (
                <div className={`peq-table-row ${index === 3 ? 'selected' : ''}`} key={band.name}>
                  <span className="table-band">
                    <i style={{ background: band.color }} /> 0{index + 1}
                  </span>
                  <span>
                    <button
                      className={`mini-switch ${band.enabled ? 'on' : ''}`}
                      onClick={() =>
                        setProfile((prev) => ({
                          ...prev,
                          bands: prev.bands.map((b, i) =>
                            i === index ? { ...b, enabled: !b.enabled } : b
                          ),
                        }))
                      }
                      aria-label={`Enable ${band.name}`}
                    >
                      <i />
                    </button>
                  </span>
                  <span>
                    <button className="select-button">
                      {band.type === 'peaking' ? 'Peaking' : band.type === 'highshelf' ? 'High Shelf' : 'Filter'} <b>⌄</b>
                    </button>
                  </span>
                  <span className="numeric-cell">{band.hz} Hz</span>
                  <span className={`numeric-cell gain ${band.gain < 0 ? 'negative' : ''}`}>
                    {band.gain > 0 ? '+' : ''}
                    {band.gain.toFixed(1)} dB
                  </span>
                  <span className="numeric-cell">{band.q.toFixed(2)}</span>
                  <span className="desc-cell">{band.desc}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="effects-section" id="app-device">
            <div className="section-title-row">
              <div>
                <span className="section-kicker">HARDWARE ENGINE</span>
                <h2>MVBass Harmonic Engine & 2.1 Bi-Amp</h2>
              </div>
            </div>
            <div className="effect-grid">
              <article className="effect-card">
                <div className="effect-card-top">
                  <span>
                    <strong>MVBass Intensity</strong>
                    <small>Harmonic bass synthesis · {profile.mvbass.cutoffFrequency} Hz</small>
                  </span>
                  <b style={{ color: '#00e676' }}>{profile.mvbass.intensity}%</b>
                </div>
                <ValueSlider
                  value={profile.mvbass.intensity}
                  min={0}
                  max={100}
                  step={1}
                  onChange={(val) =>
                    setProfile((p) => ({
                      ...p,
                      mvbass: { ...p.mvbass, intensity: val },
                    }))
                  }
                  accent="#00e676"
                  label="MVBass Intensity"
                />
              </article>

              <article className="effect-card">
                <div className="effect-card-top">
                  <span>
                    <strong>Bi-Amp CH1 (Subwoofer 4")</strong>
                    <small>Mid/Bass digital gain</small>
                  </span>
                  <b style={{ color: '#00e5ff' }}>
                    {profile.biamp.ch1Gain > 0 ? '+' : ''}
                    {profile.biamp.ch1Gain.toFixed(1)} dB
                  </b>
                </div>
                <ValueSlider
                  value={profile.biamp.ch1Gain}
                  min={-12}
                  max={6}
                  step={0.5}
                  onChange={(val) =>
                    setProfile((p) => ({
                      ...p,
                      biamp: { ...p.biamp, ch1Gain: val },
                    }))
                  }
                  accent="#00e5ff"
                  label="CH1 Bass Gain"
                />
              </article>

              <article className="effect-card">
                <div className="effect-card-top">
                  <span>
                    <strong>Bi-Amp CH2 (AIRS + Treble Dome)</strong>
                    <small>High frequency digital gain</small>
                  </span>
                  <b style={{ color: '#d4af37' }}>
                    {profile.biamp.ch2Gain > 0 ? '+' : ''}
                    {profile.biamp.ch2Gain.toFixed(1)} dB
                  </b>
                </div>
                <ValueSlider
                  value={profile.biamp.ch2Gain}
                  min={-12}
                  max={6}
                  step={0.5}
                  onChange={(val) =>
                    setProfile((p) => ({
                      ...p,
                      biamp: { ...p.biamp, ch2Gain: val },
                    }))
                  }
                  accent="#d4af37"
                  label="CH2 Treble Gain"
                />
              </article>
            </div>
          </section>

          <AICalibrationPanel
            currentProfile={profile}
            peaks={livePeaks}
            avgLevel={avgLevelDb}
            onApplyProfile={(newProfile) => {
              setProfile(newProfile)
              setActivePreset(newProfile.name)
            }}
          />

          <button className="studio-cta" onClick={() => setMobileStudio(true)}>
            <span className="cta-icon">
              <Icon name="wave" size={21} />
            </span>
            <span>
              <small>ACOUSTIC LABORATORY</small>OPEN FULL-SCREEN RTA & SIGNAL GENERATOR
            </span>
            <Icon name="chevron" />
          </button>

          <section className="studio-panel">
            <div className="studio-panel-top">
              <div>
                <span className="section-kicker">CALIBRATION LAB</span>
                <h2>Full-Screen Acoustic RTA & Signal Generator</h2>
              </div>
              <button className="close-studio" onClick={() => setMobileStudio(false)}>
                CLOSE
              </button>
            </div>
            <div className="studio-graph">
              <Spectrum
                bands={profile.bands}
                rta={rta}
                liveRtaMags={liveRtaMags}
                bypass={bypass}
              />
            </div>
            <div className="studio-controls">
              <div className="generator-panel">
                <div className="studio-control-title">
                  <Icon name="wave" />
                  <span>
                    SIGNAL GENERATOR<small>Acoustic Test Signals</small>
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    className={`rounded px-3 py-2 font-mono text-[8px] font-bold ${
                      activeSignal === 'pink' ? 'bg-[#ff8a3d] text-black' : 'bg-[#1a2027] text-white'
                    }`}
                    onClick={playPinkNoise}
                  >
                    PINK NOISE
                  </button>
                  <button
                    className={`rounded px-3 py-2 font-mono text-[8px] font-bold ${
                      activeSignal === 'sweep' ? 'bg-[#00e5ff] text-black' : 'bg-[#1a2027] text-white'
                    }`}
                    onClick={playSineSweep}
                  >
                    SINE SWEEP
                  </button>
                </div>
                <div className="tone-buttons">
                  <button onClick={() => playSingleTone(60)}>
                    60 Hz <small>SUB</small>
                  </button>
                  <button onClick={() => playSingleTone(1000)}>
                    1 kHz <small>MID</small>
                  </button>
                  <button onClick={() => playSingleTone(10000)}>
                    10 kHz <small>TREBLE</small>
                  </button>
                </div>
                {activeSignal !== 'none' && (
                  <button
                    className="mt-2 w-full rounded bg-[#ff3d3d] py-1.5 font-mono text-[8px] font-bold text-white"
                    onClick={stopSignals}
                  >
                    DỪNG PHÁT ÂM (PANIC KILL-SWITCH)
                  </button>
                )}
              </div>
              <div className="export-panel">
                <div className="studio-control-title">
                  <Icon name="download" />
                  <span>
                    DSP EXPORT<small>ACPWorkbench & Firmware</small>
                  </span>
                </div>
                <p>Export the active PEQ profile into verified hardware formats.</p>
                <button className="export-button" onClick={() => setExportOpen(true)}>
                  <Icon name="download" /> EXPORT PROFILE
                </button>
              </div>
            </div>
          </section>
        </div>
      </section>

      <nav className="mobile-app-nav" aria-label="Điều hướng ứng dụng">
        <button
          type="button"
          className={mobileTab === 'home' ? 'active' : ''}
          onClick={() => navigateMobile('home', 'app-home')}
        >
          <Icon name="home" size={19} />
          <span>Home</span>
        </button>
        <button
          type="button"
          className={mobileTab === 'eq' ? 'active' : ''}
          onClick={() => navigateMobile('eq', 'app-eq')}
        >
          <Icon name="equalizer" size={19} />
          <span>EQ</span>
        </button>
        <button
          type="button"
          className={mobileTab === 'ai' ? 'active' : ''}
          onClick={() => navigateMobile('ai', 'ai-calibration')}
        >
          <Icon name="spark" size={19} />
          <span>AI Tune</span>
        </button>
        <button
          type="button"
          className={mobileTab === 'device' ? 'active' : ''}
          onClick={() => navigateMobile('device', 'app-device')}
        >
          <Icon name="device" size={19} />
          <span>Device</span>
        </button>
      </nav>

      {muted && (
        <div className="mute-banner">
          <Icon name="power" /> DSP OUTPUT MUTED — SIGNAL PROCESSING REMAINS ACTIVE
        </div>
      )}

      {exportOpen && (
        <div className="modal-backdrop" onMouseDown={() => setExportOpen(false)}>
          <div
            className="export-modal"
            onMouseDown={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Export DSP profile"
          >
            <div className="modal-head">
              <div>
                <span className="section-kicker">PROFILE READY</span>
                <h2>Export DSP Configuration</h2>
              </div>
              <button onClick={() => setExportOpen(false)}>×</button>
            </div>
            <p>{profile.name} · 8 active bands · 44.1 kHz BP1048B2</p>
            <div className="export-options">
              <button onClick={() => downloadConfig('ini')}>
                <span>
                  <Icon name="download" />
                  <strong>ACPWorkbench (.ini)</strong>
                </span>
                <small>43 sections, golden register format</small>
                <Icon name="chevron" />
              </button>
              <button onClick={() => downloadConfig('c')}>
                <span>
                  <Icon name="wave" />
                  <strong>MVSilicon C Source (.c)</strong>
                </span>
                <small>BP1048B2 packet structures</small>
                <Icon name="chevron" />
              </button>
              <button onClick={() => downloadConfig('txt')}>
                <span>
                  <Icon name="download" />
                  <strong>Equalizer APO (.txt)</strong>
                </span>
                <small>Standard PC acoustic calibration</small>
                <Icon name="chevron" />
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
