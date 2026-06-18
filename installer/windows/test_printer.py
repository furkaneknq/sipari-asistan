"""
Yazici baglanti testi — Windows'ta calistir:
    python test_printer.py

Yazicinin IP ve PORT'unu asagida kendi ayarlariniza gore degistirin.
"""
import socket

HOST = "192.168.1.100"  # XP-80C yazicinin IP adresi (kendi IP'nize gore degistirin)
PORT = 9100             # XP-80C varsayilan port

print(f"Yaziciya baglaniliyor: {HOST}:{PORT} ...")

try:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.settimeout(5)
    srv.connect((HOST, PORT))
    print("Baglanti BASARILI!")

    # Test yazisi gonder (ESC/POS reset + Turkce codepage + metin + kesim)
    test_data = b"\x1b\x40"              # ESC @ = reset

    # Turkce codepage: tum olasi numaralari gonder (yazici tanimadigini yok sayar)
    test_data += b"\x1b\x74\x1d"         # ESC t 29 = CP857 (Xprinter/Cin yapimi)
    test_data += b"\x1b\x74\x0c"         # ESC t 12 = CP857 (Epson)

    test_data += "Yazici Testi OK!\n".encode("cp857")
    test_data += "Turkce: cCgGiIoOsSuU\n".encode("cp857")
    test_data += b"\n\n\n"
    test_data += b"\x1d\x56\x00"         # GS V 0 = tam kesim

    srv.sendall(test_data)
    print("Test yazisi gonderildi. Yazicidan cikti alin.")
    srv.close()

except socket.timeout:
    print(f"HATA: {HOST}:{PORT} adresine baglanilamadi (zaman asimi).")
    print("Yazicinin acik ve ayni agda oldugundan emin olun.")
except ConnectionRefusedError:
    print(f"HATA: {HOST}:{PORT} baglantisi reddedildi.")
    print("Yazicinin RAW/9100 modu acik mi kontrol edin.")
except Exception as e:
    print(f"HATA: {e}")
