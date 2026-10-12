/**
 * Ayarlar (Settings) Bileşeni
 * Supabase bağlantı yapılandırması, bağlantı testi, tema ve bildirim sesleri.
 */

import { config } from '../config.js';
import { testConnection, resetClient, initRealtime } from '../supabase.js';
import { sound } from '../sound.js';

export const settingsComponent = {
  init() {
    this.bindEvents();
    this.loadValues();
  },

  bindEvents() {
    // Bağlantı Testi
    const btnTest = document.getElementById('btn-test-db');
    if (btnTest) {
      btnTest.addEventListener('click', () => this.testDbConnection());
    }

    // Ayarları Kaydet
    const form = document.getElementById('settings-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveSettings();
      });
    }

    // Varsayılanlara Sıfırla
    const btnReset = document.getElementById('btn-reset-db');
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        if (confirm("Supabase ayarları varsayılanlara sıfırlansın mı?")) {
          config.resetDefaults();
          this.loadValues();
          resetClient();
          window.app.toast("Ayarlar sıfırlandı.");
        }
      });
    }

    // Ses Testi Butonu
    const btnTestSound = document.getElementById('btn-test-sound');
    if (btnTestSound) {
      btnTestSound.addEventListener('click', () => {
        sound.playIncomingCallTone();
      });
    }

    // Ses Açık/Kapalı
    const soundToggle = document.getElementById('setting-sound-enabled');
    if (soundToggle) {
      soundToggle.addEventListener('change', (e) => {
        config.setSoundEnabled(e.target.checked);
        window.app.toast(e.target.checked ? "Sesli bildirimler açıldı 🔔" : "Sesli bildirimler kapatıldı 🔕");
      });
    }
  },

  loadValues() {
    const urlInput = document.getElementById('setting-supabase-url');
    const keyInput = document.getElementById('setting-supabase-key');
    const soundToggle = document.getElementById('setting-sound-enabled');

    if (urlInput) urlInput.value = config.getSupabaseUrl();
    if (keyInput) keyInput.value = config.getSupabaseKey();
    if (soundToggle) soundToggle.checked = config.isSoundEnabled();
  },

  async testDbConnection() {
    const statusBox = document.getElementById('db-test-result');
    if (statusBox) {
      statusBox.style.display = 'block';
      statusBox.style.background = 'var(--warning-light)';
      statusBox.style.color = 'var(--warning)';
      statusBox.textContent = 'Bağlantı test ediliyor...';
    }

    const res = await testConnection();
    if (statusBox) {
      if (res.ok) {
        statusBox.style.background = 'var(--success-light)';
        statusBox.style.color = 'var(--success)';
        statusBox.textContent = '✅ Supabase bağlantısı başarılı!';
        sound.playSuccessTone();
      } else {
        statusBox.style.background = 'var(--danger-light)';
        statusBox.style.color = 'var(--danger)';
        statusBox.textContent = '❌ Bağlantı başarısız: ' + res.error;
      }
    }
  },

  saveSettings() {
    const url = document.getElementById('setting-supabase-url')?.value.trim();
    const key = document.getElementById('setting-supabase-key')?.value.trim();

    if (!url || !key) {
      alert("Supabase URL ve Key boş bırakılamaz!");
      return;
    }

    config.setSupabaseUrl(url);
    config.setSupabaseKey(key);
    resetClient();

    // Realtime'ı yeniden başlat
    initRealtime({
      onIncomingCall: (call) => window.app.callsComponent.handleNewCall(call),
      onOrderChange: () => window.app.ordersComponent.refresh()
    });

    window.app.toast("Ayarlar kaydedildi! Yeniden bağlanılıyor...");
    this.testDbConnection();
  }
};
