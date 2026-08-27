# 🎓 Bot Monitoring Kuota KRS — Universitas Malikussaleh

Bot Python yang memantau sisa kuota matakuliah di portal akademik Unimal dan mengirim
notifikasi instan ke Telegram setiap kali kuota berubah atau tersedia.

---

## ✨ Fitur

| Fitur | Detail |
|---|---|
| 🔍 Pemantauan otomatis | Cek kuota tiap **45 detik** |
| 🔔 Alert instan | Notifikasi langsung saat kuota berubah |
| 📊 Laporan rutin | Ringkasan lengkap tiap **15 menit** |
| ☁️ Cloud 24/7 | Berjalan gratis di **GitHub Actions** |
| 🔐 Tanpa hardcode | Semua kredensial via **GitHub Secrets** |

**Matakuliah yang dipantau:**
- KEAMANAN SISTEM KOMPUTER
- PEMROGRAMAN MOBILE
- REKAYASA PERANGKAT LUNAK
- CAPSTONE PROJECT

---

## 🚀 Setup Cloud (GitHub Actions) — Gratis Total

### Langkah 1 — Buat repositori GitHub

> [!IMPORTANT]
> Buat repo **PUBLIC** agar mendapatkan GitHub Actions Minutes yang tidak terbatas.
> Repo private mendapat kuota terbatas (2.000 menit/bulan di Free plan).

1. Buka [github.com/new](https://github.com/new)
2. Pilih **Public**
3. Klik **Create repository**
4. Push folder ini ke repo tersebut:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/USERNAME/REPO.git
   git push -u origin main
   ```

### Langkah 2 — Isi 3 Secrets

Buka **Settings → Secrets and variables → Actions → New repository secret**,
lalu tambahkan tiga secret berikut:

| Secret Name | Nilai | Cara dapat |
|---|---|---|
| `PHPSESSID` | Nilai cookie PHPSESSID | Lihat Langkah 3 di bawah |
| `TELEGRAM_BOT_TOKEN` | Token bot Telegram | Dari [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | ID chat Telegram kamu | Dari [@userinfobot](https://t.me/userinfobot) |

#### Cara ambil PHPSESSID:
1. Login ke portal Unimal di browser
2. Tekan **F12** → tab **Application** (Chrome) atau **Storage** (Firefox)
3. Pilih **Cookies** → cari `PHPSESSID`
4. Salin nilainya

> [!CAUTION]
> **JANGAN pernah klik tombol Logout** di portal. Logout akan menginvalidasi sesi
> dan membuat PHPSESSID tidak berlaku. Cukup tutup tab browser saja.

### Langkah 3 — Jalankan pertama kali

1. Di repositori GitHub, buka tab **Actions**
2. Pilih workflow **"Pantau Kuota KRS Unimal"**
3. Klik **Run workflow** → **Run workflow**
4. Tunggu beberapa detik — Telegram kamu akan menerima pesan:
   > ☁️ **Monitoring Cloud Dimulai**

Setelah pesan tersebut masuk, monitoring cloud sudah aktif.

---

## 🔄 Migrasi dari Skrip Lokal

> [!IMPORTANT]
> **Jangan langsung matikan skrip lokal** sebelum memverifikasi cloud sudah berjalan.
> Ikuti urutan ini untuk memastikan tidak ada celah monitoring dan tidak ada
> notifikasi duplikat.

**Prosedur migrasi yang aman:**

```
[Laptop]  pantau_krs.py  ── BERJALAN ──────────────────► [stop nanti]
[GitHub]  pantau_krs_cloud.py  ── BELUM JALAN ──► [start dulu]
```

1. **Push ke GitHub** dan pastikan workflow sudah di-trigger (manual atau cron)
2. **Tunggu pesan Telegram** "☁️ Monitoring Cloud Dimulai" masuk
3. **Verifikasi** laporan pertama (15 menit setelah start) terlihat wajar
4. **Baru kemudian** hentikan skrip lokal dengan **Ctrl+C** di terminal

> Urutan ini menjamin: tidak ada celah waktu tanpa monitoring, dan tidak ada periode
> di mana dua instance berjalan bersamaan terlalu lama (yang menyebabkan notifikasi ganda).

---

## ⚙️ Cara Kerja Otomatis

```
Cron GitHub Actions (setiap 5 jam UTC)
    │
    ▼
Jalankan pantau_krs_cloud.py
    │
    ├─► Loop: cek portal tiap 45 detik
    │        ├─► Kuota berubah? → Kirim alert instan ke Telegram
    │        └─► Tiap 15 menit → Kirim laporan ringkasan
    │
    └─► Setelah 4j55m → Exit dengan sopan (sys.exit 0)
          │
          └─► Cron berikutnya akan start instance baru
```

---

## 🛠️ Troubleshooting

### ⚠️ "Sesi login portal habis"
Bot mengirim notifikasi ini ketika string nama tidak ditemukan di HTML response.

**Solusi:**
1. Login ke portal Unimal di browser
2. Ambil nilai `PHPSESSID` terbaru (F12 → Application → Cookies)
3. Perbarui secret `PHPSESSID` di **Settings → Secrets and variables → Actions**
4. Trigger workflow manual: tab **Actions → Run workflow**

> [!CAUTION]
> **JANGAN klik Logout di portal** — ini akan menginvalidasi PHPSESSID yang sedang
> digunakan bot. Cukup tutup tab saja.

### ❌ Workflow tidak jalan padahal sudah di-push
- Pastikan file workflow ada di path: `.github/workflows/pantau.yml`
- Pastikan repo **Public** atau billing Actions sudah aktif
- Cek tab **Actions** → apakah ada error di step "Checkout repository"

### 🔔 Telegram tidak menerima pesan
- Verifikasi `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` sudah benar
- Pastikan kamu sudah pernah send `/start` ke bot kamu di Telegram
- Cek log Actions di tab **Actions** → lihat output step "Jalankan monitoring kuota"

---

## 📁 Struktur File

```
monitor_kuota/
├── pantau_krs.py           # Skrip lokal asli (jangan diubah)
├── pantau_krs_cloud.py     # Versi cloud (baca env vars, exit 4j55m)
├── requirements.txt        # requests, beautifulsoup4
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── pantau.yml      # GitHub Actions workflow
```
