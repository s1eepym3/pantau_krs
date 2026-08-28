import requests
import time
import re
import os
import sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= KONFIGURASI =================
PORTAL_BASE   = "http://portal.unimal.ac.id/"
TARGET_URL    = (
    "http://portal.unimal.ac.id/index.php"
    "?pModule=0dWjo6almcqQmdGapaeW1w=="
    "&pSub=0dWjo6almcqQmdGapaeW15islaGXqtXHqQ=="
    "&pAct=18yZqg=="
)

# Kredensial dibaca dari GitHub Secrets → env vars
UNIMAL_NIM         = os.environ["UNIMAL_NIM"]
UNIMAL_PASSWORD    = os.environ["UNIMAL_PASSWORD"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

# Verifikasi sesi: string ini harus ada di HTML setelah login berhasil
SESSION_MARKER = "MOHAMMAD HAYKHAL NASUTION"

# Matakuliah yang dipantau
TARGET_MAKUL = [
    "KEAMANAN SISTEM KOMPUTER",
    "PEMROGRAMAN MOBILE",
    "REKAYASA PERANGKAT LUNAK",   # sudah diambil (pantau untuk pindah kelas)
    "CAPSTONE PROJECT",           # sudah diambil (pantau untuk pindah kelas)
]

CHECK_INTERVAL    = 45      # detik antar refresh kuota
REPORT_INTERVAL   = 900     # laporan rutin tiap 15 menit
LOGIN_INTERVAL    = 5 * 3600  # proaktif re-login tiap 5 jam
LOGIN_RETRY_MAX   = 3       # maksimum percobaan login sebelum kirim alert
LOGIN_RETRY_DELAY = 10      # detik antar retry login

# Graceful exit sebelum batas 6 jam GitHub Actions (cron ulang tiap 5 jam)
RUN_DURATION = 4 * 3600 + 55 * 60   # 17.700 detik = 4j55m
# ===============================================

# State global
last_quota       = {}
current_status   = {}
last_report_time = 0
last_login_time  = 0

# Session tunggal — cookie PHPSESSID tersimpan otomatis di sini
SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.5 Mobile/15E148 Safari/604.1"
    )
})


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        resp   = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get("ok"):
            print("[✓] Telegram terkirim")
        else:
            print(f"[✗] DITOLAK TELEGRAM: {result.get('description')}")
    except Exception as e:
        print(f"[✗] Error koneksi Telegram: {e}")


# ============================================================
# AUTO-LOGIN
# ============================================================

def do_login() -> bool:
    """
    Login sekali ke portal menggunakan NIM + password.
    Cookie PHPSESSID tersimpan otomatis di SESSION.
    Kembalikan True jika login berhasil, False jika gagal.
    """
    global last_login_time
    try:
        # Langkah 1: GET halaman login untuk ambil form fields
        print("[🔑] Mengambil halaman login...")
        home = SESSION.get(PORTAL_BASE, timeout=15)
        soup = BeautifulSoup(home.text, "html.parser")

        # Langkah 2: Temukan <form> yang memiliki input[type=password]
        login_form = None
        for form in soup.find_all("form"):
            if form.find("input", {"type": "password"}):
                login_form = form
                break
        if login_form is None:
            print("[✗] Form login tidak ditemukan di halaman.")
            return False

        # Langkah 3: Ekstrak action URL, hidden fields, nama field username & password
        action_raw = login_form.get("action", PORTAL_BASE)
        action_url = urljoin(PORTAL_BASE, action_raw)

        payload = {}
        # Semua hidden inputs
        for inp in login_form.find_all("input", {"type": "hidden"}):
            name  = inp.get("name")
            value = inp.get("value", "")
            if name:
                payload[name] = value

        # Field username = input[type=text] pertama
        txt_input = login_form.find("input", {"type": "text"})
        pwd_input = login_form.find("input", {"type": "password"})
        if not txt_input or not pwd_input:
            print("[✗] Field username/password tidak ditemukan di form.")
            return False

        payload[txt_input["name"]] = UNIMAL_NIM
        payload[pwd_input["name"]] = UNIMAL_PASSWORD

        # Langkah 4: POST form login
        method = login_form.get("method", "post").upper()
        print(f"[🔑] Mengirim {method} ke {action_url} ...")
        if method == "GET":
            resp = SESSION.get(action_url, params=payload, timeout=15)
        else:
            resp = SESSION.post(action_url, data=payload, timeout=15)

        # Langkah 5: Validasi — GET halaman target, cek SESSION_MARKER
        check = SESSION.get(TARGET_URL, timeout=15)
        if SESSION_MARKER in check.text:
            print("[✓] Login berhasil. Sesi aktif.")
            last_login_time = time.time()
            return True
        else:
            print("[✗] Login gagal: marker nama tidak ditemukan setelah POST.")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[✗] Error koneksi saat login: {e}")
        return False


def login_with_retry(reason: str = "") -> bool:
    """
    Coba login hingga LOGIN_RETRY_MAX kali.
    Jika semua gagal: kirim alert Telegram, tunggu 5 menit, lalu return False
    (pemanggil tidak crash, akan retry di iterasi loop berikutnya).
    """
    if reason:
        print(f"[🔑] Memulai (ulang) login — alasan: {reason}")
    for attempt in range(1, LOGIN_RETRY_MAX + 1):
        print(f"[🔑] Login percobaan {attempt}/{LOGIN_RETRY_MAX}...")
        if do_login():
            send_telegram("🔑 <b>Sesi diperbarui otomatis</b>\nBot kembali memantau kuota.")
            return True
        if attempt < LOGIN_RETRY_MAX:
            print(f"[⏳] Tunggu {LOGIN_RETRY_DELAY} detik sebelum retry...")
            time.sleep(LOGIN_RETRY_DELAY)

    # Semua percobaan gagal
    alasan_display = reason or "tidak diketahui"
    send_telegram(
        f"🚨 <b>AUTO-LOGIN GAGAL</b>\n"
        f"Alasan: {alasan_display}\n"
        f"Bot akan mencoba login ulang tiap 5 menit secara otomatis.\n"
        f"Pastikan UNIMAL_NIM dan UNIMAL_PASSWORD di Secrets sudah benar."
    )
    print("[✗] Semua percobaan login gagal. Akan retry di iterasi berikutnya.")
    return False


# ============================================================
# LAPORAN RUTIN
# ============================================================

def build_report():
    lines = ["📊 <b>LAPORAN DETAIL STATUS KUOTA</b>", f"🕐 {time.strftime('%H:%M:%S')}"]
    total_terbuka = 0
    for makul in TARGET_MAKUL:
        entries = current_status.get(makul, [])
        if not entries:
            continue
        lines.append(f"\n📚 <b>{makul}</b>")
        for kelas, kuota, dosen in entries:
            icon = "🟢" if kuota > 0 else "⚪"
            if kuota > 0:
                total_terbuka += 1
            lines.append(f"{icon} Kelas {kelas} | {dosen}\n└ Sisa Kuota: <b>{kuota}</b>")
    if total_terbuka > 0:
        lines.append(f"\n🚨 <b>ADA {total_terbuka} KUOTA TERBUKA! AMBIL/PINDAH SEKARANG!</b>")
    else:
        lines.append("\n😴 Semua kuota target masih 0. Bot tetap berjaga.")
    lines.append("\n✅ Monitoring aktif • cek tiap 45 detik")
    return "\n".join(lines)


# ============================================================
# CEK KUOTA (logika parsing TIDAK DIUBAH)
# ============================================================

def check_quota() -> bool:
    """
    Ambil halaman target via SESSION (cookie otomatis terbawa).
    Jika sesi mati → login ulang otomatis, lalu coba sekali lagi.
    Kembalikan True jika berhasil parsing, False jika gagal.
    """
    try:
        response = SESSION.get(TARGET_URL, timeout=15)

        # --- REAKTIF: sesi mati → login ulang ---
        if SESSION_MARKER not in response.text:
            print("[⚠️] Sesi login habis! Memulai auto-login reaktif...")
            ok = login_with_retry(reason="sesi habis saat cek kuota")
            if not ok:
                time.sleep(300)   # tunggu 5 menit sebelum coba lagi
                return False
            # Ulangi request setelah login berhasil
            response = SESSION.get(TARGET_URL, timeout=15)
            if SESSION_MARKER not in response.text:
                print("[✗] Masih gagal setelah re-login.")
                return False

        soup = BeautifulSoup(response.text, "html.parser")
        current_status.clear()
        ringkasan = {}

        for row in soup.find_all("tr"):
            for makul in TARGET_MAKUL:
                if makul not in row.text:
                    continue
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue

                # KELAS: sel berpola "A1", "A2", dst
                kelas_idx = None
                for i, c in enumerate(cols):
                    if re.fullmatch(r"A\d+", c.get_text(strip=True)):
                        kelas_idx = i
                        break
                if kelas_idx is None:
                    continue
                kelas = cols[kelas_idx].get_text(strip=True)

                # DOSEN: sel tepat sebelum kolom KELAS
                dosen = cols[kelas_idx - 1].get_text(strip=True) if kelas_idx > 0 else "-"
                if dosen == "":
                    dosen = "-"

                # JANGKAR W/P -> setelahnya SKS, lalu SISA KUOTA
                wp_idx = None
                for i, c in enumerate(cols):
                    if c.get_text(strip=True) in ("W", "P"):
                        wp_idx = i
                        break
                kuota = None
                if wp_idx is not None and wp_idx + 2 < len(cols):
                    calon = cols[wp_idx + 2].get_text(strip=True)
                    if re.fullmatch(r"\d+", calon):
                        kuota = int(calon)
                if kuota is None:
                    continue

                current_status.setdefault(makul, []).append((kelas, kuota, dosen))
                ringkasan.setdefault(makul, []).append(f"{kelas}={kuota}")

                # --- DETEKSI PERUBAHAN (alert instan, independen dari laporan rutin) ---
                class_id = f"{makul}_{kelas}"
                prev = last_quota.get(class_id)

                if prev is None:
                    last_quota[class_id] = kuota
                    if kuota > 0:
                        send_telegram(
                            f"🚨 <b>KUOTA TERSEDIA!</b>\n"
                            f"📚 {makul}\n"
                            f"🏫 Kelas {kelas} | 👨‍ {dosen}\n"
                            f"🔥 Sisa: <b>{kuota}</b>\n"
                            f"⚡ Ambil/pindah sekarang!"
                        )
                elif kuota != prev:
                    last_quota[class_id] = kuota
                    if kuota > 0:
                        send_telegram(
                            f"🔔 <b>KUOTA BERUBAH!</b>\n"
                            f"📚 {makul}\n"
                            f"🏫 Kelas {kelas} | 👨‍🏫 {dosen}\n"
                            f"{prev} ➜ <b>{kuota}</b>\n"
                            f"⚡ Ambil/pindah sekarang!"
                        )
                    else:
                        send_telegram(
                            f"😭 <b>Kuota habis kembali</b>\n"
                            f"📚 {makul} Kelas {kelas} kembali ke 0."
                        )

        for m, items in ringkasan.items():
            print(f"[{time.strftime('%H:%M:%S')}] {m}: " + " ".join(items))
        return True

    except requests.exceptions.RequestException as e:
        print(f"[✗] Error koneksi: {e}")
        return False


# ============================================================
# MAIN LOOP
# ============================================================

if __name__ == "__main__":
    start_time = time.time()
    print("☁️  Monitoring Cloud Dimulai (Auto-Login aktif)")
    print(f"⏱️  Akan berjalan selama {RUN_DURATION // 3600}j {(RUN_DURATION % 3600) // 60}m lalu exit.")

    # Login pertama kali saat start
    if not login_with_retry(reason="start awal"):
        # Jika login awal gagal total, tetap jalan — retry akan terjadi di check_quota
        print("[⚠️] Login awal gagal, monitoring tetap dimulai (retry otomatis).")

    send_telegram(
        "☁️ <b>Monitoring Cloud Dimulai</b>\n"
        "🔑 Auto-Login aktif — sesi diperbarui otomatis.\n"
        "Refresh 45 detik • Laporan detail tiap 15 menit.\n"
        "Bot akan restart otomatis via GitHub Actions."
    )

    while True:
        now     = time.time()
        elapsed = now - start_time

        # Graceful exit sebelum batas 6 jam GitHub Actions
        if elapsed >= RUN_DURATION:
            print(f"[⏹️] Batas waktu {RUN_DURATION // 60} menit tercapai. Keluar dengan sopan.")
            sys.exit(0)

        # PROAKTIF: re-login tiap LOGIN_INTERVAL (5 jam)
        if last_login_time > 0 and (now - last_login_time) >= LOGIN_INTERVAL:
            print("[🔑] Proaktif: re-login terjadwal tiap 5 jam.")
            login_with_retry(reason="proaktif 5 jam")

        if check_quota():
            if time.time() - last_report_time >= REPORT_INTERVAL:
                send_telegram(build_report())
                last_report_time = time.time()

        # Hitung sisa waktu; jangan tidur melewati batas RUN_DURATION
        remaining  = RUN_DURATION - (time.time() - start_time)
        sleep_time = min(CHECK_INTERVAL, max(0, remaining))
        if sleep_time <= 0:
            break
        time.sleep(sleep_time)

    print("[⏹️] Loop selesai. Keluar.")
    sys.exit(0)
