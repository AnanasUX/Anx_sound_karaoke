'use client'

import { useEffect, useMemo, useState } from 'react'
import { DspProfile, DspBand } from '../dsp/types'
import { VERIFIED_PROFILES, computeProfileDiff, ProfileDiff } from '../dsp/profiles'
import { renderDspIni } from '../dsp/ini-renderer'
import { renderDspC } from '../dsp/c-renderer'
import { buildHandoffPackage, formatGeminiPrompt } from '../argon/messages'
import { validateGeminiResponse } from '../argon/validators'
import { argonBridge } from '../argon/bridge'
import { DspFlashStateMachine } from '../otg/state-machine'
import { MockDspTransport } from '../otg/mock-transport'
import { WebUsbDspTransport } from '../otg/webusb-transport'
import { FftPeak } from '../rta/fft'

const goals = [
  {
    id: 'balanced',
    name: 'Cân bằng toàn dải',
    detail: 'Phản hồi trung tính, phù hợp nghe đa thể loại',
    accent: '#00e5ff',
  },
  {
    id: 'bass',
    name: 'Bass sâu & gọn',
    detail: 'Ưu tiên 45–120 Hz, kiểm soát cộng hưởng thùng 5L',
    accent: '#ff8a3d',
  },
  {
    id: 'vocal',
    name: 'Vocal rõ & ngọt',
    detail: 'Tối ưu 500 Hz–3 kHz cho giọng hát mộc, rõ nét',
    accent: '#b4a7ff',
  },
  {
    id: 'clean',
    name: 'Chống xì & nhiễu',
    detail: 'Tối ưu gain tránh tiếng rít và méo tiếng công suất',
    accent: '#30d9f0',
  },
]

const steps = ['RTA Đo', 'Mục tiêu', 'Argon AI', 'Nạp OTG']

function MiniIcon({
  name,
  size = 18,
}: {
  name: 'ai' | 'mic' | 'file' | 'usb' | 'check' | 'settings' | 'arrow' | 'shield' | 'copy'
  size?: number
}) {
  const paths: Record<string, string> = {
    ai: 'M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M19 5l-2 2M7 17l-2 2m7-11a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z',
    mic: 'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3ZM5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-4 0h8',
    file: 'M6 2h8l4 4v16H6V2Zm8 0v5h5M9 12h6m-6 4h6',
    usb: 'M12 2v13m0-13 3 3m-3-3L9 5m3 10-4-4m4 4 4-4M8 11H5v6m11-6h3v6M5 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm14 0v4h-4v-4h4Z',
    check: 'm5 12 4 4L19 6',
    settings:
      'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-6v3m0 14v3M2 12h3m14 0h3M4.9 4.9 7 7m10 10 2.1 2.1m0-14.2L17 7M7 17l-2.1 2.1',
    arrow: 'm9 18 6-6-6-6',
    shield: 'M12 2 4 5v6c0 5.2 3.4 9 8 11 4.6-2 8-5.8 8-11V5l-8-3Zm-3 10 2 2 4-5',
    copy: 'M8 4v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7.83a2 2 0 0 0-.59-1.42l-4.83-4.83A2 2 0 0 0 15.17 1H10a2 2 0 0 0-2 2v1H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2',
  }
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
      <path d={paths[name]} />
    </svg>
  )
}

interface AICalibrationPanelProps {
  currentProfile: DspProfile
  peaks: FftPeak[]
  avgLevel: number
  onApplyProfile: (profile: DspProfile) => void
}

export default function AICalibrationPanel({
  currentProfile,
  peaks,
  avgLevel,
  onApplyProfile,
}: AICalibrationPanelProps) {
  const [step, setStep] = useState(0)
  const [goal, setGoal] = useState('balanced')
  const [sourceMode, setSourceMode] = useState<'argon' | 'ready'>('argon')
  const [readyProfileId, setReadyProfileId] = useState('bo-8ohm-24v')
  const [argonOpen, setArgonOpen] = useState(false)
  const [argonConnected, setArgonConnected] = useState(true)

  // Gemini Argon Handoff State
  const [handoffPkg, setHandoffPkg] = useState<ReturnType<typeof buildHandoffPackage> | null>(null)
  const [copiedPrompt, setCopiedPrompt] = useState(false)
  const [geminiJsonInput, setGeminiJsonInput] = useState('')
  const [parseError, setParseError] = useState<string | null>(null)
  const [proposedProfile, setProposedProfile] = useState<DspProfile | null>(null)
  const [diff, setDiff] = useState<ProfileDiff | null>(null)

  // OTG Flash state
  const [transportType, setTransportType] = useState<'webusb' | 'mock'>('mock')
  const [flashProgress, setFlashProgress] = useState<{
    status: string
    progress: number
    message: string
  }>({
    status: 'idle',
    progress: 0,
    message: 'Sẵn sàng nạp qua cổng USB OTG',
  })

  // Prepare package when step enters Argon stage
  useEffect(() => {
    const pkg = buildHandoffPackage(currentProfile, peaks, avgLevel, goal)
    setHandoffPkg(pkg)
  }, [currentProfile, peaks, avgLevel, goal])

  // Subscribe to Argon cross-tab broadcast
  useEffect(() => {
    const unsubscribe = argonBridge.onResponse((rawJson) => {
      setGeminiJsonInput(rawJson)
      handleParseGemini(rawJson)
    })
    return () => unsubscribe()
  }, [handoffPkg])

  const handleCopyPrompt = async () => {
    if (!handoffPkg) return
    const success = await argonBridge.copyPromptToClipboard(handoffPkg)
    if (success) {
      setCopiedPrompt(true)
      setTimeout(() => setCopiedPrompt(false), 2500)
    }
  }

  const handleParseGemini = (inputToParse?: string) => {
    setParseError(null)
    const text = inputToParse || geminiJsonInput
    if (!text.trim()) {
      setParseError('Vui lòng dán kết quả JSON từ Gemini trong trình duyệt Argon!')
      return
    }

    const outcome = validateGeminiResponse(text, handoffPkg?.measurementId, handoffPkg?.nonce)
    if (!outcome.valid || !outcome.data) {
      setParseError(outcome.error || 'Dữ liệu không hợp lệ.')
      return
    }

    const data = outcome.data
    // Build proposed profile
    const updatedBands: DspBand[] = currentProfile.bands.map((band, idx) => {
      const prop = data.proposedBands.find((b) => b.id === band.id) || data.proposedBands[idx]
      return {
        ...band,
        gain: prop?.gain !== undefined ? prop.gain : band.gain,
        q: prop?.q !== undefined ? prop.q : band.q,
      }
    })

    const newProfile: DspProfile = {
      ...currentProfile,
      id: `ai-gemini-${Date.now()}`,
      name: `Gemini AI: ${goal.toUpperCase()}`,
      category: 'ai_generated',
      masterPreamp: data.proposedPreamp ?? currentProfile.masterPreamp,
      mvbass: {
        ...currentProfile.mvbass,
        intensity: data.proposedMvbass?.intensity ?? currentProfile.mvbass.intensity,
        cutoffFrequency: data.proposedMvbass?.cutoffFrequency ?? currentProfile.mvbass.cutoffFrequency,
      },
      bands: updatedBands,
      description: data.reasoning,
      verified: true,
    }

    setProposedProfile(newProfile)
    setDiff(computeProfileDiff(currentProfile, newProfile))
    setStep(2) // Jump to review / config diff
  }

  const applyReadyProfile = () => {
    const found = VERIFIED_PROFILES.find((p) => p.id === readyProfileId)
    if (found) {
      onApplyProfile(found)
      setStep(2)
    }
  }

  const handleApplyToEq = () => {
    if (proposedProfile) {
      onApplyProfile(proposedProfile)
      setStep(3)
    }
  }

  const downloadFile = (format: 'ini' | 'c') => {
    const target = proposedProfile || currentProfile
    const content = format === 'ini' ? renderDspIni(target) : renderDspC(target)
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${target.id || 'dsp_tuned'}.${format}`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const executeOtgFlash = async () => {
    const target = proposedProfile || currentProfile
    const transport = transportType === 'webusb' ? new WebUsbDspTransport() : new MockDspTransport()
    const stateMachine = new DspFlashStateMachine(transport)

    await stateMachine.executeFlashPipeline(target, (p) => {
      setFlashProgress({
        status: p.status,
        progress: p.progress,
        message: p.message,
      })
    })
  }

  return (
    <section
      id="ai-calibration"
      className="mt-2.5 overflow-hidden rounded-xl border border-[#29313a] bg-[linear-gradient(145deg,#171b21,#111419)] shadow-[inset_0_1px_rgba(255,255,255,.03),0_18px_45px_rgba(0,0,0,.3)]"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 border-b border-[#252b33] px-4 py-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl border border-[#214c56] bg-[#0c252b] text-[#00e5ff] shadow-[inset_0_0_14px_rgba(0,229,255,.08)]">
            <MiniIcon name="ai" size={21} />
          </span>
          <div>
            <span className="font-mono text-[7px] font-semibold tracking-[.18em] text-[#60717c]">
              ACOUSTIC RTA ASSISTANT · BP1048B2
            </span>
            <h2 className="mt-1 text-[15px] font-semibold tracking-[-.02em] text-white">
              Gemini Argon Calibration
            </h2>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setArgonOpen(true)}
          className="flex min-h-10 items-center justify-between gap-3 rounded-lg border border-[#453d24] bg-[#211d12] px-3 font-mono text-[8px] text-[#d7c476] transition hover:border-[#746633] md:justify-center"
        >
          <MiniIcon name="settings" size={15} />
          <span className="flex flex-col text-left">
            <small className="text-[6px] tracking-[.12em] text-[#776d43]">ARGON BROWSER</small>
            {argonConnected ? 'SẴN SÀNG KẾT NỐI' : 'CHƯA MỞ TAB ARGON'}
          </span>
          <MiniIcon name="arrow" size={13} />
        </button>
      </div>

      {/* Stepper Navigation */}
      <div className="grid grid-cols-4 border-b border-[#252b33] bg-[#0e1115] px-3 md:px-6">
        {steps.map((label, index) => (
          <button
            type="button"
            key={label}
            onClick={() => setStep(index)}
            className={`relative flex min-h-14 items-center justify-center gap-2 border-b-2 font-mono text-[7px] transition ${
              index === step
                ? 'border-[#00e5ff] text-[#c8faff]'
                : index < step
                  ? 'border-transparent text-[#00e676]'
                  : 'border-transparent text-[#48515c]'
            }`}
          >
            <span
              className={`grid size-5 place-items-center rounded-full border text-[7px] ${
                index < step
                  ? 'border-[#1c5a3d] bg-[#11281d]'
                  : index === step
                    ? 'border-[#176776] bg-[#102a30]'
                    : 'border-[#303640] bg-[#15181d]'
              }`}
            >
              {index < step ? <MiniIcon name="check" size={11} /> : index + 1}
            </span>
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Step Content */}
      <div className="p-4 md:p-6">
        {/* Step 0: RTA Measurement Overview */}
        {step === 0 && (
          <div className="space-y-4">
            <div className="rounded-lg border border-[#2b3542] bg-[#14181f] p-4">
              <span className="font-mono text-[7px] tracking-wider text-[#798897]">
                DỮ LIỆU ĐO RTA MICROPHONE
              </span>
              <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded border border-[#1f262f] bg-[#0b0e12] p-3">
                  <small className="text-[7px] text-[#556372]">MỨC ÂM BÌNH QUÂN</small>
                  <p className="mt-1 font-mono text-sm text-[#00e5ff]">{avgLevel.toFixed(1)} dBFS</p>
                </div>
                <div className="rounded border border-[#1f262f] bg-[#0b0e12] p-3">
                  <small className="text-[7px] text-[#556372]">ĐỈNH CỘNG HƯỞNG (PEAK 1)</small>
                  <p className="mt-1 font-mono text-sm text-[#ff8a3d]">
                    {peaks[0] ? `${peaks[0].freq} Hz (${peaks[0].magnitude} dB)` : '165 Hz (Box)'}
                  </p>
                </div>
                <div className="rounded border border-[#1f262f] bg-[#0b0e12] p-3">
                  <small className="text-[7px] text-[#556372]">ĐỈNH 2 (MID/TREBLE)</small>
                  <p className="mt-1 font-mono text-sm text-[#b4a7ff]">
                    {peaks[1] ? `${peaks[1].freq} Hz (${peaks[1].magnitude} dB)` : '2.5 kHz'}
                  </p>
                </div>
                <div className="rounded border border-[#1f262f] bg-[#0b0e12] p-3">
                  <small className="text-[7px] text-[#556372]">THỂ TÍCH THÙNG LOA</small>
                  <p className="mt-1 font-mono text-sm text-[#d4af37]">5.0 Lít (Bi-Amp)</p>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded-lg border border-[#00e5ff] bg-[#0c252b] px-4 py-2 font-mono text-[8px] text-[#00e5ff] transition hover:bg-[#123841]"
              >
                TIẾP TỤC CHỌN MỤC TIÊU →
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Goal Selection */}
        {step === 1 && (
          <div className="space-y-4">
            <span className="font-mono text-[7px] tracking-wider text-[#798897]">
              CHỌN MỤC TIÊU TỐI ƯU HÓA ÂM THANH
            </span>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {goals.map((g) => (
                <button
                  type="button"
                  key={g.id}
                  onClick={() => setGoal(g.id)}
                  className={`rounded-lg border p-4 text-left transition ${
                    goal === g.id
                      ? 'border-[#00e5ff] bg-[#0d2228]'
                      : 'border-[#262f3a] bg-[#12161c] hover:border-[#3a4757]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">{g.name}</span>
                    <span className="size-2 rounded-full" style={{ backgroundColor: g.accent }} />
                  </div>
                  <p className="mt-2 text-xs text-[#7e8f9e]">{g.detail}</p>
                </button>
              ))}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setSourceMode('argon')}
                className={`rounded px-3 py-1.5 font-mono text-[7px] ${
                  sourceMode === 'argon' ? 'bg-[#00e5ff] text-black font-bold' : 'bg-[#181d24] text-[#8fa2b4]'
                }`}
              >
                PHÂN TÍCH VỚI GEMINI ARGON
              </button>
              <button
                type="button"
                onClick={() => setSourceMode('ready')}
                className={`rounded px-3 py-1.5 font-mono text-[7px] ${
                  sourceMode === 'ready' ? 'bg-[#d4af37] text-black font-bold' : 'bg-[#181d24] text-[#8fa2b4]'
                }`}
              >
                CHỌN CẤU HÌNH CÓ SẴN (PRESETS)
              </button>
            </div>

            {sourceMode === 'ready' ? (
              <div className="rounded-lg border border-[#2b3542] bg-[#14181f] p-4">
                <span className="font-mono text-[7px] text-[#798897]">CHỌN PROFILE ĐÃ ĐƯỢC XÁC MINH</span>
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {VERIFIED_PROFILES.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setReadyProfileId(p.id)}
                      className={`rounded border p-3 text-left transition ${
                        readyProfileId === p.id
                          ? 'border-[#d4af37] bg-[#221f14]'
                          : 'border-[#222933] bg-[#0c0f13]'
                      }`}
                    >
                      <b className="text-sm text-white">{p.name}</b>
                      <p className="mt-1 text-xs text-[#7e8f9e]">{p.description}</p>
                    </button>
                  ))}
                </div>
                <div className="mt-4 flex justify-end">
                  <button
                    type="button"
                    onClick={applyReadyProfile}
                    className="rounded bg-[#d4af37] px-4 py-2 font-mono text-[8px] font-bold text-black"
                  >
                    ÁP DỤNG PROFILE NÀY →
                  </button>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-[#2b3542] bg-[#14181f] p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h4 className="font-semibold text-white">Chuyển tiếp đến Gemini (Argon)</h4>
                    <p className="text-xs text-[#7e8f9e]">
                      Sao chép prompt an toàn, dán vào tab Gemini đang đăng nhập trong Argon, sau đó dán kết quả JSON vào đây.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyPrompt}
                    className="flex items-center gap-2 rounded border border-[#00e5ff] bg-[#0a2329] px-4 py-2 font-mono text-[8px] font-bold text-[#00e5ff] hover:bg-[#113842]"
                  >
                    <MiniIcon name="copy" size={14} />
                    {copiedPrompt ? 'ĐÃ SAO CHÉP PROMPT!' : 'SAO CHÉP PROMPT CHO GEMINI'}
                  </button>
                </div>

                <div className="mt-4">
                  <label className="block font-mono text-[7px] text-[#798897]">
                    DÁN KHỐI JSON PHẢN HỒI TỪ GEMINI:
                  </label>
                  <textarea
                    rows={5}
                    value={geminiJsonInput}
                    onChange={(e) => setGeminiJsonInput(e.target.value)}
                    placeholder='{"measurementId": "...", "nonce": "...", "proposedBands": [...]}'
                    className="mt-1 w-full rounded border border-[#2b3542] bg-[#0a0d11] p-3 font-mono text-xs text-white placeholder-[#384351] focus:border-[#00e5ff] focus:outline-none"
                  />
                  {parseError && (
                    <p className="mt-1 font-mono text-xs text-[#ff5252]">⚠ {parseError}</p>
                  )}
                  <div className="mt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => handleParseGemini()}
                      className="rounded bg-[#00e5ff] px-4 py-2 font-mono text-[8px] font-bold text-black hover:bg-[#33ebff]"
                    >
                      XÁC THỰC VÀ XEM TRƯỚC DIFF →
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Diff Preview & Confirmation */}
        {step === 2 && (
          <div className="space-y-4">
            <span className="font-mono text-[7px] tracking-wider text-[#798897]">
              SO SÁNH THAY ĐỔI TRƯỚC KHI ÁP DỤNG (DIFF PREVIEW)
            </span>

            {proposedProfile && diff && (
              <div className="rounded-lg border border-[#2b3542] bg-[#14181f] p-4">
                <div className="mb-3 flex items-center justify-between border-b border-[#222933] pb-2">
                  <b className="text-sm text-white">{proposedProfile.name}</b>
                  <span className="font-mono text-[7px] text-[#00e5ff]">
                    {proposedProfile.description}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {diff.bandDiffs.map((bd) => (
                    <div
                      key={bd.id}
                      className="rounded border border-[#1e252e] bg-[#0c0f13] p-2 text-center"
                    >
                      <small className="block text-[7px] text-[#5d6c7b]">{bd.name} ({bd.hz}Hz)</small>
                      <span className="font-mono text-xs text-[#8094a6]">{bd.oldGain} dB</span>
                      <span className="mx-1 text-[#424d5a]">→</span>
                      <b
                        className={`font-mono text-xs ${
                          bd.deltaGain > 0
                            ? 'text-[#00e5ff]'
                            : bd.deltaGain < 0
                              ? 'text-[#ff8a3d]'
                              : 'text-white'
                        }`}
                      >
                        {bd.newGain} dB ({bd.deltaGain > 0 ? `+${bd.deltaGain}` : bd.deltaGain})
                      </b>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex flex-wrap gap-3 border-t border-[#222933] pt-3">
                  <button
                    type="button"
                    onClick={handleApplyToEq}
                    className="rounded bg-[#00e5ff] px-4 py-2 font-mono text-[8px] font-bold text-black"
                  >
                    ÁP DỤNG VÀO BỘ ĐIỀU KHIỂN EQ
                  </button>
                  <button
                    type="button"
                    onClick={() => downloadFile('ini')}
                    className="rounded border border-[#2b3542] bg-[#10141a] px-3 py-2 font-mono text-[8px] text-white hover:border-[#00e5ff]"
                  >
                    TẢI FILE .INI
                  </button>
                  <button
                    type="button"
                    onClick={() => downloadFile('c')}
                    className="rounded border border-[#2b3542] bg-[#10141a] px-3 py-2 font-mono text-[8px] text-white hover:border-[#00e5ff]"
                  >
                    TẢI FILE .C
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: OTG Flasher Pipeline */}
        {step === 3 && (
          <div className="space-y-4">
            <span className="font-mono text-[7px] tracking-wider text-[#798897]">
              NẠP THIẾT BỊ QUA CỔNG USB OTG (BP1048B2)
            </span>

            <div className="rounded-lg border border-[#2b3542] bg-[#14181f] p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-white">Chế độ giao tiếp phần cứng</h4>
                  <p className="text-xs text-[#7e8f9e]">
                    Đảm bảo an toàn: Tự động sao lưu thanh ghi và kiểm tra tính toàn vẹn (Read-back Verify).
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setTransportType('mock')}
                    className={`rounded px-3 py-1 font-mono text-[7px] ${
                      transportType === 'mock' ? 'bg-[#00e5ff] text-black font-bold' : 'bg-[#181d24] text-white'
                    }`}
                  >
                    MÔ PHỎNG (MOCK)
                  </button>
                  <button
                    type="button"
                    onClick={() => setTransportType('webusb')}
                    className={`rounded px-3 py-1 font-mono text-[7px] ${
                      transportType === 'webusb' ? 'bg-[#00e5ff] text-black font-bold' : 'bg-[#181d24] text-white'
                    }`}
                  >
                    CỔNG THẬT (WEBUSB)
                  </button>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-4">
                <div className="flex justify-between font-mono text-xs">
                  <span className="text-[#8fa2b4]">{flashProgress.message}</span>
                  <span className="text-[#00e5ff]">{flashProgress.progress}%</span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[#0a0d11]">
                  <div
                    className="h-full bg-[linear-gradient(90deg,#00e5ff,#00e676)] transition-all duration-300"
                    style={{ width: `${flashProgress.progress}%` }}
                  />
                </div>
              </div>

              <div className="mt-4 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={executeOtgFlash}
                  className="rounded bg-[#00e676] px-5 py-2 font-mono text-[8px] font-bold text-black hover:bg-[#33ff99]"
                >
                  BẮT ĐẦU NẠP VÀ XÁC MINH (FLASH & VERIFY)
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
