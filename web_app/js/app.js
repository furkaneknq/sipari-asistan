/**
 * Ana Uygulama Yöneticisi (App Controller)
 * Sekme navigasyonu, tema geçişi, Supabase Realtime aboneliği ve global kısayollar.
 */

import { config } from './config.js';
import { initRealtime } from './supabase.js';
import { ordersComponent } from './components/orders.js';
import { orderModal } from './components/orderModal.js';
import { callsComponent } from './components/calls.js';
import { customersComponent } from './components/customers.js';
import { productsComponent } from './components/products.js';
import { couriersComponent } from './components/couriers.js';
import { settingsComponent } from './components/settings.js';

class App {
  constructor() {
    this.ordersComponent = ordersComponent;
    this.orderModal = orderModal;
    this.callsComponent = callsComponent;
    this.customersComponent = customersComponent;
    this.productsComponent = productsComponent;
    this.couriersComponent = couriersComponent;
    this.settingsComponent = settingsComponent;
  }

  async init() {
    console.log("🚀 Sipariş Takip Sistemi Web Portu Başlatılıyor...");

    // Tema Ayarı
    this.applyTheme(config.getTheme());
    this.bindThemeToggle();

    // Sekme Navigasyonu
    this.bindTabs();

    // Modalları ve Bileşenleri Başlat
    await Promise.all([
      this.ordersComponent.init(),
      this.orderModal.init(),
      this.callsComponent.init(),
      this.customersComponent.init(),
      this.productsComponent.init(),
      this.couriersComponent.init(),
      this.settingsComponent.init()
    ]);

    // Yeni Sipariş Butonu
    const btnNewOrder = document.getElementById('btn-new-order-global');
    if (btnNewOrder) {
      btnNewOrder.addEventListener('click', () => {
        this.orderModal.open();
      });
    }

    // Supabase Realtime Başlat
    initRealtime({
      onIncomingCall: (call) => this.callsComponent.handleNewCall(call),
      onOrderChange: (payload) => {
        console.log("[Realtime Sipariş Güncellemesi]", payload);
        this.ordersComponent.refresh();
      }
    });

    // Klavye Kısayolları
    this.bindKeyboardShortcuts();

    // Canlı Saat
    this.startClock();
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const btn = document.getElementById('btn-theme-toggle');
    if (btn) {
      btn.innerHTML = theme === 'light' ? '🌙' : '☀️';
      btn.title = theme === 'light' ? 'Koyu Temaya Geç' : 'Açık Temaya Geç';
    }
  }

  bindThemeToggle() {
    const btn = document.getElementById('btn-theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const current = config.getTheme();
        const next = current === 'light' ? 'dark' : 'light';
        config.setTheme(next);
        this.applyTheme(next);
      });
    }
  }

  bindTabs() {
    const tabBtns = document.querySelectorAll('.nav-tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.dataset.tab;
        this.switchTab(targetTab);
      });
    });
  }

  switchTab(tabId) {
    // Sekme Butonlarını Güncelle
    document.querySelectorAll('.nav-tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tabId);
    });

    // İçerik Panellerini Güncelle
    document.querySelectorAll('.tab-pane').forEach(p => {
      p.classList.toggle('active', p.id === `tab-${tabId}`);
    });

    // Sekmeye özel yenileme
    if (tabId === 'orders') this.ordersComponent.refresh();
    else if (tabId === 'calls') this.callsComponent.refreshHistory();
    else if (tabId === 'customers') this.customersComponent.refresh();
    else if (tabId === 'products') this.productsComponent.refresh();
    else if (tabId === 'couriers') this.couriersComponent.refresh();
  }

  bindKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // ESC ile açık modalları kapat
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
      }
      // F2 veya Alt+N: Yeni Sipariş
      if (e.key === 'F2' || (e.altKey && e.key.toLowerCase() === 'n')) {
        e.preventDefault();
        this.orderModal.open();
      }
    });
  }

  startClock() {
    const timeEl = document.getElementById('header-live-time');
    const updateTime = () => {
      if (timeEl) {
        const now = new Date();
        timeEl.textContent = now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }
    };
    updateTime();
    setInterval(updateTime, 1000);
  }

  toast(message) {
    const container = document.getElementById('system-toast-container');
    if (!container) return;

    const el = document.createElement('div');
    el.className = 'system-toast';
    el.innerHTML = `<span>💬</span> <span>${message}</span>`;
    container.appendChild(el);

    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(10px)';
      el.style.transition = 'all 0.25s ease';
      setTimeout(() => el.remove(), 250);
    }, 3200);
  }

  // Global Kısayol Yardımcıları (HTML onclick için)
  quickSetStatus(orderId, status) {
    this.ordersComponent.quickSetStatus(orderId, status);
  }

  openEditOrderModal(orderId) {
    this.orderModal.open({ orderId });
  }
}

// Uygulamayı Global Nesne Olarak Başlat
window.app = new App();
document.addEventListener('DOMContentLoaded', () => {
  window.app.init();
});
