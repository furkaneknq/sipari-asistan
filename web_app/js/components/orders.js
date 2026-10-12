/**
 * Siparişler Paneli Bileşeni
 * Sipariş listesi, KPI istatistikleri, filtreler, hızlı durum güncelleme
 * ve detay çekmecesi mantığı.
 */

import { ordersApi, couriersApi } from '../supabase.js';
import { sound } from '../sound.js';

let currentOrders = [];
let selectedOrderId = null;
let couriersList = [];

// Filtre durumları
const filters = {
  date: new Date().toISOString().slice(0, 10), // Bugün
  status: "all",
  courierId: "__all__",
  search: ""
};

export const ordersComponent = {
  async init() {
    this.bindEvents();
    await this.loadCouriers();
    await this.refresh();
  },

  bindEvents() {
    // Hızlı Tarih Butonları
    document.querySelectorAll('.filter-date-chip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-date-chip').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');

        const mode = e.currentTarget.dataset.mode;
        const today = new Date();

        if (mode === 'today') {
          filters.date = today.toISOString().slice(0, 10);
        } else if (mode === 'yesterday') {
          const y = new Date(today);
          y.setDate(y.getDate() - 1);
          filters.date = y.toISOString().slice(0, 10);
        } else if (mode === 'all') {
          filters.date = null;
        }

        const dateInput = document.getElementById('filter-order-date');
        if (dateInput) {
          dateInput.value = filters.date || '';
        }

        this.refresh();
      });
    });

    // Manuel Tarih Seçimi
    const dateInput = document.getElementById('filter-order-date');
    if (dateInput) {
      dateInput.value = filters.date;
      dateInput.addEventListener('change', (e) => {
        filters.date = e.target.value || null;
        document.querySelectorAll('.filter-date-chip').forEach(b => b.classList.remove('active'));
        this.refresh();
      });
    }

    // Durum Filtresi
    const statusSelect = document.getElementById('filter-order-status');
    if (statusSelect) {
      statusSelect.addEventListener('change', (e) => {
        filters.status = e.target.value;
        this.refresh();
      });
    }

    // Kurye Filtresi
    const courierSelect = document.getElementById('filter-order-courier');
    if (courierSelect) {
      courierSelect.addEventListener('change', (e) => {
        filters.courierId = e.target.value;
        this.refresh();
      });
    }

    // Arama Kutusu (Debounce ile)
    const searchInput = document.getElementById('search-orders-input');
    if (searchInput) {
      let timer = null;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          filters.search = e.target.value;
          this.refresh();
        }, 250);
      });
    }

    // Yenile Butonu
    const refreshBtn = document.getElementById('btn-refresh-orders');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refresh());
    }
  },

  async loadCouriers() {
    try {
      couriersList = await couriersApi.list({ activeOnly: true });
      const select = document.getElementById('filter-order-courier');
      if (select) {
        select.innerHTML = `
          <option value="__all__">Tüm Kuryeler</option>
          <option value="__none__">Atanmamış</option>
          ${couriersList.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
        `;
      }
    } catch (err) {
      console.warn("Kuryeler yüklenemedi:", err);
    }
  },

  async refresh() {
    const tbody = document.getElementById('orders-table-body');
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 2rem; color: var(--text-muted);">Siparişler yükleniyor...</td></tr>`;
    }

    try {
      currentOrders = await ordersApi.list({
        date: filters.date,
        status: filters.status,
        courierId: filters.courierId,
        search: filters.search
      });

      this.renderKpi();
      this.renderTable();

      // Seçili sipariş varsa çekmecesini güncelle, yoksa ilkini seç
      if (currentOrders.length > 0) {
        const stillExists = currentOrders.find(o => o.id === selectedOrderId);
        if (stillExists) {
          this.selectOrder(stillExists.id);
        } else {
          this.selectOrder(currentOrders[0].id);
        }
      } else {
        this.renderDrawerEmpty();
      }
    } catch (err) {
      console.error("Sipariş listeleme hatası:", err);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 2rem; color: var(--danger);">Hata: ${err.message}</td></tr>`;
      }
    }
  },

  renderKpi() {
    const totalCount = currentOrders.length;
    let totalCiro = 0;
    let totalPaid = 0;

    currentOrders.forEach(o => {
      const amount = Number(o.total_amount || 0);
      totalCiro += amount;
      let paid = 0;
      if (o.paid_amount !== undefined && o.paid_amount !== null) {
        paid = Number(o.paid_amount);
      } else {
        paid = o.payment_status === 'paid' ? amount : 0;
      }
      totalPaid += paid;
    });

    const remainingTotal = Math.max(0, totalCiro - totalPaid);

    const elTotal = document.getElementById('kpi-total-orders');
    const elCiro = document.getElementById('kpi-total-ciro');
    const elPaid = document.getElementById('kpi-paid-total');
    const elRemaining = document.getElementById('kpi-remaining-total');

    if (elTotal) elTotal.textContent = totalCount;
    if (elCiro) elCiro.textContent = `${totalCiro.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
    if (elPaid) elPaid.textContent = `${totalPaid.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
    if (elRemaining) elRemaining.textContent = `${remainingTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
  },

  renderTable() {
    const tbody = document.getElementById('orders-table-body');
    if (!tbody) return;

    if (currentOrders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 3rem; color: var(--text-muted);">Filtreye uygun sipariş bulunamadı.</td></tr>`;
      return;
    }

    tbody.innerHTML = currentOrders.map(order => {
      const isSelected = order.id === selectedOrderId;
      const statusBadge = this.getStatusBadge(order.status);
      const customerName = order.customers?.name || "İsimsiz";
      const customerPhone = order.customers?.phone || "-";
      const courierName = order.couriers?.name || '<span style="color:var(--text-subtle);">Atanmadı</span>';
      const paymentText = order.payment_method === 'cash' ? 'Nakit' : order.payment_method === 'credit_card' ? 'Kredi Kartı' : 'IBAN';

      const amt = Number(order.total_amount || 0);
      let paid = 0;
      if (order.paid_amount !== undefined && order.paid_amount !== null) {
        paid = Number(order.paid_amount);
      } else {
        paid = order.payment_status === 'paid' ? amt : 0;
      }

      let paidClass = 'paid-pending';
      let paymentBadgeText = 'Bekliyor';
      let paymentBadgeColor = 'var(--warning)';

      if (paid >= amt - 0.005 && amt > 0) {
        paidClass = 'paid-full';
        paymentBadgeText = 'Ödendi';
        paymentBadgeColor = 'var(--success)';
      } else if (paid > 0) {
        paidClass = 'paid-partial';
        paymentBadgeText = `Kısmi (${paid.toLocaleString('tr-TR', { minimumFractionDigits: 0 })}₺)`;
        paymentBadgeColor = 'var(--warning)';
      } else if (order.payment_status === 'paid') {
        paidClass = 'paid-full';
        paymentBadgeText = 'Ödendi';
        paymentBadgeColor = 'var(--success)';
      }

      // Saat bilgisi
      let timeStr = "-";
      if (order.created_at) {
        timeStr = new Date(order.created_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
      }

      return `
        <tr class="${isSelected ? 'selected' : ''}" data-id="${order.id}">
          <td style="font-weight: 800; color: var(--primary);">#${order.order_number}</td>
          <td>${timeStr}</td>
          <td>
            <div style="font-weight: 700;">${customerName}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${customerPhone}</div>
          </td>
          <td>${courierName}</td>
          <td>
            <div style="font-weight: 600;">${paymentText}</div>
            <div id="payment-badge-${order.id}" style="font-size: 0.75rem; color: ${paymentBadgeColor}; font-weight: 700;">
              ${paymentBadgeText}
            </div>
          </td>
          <td onclick="event.stopPropagation()">
            <div style="display:flex; align-items:center; gap:3px;">
              <input type="number" step="1" min="0" class="table-inline-input"
                     value="${amt.toFixed(2)}"
                     id="total-input-${order.id}"
                     data-id="${order.id}"
                     onchange="window.app.ordersComponent.saveInlineTotal('${order.id}', this.value)"
                     title="Sipariş Toplam Tutarını Değiştir">
              <span style="font-size:0.8rem; font-weight:700; color:var(--text-muted);">₺</span>
            </div>
          </td>
          <td onclick="event.stopPropagation()">
            <div style="display:flex; align-items:center; gap:3px;">
              <input type="number" step="1" min="0" class="table-inline-input paid-spin ${paidClass}"
                     value="${paid.toFixed(2)}"
                     id="paid-input-${order.id}"
                     data-id="${order.id}"
                     data-total="${amt}"
                     onchange="window.app.ordersComponent.saveInlinePaid('${order.id}', this.value)"
                     title="Ödenen Tutarı Değiştir">
              <button type="button" class="btn-micro" title="Tamamını Ödendi Yap (=)"
                      onclick="window.app.ordersComponent.payFull('${order.id}')">=</button>
            </div>
          </td>
          <td>${statusBadge}</td>
        </tr>
      `;
    }).join('');

    // Satır tıklama olayları
    tbody.querySelectorAll('tr').forEach(tr => {
      tr.addEventListener('click', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
        const id = tr.dataset.id;
        if (id) {
          tbody.querySelectorAll('tr').forEach(r => r.classList.remove('selected'));
          tr.classList.add('selected');
          this.selectOrder(id);
        }
      });
    });
  },

  async saveInlineTotal(orderId, val) {
    const newTotal = Math.max(0, parseFloat(val) || 0);
    const order = currentOrders.find(o => o.id === orderId);
    if (!order) return;
    if (Math.abs(Number(order.total_amount || 0) - newTotal) < 0.005) return;

    order.total_amount = newTotal;

    const paidInput = document.getElementById(`paid-input-${orderId}`);
    if (paidInput) {
      paidInput.dataset.total = newTotal;
    }

    let paid = Number(order.paid_amount || 0);
    let newStatus = paid <= 0 ? 'pending' : (paid >= newTotal - 0.005 && newTotal > 0 ? 'paid' : 'partial');
    order.payment_status = newStatus;

    this.updateRowPaymentStyles(orderId, newTotal, paid, newStatus);
    this.renderKpi();
    if (selectedOrderId === orderId) this.selectOrder(orderId);

    try {
      await ordersApi.update(orderId, { total_amount: newTotal, payment_status: newStatus });
      window.app.toast(`Sipariş #${order.order_number} toplamı: ${newTotal.toFixed(2)} ₺`);
    } catch (err) {
      alert("Toplam tutar kaydedilemedi: " + err.message);
    }
  },

  async saveInlinePaid(orderId, val) {
    const newPaid = Math.max(0, parseFloat(val) || 0);
    const order = currentOrders.find(o => o.id === orderId);
    if (!order) return;
    if (order.paid_amount !== undefined && Math.abs(Number(order.paid_amount || 0) - newPaid) < 0.005) return;

    order.paid_amount = newPaid;
    const total = Number(order.total_amount || 0);
    let newStatus = newPaid <= 0 ? 'pending' : (newPaid >= total - 0.005 && total > 0 ? 'paid' : 'partial');
    order.payment_status = newStatus;

    this.updateRowPaymentStyles(orderId, total, newPaid, newStatus);
    this.renderKpi();
    if (selectedOrderId === orderId) this.selectOrder(orderId);

    try {
      await ordersApi.setPaidAmount(orderId, newPaid, total);
      window.app.toast(`Sipariş #${order.order_number} ödenen: ${newPaid.toFixed(2)} ₺`);
    } catch (err) {
      alert("Ödenen tutar kaydedilemedi: " + err.message);
    }
  },

  updateRowPaymentStyles(orderId, total, paid, status) {
    const paidInput = document.getElementById(`paid-input-${orderId}`);
    if (paidInput) {
      paidInput.value = paid.toFixed(2);
      paidInput.classList.remove('paid-full', 'paid-partial', 'paid-pending');
      if (paid >= total - 0.005 && total > 0) {
        paidInput.classList.add('paid-full');
      } else if (paid > 0) {
        paidInput.classList.add('paid-partial');
      } else {
        paidInput.classList.add('paid-pending');
      }
    }

    const badge = document.getElementById(`payment-badge-${orderId}`);
    if (badge) {
      if (paid >= total - 0.005 && total > 0) {
        badge.textContent = 'Ödendi';
        badge.style.color = 'var(--success)';
      } else if (paid > 0) {
        badge.textContent = `Kısmi (${paid.toFixed(0)}₺)`;
        badge.style.color = 'var(--warning)';
      } else {
        badge.textContent = 'Bekliyor';
        badge.style.color = 'var(--warning)';
      }
    }
  },

  async payFull(orderId) {
    const order = currentOrders.find(o => o.id === orderId);
    if (!order) return;
    const total = Number(order.total_amount || 0);
    await this.saveInlinePaid(orderId, total);
  },

  async payZero(orderId) {
    await this.saveInlinePaid(orderId, 0);
  },

  async selectOrder(orderId) {
    selectedOrderId = orderId;
    const order = currentOrders.find(o => o.id === orderId);
    if (!order) return;

    const drawer = document.getElementById('order-detail-drawer');
    if (!drawer) return;

    // Sipariş kalemlerini çek
    let items = [];
    try {
      items = await ordersApi.getItems(orderId);
    } catch (e) {
      console.warn("Kalemler çekilemedi:", e);
    }

    const customerName = order.customers?.name || "Misafir / İsimsiz";
    const customerPhone = order.customers?.phone || "-";
    const addressText = order.customer_addresses?.address_text || "Adres belirtilmemiş";

    const amt = Number(order.total_amount || 0);
    let paid = 0;
    if (order.paid_amount !== undefined && order.paid_amount !== null) {
      paid = Number(order.paid_amount);
    } else {
      paid = order.payment_status === 'paid' ? amt : 0;
    }
    const remaining = Math.max(0, amt - paid);
    let paidClass = paid >= amt - 0.005 && amt > 0 ? 'paid-full' : (paid > 0 ? 'paid-partial' : 'paid-pending');

    drawer.innerHTML = `
      <div class="drawer-header">
        <div>
          <span style="font-size:0.85rem; color:var(--text-muted);">Sipariş No</span>
          <div class="drawer-title" style="color:var(--primary);">#${order.order_number}</div>
        </div>
        <div>
          ${this.getStatusBadge(order.status)}
        </div>
      </div>

      <div style="background:var(--bg-surface-elevated); padding:0.9rem; border-radius:var(--radius-md);">
        <div style="font-weight:700; font-size:1rem;">👤 ${customerName}</div>
        <div style="font-size:0.85rem; color:var(--text-muted); margin-top:2px;">📞 ${customerPhone}</div>
        <div style="font-size:0.85rem; color:var(--text-muted); margin-top:6px; line-height:1.4;">📍 ${addressText}</div>
        ${order.notes ? `<div style="margin-top:6px; font-size:0.82rem; color:var(--warning); background:var(--warning-light); padding:4px 8px; border-radius:4px;">📝 Not: ${order.notes}</div>` : ''}
      </div>

      <div>
        <div style="font-weight:700; font-size:0.85rem; text-transform:uppercase; color:var(--text-muted); margin-bottom:0.5rem;">Sipariş Kalemleri</div>
        <div class="items-list">
          ${items.length === 0 ? `<div style="color:var(--text-subtle); font-size:0.85rem;">Kalem girilmemiş.</div>` : ''}
          ${items.map(it => `
            <div class="item-row">
              <div>
                <span style="font-weight:700;">${it.products?.name || 'Ürün'}</span>
                <span style="color:var(--text-muted); font-size:0.8rem; margin-left:4px;">x${it.quantity}</span>
              </div>
              <div style="font-weight:700;">${Number(it.total_price || 0).toFixed(2)} ₺</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div style="background:var(--bg-surface-elevated); padding:0.9rem; border-radius:var(--radius-md); display:flex; flex-direction:column; gap:0.6rem;">
        <div style="font-size:0.85rem; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Tutar ve Ödeme Durumu</div>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700; font-size:0.95rem;">Toplam Tutar:</span>
          <div style="display:flex; align-items:center; gap:4px;">
            <input type="number" step="1" min="0" class="table-inline-input" style="width:110px; font-size:1.05rem;"
                   value="${amt.toFixed(2)}"
                   onchange="window.app.ordersComponent.saveInlineTotal('${order.id}', this.value)"
                   title="Toplam Tutarı Değiştir">
            <span style="font-weight:700;">₺</span>
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700; font-size:0.95rem;">Ödenen Tutar:</span>
          <div style="display:flex; align-items:center; gap:4px;">
            <input type="number" step="1" min="0" class="table-inline-input paid-spin ${paidClass}" style="width:110px; font-size:1.05rem;"
                   value="${paid.toFixed(2)}"
                   onchange="window.app.ordersComponent.saveInlinePaid('${order.id}', this.value)"
                   title="Ödenen Tutarı Değiştir">
            <span style="font-weight:700;">₺</span>
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; padding-top:4px; border-top:1px dashed var(--border-subtle);">
          <span style="color:var(--text-muted); font-size:0.9rem;">Kalan Bakiye:</span>
          <span style="font-weight:800; font-size:1.05rem; color:${remaining > 0 ? 'var(--warning)' : 'var(--success)'};">
            ${remaining.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺
          </span>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.4rem; margin-top:0.25rem;">
          <button class="btn-secondary" style="font-size:0.8rem; padding:0.45rem; border-color:var(--success); color:var(--success);"
                  onclick="window.app.ordersComponent.payFull('${order.id}')">
            ✅ Tamamı Ödendi
          </button>
          <button class="btn-secondary" style="font-size:0.8rem; padding:0.45rem; color:var(--text-muted);"
                  onclick="window.app.ordersComponent.payZero('${order.id}')">
            ❌ Ödenmedi (0 ₺)
          </button>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:0.5rem; margin-top:0.5rem;">
        <div style="font-size:0.8rem; font-weight:700; color:var(--text-muted);">Hızlı Durum Değiştir:</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
          <button class="btn-secondary" style="font-size:0.85rem; padding:0.5rem;" onclick="window.app.quickSetStatus('${order.id}', 'on_way')">
            🏍️ Yolda
          </button>
          <button class="btn-secondary" style="font-size:0.85rem; padding:0.5rem; border-color:var(--success); color:var(--success);" onclick="window.app.quickSetStatus('${order.id}', 'delivered')">
            ✅ Teslim Edildi
          </button>
        </div>
        <button class="btn-secondary" style="font-size:0.85rem; padding:0.5rem; margin-top:0.25rem;" onclick="window.app.openEditOrderModal('${order.id}')">
          ✏️ Siparişi Düzenle
        </button>
      </div>
    `;
  },

  renderDrawerEmpty() {
    const drawer = document.getElementById('order-detail-drawer');
    if (drawer) {
      drawer.innerHTML = `
        <div style="text-align:center; padding:3rem 1rem; color:var(--text-muted);">
          <div style="font-size:2rem; margin-bottom:0.5rem;">📦</div>
          <div>Detayını görmek için bir sipariş seçiniz.</div>
        </div>
      `;
    }
  },

  getStatusBadge(status) {
    switch (status) {
      case 'new':
        return `<span class="badge-status badge-new">● Yeni</span>`;
      case 'preparing':
        return `<span class="badge-status badge-preparing">● Hazırlanıyor</span>`;
      case 'on_way':
        return `<span class="badge-status badge-on_way">● Yolda</span>`;
      case 'delivered':
        return `<span class="badge-status badge-delivered">● Teslim Edildi</span>`;
      case 'cancelled':
        return `<span class="badge-status badge-cancelled">● İptal</span>`;
      default:
        return `<span class="badge-status">${status}</span>`;
    }
  },

  async quickSetStatus(orderId, newStatus) {
    try {
      await ordersApi.updateStatus(orderId, newStatus);
      sound.playSuccessTone();
      window.app.toast("Sipariş durumu güncellendi");
      await this.refresh();
    } catch (err) {
      alert("Durum güncellenirken hata oluştu: " + err.message);
    }
  }
};
