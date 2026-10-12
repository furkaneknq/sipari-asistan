/**
 * Web Audio API ile harici ses dosyası indirmeden
 * şık bildirim ve çağrı zili tonları üretici modülü.
 */

import { config } from './config.js';

let audioCtx = null;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

export const sound = {
  /**
   * Gelen arama zili (yumuşak, iki tonlu otel/çağrı resepsiyon ding-dong sesi)
   */
  playIncomingCallTone() {
    if (!config.isSoundEnabled()) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;

      // 1. Ton (Yüksek: 784 Hz - G5)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(783.99, now);
      gain1.gain.setValueAtTime(0.25, now);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.55);

      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(now);
      osc1.stop(now + 0.6);

      // 2. Ton (Alçak ve pürüzsüz: 659.25 Hz - E5)
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(659.25, now + 0.22);
      gain2.gain.setValueAtTime(0.28, now + 0.22);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.85);

      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(now + 0.22);
      osc2.stop(now + 0.9);
    } catch (e) {
      console.warn("Ses çalınamadı (tarayıcı etkileşim izni gerekebilir):", e);
    }
  },

  /**
   * Kısa onay / yeni sipariş "bip/chime" sesi
   */
  playSuccessTone() {
    if (!config.isSoundEnabled()) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(523.25, now); // C5
      osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.12); // E5

      gain.gain.setValueAtTime(0.18, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.4);
    } catch (e) {
      console.warn("Ses çalınamadı:", e);
    }
  }
};
