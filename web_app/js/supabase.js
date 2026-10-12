/**
 * Supabase İstemcisi ve Veritabanı Yardımcı Metotları
 * ESM üzerinden @supabase/supabase-js v2 kütüphanesini yükler.
 */

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
import { config } from './config.js';

let supabaseClient = null;
let realtimeChannel = null;

export function getClient() {
  const url = config.getSupabaseUrl();
  const key = config.getSupabaseKey();

  if (!url || !key) {
    throw new Error("Supabase URL veya API Anahtarı eksik! Ayarlar sekmesinden doldurunuz.");
  }

  if (!supabaseClient) {
    supabaseClient = createClient(url, key, {
      auth: { persistSession: false },
      realtime: {
        params: {
          eventsPerSecond: 10,
        },
      },
    });
    if (supabaseClient && !supabaseClient.table) {
      supabaseClient.table = function (t) { return supabaseClient.from(t); };
    }
  }
  return supabaseClient;
}

export function resetClient() {
  if (realtimeChannel && supabaseClient) {
    supabaseClient.removeChannel(realtimeChannel);
    realtimeChannel = null;
  }
  supabaseClient = null;
}

export async function testConnection() {
  try {
    const client = getClient();
    const { data, error } = await client.from("categories").select("id").limit(1);
    if (error) return { ok: false, error: error.message };
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

// =========================================================================
// 1) SİPARİŞLER (ORDERS)
// =========================================================================

export const ordersApi = {
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

  async create({
    customerId,
    addressId = null,
    courierId = null,
    status = "new",
    orderDate = new Date().toISOString().slice(0, 10),
    deliveryTime = null,
    paymentMethod = "cash",
    paymentStatus = "pending",
    notes = "",
    items = [],
    totalAmount = 0,
    paidAmount = 0
  }) {
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

    // 1. Sipariş ana kaydını ekle
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

    // 2. Kalemleri ekle
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

      const { error: itemsError } = await client
        .from("order_items")
        .insert(itemsPayload);

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

  async updateCourier(orderId, courierId) {
    const client = getClient();
    const { data, error } = await client
      .from("orders")
      .update({ courier_id: courierId || null })
      .eq("id", orderId)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async updatePayment(orderId, paymentMethod, paymentStatus) {
    const client = getClient();
    const { data, error } = await client
      .from("orders")
      .update({
        payment_method: paymentMethod,
        payment_status: paymentStatus
      })
      .eq("id", orderId)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async update(orderId, updates, newItems = null) {
    const client = getClient();
    const { data, error } = await client
      .from("orders")
      .update(updates)
      .eq("id", orderId)
      .select()
      .single();

    if (error) throw error;

    if (newItems !== null) {
      // Eski kalemleri sil, yenileri ekle
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
  },

  async delete(orderId) {
    const client = getClient();
    const { error } = await client.from("orders").delete().eq("id", orderId);
    if (error) throw error;
    return true;
  }
};

// =========================================================================
// 2) MÜŞTERİLER (CUSTOMERS) & ADRESLER
// =========================================================================

export const customersApi = {
  async list({ search = "", includeGuests = false, limit = 100 } = {}) {
    const client = getClient();
    let query = client
      .from("customers")
      .select("id, name, phone, email, notes, is_guest, created_at")
      .order("name", { ascending: true });

    if (!includeGuests) {
      query = query.eq("is_guest", false);
    }

    if (search && search.trim()) {
      const s = search.trim();
      query = query.or(`name.ilike.%${s}%,phone.ilike.%${s}%`);
    }

    if (limit > 0) {
      query = query.limit(limit);
    }

    const { data, error } = await query;
    if (error) throw error;
    return data || [];
  },

  async get(id) {
    const client = getClient();
    const { data, error } = await client
      .from("customers")
      .select("*")
      .eq("id", id)
      .single();
    if (error) throw error;
    return data;
  },

  async findByPhone(phone) {
    const client = getClient();
    const cleanPhone = phone.replace(/\D/g, "");
    // Son 10 haneye göre ara
    const last10 = cleanPhone.slice(-10);

    const { data, error } = await client
      .from("customers")
      .select("*")
      .or(`phone.eq.${cleanPhone},phone.ilike.%${last10}`)
      .limit(1);

    if (error) throw error;
    return data && data.length > 0 ? data[0] : null;
  },

  async create({ name, phone, email = "", notes = "", is_guest = false }) {
    const client = getClient();
    const { data, error } = await client
      .from("customers")
      .insert({
        name: name.trim(),
        phone: phone.trim(),
        email: email ? email.trim() : null,
        notes: notes ? notes.trim() : null,
        is_guest: !!is_guest
      })
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async update(id, updates) {
    const client = getClient();
    const { data, error } = await client
      .from("customers")
      .update(updates)
      .eq("id", id)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async delete(id) {
    const client = getClient();
    const { error } = await client.from("customers").delete().eq("id", id);
    if (error) throw error;
    return true;
  },

  async getAddresses(customerId) {
    const client = getClient();
    const { data, error } = await client
      .from("customer_addresses")
      .select("*")
      .eq("customer_id", customerId)
      .order("is_default", { ascending: false });
    if (error) throw error;
    return data || [];
  },

  async addAddress({ customerId, title = "Ev", addressText, isDefault = false }) {
    const client = getClient();
    if (isDefault) {
      await client
        .from("customer_addresses")
        .update({ is_default: false })
        .eq("customer_id", customerId);
    }
    const { data, error } = await client
      .from("customer_addresses")
      .insert({
        customer_id: customerId,
        title: title || "Adres",
        address_text: addressText.trim(),
        is_default: !!isDefault
      })
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async getRecentOrders(customerId, limit = 5) {
    const client = getClient();
    const { data, error } = await client
      .from("orders")
      .select(`
        id,
        order_number,
        order_date,
        total_amount,
        status,
        created_at
      `)
      .eq("customer_id", customerId)
      .order("created_at", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return data || [];
  }
};

// =========================================================================
// 3) KATEGORİLER & ÜRÜNLER (PRODUCTS)
// =========================================================================

export const productsApi = {
  async getCategories() {
    const client = getClient();
    const { data, error } = await client
      .from("categories")
      .select("*")
      .order("sort_order", { ascending: true });
    if (error) throw error;
    return data || [];
  },

  async createCategory({ name, sort_order = 0, color = "#4f46e5" }) {
    const client = getClient();
    const { data, error } = await client
      .from("categories")
      .insert({ name: name.trim(), sort_order, color, is_active: true })
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async updateCategory(id, updates) {
    const client = getClient();
    const { data, error } = await client
      .from("categories")
      .update(updates)
      .eq("id", id)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async deleteCategory(id) {
    const client = getClient();
    const { error } = await client.from("categories").delete().eq("id", id);
    if (error) throw error;
    return true;
  },

  async getProducts({ activeOnly = false } = {}) {
    const client = getClient();
    let query = client
      .from("products")
      .select(`
        id,
        category_id,
        name,
        price,
        unit,
        is_active,
        sort_order,
        categories:category_id (name, color)
      `)
      .order("sort_order", { ascending: true })
      .order("name", { ascending: true });

    if (activeOnly) {
      query = query.eq("is_active", true);
    }

    const { data, error } = await query;
    if (error) throw error;
    return data || [];
  },

  async createProduct({ category_id, name, price, unit = "adet", sort_order = 0, is_active = true }) {
    const client = getClient();
    const { data, error } = await client
      .from("products")
      .insert({
        category_id: category_id || null,
        name: name.trim(),
        price: Number(price),
        unit: unit || "adet",
        sort_order: Number(sort_order),
        is_active: !!is_active
      })
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async updateProduct(id, updates) {
    const client = getClient();
    const { data, error } = await client
      .from("products")
      .update(updates)
      .eq("id", id)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async deleteProduct(id) {
    const client = getClient();
    const { error } = await client.from("products").delete().eq("id", id);
    if (error) throw error;
    return true;
  }
};

// =========================================================================
// 4) KURYELER (COURIERS)
// =========================================================================

export const couriersApi = {
  async list({ activeOnly = false } = {}) {
    const client = getClient();
    let query = client.from("couriers").select("*").order("name", { ascending: true });
    if (activeOnly) query = query.eq("is_active", true);
    const { data, error } = await query;
    if (error) throw error;
    return data || [];
  },

  async create({ name, phone, password = "" }) {
    const client = getClient();
    const { data, error } = await client
      .from("couriers")
      .insert({
        name: name.trim(),
        phone: phone.trim(),
        password: password || null,
        is_active: true
      })
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async update(id, updates) {
    const client = getClient();
    const { data, error } = await client
      .from("couriers")
      .update(updates)
      .eq("id", id)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async delete(id) {
    const client = getClient();
    const { error } = await client.from("couriers").delete().eq("id", id);
    if (error) throw error;
    return true;
  }
};

// =========================================================================
// 5) GELEN ARAMALAR (INCOMING CALLS)
// =========================================================================

export const callsApi = {
  async list({ limit = 50 } = {}) {
    const client = getClient();
    const { data, error } = await client
      .from("incoming_calls")
      .select(`
        id,
        phone_number,
        device_id,
        customer_id,
        is_processed,
        created_at,
        customers:customer_id (id, name, phone)
      `)
      .order("created_at", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return data || [];
  },

  async markProcessed(id) {
    const client = getClient();
    const { data, error } = await client
      .from("incoming_calls")
      .update({ is_processed: true })
      .eq("id", id)
      .select()
      .single();
    if (error) throw error;
    return data;
  }
};

// =========================================================================
// 6) REALTIME SUBSCRIPTION
// =========================================================================

export function initRealtime({ onIncomingCall, onOrderChange }) {
  try {
    const client = getClient();

    if (realtimeChannel) {
      client.removeChannel(realtimeChannel);
    }

    realtimeChannel = client
      .channel('schema-db-changes')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'incoming_calls' },
        payload => {
          if (onIncomingCall) onIncomingCall(payload.new);
        }
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'orders' },
        payload => {
          if (onOrderChange) onOrderChange(payload);
        }
      )
      .subscribe((status) => {
        console.log(`[Supabase Realtime] Durum: ${status}`);
        const statusEl = document.getElementById("realtime-badge");
        if (statusEl) {
          if (status === "SUBSCRIBED") {
            statusEl.className = "status-badge status-connected";
            statusEl.textContent = "● Canlı Bağlı";
          } else {
            statusEl.className = "status-badge status-connecting";
            statusEl.textContent = "○ Bağlanıyor...";
          }
        }
      });

    return realtimeChannel;
  } catch (err) {
    console.warn("Realtime başlatılamadı:", err);
    return null;
  }
}
