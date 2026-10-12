/**
 * Müşteriler (Customers) Bileşeni
 * Müşteri listesi, arama, yeni müşteri ekleme/düzenleme ve adres yönetimi.
 */

import { customersApi } from '../supabase.js';

let editingCustomerId = null;

export const customersComponent = {
  async init() {
    this.bindEvents();
    await this.refresh();
  },

  bindEvents() {
    const searchInput = document.getElementById('search-customers-input');
    if (searchInput) {
      let timer = null;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => this.refresh(e.target.value), 250);
      });
    }

    const btnNew = document.getElementById('btn-new-customer');
    if (btnNew) {
      btnNew.addEventListener('click', () => this.openNewCustomerModal());
    }

    const form = document.getElementById('customer-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveCustomer();
      });
    }

    const btnClose = document.getElementById('btn-close-customer-modal');
    if (btnClose) btnClose.addEventListener('click', () => this.closeModal());
  },

  async refresh(search = "") {
    const tbody = document.getElementById('customers-table-body');
    if (!tbody) return;

    try {
      const customers = await customersApi.list({ search, includeGuests: false, limit: 100 });
      if (customers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 3rem; color: var(--text-muted);">Müşteri bulunamadı.</td></tr>`;
        return;
      }

      tbody.innerHTML = customers.map(c => `
        <tr>
          <td style="font-weight:700;">${c.name}</td>
          <td>${c.phone}</td>
          <td>${c.notes || '-'}</td>
          <td>${new Date(c.created_at).toLocaleDateString('tr-TR')}</td>
          <td>
            <div style="display:flex; gap:0.4rem;">
              <button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.customersComponent.openEditCustomerModal('${c.id}')">
                ✏️ Düzenle
              </button>
              <button class="btn-primary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.orderModal.open({ prefillCustomerId: '${c.id}' })">
                🛍️ Sipariş Ver
              </button>
            </div>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--danger);">Hata: ${err.message}</td></tr>`;
    }
  },

  openNewCustomerModal(prefillPhone = "") {
    editingCustomerId = null;
    const modal = document.getElementById('customer-modal');
    const title = document.getElementById('customer-modal-title');
    const form = document.getElementById('customer-form');
    if (form) form.reset();

    if (title) title.textContent = "👤 Yeni Müşteri Kaydı";
    const phoneInput = document.getElementById('cust-phone');
    if (phoneInput && prefillPhone) phoneInput.value = prefillPhone;

    const addressGroup = document.getElementById('cust-address-group');
    if (addressGroup) addressGroup.style.display = 'block';

    if (modal) modal.classList.add('open');
  },

  async openEditCustomerModal(id) {
    editingCustomerId = id;
    const modal = document.getElementById('customer-modal');
    const title = document.getElementById('customer-modal-title');
    if (title) title.textContent = "✏️ Müşteri Bilgilerini Düzenle";

    const addressGroup = document.getElementById('cust-address-group');
    if (addressGroup) addressGroup.style.display = 'none'; // Düzenlemede temel bilgiler güncellenir

    try {
      const c = await customersApi.get(id);
      if (!c) return;

      document.getElementById('cust-name').value = c.name || '';
      document.getElementById('cust-phone').value = c.phone || '';
      document.getElementById('cust-email').value = c.email || '';
      document.getElementById('cust-notes').value = c.notes || '';

      if (modal) modal.classList.add('open');
    } catch (err) {
      alert("Müşteri bilgileri alınamadı: " + err.message);
    }
  },

  closeModal() {
    const modal = document.getElementById('customer-modal');
    if (modal) modal.classList.remove('open');
  },

  async saveCustomer() {
    const name = document.getElementById('cust-name').value.trim();
    const phone = document.getElementById('cust-phone').value.trim();
    const email = document.getElementById('cust-email').value.trim();
    const notes = document.getElementById('cust-notes').value.trim();
    const address = document.getElementById('cust-address')?.value.trim();

    if (!name || !phone) {
      alert("Lütfen isim ve telefon alanlarını doldurunuz.");
      return;
    }

    try {
      if (editingCustomerId) {
        await customersApi.update(editingCustomerId, { name, phone, email: email || null, notes: notes || null });
        window.app.toast("Müşteri bilgileri güncellendi");
      } else {
        const newCust = await customersApi.create({ name, phone, email, notes, is_guest: false });
        if (address) {
          await customersApi.addAddress({
            customerId: newCust.id,
            title: "Ev",
            addressText: address,
            isDefault: true
          });
        }
        window.app.toast("Yeni müşteri eklendi");
      }

      this.closeModal();
      this.refresh();
    } catch (err) {
      alert("Kaydedilirken hata oluştu: " + err.message);
    }
  }
};
