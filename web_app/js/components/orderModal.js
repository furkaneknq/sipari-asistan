/**
 * Yeni Sipariş & Sipariş Düzenleme Modalı
 * Müşteri seçimi, hızlı misafir modu, kategori ve ürün sepeti,
 * kurye atama ve not yönetimi.
 */

import { ordersApi, customersApi, productsApi, couriersApi } from '../supabase.js';
import { sound } from '../sound.js';

let editingOrderId = null;
let cachedCategories = [];
let cachedProducts = [];
let cachedCouriers = [];
let currentCart = []; // { productId, name, quantity, unit, unitPrice }
let totalAmountManuallyEdited = false;

export const orderModal = {
  async init() {
    this.bindEvents();
  },

  bindEvents() {
    const modal = document.getElementById('order-modal');
    const closeBtn = document.getElementById('btn-close-order-modal');
    const cancelBtn = document.getElementById('btn-cancel-order-modal');
    const form = document.getElementById('order-form');

    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (cancelBtn) cancelBtn.addEventListener('click', () => this.close());

    // = Sepet Tutarı Butonu: Ödenen tutarı toplam tutara eşitle ve durumu 'Ödendi' yap
    const fillPaidBtn = document.getElementById('btn-fill-paid-total');
    if (fillPaidBtn) {
      fillPaidBtn.addEventListener('click', () => {
        const totalInput = document.getElementById('order-total-amount-input');
        const paidInput = document.getElementById('order-paid-amount-input');
        const statusSelect = document.getElementById('order-payment-status');
        if (totalInput && paidInput) {
          paidInput.value = Number(totalInput.value || 0).toFixed(2);
          if (statusSelect) statusSelect.value = 'paid';
        }
      });
    }

    const totalAmountInput = document.getElementById('order-total-amount-input');
    if (totalAmountInput) {
      totalAmountInput.addEventListener('input', () => {
        totalAmountManuallyEdited = true;
      });
    }

    const paidAmountInput = document.getElementById('order-paid-amount-input');
    if (paidAmountInput) {
      paidAmountInput.addEventListener('input', () => {
        const p = parseFloat(paidAmountInput.value) || 0;
        const t = parseFloat(document.getElementById('order-total-amount-input')?.value) || 0;
        const statusSelect = document.getElementById('order-payment-status');
        if (statusSelect) {
          if (p >= t - 0.005 && t > 0) statusSelect.value = 'paid';
          else if (p <= 0) statusSelect.value = 'pending';
        }
      });
    }

    // Misafir Modu Değişimi
    const guestCheckbox = document.getElementById('order-is-guest');
    if (guestCheckbox) {
      guestCheckbox.addEventListener('change', (e) => {
        const isGuest = e.target.checked;
        const regSection = document.getElementById('registered-customer-section');
        const guestSection = document.getElementById('guest-customer-section');
        if (regSection) regSection.style.display = isGuest ? 'none' : 'block';
        if (guestSection) guestSection.style.display = isGuest ? 'grid' : 'none';
      });
    }

    // Müşteri Arama Input (autocomplete)
    const custSearch = document.getElementById('order-customer-search');
    if (custSearch) {
      custSearch.addEventListener('input', async (e) => {
        const q = e.target.value.trim();
        const resultsEl = document.getElementById('customer-search-results');
        if (!resultsEl) return;

        if (q.length < 2) {
          resultsEl.style.display = 'none';
          return;
        }

        try {
          const list = await customersApi.list({ search: q, limit: 8 });
          if (list.length === 0) {
            resultsEl.innerHTML = `<div style="padding:0.75rem; color:var(--text-muted); font-size:0.85rem;">Müşteri bulunamadı.</div>`;
          } else {
            resultsEl.innerHTML = list.map(c => `
              <div class="cust-search-item" data-id="${c.id}" data-name="${c.name}" data-phone="${c.phone}" style="padding:0.6rem 0.8rem; cursor:pointer; border-bottom:1px solid var(--border-subtle);">
                <div style="font-weight:700;">${c.name}</div>
                <div style="font-size:0.8rem; color:var(--text-muted);">${c.phone}</div>
              </div>
            `).join('');

            resultsEl.querySelectorAll('.cust-search-item').forEach(item => {
              item.addEventListener('click', () => {
                this.selectCustomer(item.dataset.id, item.dataset.name, item.dataset.phone);
                resultsEl.style.display = 'none';
              });
            });
          }
          resultsEl.style.display = 'block';
        } catch (err) {
          console.warn("Müşteri arama hatası:", err);
        }
      });
    }

    // Hızlı Not Çipleri
    document.querySelectorAll('.order-quick-note').forEach(chip => {
      chip.addEventListener('click', (e) => {
        const text = e.currentTarget.textContent.trim();
        const notesInput = document.getElementById('order-notes');
        if (notesInput) {
          if (notesInput.value) {
            notesInput.value += ` - ${text}`;
          } else {
            notesInput.value = text;
          }
        }
      });
    });

    // Form Gönderimi (Kayıt)
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveOrder();
      });
    }
  },

  async open({ orderId = null, prefillCustomerId = null, prefillPhone = null, prefillName = null } = {}) {
    editingOrderId = orderId;
    currentCart = [];
    totalAmountManuallyEdited = false;

    const modal = document.getElementById('order-modal');
    const titleEl = document.getElementById('order-modal-title');
    if (!modal) return;

    if (titleEl) {
      titleEl.textContent = orderId ? "✏️ Siparişi Düzenle" : "🛍️ Yeni Sipariş Oluştur";
    }

    // Verileri önbellekle
    try {
      [cachedCategories, cachedProducts, cachedCouriers] = await Promise.all([
        productsApi.getCategories(),
        productsApi.getProducts({ activeOnly: true }),
        couriersApi.list({ activeOnly: true })
      ]);
    } catch (e) {
      console.warn("Önbellek yükleme hatası:", e);
    }

    this.renderCategoryPills();
    this.renderProductsPicker();
    this.populateCouriersSelect();

    // Formu Sıfırla
    const form = document.getElementById('order-form');
    if (form) form.reset();

    const guestCheckbox = document.getElementById('order-is-guest');
    const regSection = document.getElementById('registered-customer-section');
    const guestSection = document.getElementById('guest-customer-section');
    const custSearch = document.getElementById('order-customer-search');
    const selectedCustInfo = document.getElementById('selected-customer-info');
    const hiddenCustId = document.getElementById('order-customer-id');

    if (hiddenCustId) hiddenCustId.value = "";
    if (selectedCustInfo) selectedCustInfo.innerHTML = "";
    if (custSearch) custSearch.value = "";

    const totalInput = document.getElementById('order-total-amount-input');
    const paidInput = document.getElementById('order-paid-amount-input');
    if (totalInput) totalInput.value = "0.00";
    if (paidInput) paidInput.value = "0.00";

    // Ön doldurma (Prefill)
    if (prefillCustomerId) {
      try {
        const c = await customersApi.get(prefillCustomerId);
        if (c) this.selectCustomer(c.id, c.name, c.phone);
      } catch (err) {
        console.warn(err);
      }
    } else if (prefillPhone) {
      // Misafir moduna geçir veya telefonu doldur
      if (guestCheckbox) guestCheckbox.checked = true;
      if (regSection) regSection.style.display = 'none';
      if (guestSection) guestSection.style.display = 'grid';

      const phoneInput = document.getElementById('guest-phone');
      const nameInput = document.getElementById('guest-name');
      if (phoneInput) phoneInput.value = prefillPhone;
      if (nameInput && prefillName) nameInput.value = prefillName;
    } else {
      if (guestCheckbox) guestCheckbox.checked = false;
      if (regSection) regSection.style.display = 'block';
      if (guestSection) guestSection.style.display = 'none';
    }

    // Eğer düzenleme modundaysa sipariş bilgilerini yükle
    if (orderId) {
      await this.loadExistingOrder(orderId);
    }

    this.renderCart();
    modal.classList.add('open');
  },

  close() {
    const modal = document.getElementById('order-modal');
    if (modal) modal.classList.remove('open');
  },

  populateCouriersSelect() {
    const select = document.getElementById('order-courier-select');
    if (!select) return;
    select.innerHTML = `
      <option value="">-- Kurye Seçiniz (Opsiyonel) --</option>
      ${cachedCouriers.map(c => `<option value="${c.id}">${c.name} (${c.phone})</option>`).join('')}
    `;
  },

  async selectCustomer(id, name, phone) {
    const hiddenId = document.getElementById('order-customer-id');
    const selectedInfo = document.getElementById('selected-customer-info');
    const addressSelect = document.getElementById('order-address-select');

    if (hiddenId) hiddenId.value = id;
    if (selectedInfo) {
      selectedInfo.innerHTML = `
        <div style="background:var(--primary-light); color:var(--primary); padding:0.6rem 0.9rem; border-radius:var(--radius-md); display:flex; justify-content:space-between; align-items:center;">
          <div><strong>${name}</strong> (${phone})</div>
          <button type="button" style="color:var(--danger); font-size:0.85rem;" onclick="document.getElementById('order-customer-id').value=''; document.getElementById('selected-customer-info').innerHTML='';">Değiştir</button>
        </div>
      `;
    }

    // Adreslerini çek
    if (addressSelect) {
      addressSelect.innerHTML = `<option value="">Adresler yükleniyor...</option>`;
      try {
        const addresses = await customersApi.getAddresses(id);
        if (addresses.length === 0) {
          addressSelect.innerHTML = `<option value="">Kayıtlı adres yok (Manuel girebilirsiniz)</option>`;
        } else {
          addressSelect.innerHTML = addresses.map(a => `
            <option value="${a.id}" ${a.is_default ? 'selected' : ''}>
              ${a.title || 'Adres'}: ${a.address_text}
            </option>
          `).join('');
        }
      } catch (e) {
        addressSelect.innerHTML = `<option value="">Adres yüklenemedi</option>`;
      }
    }
  },

  renderCategoryPills() {
    const container = document.getElementById('order-categories-pills');
    if (!container) return;

    container.innerHTML = `
      <button type="button" class="category-pill active" data-id="all">Tümü</button>
      ${cachedCategories.map(cat => `
        <button type="button" class="category-pill" data-id="${cat.id}">${cat.name}</button>
      `).join('')}
    `;

    container.querySelectorAll('.category-pill').forEach(btn => {
      btn.addEventListener('click', (e) => {
        container.querySelectorAll('.category-pill').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.renderProductsPicker(e.currentTarget.dataset.id);
      });
    });
  },

  renderProductsPicker(selectedCatId = "all") {
    const container = document.getElementById('order-products-picker');
    if (!container) return;

    let filtered = cachedProducts;
    if (selectedCatId && selectedCatId !== 'all') {
      filtered = cachedProducts.filter(p => p.category_id === selectedCatId);
    }

    if (filtered.length === 0) {
      container.innerHTML = `<div style="grid-column: 1/-1; padding: 1.5rem; text-align: center; color: var(--text-muted);">Bu kategoride ürün bulunamadı.</div>`;
      return;
    }

    container.innerHTML = filtered.map(prod => `
      <div class="product-picker-card" data-id="${prod.id}">
        <div>
          <div class="picker-product-name">${prod.name}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${prod.unit || 'adet'}</div>
        </div>
        <div class="picker-product-price">${Number(prod.price).toFixed(2)} ₺</div>
      </div>
    `).join('');

    container.querySelectorAll('.product-picker-card').forEach(card => {
      card.addEventListener('click', () => {
        const prod = cachedProducts.find(p => p.id === card.dataset.id);
        if (prod) this.addToCart(prod);
      });
    });
  },

  addToCart(prod) {
    const existing = currentCart.find(item => item.productId === prod.id);
    if (existing) {
      existing.quantity += 1;
    } else {
      currentCart.push({
        productId: prod.id,
        name: prod.name,
        quantity: 1,
        unit: prod.unit || "adet",
        unitPrice: Number(prod.price)
      });
    }
    sound.playSuccessTone();
    this.renderCart();
  },

  renderCart() {
    const container = document.getElementById('order-cart-items');
    const totalEl = document.getElementById('order-cart-total');
    if (!container) return;

    let grandTotal = 0;

    if (currentCart.length === 0) {
      container.innerHTML = `<div style="padding:1.5rem; text-align:center; color:var(--text-muted); font-size:0.9rem;">Sepet boş. Yukarıdan ürünlere tıklayarak ekleyiniz.</div>`;
      if (totalEl) totalEl.textContent = "0.00 ₺";
      return;
    }

    container.innerHTML = currentCart.map((item, idx) => {
      const itemTotal = item.quantity * item.unitPrice;
      grandTotal += itemTotal;
      return `
        <div class="item-row" style="padding: 0.6rem 0.8rem;">
          <div style="flex:1;">
            <div style="font-weight:700;">${item.name}</div>
            <div style="font-size:0.8rem; color:var(--text-muted);">${item.unitPrice.toFixed(2)} ₺ / ${item.unit}</div>
          </div>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <button type="button" class="btn-icon" style="width:28px; height:28px;" onclick="window.app.orderModal.updateItemQty(${idx}, -1)">-</button>
            <span style="font-weight:800; min-width:20px; text-align:center;">${item.quantity}</span>
            <button type="button" class="btn-icon" style="width:28px; height:28px;" onclick="window.app.orderModal.updateItemQty(${idx}, 1)">+</button>
          </div>
          <div style="font-weight:800; min-width:80px; text-align:right;">
            ${itemTotal.toFixed(2)} ₺
          </div>
          <button type="button" style="color:var(--danger); margin-left:0.5rem; font-size:1.1rem;" onclick="window.app.orderModal.removeItem(${idx})">×</button>
        </div>
      `;
    }).join('');

    if (totalEl) {
      totalEl.textContent = `${grandTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
    }
    const totalAmountInput = document.getElementById('order-total-amount-input');
    if (totalAmountInput && !totalAmountManuallyEdited) {
      totalAmountInput.value = grandTotal.toFixed(2);
    }
  },

  updateItemQty(idx, delta) {
    if (currentCart[idx]) {
      currentCart[idx].quantity += delta;
      if (currentCart[idx].quantity <= 0) {
        currentCart.splice(idx, 1);
      }
      this.renderCart();
    }
  },

  removeItem(idx) {
    currentCart.splice(idx, 1);
    this.renderCart();
  },

  async loadExistingOrder(orderId) {
    try {
      const existing = (await ordersApi.list({ date: null })).find(o => o.id === orderId);
      if (!existing) return;

      const items = await ordersApi.getItems(orderId);
      currentCart = items.map(it => ({
        productId: it.product_id,
        name: it.products?.name || "Ürün",
        quantity: Number(it.quantity),
        unit: it.unit || "adet",
        unitPrice: Number(it.unit_price)
      }));

      totalAmountManuallyEdited = true;
      const tot = Number(existing.total_amount || 0);
      let paid = 0;
      if (existing.paid_amount !== undefined && existing.paid_amount !== null) {
        paid = Number(existing.paid_amount);
      } else {
        paid = existing.payment_status === 'paid' ? tot : 0;
      }

      const totalInput = document.getElementById('order-total-amount-input');
      if (totalInput) totalInput.value = tot.toFixed(2);
      const paidInput = document.getElementById('order-paid-amount-input');
      if (paidInput) paidInput.value = paid.toFixed(2);

      if (existing.customer_id) {
        this.selectCustomer(existing.customer_id, existing.customers?.name || "", existing.customers?.phone || "");
      }

      const courierSelect = document.getElementById('order-courier-select');
      if (courierSelect && existing.courier_id) {
        courierSelect.value = existing.courier_id;
      }

      const statusSelect = document.getElementById('order-status-select');
      if (statusSelect) statusSelect.value = existing.status;

      const paymentMethod = document.getElementById('order-payment-method');
      if (paymentMethod) paymentMethod.value = existing.payment_method || 'cash';

      const paymentStatus = document.getElementById('order-payment-status');
      if (paymentStatus) paymentStatus.value = existing.payment_status || 'pending';

      const notesInput = document.getElementById('order-notes');
      if (notesInput) notesInput.value = existing.notes || '';
    } catch (err) {
      console.warn("Mevcut sipariş yüklenemedi:", err);
    }
  },

  async saveOrder() {
    const isGuest = document.getElementById('order-is-guest')?.checked;
    let customerId = document.getElementById('order-customer-id')?.value;
    let addressId = document.getElementById('order-address-select')?.value || null;

    // Eğer misafir modundaysa anında müşteri kaydı oluştur (is_guest: true)
    if (isGuest) {
      const guestName = document.getElementById('guest-name')?.value.trim();
      const guestPhone = document.getElementById('guest-phone')?.value.trim();
      const guestAddress = document.getElementById('guest-address')?.value.trim();

      if (!guestPhone) {
        alert("Lütfen misafir telefon numarasını giriniz.");
        return;
      }

      try {
        const newCust = await customersApi.create({
          name: guestName || "Misafir Müşteri",
          phone: guestPhone,
          is_guest: true
        });
        customerId = newCust.id;

        if (guestAddress) {
          const newAddr = await customersApi.addAddress({
            customerId: customerId,
            title: "Misafir Adres",
            addressText: guestAddress,
            isDefault: true
          });
          addressId = newAddr.id;
        }
      } catch (err) {
        alert("Misafir kaydı oluşturulurken hata: " + err.message);
        return;
      }
    }

    if (!customerId) {
      alert("Lütfen bir müşteri seçiniz veya Misafir Modunu aktif ediniz.");
      return;
    }

    if (currentCart.length === 0) {
      alert("Lütfen sepete en az bir ürün ekleyiniz.");
      return;
    }

    const courierId = document.getElementById('order-courier-select')?.value || null;
    const status = document.getElementById('order-status-select')?.value || 'new';
    const paymentMethod = document.getElementById('order-payment-method')?.value || 'cash';
    const notes = document.getElementById('order-notes')?.value || '';

    const totalAmount = Math.max(0, parseFloat(document.getElementById('order-total-amount-input')?.value) || 0);
    const paidAmount = Math.max(0, parseFloat(document.getElementById('order-paid-amount-input')?.value) || 0);
    let paymentStatus = document.getElementById('order-payment-status')?.value || 'pending';
    if (paidAmount >= totalAmount - 0.005 && totalAmount > 0) {
      paymentStatus = 'paid';
    } else if (paidAmount > 0) {
      paymentStatus = 'partial';
    }

    try {
      if (editingOrderId) {
        await ordersApi.update(editingOrderId, {
          customer_id: customerId,
          address_id: addressId,
          courier_id: courierId,
          status,
          payment_method: paymentMethod,
          payment_status: paymentStatus,
          notes,
          total_amount: totalAmount,
          paid_amount: paidAmount
        }, currentCart);
        window.app.toast("Sipariş başarıyla güncellendi.");
      } else {
        await ordersApi.create({
          customerId,
          addressId,
          courierId,
          status,
          paymentMethod,
          paymentStatus,
          notes,
          items: currentCart,
          totalAmount,
          paidAmount
        });
        window.app.toast("Yeni sipariş oluşturuldu! 🎉");
      }

      sound.playSuccessTone();
      this.close();
      await window.app.ordersComponent.refresh();
    } catch (err) {
      alert("Sipariş kaydedilirken hata oluştu: " + err.message);
    }
  }
};
