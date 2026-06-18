import win32print

# Yazici adi (ayni .env dosyasindaki PRINTER_WIN_NAME)
printer_name = "XP-80C"

try:
    handle = win32print.OpenPrinter(printer_name)
    win32print.StartDocPrinter(handle, 1, ("ESC/POS", None, "RAW"))
    win32print.StartPagePrinter(handle)

    tests = [
        (b"\x1b\x74\x1d", "cp857", "TEST 1: ESC t 29 + cp857 (Xprinter)"),
        (b"\x1b\x74\x0c", "cp857", "TEST 2: ESC t 12 + cp857 (Epson)"),
        (b"\x1b\x74\x25", "cp857", "TEST 3: ESC t 37 + cp857 (Star)"),
        (b"\x1b\x74\x08", "cp857", "TEST 4: ESC t 8  + cp857 (Datecs)"),
        (b"\x1b\x74\x11", "cp1254", "TEST 5: ESC t 17 + cp1254 (WPC1254)"),
        (b"\x1b\x74\x49", "cp1254", "TEST 6: ESC t 73 + cp1254 (WPC1254 Alt)"),
        (b"", "utf-8", "TEST 7: No codepage + UTF-8"),
    ]

    buf = bytearray()
    
    for cmd, enc, name in tests:
        buf.extend(b"\x1b\x40") # Her test oncesi reset
        buf.extend(cmd)
        try:
            text = f"{name}\nTurkce: cCgGiIoOsSuU (Ingilizce)\nTurkce: çÇğĞıİöÖşŞüÜ (Ozel Karakterler)\n--------------------------------\n\n".encode(enc, errors='replace')
            buf.extend(text)
        except Exception:
            pass

    buf.extend(b"\n\n\n\x1d\x56\x00") # Tam kesim
    
    win32print.WritePrinter(handle, bytes(buf))
    win32print.EndPagePrinter(handle)
    win32print.EndDocPrinter(handle)
    win32print.ClosePrinter(handle)
    print("Test fise gonderildi! Lutfen fis ciktisindaki 'Ozel Karakterler' satirina bakin.")
    print("Hangi TEST numarasinda Turkce karakterler Duzgun (çÇğĞıİöÖşŞüÜ) cikti?")
except Exception as e:
    print("HATA:", e)
