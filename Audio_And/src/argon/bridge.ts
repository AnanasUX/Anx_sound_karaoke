/**
 * BEST SOUND DSP CONTROLLER — Argon Browser Communication Bridge
 * Operates cross-tab or via clipboard without requiring any API keys or network requests.
 */

import { GeminiHandoffPackage } from '../dsp/types'
import { formatGeminiPrompt } from './messages'

export const ARGON_CHANNEL_NAME = 'bestsound_dsp_argon_channel'

export class ArgonBridge {
  private channel: BroadcastChannel | null = null

  constructor() {
    if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
      this.channel = new BroadcastChannel(ARGON_CHANNEL_NAME)
    }
  }

  /**
   * Broadcasts the package across browser contexts (e.g. adjacent Argon tabs)
   */
  public broadcastPackage(pkg: GeminiHandoffPackage): void {
    if (this.channel) {
      this.channel.postMessage({ type: 'GEMINI_HANDOFF_REQUEST', payload: pkg })
    }
  }

  /**
   * Subscribes to incoming Gemini responses from other Argon tabs
   */
  public onResponse(callback: (rawJson: string) => void): () => void {
    if (!this.channel) return () => {}

    const handler = (event: MessageEvent) => {
      if (event.data && event.data.type === 'GEMINI_HANDOFF_RESPONSE') {
        callback(event.data.payload)
      }
    }

    this.channel.addEventListener('message', handler)
    return () => {
      this.channel?.removeEventListener('message', handler)
    }
  }

  /**
   * Copies formatted Markdown prompt to clipboard for 1-click paste into active Gemini chat in Argon
   */
  public async copyPromptToClipboard(pkg: GeminiHandoffPackage): Promise<boolean> {
    const promptText = formatGeminiPrompt(pkg)
    if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(promptText)
        return true
      } catch (err) {
        console.warn('Clipboard write failed, falling back:', err)
      }
    }

    // Fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = promptText
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }

  public destroy(): void {
    if (this.channel) {
      this.channel.close()
      this.channel = null
    }
  }
}

export const argonBridge = new ArgonBridge()
