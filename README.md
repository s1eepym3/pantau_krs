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
| 🔑 Auto-Login | Login otomatis dengan NIM+password, **sesi tidak pernah kedaluwarsa** |
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

### Langkah 2 — Isi 4 Secrets

Buka **Settings → Secrets and variables → Actions → New repository secret**,
lalu tambahkan **satu per satu** keempat secret berikut:

| Secret Name | Nilai | Keterangan |
|---|---|---|
| `UNIMAL_NIM` | NIM kamu (contoh: `230170166`) | Digunakan untuk auto-login portal |
| `UNIMAL_PASSWORD` | Password portal akademik kamu | Digunakan untuk auto-login portal |
| `TELEGRAM_BOT_TOKEN` | Token bot Telegram | Dari [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | ID chat Telegram kamu (bisa banyak, pisahkan dengan koma) | Dari [@userinfobot](https://t.me/userinfobot), contoh: `908908992` atau `908908992,12345678` |

> [!IMPORTANT]
> Bot akan login **otomatis** menggunakan NIM + password setiap kali dijalankan.
> Kamu **tidak perlu lagi menyentuh PHPSESSID** — sesi diperbarui sendiri.

### Langkah 3 — Jalankan pertama kali

1. Di repositori GitHub, buka tab **Actions**
2. Pilih workflow **"Pantau Kuota KRS Unimal"**
3. Klik **Run workflow** → **Run workflow**
4. Tunggu beberapa detik — Telegram kamu akan menerima pesan:
   > ☁️ **Monitoring Cloud Dimulai** — 🔑 Auto-Login aktif

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
    ├─► [🔑] Login otomatis dengan NIM + password
    │         └─► Cookie PHPSESSID tersimpan di session
    │
    ├─► Loop: cek portal tiap 45 detik
    │        ├─► Sesi mati? → Re-login reaktif otomatis
    │        ├─► Tiap 5 jam → Re-login proaktif otomatis
    │        ├─► Kuota berubah? → Kirim alert instan ke Telegram
    │        └─► Tiap 15 menit → Kirim laporan ringkasan
    │
    └─► Setelah 4j55m → Exit dengan sopan (sys.exit 0)
          │
          └─► Cron berikutnya akan start instance baru
```

---

## 🛠️ Troubleshooting

### 🚨 "AUTO-LOGIN GAGAL"
Bot mengirim notifikasi ini ketika login dengan NIM + password gagal setelah 3 kali percobaan.

**Kemungkinan penyebab & solusi:**

| Penyebab | Solusi |
|---|---|
| NIM/password salah di Secrets | Update secret `UNIMAL_NIM` atau `UNIMAL_PASSWORD` |
| Portal sedang down/maintenance | Bot akan retry otomatis tiap 5 menit, tidak perlu tindakan |
| Portal mengubah struktur form login | Buka issue di repo atau cek log Actions untuk detailnya |

Setelah update secret: buka **Actions → Run workflow** untuk restart bot.

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
