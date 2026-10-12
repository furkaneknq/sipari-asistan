/**
 * Kuryeler (Couriers) Yönetim Bileşeni
 */

import { couriersApi } from '../supabase.js';

let editingCourierId = null;

export const couriersComponent = {
  async init() {
    this.bindEvents();
    await this.refresh();
  },

  bindEvents() {
    const btnNew = document.getElementById('btn-new-courier');
    if (btnNew) btnNew.addEventListener('click', () => this.openNewCourierModal());

    const form = document.getElementById('courier-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveCourier();
      });
    }

    const btnClose = document.getElementById('btn-close-courier-modal');
    if (btnClose) btnClose.addEventListener('click', () => this.closeModal());
  },

  async refresh() {
    const tbody = document.getElementById('couriers-table-body');
    if (!tbody) return;

    try {
      const list = await couriersApi.list();
      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:3rem; color:var(--text-muted);">Kayıtlı kurye bulunamadı.</td></tr>`;
        return;
      }

      tbody.innerHTML = list.map(c => `
        <tr>
          <td style="font-weight:700;">🏍️ ${c.name}</td>
          <td>${c.phone}</td>
          <td>
            ${c.is_active ? `<span class="badge-status badge-delivered">Aktif</span>` : `<span class="badge-status badge-cancelled">Pasif</span>`}
          </td>
          <td>
            <button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.couriersComponent.openEditCourierModal('${c.id}')">
              ✏️ Düzenle
            </button>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:var(--danger);">Hata: ${err.message}</td></tr>`;
    }
  },

  openNewCourierModal() {
    editingCourierId = null;
    const modal = document.getElementById('courier-modal');
    const form = document.getElementById('courier-form');
    if (form) form.reset();
    document.getElementById('courier-modal-title').textContent = "🏍️ Yeni Kurye Ekle";
    if (modal) modal.classList.add('open');
  },

  async openEditCourierModal(id) {
    editingCourierId = id;
    const modal = document.getElementById('courier-modal');
    document.getElementById('courier-modal-title').textContent = "✏️ Kuryeyi Düzenle";

    try {
      const list = await couriersApi.list();
      const c = list.find(item => item.id === id);
      if (!c) return;

      document.getElementById('courier-name').value = c.name;
      document.getElementById('courier-phone').value = c.phone;
      document.getElementById('courier-active').checked = c.is_active;

      if (modal) modal.classList.add('open');
    } catch (err) {
      alert("Kurye bilgisi alınamadı: " + err.message);
    }
  },

  closeModal() {
    const modal = document.getElementById('courier-modal');
    if (modal) modal.classList.remove('open');
  },

  async saveCourier() {
    const name = document.getElementById('courier-name').value.trim();
    const phone = document.getElementById('courier-phone').value.trim();
    const is_active = document.getElementById('courier-active').checked;

    if (!name || !phone) {
      alert("Lütfen kurye adını ve telefonunu giriniz.");
      return;
    }

    try {
      if (editingCourierId) {
        await couriersApi.update(editingCourierId, { name, phone, is_active });
        window.app.toast("Kurye güncellendi");
      } else {
        await couriersApi.create({ name, phone });
        window.app.toast("Yeni kurye eklendi");
      }
      this.closeModal();
      this.refresh();
      window.app.ordersComponent.loadCouriers();
    } catch (err) {
      alert("Kayıt hatası: " + err.message);
    }
  }
};
