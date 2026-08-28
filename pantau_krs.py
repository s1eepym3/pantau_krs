import requests
import time
import re
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= KONFIGURASI =================
# Halaman "Informasi Matakuliah Ditawarkan" (menampilkan SEMUA matkul, termasuk yang sudah diambil)
TARGET_URL = "http://portal.unimal.ac.id/index.php?pModule=0dWjo6almcqQmdGapaeW1w==&pSub=0dWjo6almcqQmdGapaeW15islaGXqtXHqQ==&pAct=18yZqg=="

# Cookie TIDAK perlu diganti (PHPSESSID berlaku seluruh portal). Ganti hanya jika sesi kedaluwarsa.
COOKIES = {
    "PHPSESSID": "ISI_COOKIE_PHPSESSID_DISINI"
}

# Matakuliah yang dipantau — tambah/kurangi sesuai kebutuhan
TARGET_MAKUL = [
    "KEAMANAN SISTEM KOMPUTER",
    "PEMROGRAMAN MOBILE",
    "REKAYASA PERANGKAT LUNAK",  # sudah diambil (pantau untuk pindah kelas)
    "CAPSTONE PROJECT",          # sudah diambil (pantau untuk pindah kelas)
]

TELEGRAM_BOT_TOKEN = "ISI_BOT_TOKEN_DISINI"
TELEGRAM_CHAT_ID = "ISI_CHAT_ID_DISINI"

CHECK_INTERVAL = 45      # Refresh belakang layar tiap 15 detik
REPORT_INTERVAL = 900    # Laporan rutin tiap 15 menit (20 mnt = 1200, 30 mnt = 1800)
# ===============================================

last_quota = {}
current_status = {}
last_report_time = 0

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        if result.get('ok'):
            print("[✓] Telegram terkirim")
        else:
            print(f"[✗] DITOLAK TELEGRAM: {result.get('description')}")
    except Exception as e:
        print(f"[✗] Error koneksi Telegram: {e}")

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
    lines.append("\n✅ Monitoring aktif • cek tiap 15 detik")
    return "\n".join(lines)

def check_quota():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
    }
    try:
        response = requests.get(TARGET_URL, cookies=COOKIES, headers=headers, verify=False, timeout=15)

        if "MOHAMMAD HAYKHAL NASUTION" not in response.text:
            print("[⚠️] Sesi login habis!")
            send_telegram_notification("⚠️ <b>PERINGATAN:</b> Sesi login portal habis. Silakan update cookie di skrip!")
            time.sleep(300)
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        current_status.clear()
        ringkasan = {}

        for row in soup.find_all('tr'):
            for makul in TARGET_MAKUL:
                if makul not in row.text:
                    continue
                cols = row.find_all('td')
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
                        send_telegram_notification(
                            f"🚨 <b>KUOTA TERSEDIA!</b>\n📚 {makul}\n🏫 Kelas {kelas} | 👨‍ {dosen}\n🔥 Sisa: <b>{kuota}</b>\n⚡ Ambil/pindah sekarang!")
                elif kuota != prev:
                    last_quota[class_id] = kuota
                    if kuota > 0:
                        send_telegram_notification(
                            f"🔔 <b>KUOTA BERUBAH!</b>\n📚 {makul}\n🏫 Kelas {kelas} | 👨‍🏫 {dosen}\n{prev} ➜ <b>{kuota}</b>\n⚡ Ambil/pindah sekarang!")
                    else:
                        send_telegram_notification(
                            f"😭 <b>Kuota habis kembali</b>\n📚 {makul} Kelas {kelas} kembali ke 0.")

        for m, items in ringkasan.items():
            print(f"[{time.strftime('%H:%M:%S')}] {m}: " + " ".join(items))
        return True

    except requests.exceptions.RequestException as e:
        print(f"[✗] Error koneksi: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Memulai monitoring kuota matakuliah...")
    send_telegram_notification("✅ <b>Monitoring Dimulai</b>\nRefresh 15 detik • Laporan detail tiap 15 menit.")

    while True:
        if check_quota():
            if time.time() - last_report_time >= REPORT_INTERVAL:
                send_telegram_notification(build_report())
                last_report_time = time.time()
        time.sleep(CHECK_INTERVAL)