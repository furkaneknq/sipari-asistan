/**
 * Sipariş Takip Sistemi - Web Port Yapılandırması
 * Supabase bağlantı parametrelerini ve varsayılan ayarları yönetir.
 */

const DEFAULT_SUPABASE_URL = "https://xgvlgmikxchpttydtelb.supabase.co";
// Güvenlik: Secret key burada saklanmıyor. Kullanıcı Ayarlar panelinden girer.
const DEFAULT_SUPABASE_KEY = "";

export const config = {
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
