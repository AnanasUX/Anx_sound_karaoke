/**
 * BEST SOUND DSP CONTROLLER — Gemini Argon Handoff Messages
 * Assembles strict, structured payloads for zero-key acoustic analysis.
 */

import { GeminiHandoffPackage, DspProfile } from '../dsp/types'
import { FftPeak } from '../rta/fft'

export function generateNonce(): string {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36).substring(4)
}

export function buildHandoffPackage(
  profile: DspProfile,
  peaks: FftPeak[],
  avgLevel: number,
  targetGoal: string
): GeminiHandoffPackage {
  const measurementId = `meas-${Date.now()}`
  const nonce = generateNonce()

  return {
    measurementId,
    nonce,
    timestamp: new Date().toISOString(),
    deviceContext: {
      chip: 'BP1048B2',
      firmwareType: 48,
      sampleRate: 44100,
      speakerLayout: '2.1 Bi-Amp (Sub 4" + Mid AIRS + Treble Dome)',
      enclosureVolume: '5L',
    },
    currentSettings: {
      masterPreamp: profile.masterPreamp,
      mvbass: profile.mvbass,
      biamp: profile.biamp,
      bands: profile.bands.map((b) => ({
        id: b.id,
        name: b.name,
        hz: b.hz,
        gain: b.gain,
        q: b.q,
      })),
    },
    measurementSummary: {
      avgLevel,
      resonancePeaks: peaks.map((p) => ({ freq: p.freq, magnitude: p.magnitude })),
      lowFreqRollOff: 45, // typical F3 for this 5L box
      highFreqResponse: 18000,
      targetGoal,
    },
  }
}

/**
 * Generates the Markdown/JSON prompt to paste into Gemini in Argon browser
 */
export function formatGeminiPrompt(pkg: GeminiHandoffPackage): string {
  return `Bạn là Kỹ sư Trưởng Âm thanh DSP chuyên về chip MVSilicon BP1048B2 và cấu hình loa DIY 2.1 Bi-Amp (Thùng 5L, Sub 4" + Mid AIRS + Treble Dome).

Hãy phân tích dữ liệu đo RTA thực tế dưới đây và đưa ra đề xuất hiệu chỉnh PEQ tối ưu cho mục tiêu: "${pkg.measurementSummary.targetGoal}".

QUY TẮC BẮT BUỘC:
1. KHÔNG tạo code, script, binary, hoặc lệnh hex USB.
2. CHỈ TRẢ VỀ DUY NHẤT một khối JSON hợp lệ theo đúng cấu trúc bên dưới, không kèm văn bản ngoài khối JSON.
3. Giữ nguyên "measurementId" và "nonce" chính xác như gói tin vào.
4. Giới hạn an toàn: Gain trong khoảng [-12.0 dB, +6.0 dB], Q trong khoảng [0.2, 12.0], MVBass intensity [0, 100].

DỮ LIỆU ĐO RTA HIỆN TẠI:
\`\`\`json
${JSON.stringify(pkg, null, 2)}
\`\`\`

CẤU TRÚC JSON PHẢI TRẢ VỀ:
\`\`\`json
{
  "measurementId": "${pkg.measurementId}",
  "nonce": "${pkg.nonce}",
  "proposedBands": [
    { "id": 1, "gain": 0.0, "q": 0.8 },
    { "id": 2, "gain": 0.0, "q": 1.1 },
    { "id": 3, "gain": 0.0, "q": 1.3 },
    { "id": 4, "gain": 0.0, "q": 2.4 },
    { "id": 5, "gain": 0.0, "q": 1.2 },
    { "id": 6, "gain": 0.0, "q": 1.4 },
    { "id": 7, "gain": 0.0, "q": 1.8 },
    { "id": 8, "gain": 0.0, "q": 0.9 }
  ],
  "proposedMvbass": {
    "intensity": 65,
    "cutoffFrequency": 75
  },
  "proposedPreamp": -1.5,
  "reasoning": "Giải thích ngắn gọn lý do tinh chỉnh dải tần...",
  "confidenceScore": 0.92
}
\`\`\`
`
}
