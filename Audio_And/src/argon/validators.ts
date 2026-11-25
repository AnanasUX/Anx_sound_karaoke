/**
 * BEST SOUND DSP CONTROLLER — Gemini Response Strict Validator
 * Prevents prompt injection, malicious commands, out-of-bound gains, and nonce mismatches.
 */

import { GeminiResultPackage } from '../dsp/types'
import { clamp, DSP_LIMITS } from '../dsp/limits'

export interface ValidationOutcome {
  valid: boolean
  data?: GeminiResultPackage
  error?: string
}

export function validateGeminiResponse(
  rawInput: string,
  expectedMeasurementId?: string,
  expectedNonce?: string
): ValidationOutcome {
  if (!rawInput || typeof rawInput !== 'string') {
    return { valid: false, error: 'Dữ liệu phản hồi rỗng hoặc không đúng định dạng chuỗi.' }
  }

  // Extract JSON block if surrounded by markdown code fences
  let jsonString = rawInput.trim()
  const codeBlockMatch = jsonString.match(/```(?:json)?\s*([\s\S]*?)\s*```/)
  if (codeBlockMatch) {
    jsonString = codeBlockMatch[1].trim()
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(jsonString)
  } catch (err) {
    return { valid: false, error: `Lỗi phân tích cú pháp JSON: ${String(err)}` }
  }

  if (typeof parsed !== 'object' || parsed === null) {
    return { valid: false, error: 'Phản hồi không phải là một đối tượng JSON hợp lệ.' }
  }

  const obj = parsed as Record<string, unknown>

  // 1. Nonce and MeasurementId verification
  const measurementId = String(obj.measurementId || '')
  const nonce = String(obj.nonce || '')

  if (expectedMeasurementId && measurementId !== expectedMeasurementId) {
    return {
      valid: false,
      error: `MeasurementId không khớp (nhận: ${measurementId}, mong đợi: ${expectedMeasurementId}).`,
    }
  }

  if (expectedNonce && nonce !== expectedNonce) {
    return {
      valid: false,
      error: `Nonce bảo mật không khớp. Gói tin có thể đã bị sửa đổi hoặc là phản hồi cũ.`,
    }
  }

  // 2. Bands validation
  if (!Array.isArray(obj.proposedBands)) {
    return { valid: false, error: 'Thiếu mảng proposedBands trong kết quả phân tích.' }
  }

  const validatedBands = obj.proposedBands.map((b: unknown, idx: number) => {
    const bandObj = (typeof b === 'object' && b !== null ? b : {}) as Record<string, unknown>
    const id = typeof bandObj.id === 'number' ? bandObj.id : idx + 1
    const rawGain = Number(bandObj.gain)
    const rawQ = Number(bandObj.q)
    const rawHz = Number(bandObj.hz)

    const gain = isNaN(rawGain)
      ? 0.0
      : clamp(rawGain, DSP_LIMITS.GAIN_MIN_DB, DSP_LIMITS.GAIN_MAX_DB)

    const q = isNaN(rawQ) ? undefined : clamp(rawQ, DSP_LIMITS.Q_MIN, DSP_LIMITS.Q_MAX)
    const hz = isNaN(rawHz) ? undefined : clamp(rawHz, DSP_LIMITS.FREQ_MIN_HZ, DSP_LIMITS.FREQ_MAX_HZ)

    return {
      id,
      gain: Math.round(gain * 10) / 10,
      q: q !== undefined ? Math.round(q * 100) / 100 : undefined,
      hz: hz !== undefined ? Math.round(hz) : undefined,
    }
  })

  // 3. MVBass validation
  let proposedMvbass: { intensity?: number; cutoffFrequency?: number } | undefined = undefined
  if (typeof obj.proposedMvbass === 'object' && obj.proposedMvbass !== null) {
    const mv = obj.proposedMvbass as Record<string, unknown>
    const rawInt = Number(mv.intensity)
    const rawCutoff = Number(mv.cutoffFrequency)

    proposedMvbass = {
      intensity: isNaN(rawInt)
        ? undefined
        : clamp(rawInt, DSP_LIMITS.MVBASS_INTENSITY_MIN, DSP_LIMITS.MVBASS_INTENSITY_MAX),
      cutoffFrequency: isNaN(rawCutoff)
        ? undefined
        : clamp(rawCutoff, DSP_LIMITS.MVBASS_CUTOFF_MIN_HZ, DSP_LIMITS.MVBASS_CUTOFF_MAX_HZ),
    }
  }

  // 4. Preamp validation
  const rawPreamp = Number(obj.proposedPreamp)
  const proposedPreamp = isNaN(rawPreamp)
    ? undefined
    : clamp(rawPreamp, DSP_LIMITS.PREAMP_MIN_DB, DSP_LIMITS.PREAMP_MAX_DB)

  // 5. Reasoning sanitization
  let reasoning = String(obj.reasoning || 'Không có mô tả chi tiết.')
  // Strip potentially hazardous HTML/tags
  reasoning = reasoning.replace(/<[^>]*>/g, '').trim().substring(0, 500)

  // 6. Confidence Score
  const rawScore = Number(obj.confidenceScore)
  const confidenceScore = isNaN(rawScore) ? 0.85 : clamp(rawScore, 0.0, 1.0)

  return {
    valid: true,
    data: {
      measurementId,
      nonce,
      proposedBands: validatedBands,
      proposedMvbass,
      proposedPreamp,
      reasoning,
      confidenceScore,
    },
  }
}
