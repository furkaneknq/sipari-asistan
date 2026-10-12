/**
 * Ürünler ve Kategoriler (Products & Categories) Yönetimi
 */

import { productsApi } from '../supabase.js';

let editingProductId = null;
let editingCategoryId = null;

export const productsComponent = {
  async init() {
    this.bindEvents();
    await this.refresh();
  },

  bindEvents() {
    const btnNewProduct = document.getElementById('btn-new-product');
    if (btnNewProduct) btnNewProduct.addEventListener('click', () => this.openNewProductModal());

    const btnNewCat = document.getElementById('btn-new-category');
    if (btnNewCat) btnNewCat.addEventListener('click', () => this.openNewCategoryModal());

    const formProd = document.getElementById('product-form');
    if (formProd) {
      formProd.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveProduct();
      });
    }

    const formCat = document.getElementById('category-form');
    if (formCat) {
      formCat.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveCategory();
      });
    }

    const btnCloseProd = document.getElementById('btn-close-product-modal');
    if (btnCloseProd) btnCloseProd.addEventListener('click', () => this.closeProductModal());

    const btnCloseCat = document.getElementById('btn-close-category-modal');
    if (btnCloseCat) btnCloseCat.addEventListener('click', () => this.closeCategoryModal());
  },

  async refresh() {
    await Promise.all([this.refreshCategories(), this.refreshProducts()]);
  },

  async refreshCategories() {
    const container = document.getElementById('categories-list-container');
    const select = document.getElementById('prod-category-select');
    if (!container) return;

    try {
      const categories = await productsApi.getCategories();
      container.innerHTML = categories.map(cat => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.8rem; background:var(--bg-surface-elevated); border-radius:var(--radius-md); border-left:4px solid ${cat.color || 'var(--primary)'};">
          <div style="font-weight:700;">${cat.name}</div>
          <div style="display:flex; gap:0.4rem;">
            <button class="btn-secondary" style="font-size:0.75rem; padding:0.25rem 0.5rem;" onclick="window.app.productsComponent.openEditCategoryModal('${cat.id}', '${cat.name}', '${cat.color || '#4f46e5'}', ${cat.sort_order || 0})">Düzenle</button>
          </div>
        </div>
      `).join('');

      if (select) {
        select.innerHTML = `
          <option value="">-- Kategori Seçiniz --</option>
          ${categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
        `;
      }
    } catch (err) {
      console.warn("Kategoriler yüklenemedi:", err);
    }
  },

  async refreshProducts() {
    const tbody = document.getElementById('products-table-body');
    if (!tbody) return;

    try {
      const products = await productsApi.getProducts();
      if (products.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:3rem; color:var(--text-muted);">Ürün bulunamadı.</td></tr>`;
        return;
      }

      tbody.innerHTML = products.map(p => `
        <tr>
          <td style="font-weight:700;">${p.name}</td>
          <td>
            <span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:var(--radius-full);">
              ${p.categories?.name || 'Kategorisiz'}
            </span>
          </td>
          <td style="font-weight:800; color:var(--success); font-size:1.05rem;">
            ${Number(p.price).toFixed(2)} ₺ / ${p.unit || 'adet'}
          </td>
          <td>
            ${p.is_active ? `<span class="badge-status badge-delivered">Aktif</span>` : `<span class="badge-status badge-cancelled">Pasif</span>`}
          </td>
          <td>
            <button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.productsComponent.openEditProductModal('${p.id}')">
              ✏️ Düzenle
            </button>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--danger);">Hata: ${err.message}</td></tr>`;
    }
  },

  openNewProductModal() {
    editingProductId = null;
    const modal = document.getElementById('product-modal');
    const form = document.getElementById('product-form');
    if (form) form.reset();
    document.getElementById('product-modal-title').textContent = "📦 Yeni Ürün Ekle";
    if (modal) modal.classList.add('open');
  },

  async openEditProductModal(id) {
    editingProductId = id;
    const modal = document.getElementById('product-modal');
    document.getElementById('product-modal-title').textContent = "✏️ Ürünü Düzenle";

    try {
      const products = await productsApi.getProducts();
      const p = products.find(item => item.id === id);
      if (!p) return;

      document.getElementById('prod-name').value = p.name;
      document.getElementById('prod-category-select').value = p.category_id || '';
      document.getElementById('prod-price').value = p.price;
      document.getElementById('prod-unit').value = p.unit || 'adet';
      document.getElementById('prod-active').checked = p.is_active;

      if (modal) modal.classList.add('open');
    } catch (err) {
      alert("Ürün bilgisi alınamadı: " + err.message);
    }
  },

  closeProductModal() {
    const modal = document.getElementById('product-modal');
    if (modal) modal.classList.remove('open');
  },

  async saveProduct() {
    const name = document.getElementById('prod-name').value.trim();
    const category_id = document.getElementById('prod-category-select').value || null;
    const price = document.getElementById('prod-price').value;
    const unit = document.getElementById('prod-unit').value.trim() || 'adet';
    const is_active = document.getElementById('prod-active').checked;

    if (!name || !price) {
      alert("Lütfen ürün adı ve fiyatını giriniz.");
      return;
    }

    try {
      if (editingProductId) {
        await productsApi.updateProduct(editingProductId, { name, category_id, price: Number(price), unit, is_active });
        window.app.toast("Ürün güncellendi");
      } else {
        await productsApi.createProduct({ name, category_id, price: Number(price), unit, is_active });
        window.app.toast("Yeni ürün eklendi");
      }
      this.closeProductModal();
      this.refreshProducts();
    } catch (err) {
      alert("Kayıt hatası: " + err.message);
    }
  },

  openNewCategoryModal() {
    editingCategoryId = null;
    const modal = document.getElementById('category-modal');
    const form = document.getElementById('category-form');
    if (form) form.reset();
    document.getElementById('category-modal-title').textContent = "🏷️ Yeni Kategori Ekle";
    if (modal) modal.classList.add('open');
  },

  openEditCategoryModal(id, name, color, sortOrder) {
    editingCategoryId = id;
    const modal = document.getElementById('category-modal');
    document.getElementById('category-modal-title').textContent = "✏️ Kategoriyi Düzenle";
    document.getElementById('cat-name').value = name;
    document.getElementById('cat-color').value = color || '#4f46e5';
    document.getElementById('cat-sort').value = sortOrder || 0;
    if (modal) modal.classList.add('open');
  },

  closeCategoryModal() {
    const modal = document.getElementById('category-modal');
    if (modal) modal.classList.remove('open');
  },

  async saveCategory() {
    const name = document.getElementById('cat-name').value.trim();
    const color = document.getElementById('cat-color').value;
    const sort_order = Number(document.getElementById('cat-sort').value || 0);

    if (!name) {
      alert("Kategori adı zorunludur.");
      return;
    }

    try {
      if (editingCategoryId) {
        await productsApi.updateCategory(editingCategoryId, { name, color, sort_order });
        window.app.toast("Kategori güncellendi");
      } else {
        await productsApi.createCategory({ name, color, sort_order });
        window.app.toast("Yeni kategori eklendi");
      }
      this.closeCategoryModal();
      this.refreshCategories();
    } catch (err) {
      alert("Kategori kayıt hatası: " + err.message);
    }
  }
};
