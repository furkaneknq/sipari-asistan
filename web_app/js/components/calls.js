/**
 * Gelen Aramalar (Incoming Calls) Bileşeni
 * Anlık arama yakalama (Realtime), sesli uyarı zili,
 * ekranın sağ üstünde beliren zengin popup bildirimi ve geçmiş tablosu.
 */

import { callsApi, customersApi } from '../supabase.js';
import { sound } from '../sound.js';

let activeToasts = [];

export const callsComponent = {
  async init() {
    this.bindEvents();
    await this.refreshHistory();
  },

  bindEvents() {
    const refreshBtn = document.getElementById('btn-refresh-calls');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refreshHistory());
    }
  },

  /**
   * Supabase Realtime'dan yeni arama düştüğünde çağrılır
   */
  async handleNewCall(callRecord) {
    console.log("[Arama Bildirimi]", callRecord);
    sound.playIncomingCallTone();

    const phone = callRecord.phone_number;
    let customer = null;

    if (callRecord.customer_id) {
      try {
        customer = await customersApi.get(callRecord.customer_id);
      } catch (e) {
        console.warn(e);
      }
    } else if (phone) {
      try {
        customer = await customersApi.findByPhone(phone);
      } catch (e) {
        console.warn(e);
      }
    }

    this.showCallToast(callRecord, customer);
    this.refreshHistory();
  },

  showCallToast(callRecord, customer) {
    const container = document.getElementById('call-toast-container');
    if (!container) return;

    const phone = callRecord.phone_number || "Numarasız";
    const custName = customer ? customer.name : "Kayıtsız Numara";
    const toastId = `call-toast-${Date.now()}`;

    const toast = document.createElement('div');
    toast.className = 'call-toast';
    toast.id = toastId;

    toast.innerHTML = `
      <div class="call-toast-header">
        <div class="call-toast-badge">
          <div class="call-pulse-dot"></div>
          GELEN ARAMA
        </div>
        <button type="button" class="btn-close-toast" style="color:var(--text-muted); font-size:1.2rem; line-height:1;">×</button>
      </div>

      <div>
        <div class="call-phone-number">${phone}</div>
        <div class="call-customer-name" style="margin-top:2px;">
          ${customer ? `👤 ${custName}` : `⚠️ Yeni Müşteri`}
        </div>
      </div>

      <div class="call-toast-actions">
        ${customer ? `
          <button type="button" class="btn-primary btn-toast-order" style="grid-column: 1 / -1; justify-content:center;">
            🛍️ Sipariş Oluştur
          </button>
        ` : `
          <button type="button" class="btn-primary btn-toast-guest" style="font-size:0.85rem; justify-content:center;">
            ⚡ Hızlı Sipariş
          </button>
          <button type="button" class="btn-secondary btn-toast-new-cust" style="font-size:0.85rem; justify-content:center;">
            ➕ Müşteri Kaydet
          </button>
        `}
      </div>
    `;

    // Buton Eylemleri
    const closeBtn = toast.querySelector('.btn-close-toast');
    closeBtn.addEventListener('click', () => this.dismissToast(toastId));

    const orderBtn = toast.querySelector('.btn-toast-order');
    if (orderBtn && customer) {
      orderBtn.addEventListener('click', () => {
        callsApi.markProcessed(callRecord.id);
        window.app.orderModal.open({ prefillCustomerId: customer.id });
        this.dismissToast(toastId);
      });
    }

    const guestBtn = toast.querySelector('.btn-toast-guest');
    if (guestBtn) {
      guestBtn.addEventListener('click', () => {
        callsApi.markProcessed(callRecord.id);
        window.app.orderModal.open({ prefillPhone: phone });
        this.dismissToast(toastId);
      });
    }

    const newCustBtn = toast.querySelector('.btn-toast-new-cust');
    if (newCustBtn) {
      newCustBtn.addEventListener('click', () => {
        callsApi.markProcessed(callRecord.id);
        window.app.customersComponent.openNewCustomerModal(phone);
        this.dismissToast(toastId);
      });
    }

    // 35 saniye sonra otomatik kapat (mouse üzerindeyken durdur)
    let closeTimeout = setTimeout(() => this.dismissToast(toastId), 35000);
    toast.addEventListener('mouseenter', () => clearTimeout(closeTimeout));
    toast.addEventListener('mouseleave', () => {
      closeTimeout = setTimeout(() => this.dismissToast(toastId), 15000);
    });

    container.appendChild(toast);
    activeToasts.push(toastId);
  },

  dismissToast(toastId) {
    const el = document.getElementById(toastId);
    if (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateX(100%)';
      setTimeout(() => el.remove(), 250);
    }
  },

  async refreshHistory() {
    const tbody = document.getElementById('calls-table-body');
    if (!tbody) return;

    try {
      const calls = await callsApi.list({ limit: 40 });
      if (calls.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 3rem; color: var(--text-muted);">Henüz arama kaydı yok.</td></tr>`;
        return;
      }

      tbody.innerHTML = calls.map(call => {
        const timeStr = new Date(call.created_at).toLocaleString('tr-TR', {
          day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
        });
        const custName = call.customers?.name || '<span style="color:var(--text-subtle);">Kayıtsız</span>';
        const isProcessed = call.is_processed;

        return `
          <tr>
            <td><strong>${call.phone_number}</strong></td>
            <td>${custName}</td>
            <td>${timeStr}</td>
            <td>
              ${isProcessed
                ? `<span class="badge-status badge-delivered">İşlendi</span>`
                : `<span class="badge-status badge-new">Bekliyor</span>`}
            </td>
            <td>
              <button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.orderModal.open({ prefillPhone: '${call.phone_number}', prefillCustomerId: '${call.customer_id || ''}' })">
                🛍️ Sipariş Aç
              </button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--danger);">Aramalar yüklenemedi: ${err.message}</td></tr>`;
    }
  }
};
