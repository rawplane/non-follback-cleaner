# 🚀 Auto Unfollow Instagram (Non-Follback Cleaner) - Modernized Edition

Script automasi modern Python untuk mendeteksi dan unfollow akun Instagram yang **tidak follow back (non-follback)** menggunakan sesi profil **Brave Browser** berbasis **Playwright**, antarmuka terminal **Rich + Typer**, dan database lokal **SQLite**.

---

## 🌟 Fitur Utama & Peningkatan Modern

- **Playwright Persistent Context Engine**: Menggantikan Selenium webdriver. Lebih ringan, minim penggunaan RAM, dan anti-detection stealth tingkat tinggi.
- **Direct Web API & GraphQL Scraping**: Pengambilan 100% data Following & Followers secara instan via internal API tanpa manipulasi DOM yang rapuh.
- **Direct API Unfollow with Fallback**: Eksekusi unfollow langsung via endpoint API authenticated origin Instagram dengan fallback mulus ke UI interaction.
- **Modern Terminal UI (Rich & Typer)**: Dashboard terminal elegan, visual table modern, real-time progress bar, dan status countdown interaktif.
- **Dual Mode CLI**: Dapat dijalankan lewat interactive menu interaktif (`python3 main.py`) ataupun CLI subcommands (`python3 main.py scan`, `unfollow`, `whitelist`, `logs`).
- **SQLite Audit & History Tracking**: Menyimpan hasil scan, daftar whitelist, dan log setiap aksi eksekusi ke file database lokal `cleaner.db`.
- **Anti-Ban & Safety Delays**: Delay acak terdistribusi, pengelompokan batch otomatis, serta deteksi respons Action Block (*Try Again Later* / Rate Limit 429).

---

## 📁 Struktur Direktori

```
non-follback-cleaner/
├── config.py             # Konfigurasi browser, delay, dan batas eksekusi
├── storage.py            # Modul database SQLite (whitelist, history, action logs)
├── unfollower.py         # Playwright core engine & direct API client
├── main.py               # Antarmuka CLI Typer + Rich TUI Dashboard
├── test_cleaner.py       # Unit tests verifikasi parser, storage & logic
├── requirements.txt      # Dependensi modern (playwright, httpx, rich, typer)
├── cleaner.db            # Database SQLite lokal (dibuat otomatis)
└── README.md             # Dokumentasi proyek
```

---

## 🛠️ Kebutuhan Sistem

- **OS**: Linux Mint / Ubuntu / Debian-based
- **Python**: Python 3.9+
- **Browser**: Brave Browser (`/usr/bin/brave-browser`)

---

## 📦 Instalasi & Menjalankan

1. **Install Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Jalankan Menu Interaktif (TUI)**:
   ```bash
   python3 main.py
   ```

3. **Atau Gunakan Direct CLI Subcommand**:
   - **Scan Non-Follback**:
     ```bash
     python3 main.py scan
     ```
   - **Simulasi Unfollow (Dry-Run)**:
     ```bash
     python3 main.py unfollow --dry-run
     ```
   - **Unfollow Nyata (Real Mode)**:
     ```bash
     python3 main.py unfollow --real --batch-size 20
     ```
   - **Kelola Whitelist**:
     ```bash
     python3 main.py whitelist list
     python3 main.py whitelist add username_teman
     python3 main.py whitelist remove username_teman
     ```
   - **Cek Riwayat Log Aktivitas**:
     ```bash
     python3 main.py logs --limit 20
     ```
   - **Cek Konfigurasi**:
     ```bash
     python3 main.py config
     ```

---

## ⚙️ Pengaturan di `config.py`

| Parameter | Deskripsi | Default |
| :--- | :--- | :--- |
| `AUTOMATION_PROFILE_DIR` | Direktori sesi profil otomatisasi browser | `~/.config/auto-unfollow-ig-brave` |
| `HEADLESS_MODE` | Sembunyikan jendela browser saat berjalan | `False` |
| `MAX_UNFOLLOW_LIMIT` | Batas maksimum unfollow per batch | `25` |
| `MIN_DELAY_SECONDS` | Jeda minimum antar aksi unfollow | `2` detik |
| `MAX_DELAY_SECONDS` | Jeda maksimum antar aksi unfollow | `5` detik |
| `WHITELIST_FILE` | File fallback whitelist eksternal | `"whitelist.txt"` |
