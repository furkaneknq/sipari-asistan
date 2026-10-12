/**
 * Sipariş Takip Sistemi - Web Portu Tümleşik İstemci Paketi (Bundle)
 * Hem file:/// (doğrudan çift tıklama) hem de http:// (web sunucusu)
 * protokollerinde sıfır CORS hatası ile çalışacak şekilde yapılandırılmıştır.
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. YAPILANDIRMA (CONFIG)
  // =========================================================================
  const DEFAULT_SUPABASE_URL = "https://xgvlgmikxchpttydtelb.supabase.co";
  // Güvenlik: Secret key burada saklanmıyor. Kullanıcı Ayarlar panelinden girer.
  const DEFAULT_SUPABASE_KEY = "";

  const config = {
    getSupabaseUrl() {
      return localStorage.getItem("order_tracking_supabase_url") || DEFAULT_SUPABASE_URL;
    },
    setSupabaseUrl(url) {
      if (url) localStorage.setItem("order_tracking_supabase_url", url.trim());
      else localStorage.removeItem("order_tracking_supabase_url");
    },
    getSupabaseKey() {
      return localStorage.getItem("order_tracking_supabase_key") || DEFAULT_SUPABASE_KEY;
    },
    setSupabaseKey(key) {
      if (key) localStorage.setItem("order_tracking_supabase_key", key.trim());
      else localStorage.removeItem("order_tracking_supabase_key");
    },
    getTheme() {
      return localStorage.getItem("order_tracking_theme") || "dark";
    },
    setTheme(theme) {
      localStorage.setItem("order_tracking_theme", theme);
    },
    isSoundEnabled() {
      const val = localStorage.getItem("order_tracking_sound");
      return val === null ? true : val === "true";
    },
    setSoundEnabled(enabled) {
      localStorage.setItem("order_tracking_sound", String(enabled));
    },
    resetDefaults() {
      localStorage.removeItem("order_tracking_supabase_url");
      localStorage.removeItem("order_tracking_supabase_key");
    }
  };

  // =========================================================================
  // 2. SES SİSTEMİ (WEB AUDIO API)
  // =========================================================================
  let audioCtx = null;
  function getAudioContext() {
    if (!audioCtx) {
      const AudioClass = window.AudioContext || window.webkitAudioContext;
      if (AudioClass) audioCtx = new AudioClass();
    }
    if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  }

  const sound = {
    playIncomingCallTone() {
      if (!config.isSoundEnabled()) return;
      try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const now = ctx.currentTime;

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
        console.warn("Ses çalınamadı:", e);
      }
    },

    playSuccessTone() {
      if (!config.isSoundEnabled()) return;
      try {
        const ctx = getAudioContext();
        if (!ctx) return;
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.12);
        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.4);
      } catch (e) {
        console.warn("Ses hatası:", e);
      }
    }
  };

  // =========================================================================
  // 3. SUPABASE İSTEMCİSİ VE API METOTLARI
  // =========================================================================
  let supabaseClient = null;
  let realtimeChannel = null;

  function getClient() {
    if (!window.supabase || !window.supabase.createClient) {
      throw new Error("Supabase kütüphanesi yüklenemedi. İnternet bağlantınızı kontrol ediniz.");
    }
    let url = config.getSupabaseUrl();
    const key = config.getSupabaseKey();

    // Eğer localhost üzerinde çalışıyorsa ve anahtar secret key (sb_secret_...) ise,
    // Supabase Gateway'in tarayıcı engeline takılmamak için yerel ters proxy'yi kullan:
    if (window.location.protocol.startsWith('http') && key.startsWith('sb_secret_')) {
      url = `${window.location.origin}/supabase-proxy`;
    }

    if (!supabaseClient) {
      supabaseClient = window.supabase.createClient(url, key, {
        auth: { persistSession: false },
        realtime: { params: { eventsPerSecond: 10 } }
      });
      if (supabaseClient && !supabaseClient.table) {
        supabaseClient.table = function (t) { return supabaseClient.from(t); };
      }
    }
    return supabaseClient;
  }

  function resetClient() {
    if (realtimeChannel && supabaseClient) {
      supabaseClient.removeChannel(realtimeChannel);
      realtimeChannel = null;
    }
    supabaseClient = null;
  }

  async function testConnection() {
    try {
      const client = getClient();
      const { data, error } = await client.from("categories").select("id").limit(1);
      if (error) return { ok: false, error: error.message };
      return { ok: true, data };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  }

  const ordersApi = {
    async list({ date, status, courierId, search, startDate, endDate } = {}) {
      const client = getClient();
      let query = client
        .from("orders")
        .select(`
          id,
          order_number,
          status,
          order_date,
          delivery_date,
          delivery_time,
          total_amount,
          paid_amount,
          payment_method,
          payment_status,
          notes,
          created_at,
          customer_id,
          address_id,
          courier_id,
          customers:customer_id (id, name, phone, is_guest),
          customer_addresses:address_id (id, title, address_text),
          couriers:courier_id (id, name, phone)
        `)
        .order("created_at", { ascending: false });

      if (date) {
        query = query.eq("order_date", date);
      } else if (startDate && endDate) {
        query = query.gte("order_date", startDate).lte("order_date", endDate);
      }

      if (status && status !== "all") {
        query = query.eq("status", status);
      }

      if (courierId) {
        if (courierId === "__none__") {
          query = query.is("courier_id", null);
        } else if (courierId !== "__all__") {
          query = query.eq("courier_id", courierId);
        }
      }

      const { data, error } = await query;
      if (error) throw error;

      let rows = data || [];
      if (search && search.trim()) {
        const s = search.trim().toLowerCase();
        rows = rows.filter(r => {
          const cName = (r.customers?.name || "").toLowerCase();
          const cPhone = (r.customers?.phone || "");
          const sNo = String(r.order_number || "");
          return cName.includes(s) || cPhone.includes(s) || sNo.includes(s);
        });
      }
      return rows;
    },

    async getItems(orderId) {
      const client = getClient();
      const { data, error } = await client
        .from("order_items")
        .select(`
          id,
          order_id,
          product_id,
          quantity,
          unit,
          unit_price,
          total_price,
          notes,
          products:product_id (name, unit)
        `)
        .eq("order_id", orderId);

      if (error) throw error;
      return data || [];
    },

    async create({ customerId, addressId = null, courierId = null, status = "new", orderDate = new Date().toISOString().slice(0, 10), deliveryTime = null, paymentMethod = "cash", paymentStatus = "pending", notes = "", items = [], totalAmount = 0, paidAmount = 0 }) {
      const client = getClient();
      const tot = Number(totalAmount || 0);
      const paid = Math.max(0, Number(paidAmount || 0));
      let derivedStatus = paymentStatus;
      if (paid <= 0) {
        derivedStatus = paymentStatus === 'paid' ? 'paid' : 'pending';
      } else if (paid >= tot - 0.005 && tot > 0) {
        derivedStatus = 'paid';
      } else {
        derivedStatus = 'partial';
      }

      const { data: orderData, error: orderError } = await client
        .from("orders")
        .insert({
          customer_id: customerId,
          address_id: addressId,
          courier_id: courierId,
          status: status,
          order_date: orderDate,
          delivery_time: deliveryTime,
          payment_method: paymentMethod,
          payment_status: derivedStatus,
          notes: notes || null,
          total_amount: tot,
          paid_amount: paid
        })
        .select()
        .single();

      if (orderError) throw orderError;
      const orderId = orderData.id;

      if (items.length > 0) {
        const itemsPayload = items.map(item => ({
          order_id: orderId,
          product_id: item.productId || null,
          quantity: item.quantity,
          unit: item.unit || "adet",
          unit_price: item.unitPrice,
          total_price: Number((item.quantity * item.unitPrice).toFixed(2)),
          notes: item.notes || null
        }));

        const { error: itemsError } = await client.from("order_items").insert(itemsPayload);
        if (itemsError) throw itemsError;
      }
      return orderData;
    },

    async updateStatus(orderId, status) {
      const client = getClient();
      const { data, error } = await client
        .from("orders")
        .update({ status })
        .eq("id", orderId)
        .select()
        .single();
      if (error) throw error;
      return data;
    },

    async setPaidAmount(orderId, paidAmount, orderTotal = null) {
      const client = getClient();
      const paid = Math.max(0, Number(paidAmount || 0));
      const total = Number(orderTotal !== null ? orderTotal : 0);
      let status = "pending";
      if (paid <= 0) {
        status = "pending";
      } else if (paid >= total - 0.005 && total > 0) {
        status = "paid";
      } else {
        status = "partial";
      }
      const { data, error } = await client
        .from("orders")
        .update({ paid_amount: paid, payment_status: status })
        .eq("id", orderId)
        .select()
        .single();
      if (error) throw error;
      return data;
    },

    async setTotalAmount(orderId, totalAmount) {
      const client = getClient();
      const total = Math.max(0, Number(totalAmount || 0));
      const { data, error } = await client
        .from("orders")
        .update({ total_amount: total })
        .eq("id", orderId)
        .select()
        .single();
      if (error) throw error;
      return data;
    },

    async update(orderId, updates, newItems = null) {
      const client = getClient();
      const { data, error } = await client.from("orders").update(updates).eq("id", orderId).select().single();
      if (error) throw error;

      if (newItems !== null) {
        await client.from("order_items").delete().eq("order_id", orderId);
        if (newItems.length > 0) {
          const itemsPayload = newItems.map(item => ({
            order_id: orderId,
            product_id: item.productId || null,
            quantity: item.quantity,
            unit: item.unit || "adet",
            unit_price: item.unitPrice,
            total_price: Number((item.quantity * item.unitPrice).toFixed(2)),
            notes: item.notes || null
          }));
          const { error: itemsErr } = await client.from("order_items").insert(itemsPayload);
          if (itemsErr) throw itemsErr;
        }
      }
      return data;
    }
  };

  const customersApi = {
    async list({ search = "", includeGuests = false, limit = 100 } = {}) {
      const client = getClient();
      let query = client.from("customers").select("id, name, phone, email, notes, is_guest, created_at").order("name", { ascending: true });
      if (!includeGuests) query = query.eq("is_guest", false);
      if (search && search.trim()) {
        const s = search.trim();
        query = query.or(`name.ilike.%${s}%,phone.ilike.%${s}%`);
      }
      if (limit > 0) query = query.limit(limit);
      const { data, error } = await query;
      if (error) throw error;
      return data || [];
    },

    async get(id) {
      const client = getClient();
      const { data, error } = await client.from("customers").select("*").eq("id", id).single();
      if (error) throw error;
      return data;
    },

    async findByPhone(phone) {
      const client = getClient();
      const cleanPhone = phone.replace(/\D/g, "");
      const last10 = cleanPhone.slice(-10);
      const { data, error } = await client.from("customers").select("*").or(`phone.eq.${cleanPhone},phone.ilike.%${last10}`).limit(1);
      if (error) throw error;
      return data && data.length > 0 ? data[0] : null;
    },

    async create({ name, phone, email = "", notes = "", is_guest = false }) {
      const client = getClient();
      const { data, error } = await client.from("customers").insert({
        name: name.trim(),
        phone: phone.trim(),
        email: email ? email.trim() : null,
        notes: notes ? notes.trim() : null,
        is_guest: !!is_guest
      }).select().single();
      if (error) throw error;
      return data;
    },

    async update(id, updates) {
      const client = getClient();
      const { data, error } = await client.from("customers").update(updates).eq("id", id).select().single();
      if (error) throw error;
      return data;
    },

    async getAddresses(customerId) {
      const client = getClient();
      const { data, error } = await client.from("customer_addresses").select("*").eq("customer_id", customerId).order("is_default", { ascending: false });
      if (error) throw error;
      return data || [];
    },

    async addAddress({ customerId, title = "Ev", addressText, isDefault = false }) {
      const client = getClient();
      if (isDefault) {
        await client.from("customer_addresses").update({ is_default: false }).eq("customer_id", customerId);
      }
      const { data, error } = await client.from("customer_addresses").insert({
        customer_id: customerId,
        title: title || "Adres",
        address_text: addressText.trim(),
        is_default: !!isDefault
      }).select().single();
      if (error) throw error;
      return data;
    }
  };

  const productsApi = {
    async getCategories() {
      const client = getClient();
      const { data, error } = await client.from("categories").select("*").order("sort_order", { ascending: true });
      if (error) throw error;
      return data || [];
    },
    async createCategory({ name, sort_order = 0, color = "#4f46e5" }) {
      const client = getClient();
      const { data, error } = await client.from("categories").insert({ name: name.trim(), sort_order, color, is_active: true }).select().single();
      if (error) throw error;
      return data;
    },
    async updateCategory(id, updates) {
      const client = getClient();
      const { data, error } = await client.from("categories").update(updates).eq("id", id).select().single();
      if (error) throw error;
      return data;
    },
    async getProducts({ activeOnly = false } = {}) {
      const client = getClient();
      let query = client.from("products").select("id, category_id, name, price, unit, is_active, sort_order, categories:category_id (name, color)").order("sort_order", { ascending: true }).order("name", { ascending: true });
      if (activeOnly) query = query.eq("is_active", true);
      const { data, error } = await query;
      if (error) throw error;
      return data || [];
    },
    async createProduct({ category_id, name, price, unit = "adet", sort_order = 0, is_active = true }) {
      const client = getClient();
      const { data, error } = await client.from("products").insert({ category_id: category_id || null, name: name.trim(), price: Number(price), unit, sort_order: Number(sort_order), is_active: !!is_active }).select().single();
      if (error) throw error;
      return data;
    },
    async updateProduct(id, updates) {
      const client = getClient();
      const { data, error } = await client.from("products").update(updates).eq("id", id).select().single();
      if (error) throw error;
      return data;
    }
  };

  const couriersApi = {
    async list({ activeOnly = false } = {}) {
      const client = getClient();
      let query = client.from("couriers").select("*").order("name", { ascending: true });
      if (activeOnly) query = query.eq("is_active", true);
      const { data, error } = await query;
      if (error) throw error;
      return data || [];
    },
    async create({ name, phone }) {
      const client = getClient();
      const { data, error } = await client.from("couriers").insert({ name: name.trim(), phone: phone.trim(), is_active: true }).select().single();
      if (error) throw error;
      return data;
    },
    async update(id, updates) {
      const client = getClient();
      const { data, error } = await client.from("couriers").update(updates).eq("id", id).select().single();
      if (error) throw error;
      return data;
    }
  };

  const callsApi = {
    async list({ limit = 50 } = {}) {
      const client = getClient();
      const { data, error } = await client.from("incoming_calls").select("id, phone_number, device_id, customer_id, is_processed, created_at, customers:customer_id (id, name, phone)").order("created_at", { ascending: false }).limit(limit);
      if (error) throw error;
      return data || [];
    },
    async markProcessed(id) {
      const client = getClient();
      const { data, error } = await client.from("incoming_calls").update({ is_processed: true }).eq("id", id).select().single();
      if (error) throw error;
      return data;
    }
  };

  function initRealtime({ onIncomingCall, onOrderChange }) {
    try {
      const client = getClient();
      if (realtimeChannel) client.removeChannel(realtimeChannel);

      realtimeChannel = client
        .channel('db-realtime-sync')
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'incoming_calls' }, payload => {
          if (onIncomingCall) onIncomingCall(payload.new);
        })
        .on('postgres_changes', { event: '*', schema: 'public', table: 'orders' }, payload => {
          if (onOrderChange) onOrderChange(payload);
        })
        .subscribe(status => {
          console.log("[Supabase Realtime]:", status);
          const badge = document.getElementById("realtime-badge");
          if (badge) {
            if (status === "SUBSCRIBED") {
              badge.className = "status-badge status-connected";
              badge.textContent = "● Canlı Bağlı";
            } else {
              badge.className = "status-badge status-connecting";
              badge.textContent = "○ Bağlanıyor...";
            }
          }
        });
      return realtimeChannel;
    } catch (err) {
      console.warn("Realtime kurulamadı:", err);
      return null;
    }
  }

  // =========================================================================
  // 4. SİPARİŞLER PANELİ BİLEŞENİ
  // =========================================================================
  let currentOrders = [];
  let selectedOrderId = null;
  let couriersList = [];
  const filters = {
    date: new Date().toISOString().slice(0, 10),
    status: "all",
    courierId: "__all__",
    search: ""
  };

  const ordersComponent = {
    async init() {
      this.bindEvents();
      await this.loadCouriers();
      await this.refresh();
    },

    bindEvents() {
      document.querySelectorAll('.filter-date-chip').forEach(btn => {
        btn.addEventListener('click', (e) => {
          document.querySelectorAll('.filter-date-chip').forEach(b => b.classList.remove('active'));
          e.currentTarget.classList.add('active');
          const mode = e.currentTarget.dataset.mode;
          const today = new Date();
          if (mode === 'today') filters.date = today.toISOString().slice(0, 10);
          else if (mode === 'yesterday') {
            const y = new Date(today);
            y.setDate(y.getDate() - 1);
            filters.date = y.toISOString().slice(0, 10);
          } else if (mode === 'all') filters.date = null;

          const dateInput = document.getElementById('filter-order-date');
          if (dateInput) dateInput.value = filters.date || '';
          this.refresh();
        });
      });

      const dateInput = document.getElementById('filter-order-date');
      if (dateInput) {
        dateInput.value = filters.date;
        dateInput.addEventListener('change', (e) => {
          filters.date = e.target.value || null;
          document.querySelectorAll('.filter-date-chip').forEach(b => b.classList.remove('active'));
          this.refresh();
        });
      }

      const statusSelect = document.getElementById('filter-order-status');
      if (statusSelect) statusSelect.addEventListener('change', (e) => { filters.status = e.target.value; this.refresh(); });

      const courierSelect = document.getElementById('filter-order-courier');
      if (courierSelect) courierSelect.addEventListener('change', (e) => { filters.courierId = e.target.value; this.refresh(); });

      const searchInput = document.getElementById('search-orders-input');
      if (searchInput) {
        let t = null;
        searchInput.addEventListener('input', (e) => {
          clearTimeout(t);
          t = setTimeout(() => { filters.search = e.target.value; this.refresh(); }, 250);
        });
      }

      const refreshBtn = document.getElementById('btn-refresh-orders');
      if (refreshBtn) refreshBtn.addEventListener('click', () => this.refresh());
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
      if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:2rem; color:var(--text-muted);">Siparişler yükleniyor...</td></tr>`;

      try {
        currentOrders = await ordersApi.list({
          date: filters.date,
          status: filters.status,
          courierId: filters.courierId,
          search: filters.search
        });

        this.renderKpi();
        this.renderTable();

        if (currentOrders.length > 0) {
          const stillExists = currentOrders.find(o => o.id === selectedOrderId);
          this.selectOrder(stillExists ? stillExists.id : currentOrders[0].id);
        } else {
          this.renderDrawerEmpty();
        }
      } catch (err) {
        console.error("Sipariş hatası:", err);
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:2rem; color:var(--danger);">Bağlantı hatası: ${err.message}</td></tr>`;
      }
    },

    renderKpi() {
      let totalCiro = 0;
      let totalPaid = 0;
      currentOrders.forEach(o => {
        const amt = Number(o.total_amount || 0);
        totalCiro += amt;
        let paid = 0;
        if (o.paid_amount !== undefined && o.paid_amount !== null) {
          paid = Number(o.paid_amount);
        } else {
          paid = o.payment_status === 'paid' ? amt : 0;
        }
        totalPaid += paid;
      });

      const remainingTotal = Math.max(0, totalCiro - totalPaid);

      const elTotal = document.getElementById('kpi-total-orders');
      const elCiro = document.getElementById('kpi-total-ciro');
      const elPaid = document.getElementById('kpi-paid-total');
      const elRemaining = document.getElementById('kpi-remaining-total');

      if (elTotal) elTotal.textContent = currentOrders.length;
      if (elCiro) elCiro.textContent = `${totalCiro.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
      if (elPaid) elPaid.textContent = `${totalPaid.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
      if (elRemaining) elRemaining.textContent = `${remainingTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
    },

    renderTable() {
      const tbody = document.getElementById('orders-table-body');
      if (!tbody) return;

      if (currentOrders.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:3rem; color:var(--text-muted);">Filtreye uygun sipariş bulunamadı.</td></tr>`;
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

        let timeStr = "-";
        if (order.created_at) {
          timeStr = new Date(order.created_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
        }

        return `
          <tr class="${isSelected ? 'selected' : ''}" data-id="${order.id}">
            <td style="font-weight:800; color:var(--primary);">#${order.order_number}</td>
            <td>${timeStr}</td>
            <td>
              <div style="font-weight:700;">${customerName}</div>
              <div style="font-size:0.8rem; color:var(--text-muted);">${customerPhone}</div>
            </td>
            <td>${courierName}</td>
            <td>
              <div style="font-weight:600;">${paymentText}</div>
              <div id="payment-badge-${order.id}" style="font-size:0.75rem; color:${paymentBadgeColor}; font-weight:700;">
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

      let items = [];
      try { items = await ordersApi.getItems(orderId); } catch (e) { console.warn(e); }

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
          <div>${this.getStatusBadge(order.status)}</div>
        </div>

        <div style="background:var(--bg-surface-elevated); padding:0.9rem; border-radius:var(--radius-md);">
          <div style="font-weight:700; font-size:1rem;">👤 ${customerName}</div>
          <div style="font-size:0.85rem; color:var(--text-muted); margin-top:2px;">📞 ${customerPhone}</div>
          <div style="font-size:0.85rem; color:var(--text-muted); margin-top:6px; line-height:1.4;">📍 ${addressText}</div>
          ${order.notes ? `<div style="margin-top:6px; font-size:0.82rem; color:var(--warning); background:var(--warning-light); padding:4px 8px; border-radius:4px;">📝 ${order.notes}</div>` : ''}
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
            <button class="btn-secondary" style="font-size:0.85rem; padding:0.5rem;" onclick="window.app.quickSetStatus('${order.id}', 'on_way')">🏍️ Yolda</button>
            <button class="btn-secondary" style="font-size:0.85rem; padding:0.5rem; border-color:var(--success); color:var(--success);" onclick="window.app.quickSetStatus('${order.id}', 'delivered')">✅ Teslim Edildi</button>
          </div>
          <button class="btn-secondary" style="font-size:0.85rem; padding:0.5rem; margin-top:0.25rem;" onclick="window.app.openEditOrderModal('${order.id}')">✏️ Siparişi Düzenle</button>
        </div>
      `;
    },

    renderDrawerEmpty() {
      const drawer = document.getElementById('order-detail-drawer');
      if (drawer) drawer.innerHTML = `<div style="text-align:center; padding:3rem 1rem; color:var(--text-muted);"><div style="font-size:2rem; margin-bottom:0.5rem;">📦</div><div>Detayını görmek için bir sipariş seçiniz.</div></div>`;
    },

    getStatusBadge(status) {
      switch (status) {
        case 'new': return `<span class="badge-status badge-new">● Yeni</span>`;
        case 'preparing': return `<span class="badge-status badge-preparing">● Hazırlanıyor</span>`;
        case 'on_way': return `<span class="badge-status badge-on_way">● Yolda</span>`;
        case 'delivered': return `<span class="badge-status badge-delivered">● Teslim Edildi</span>`;
        case 'cancelled': return `<span class="badge-status badge-cancelled">● İptal</span>`;
        default: return `<span class="badge-status">${status}</span>`;
      }
    },

    async quickSetStatus(orderId, newStatus) {
      try {
        await ordersApi.updateStatus(orderId, newStatus);
        sound.playSuccessTone();
        window.app.toast("Sipariş durumu güncellendi");
        await this.refresh();
      } catch (err) {
        alert("Durum güncellenirken hata: " + err.message);
      }
    }
  };

  // =========================================================================
  // 5. YENİ / DÜZENLE SİPARİŞ MODALI BİLEŞENİ
  // =========================================================================
  let editingOrderId = null;
  let cachedCategories = [];
  let cachedProducts = [];
  let cachedCouriers = [];
  let currentCart = [];
  let totalAmountManuallyEdited = false;

  const orderModal = {
    async init() {
      this.bindEvents();
    },

    bindEvents() {
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

      const custSearch = document.getElementById('order-customer-search');
      if (custSearch) {
        custSearch.addEventListener('input', async (e) => {
          const q = e.target.value.trim();
          const resultsEl = document.getElementById('customer-search-results');
          if (!resultsEl) return;
          if (q.length < 2) { resultsEl.style.display = 'none'; return; }

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
          } catch (err) { console.warn(err); }
        });
      }

      document.querySelectorAll('.order-quick-note').forEach(chip => {
        chip.addEventListener('click', (e) => {
          const text = e.currentTarget.textContent.trim();
          const notesInput = document.getElementById('order-notes');
          if (notesInput) {
            notesInput.value = notesInput.value ? `${notesInput.value} - ${text}` : text;
          }
        });
      });

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
      if (titleEl) titleEl.textContent = orderId ? "✏️ Siparişi Düzenle" : "🛍️ Yeni Sipariş Oluştur";

      try {
        [cachedCategories, cachedProducts, cachedCouriers] = await Promise.all([
          productsApi.getCategories(),
          productsApi.getProducts({ activeOnly: true }),
          couriersApi.list({ activeOnly: true })
        ]);
      } catch (e) { console.warn(e); }

      this.renderCategoryPills();
      this.renderProductsPicker();
      this.populateCouriersSelect();

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

      if (prefillCustomerId) {
        try {
          const c = await customersApi.get(prefillCustomerId);
          if (c) this.selectCustomer(c.id, c.name, c.phone);
        } catch (err) { console.warn(err); }
      } else if (prefillPhone) {
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

      if (orderId) await this.loadExistingOrder(orderId);
      this.renderCart();
      if (modal) modal.classList.add('open');
    },

    close() {
      const modal = document.getElementById('order-modal');
      if (modal) modal.classList.remove('open');
    },

    populateCouriersSelect() {
      const select = document.getElementById('order-courier-select');
      if (!select) return;
      select.innerHTML = `<option value="">-- Kurye Seçiniz (Opsiyonel) --</option>${cachedCouriers.map(c => `<option value="${c.id}">${c.name} (${c.phone})</option>`).join('')}`;
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

      if (addressSelect) {
        addressSelect.innerHTML = `<option value="">Adresler yükleniyor...</option>`;
        try {
          const addresses = await customersApi.getAddresses(id);
          if (addresses.length === 0) {
            addressSelect.innerHTML = `<option value="">Kayıtlı adres yok</option>`;
          } else {
            addressSelect.innerHTML = addresses.map(a => `<option value="${a.id}" ${a.is_default ? 'selected' : ''}>${a.title || 'Adres'}: ${a.address_text}</option>`).join('');
          }
        } catch (e) { addressSelect.innerHTML = `<option value="">Adres hatası</option>`; }
      }
    },

    renderCategoryPills() {
      const container = document.getElementById('order-categories-pills');
      if (!container) return;
      container.innerHTML = `
        <button type="button" class="category-pill active" data-id="all">Tümü</button>
        ${cachedCategories.map(cat => `<button type="button" class="category-pill" data-id="${cat.id}">${cat.name}</button>`).join('')}
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
        container.innerHTML = `<div style="grid-column: 1/-1; padding: 1.5rem; text-align: center; color: var(--text-muted);">Ürün bulunamadı.</div>`;
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
      if (existing) existing.quantity += 1;
      else {
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
        container.innerHTML = `<div style="padding:1.5rem; text-align:center; color:var(--text-muted); font-size:0.9rem;">Sepet boş. Ürün seçiniz.</div>`;
        if (totalEl) totalEl.textContent = "0,00 ₺";
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
            <div style="font-weight:800; min-width:80px; text-align:right;">${itemTotal.toFixed(2)} ₺</div>
            <button type="button" style="color:var(--danger); margin-left:0.5rem; font-size:1.1rem;" onclick="window.app.orderModal.removeItem(${idx})">×</button>
          </div>
        `;
      }).join('');

      if (totalEl) totalEl.textContent = `${grandTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺`;
      const totalAmountInput = document.getElementById('order-total-amount-input');
      if (totalAmountInput && !totalAmountManuallyEdited) {
        totalAmountInput.value = grandTotal.toFixed(2);
      }
    },

    updateItemQty(idx, delta) {
      if (currentCart[idx]) {
        currentCart[idx].quantity += delta;
        if (currentCart[idx].quantity <= 0) currentCart.splice(idx, 1);
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
        if (courierSelect && existing.courier_id) courierSelect.value = existing.courier_id;
        const statusSelect = document.getElementById('order-status-select');
        if (statusSelect) statusSelect.value = existing.status;
        const paymentMethod = document.getElementById('order-payment-method');
        if (paymentMethod) paymentMethod.value = existing.payment_method || 'cash';
        const paymentStatus = document.getElementById('order-payment-status');
        if (paymentStatus) paymentStatus.value = existing.payment_status || 'pending';
        const notesInput = document.getElementById('order-notes');
        if (notesInput) notesInput.value = existing.notes || '';
      } catch (err) { console.warn(err); }
    },

    async saveOrder() {
      const isGuest = document.getElementById('order-is-guest')?.checked;
      let customerId = document.getElementById('order-customer-id')?.value;
      let addressId = document.getElementById('order-address-select')?.value || null;

      if (isGuest) {
        const guestName = document.getElementById('guest-name')?.value.trim();
        const guestPhone = document.getElementById('guest-phone')?.value.trim();
        const guestAddress = document.getElementById('guest-address')?.value.trim();

        if (!guestPhone) { alert("Lütfen misafir telefon numarasını giriniz."); return; }
        try {
          const newCust = await customersApi.create({ name: guestName || "Misafir Müşteri", phone: guestPhone, is_guest: true });
          customerId = newCust.id;
          if (guestAddress) {
            const newAddr = await customersApi.addAddress({ customerId, title: "Misafir Adres", addressText: guestAddress, isDefault: true });
            addressId = newAddr.id;
          }
        } catch (err) { alert("Misafir kaydı hatası: " + err.message); return; }
      }

      if (!customerId) { alert("Lütfen müşteri seçiniz veya Misafir Modunu aktif ediniz."); return; }
      if (currentCart.length === 0) { alert("Sepete en az bir ürün ekleyiniz."); return; }

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
          window.app.toast("Sipariş güncellendi");
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
      } catch (err) { alert("Sipariş hatası: " + err.message); }
    }
  };

  // =========================================================================
  // 6. GELEN ARAMALAR BİLEŞENİ
  // =========================================================================
  const callsComponent = {
    async init() {
      const refreshBtn = document.getElementById('btn-refresh-calls');
      if (refreshBtn) refreshBtn.addEventListener('click', () => this.refreshHistory());
      await this.refreshHistory();
    },

    async handleNewCall(callRecord) {
      sound.playIncomingCallTone();
      const phone = callRecord.phone_number;
      let customer = null;
      if (callRecord.customer_id) {
        try { customer = await customersApi.get(callRecord.customer_id); } catch (e) { }
      } else if (phone) {
        try { customer = await customersApi.findByPhone(phone); } catch (e) { }
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
          <div class="call-toast-badge"><div class="call-pulse-dot"></div>GELEN ARAMA</div>
          <button type="button" class="btn-close-toast" style="color:var(--text-muted); font-size:1.2rem;">×</button>
        </div>
        <div>
          <div class="call-phone-number">${phone}</div>
          <div class="call-customer-name" style="margin-top:2px;">${customer ? `👤 ${custName}` : `⚠️ Yeni Müşteri`}</div>
        </div>
        <div class="call-toast-actions">
          ${customer ? `
            <button type="button" class="btn-primary btn-toast-order" style="grid-column: 1 / -1; justify-content:center;">🛍️ Sipariş Oluştur</button>
          ` : `
            <button type="button" class="btn-primary btn-toast-guest" style="font-size:0.85rem; justify-content:center;">⚡ Hızlı Sipariş</button>
            <button type="button" class="btn-secondary btn-toast-new-cust" style="font-size:0.85rem; justify-content:center;">➕ Müşteri Kaydet</button>
          `}
        </div>
      `;

      toast.querySelector('.btn-close-toast').addEventListener('click', () => toast.remove());
      const orderBtn = toast.querySelector('.btn-toast-order');
      if (orderBtn && customer) {
        orderBtn.addEventListener('click', () => {
          callsApi.markProcessed(callRecord.id);
          window.app.orderModal.open({ prefillCustomerId: customer.id });
          toast.remove();
        });
      }
      const guestBtn = toast.querySelector('.btn-toast-guest');
      if (guestBtn) {
        guestBtn.addEventListener('click', () => {
          callsApi.markProcessed(callRecord.id);
          window.app.orderModal.open({ prefillPhone: phone });
          toast.remove();
        });
      }
      const newCustBtn = toast.querySelector('.btn-toast-new-cust');
      if (newCustBtn) {
        newCustBtn.addEventListener('click', () => {
          callsApi.markProcessed(callRecord.id);
          window.app.customersComponent.openNewCustomerModal(phone);
          toast.remove();
        });
      }

      container.appendChild(toast);
      setTimeout(() => toast.remove(), 35000);
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
          const timeStr = new Date(call.created_at).toLocaleString('tr-TR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
          const custName = call.customers?.name || '<span style="color:var(--text-subtle);">Kayıtsız</span>';
          return `
            <tr>
              <td><strong>${call.phone_number}</strong></td>
              <td>${custName}</td>
              <td>${timeStr}</td>
              <td>${call.is_processed ? `<span class="badge-status badge-delivered">İşlendi</span>` : `<span class="badge-status badge-new">Bekliyor</span>`}</td>
              <td>
                <button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.orderModal.open({ prefillPhone: '${call.phone_number}', prefillCustomerId: '${call.customer_id || ''}' })">🛍️ Sipariş Aç</button>
              </td>
            </tr>
          `;
        }).join('');
      } catch (err) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--danger);">Hata: ${err.message}</td></tr>`; }
    }
  };

  // =========================================================================
  // 7. MÜŞTERİLER BİLEŞENİ
  // =========================================================================
  let editingCustomerId = null;
  const customersComponent = {
    async init() {
      const searchInput = document.getElementById('search-customers-input');
      if (searchInput) {
        let t = null;
        searchInput.addEventListener('input', (e) => { clearTimeout(t); t = setTimeout(() => this.refresh(e.target.value), 250); });
      }
      const btnNew = document.getElementById('btn-new-customer');
      if (btnNew) btnNew.addEventListener('click', () => this.openNewCustomerModal());

      const form = document.getElementById('customer-form');
      if (form) form.addEventListener('submit', (e) => { e.preventDefault(); this.saveCustomer(); });

      const btnClose = document.getElementById('btn-close-customer-modal');
      if (btnClose) btnClose.addEventListener('click', () => this.closeModal());
      await this.refresh();
    },

    async refresh(search = "") {
      const tbody = document.getElementById('customers-table-body');
      if (!tbody) return;
      try {
        const customers = await customersApi.list({ search, includeGuests: false, limit: 100 });
        if (customers.length === 0) {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:3rem; color:var(--text-muted);">Müşteri bulunamadı.</td></tr>`;
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
                <button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.customersComponent.openEditCustomerModal('${c.id}')">✏️ Düzenle</button>
                <button class="btn-primary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.orderModal.open({ prefillCustomerId: '${c.id}' })">🛍️ Sipariş Ver</button>
              </div>
            </td>
          </tr>
        `).join('');
      } catch (err) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--danger);">Hata: ${err.message}</td></tr>`; }
    },

    openNewCustomerModal(prefillPhone = "") {
      editingCustomerId = null;
      const modal = document.getElementById('customer-modal');
      const form = document.getElementById('customer-form');
      if (form) form.reset();
      document.getElementById('customer-modal-title').textContent = "👤 Yeni Müşteri Kaydı";
      const phoneInput = document.getElementById('cust-phone');
      if (phoneInput && prefillPhone) phoneInput.value = prefillPhone;
      document.getElementById('cust-address-group').style.display = 'block';
      if (modal) modal.classList.add('open');
    },

    async openEditCustomerModal(id) {
      editingCustomerId = id;
      const modal = document.getElementById('customer-modal');
      document.getElementById('customer-modal-title').textContent = "✏️ Müşteri Düzenle";
      document.getElementById('cust-address-group').style.display = 'none';
      try {
        const c = await customersApi.get(id);
        if (!c) return;
        document.getElementById('cust-name').value = c.name || '';
        document.getElementById('cust-phone').value = c.phone || '';
        document.getElementById('cust-email').value = c.email || '';
        document.getElementById('cust-notes').value = c.notes || '';
        if (modal) modal.classList.add('open');
      } catch (err) { alert("Hata: " + err.message); }
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

      if (!name || !phone) { alert("İsim ve telefon zorunludur."); return; }
      try {
        if (editingCustomerId) {
          await customersApi.update(editingCustomerId, { name, phone, email: email || null, notes: notes || null });
          window.app.toast("Müşteri güncellendi");
        } else {
          const newCust = await customersApi.create({ name, phone, email, notes, is_guest: false });
          if (address) await customersApi.addAddress({ customerId: newCust.id, title: "Ev", addressText: address, isDefault: true });
          window.app.toast("Yeni müşteri eklendi");
        }
        this.closeModal();
        this.refresh();
      } catch (err) { alert("Hata: " + err.message); }
    }
  };

  // =========================================================================
  // 8. ÜRÜNLER & KATEGORİLER BİLEŞENİ
  // =========================================================================
  let editingProductId = null;
  let editingCategoryId = null;

  const productsComponent = {
    async init() {
      document.getElementById('btn-new-product')?.addEventListener('click', () => this.openNewProductModal());
      document.getElementById('btn-new-category')?.addEventListener('click', () => this.openNewCategoryModal());
      document.getElementById('product-form')?.addEventListener('submit', (e) => { e.preventDefault(); this.saveProduct(); });
      document.getElementById('category-form')?.addEventListener('submit', (e) => { e.preventDefault(); this.saveCategory(); });
      document.getElementById('btn-close-product-modal')?.addEventListener('click', () => this.closeProductModal());
      document.getElementById('btn-close-category-modal')?.addEventListener('click', () => this.closeCategoryModal());
      await this.refresh();
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
            <button class="btn-secondary" style="font-size:0.75rem; padding:0.25rem 0.5rem;" onclick="window.app.productsComponent.openEditCategoryModal('${cat.id}', '${cat.name}', '${cat.color || '#4f46e5'}', ${cat.sort_order || 0})">Düzenle</button>
          </div>
        `).join('');
        if (select) {
          select.innerHTML = `<option value="">-- Kategori Seçiniz --</option>${categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}`;
        }
      } catch (err) { console.warn(err); }
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
            <td><span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:var(--radius-full);">${p.categories?.name || 'Kategorisiz'}</span></td>
            <td style="font-weight:800; color:var(--success); font-size:1.05rem;">${Number(p.price).toFixed(2)} ₺ / ${p.unit || 'adet'}</td>
            <td>${p.is_active ? `<span class="badge-status badge-delivered">Aktif</span>` : `<span class="badge-status badge-cancelled">Pasif</span>`}</td>
            <td><button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.productsComponent.openEditProductModal('${p.id}')">✏️ Düzenle</button></td>
          </tr>
        `).join('');
      } catch (err) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--danger);">Hata: ${err.message}</td></tr>`; }
    },

    openNewProductModal() {
      editingProductId = null;
      document.getElementById('product-form')?.reset();
      document.getElementById('product-modal-title').textContent = "📦 Yeni Ürün Ekle";
      document.getElementById('product-modal')?.classList.add('open');
    },

    async openEditProductModal(id) {
      editingProductId = id;
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
        document.getElementById('product-modal')?.classList.add('open');
      } catch (err) { alert(err.message); }
    },

    closeProductModal() { document.getElementById('product-modal')?.classList.remove('open'); },

    async saveProduct() {
      const name = document.getElementById('prod-name').value.trim();
      const category_id = document.getElementById('prod-category-select').value || null;
      const price = document.getElementById('prod-price').value;
      const unit = document.getElementById('prod-unit').value.trim() || 'adet';
      const is_active = document.getElementById('prod-active').checked;
      if (!name || !price) { alert("İsim ve fiyat zorunludur."); return; }
      try {
        if (editingProductId) await productsApi.updateProduct(editingProductId, { name, category_id, price: Number(price), unit, is_active });
        else await productsApi.createProduct({ name, category_id, price: Number(price), unit, is_active });
        this.closeProductModal();
        this.refreshProducts();
      } catch (err) { alert(err.message); }
    },

    openNewCategoryModal() {
      editingCategoryId = null;
      document.getElementById('category-form')?.reset();
      document.getElementById('category-modal-title').textContent = "🏷️ Yeni Kategori Ekle";
      document.getElementById('category-modal')?.classList.add('open');
    },

    openEditCategoryModal(id, name, color, sortOrder) {
      editingCategoryId = id;
      document.getElementById('category-modal-title').textContent = "✏️ Kategoriyi Düzenle";
      document.getElementById('cat-name').value = name;
      document.getElementById('cat-color').value = color || '#4f46e5';
      document.getElementById('cat-sort').value = sortOrder || 0;
      document.getElementById('category-modal')?.classList.add('open');
    },

    closeCategoryModal() { document.getElementById('category-modal')?.classList.remove('open'); },

    async saveCategory() {
      const name = document.getElementById('cat-name').value.trim();
      const color = document.getElementById('cat-color').value;
      const sort_order = Number(document.getElementById('cat-sort').value || 0);
      if (!name) { alert("Kategori adı zorunludur."); return; }
      try {
        if (editingCategoryId) await productsApi.updateCategory(editingCategoryId, { name, color, sort_order });
        else await productsApi.createCategory({ name, color, sort_order });
        this.closeCategoryModal();
        this.refreshCategories();
      } catch (err) { alert(err.message); }
    }
  };

  // =========================================================================
  // 9. KURYELER BİLEŞENİ
  // =========================================================================
  let editingCourierId = null;
  const couriersComponent = {
    async init() {
      document.getElementById('btn-new-courier')?.addEventListener('click', () => this.openNewCourierModal());
      document.getElementById('courier-form')?.addEventListener('submit', (e) => { e.preventDefault(); this.saveCourier(); });
      document.getElementById('btn-close-courier-modal')?.addEventListener('click', () => this.closeModal());
      await this.refresh();
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
            <td>${c.is_active ? `<span class="badge-status badge-delivered">Aktif</span>` : `<span class="badge-status badge-cancelled">Pasif</span>`}</td>
            <td><button class="btn-secondary" style="font-size:0.8rem; padding:0.35rem 0.75rem;" onclick="window.app.couriersComponent.openEditCourierModal('${c.id}')">✏️ Düzenle</button></td>
          </tr>
        `).join('');
      } catch (err) { tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:var(--danger);">Hata: ${err.message}</td></tr>`; }
    },

    openNewCourierModal() {
      editingCourierId = null;
      document.getElementById('courier-form')?.reset();
      document.getElementById('courier-modal-title').textContent = "🏍️ Yeni Kurye Ekle";
      document.getElementById('courier-modal')?.classList.add('open');
    },

    async openEditCourierModal(id) {
      editingCourierId = id;
      document.getElementById('courier-modal-title').textContent = "✏️ Kuryeyi Düzenle";
      try {
        const list = await couriersApi.list();
        const c = list.find(item => item.id === id);
        if (!c) return;
        document.getElementById('courier-name').value = c.name;
        document.getElementById('courier-phone').value = c.phone;
        document.getElementById('courier-active').checked = c.is_active;
        document.getElementById('courier-modal')?.classList.add('open');
      } catch (err) { alert(err.message); }
    },

    closeModal() { document.getElementById('courier-modal')?.classList.remove('open'); },

    async saveCourier() {
      const name = document.getElementById('courier-name').value.trim();
      const phone = document.getElementById('courier-phone').value.trim();
      const is_active = document.getElementById('courier-active').checked;
      if (!name || !phone) { alert("İsim ve telefon zorunludur."); return; }
      try {
        if (editingCourierId) await couriersApi.update(editingCourierId, { name, phone, is_active });
        else await couriersApi.create({ name, phone });
        this.closeModal();
        this.refresh();
        ordersComponent.loadCouriers();
      } catch (err) { alert(err.message); }
    }
  };

  // =========================================================================
  // 10. AYARLAR BİLEŞENİ
  // =========================================================================
  const settingsComponent = {
    init() {
      document.getElementById('btn-test-db')?.addEventListener('click', () => this.testDbConnection());
      document.getElementById('settings-form')?.addEventListener('submit', (e) => { e.preventDefault(); this.saveSettings(); });
      document.getElementById('btn-reset-db')?.addEventListener('click', () => {
        if (confirm("Supabase ayarları varsayılanlara sıfırlansın mı?")) {
          config.resetDefaults();
          this.loadValues();
          resetClient();
          window.app.toast("Ayarlar sıfırlandı.");
        }
      });
      document.getElementById('btn-test-sound')?.addEventListener('click', () => sound.playIncomingCallTone());
      document.getElementById('setting-sound-enabled')?.addEventListener('change', (e) => {
        config.setSoundEnabled(e.target.checked);
        window.app.toast(e.target.checked ? "Ses açıldı 🔔" : "Ses kapatıldı 🔕");
      });
      this.loadValues();
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
      if (!url || !key) { alert("URL ve Key boş bırakılamaz!"); return; }
      config.setSupabaseUrl(url);
      config.setSupabaseKey(key);
      resetClient();
      initRealtime({
        onIncomingCall: (call) => callsComponent.handleNewCall(call),
        onOrderChange: () => ordersComponent.refresh()
      });
      window.app.toast("Ayarlar kaydedildi!");
      this.testDbConnection();
    }
  };

  // =========================================================================
  // 11. ANA UYGULAMA (APP)
  // =========================================================================
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
      console.log("🚀 Sipariş Takip Sistemi Başlatılıyor...");
      this.applyTheme(config.getTheme());
      this.bindThemeToggle();
      this.bindTabs();

      await Promise.all([
        this.ordersComponent.init(),
        this.orderModal.init(),
        this.callsComponent.init(),
        this.customersComponent.init(),
        this.productsComponent.init(),
        this.couriersComponent.init(),
        this.settingsComponent.init()
      ]);

      document.getElementById('btn-new-order-global')?.addEventListener('click', () => this.orderModal.open());

      initRealtime({
        onIncomingCall: (call) => this.callsComponent.handleNewCall(call),
        onOrderChange: () => this.ordersComponent.refresh()
      });

      this.bindKeyboardShortcuts();
      this.startClock();
    }

    applyTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      const btn = document.getElementById('btn-theme-toggle');
      if (btn) btn.innerHTML = theme === 'light' ? '🌙' : '☀️';
    }

    bindThemeToggle() {
      document.getElementById('btn-theme-toggle')?.addEventListener('click', () => {
        const next = config.getTheme() === 'light' ? 'dark' : 'light';
        config.setTheme(next);
        this.applyTheme(next);
      });
    }

    bindTabs() {
      document.querySelectorAll('.nav-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
      });
    }

    switchTab(tabId) {
      document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `tab-${tabId}`));
      if (tabId === 'orders') this.ordersComponent.refresh();
      else if (tabId === 'calls') this.callsComponent.refreshHistory();
      else if (tabId === 'customers') this.customersComponent.refresh();
      else if (tabId === 'products') this.productsComponent.refresh();
      else if (tabId === 'couriers') this.couriersComponent.refresh();
    }

    bindKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
        if (e.key === 'F2' || (e.altKey && e.key.toLowerCase() === 'n')) {
          e.preventDefault();
          this.orderModal.open();
        }
      });
    }

    startClock() {
      const timeEl = document.getElementById('header-live-time');
      const tick = () => {
        if (timeEl) timeEl.textContent = new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      };
      tick();
      setInterval(tick, 1000);
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
        el.style.transition = 'all 0.25s';
        setTimeout(() => el.remove(), 250);
      }, 3000);
    }

    quickSetStatus(orderId, status) { this.ordersComponent.quickSetStatus(orderId, status); }
    openEditOrderModal(orderId) { this.orderModal.open({ orderId }); }
    saveInlineTotal(orderId, val) { this.ordersComponent.saveInlineTotal(orderId, val); }
    saveInlinePaid(orderId, val) { this.ordersComponent.saveInlinePaid(orderId, val); }
    payFull(orderId) { this.ordersComponent.payFull(orderId); }
    payZero(orderId) { this.ordersComponent.payZero(orderId); }
  }

  window.app = new App();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.app.init());
  } else {
    window.app.init();
  }
})();
