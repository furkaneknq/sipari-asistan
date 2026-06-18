-- Arama geçmişinde cevapsız arama işaretleme için
ALTER TABLE incoming_calls ADD COLUMN IF NOT EXISTS is_unanswered BOOLEAN DEFAULT FALSE;

-- Cevapsız aramalar için status gösterimi
COMMENT ON COLUMN incoming_calls.is_unanswered IS 'Kullanıcı popup''ı işlem yapmadan kapattığında True';