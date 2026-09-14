# ✏️ Papan Tulis Udara — Air Writing

Aplikasi menggambar di udara menggunakan gerakan tangan, langsung di browser.  
Tidak perlu instalasi Python, conda, atau library apapun.

---

## 🚀 Cara Menjalankan

### Langkah 1 — Download
Simpan file `index.html` ke sebuah folder di komputer kamu.

```
📁 airwrite/
   └── index.html
```

> Kamu bisa menambahkan file gambar PNG/JPG ke dalam folder yang sama  
> untuk dijadikan background papan tulis (opsional).

---

### Langkah 2 — Jalankan Local Server

> ⚠️ File ini **tidak bisa** langsung dibuka dengan double-click.  
> Browser memblokir akses kamera dari `file://`. Harus lewat local server.

Pilih salah satu cara di bawah:

---

#### 🐍 Cara A — Python (direkomendasikan, sudah ada di Mac/Linux)

```bash
# Masuk ke folder tempat index.html disimpan
cd ~/Downloads/airwrite

# Jalankan server
python3 -m http.server 8000
```

Buka browser → **`http://localhost:8000`**

---

#### 🟢 Cara B — Node.js

```bash
cd ~/Downloads/airwrite
npx serve .
```

Buka link yang muncul di terminal (biasanya `http://localhost:3000`)

---

#### 🟦 Cara C — VS Code Live Server

1. Install extension **Live Server** di VS Code
2. Buka folder project di VS Code
3. Klik kanan `index.html` → **Open with Live Server**
4. Browser terbuka otomatis

---

### Langkah 3 — Izinkan Kamera

Saat pertama kali dibuka, browser akan meminta izin kamera.  
Klik **Izinkan / Allow**.

---

### Langkah 4 — Tunggu Loading

Model deteksi tangan (MediaPipe) akan diunduh otomatis dari internet.  
Proses ini memakan waktu **5–15 detik** tergantung kecepatan koneksi.  
Setelah loading selesai, tangan langsung bisa digunakan.

---

## 📋 Panduan Gesture

### ✋ Tangan Kanan — Menggambar

| Gesture | Aksi | Ketebalan |
|---|---|---|
| ☝️ 1 jari (telunjuk) | Gambar | 4px |
| ✌️ 2 jari (telunjuk + tengah) | Gambar | 8px |
| 🤟 3 jari | Gambar | 16px |
| 4️⃣ 4 jari | Gambar | 24px |
| 🖐️ 5 jari | Gambar | 30px |
| 🤏 Pinch (jempol + telunjuk rapat) | **Pilih Warna** | — |

**Cara Pilih Warna (Pinch):**
1. Rapatkan ujung jempol dan ujung telunjuk tangan kanan (jarak < 40px)
2. Rainbow bar warna muncul di atas layar
3. Geser tangan ke **kiri/kanan** untuk mengubah warna (Hue 0–360°)
4. Lepas pinch → warna terkunci, siap menggambar

---

### 🤚 Tangan Kiri — Menghapus

| Gesture | Aksi | Ukuran Hapus |
|---|---|---|
| ☝️ 1 jari | Hapus | 8px |
| ✌️ 2 jari | Hapus | 16px |
| 🤟 3 jari | Hapus | 32px |
| 4️⃣ 4 jari | Hapus | 50px |
| 🖐️ 5 jari + **bergerak** | Hapus | 72px |
| 🖐️ 5 jari + **diam ±1.2 detik** | **CLEAR PAGE** | Seluruh canvas |

**Cara Clear Page:**
1. Buka semua 5 jari tangan kiri
2. Tahan **diam di tempat** (jangan digerakkan)
3. Cincin progres biru akan muncul dan mengisi
4. Setelah penuh (~1.2 detik) → seluruh canvas dibersihkan

> Selama 5 jari masih **bergerak**, dianggap menghapus area biasa (72px).  
> Clear Page hanya terpicu saat benar-benar **diam**.

---

### 🙌 Gesture Gabungan (Kedua Tangan)

| Gesture | Aksi |
|---|---|
| 🖐️ 5 jari kanan + 🖐️ 5 jari kiri bersamaan | **Tangkap Layar (Screenshot)** |

Gambar akan otomatis tersimpan sebagai file PNG di folder Downloads.  
Nama file: `airchalk_000.png`, `airchalk_001.png`, dst.

---

## ⌨️ Tombol Keyboard

| Tombol | Aksi |
|---|---|
| `C` | Bersihkan seluruh canvas |
| `S` | Simpan / Screenshot |
| `B` | Ganti background (cycle) |
| `Q` | — *(tutup tab browser)* |

---

## 🖼️ Mengganti Background

**Lewat tombol di aplikasi:**
1. Klik tombol **📂 Unggah Background** → pilih file PNG/JPG
2. Klik tombol **🖼️ Ganti Background** untuk berganti-ganti

**Lewat keyboard:**
- Tekan `B` untuk cycle background

**Lewat folder (cara manual):**
> Fitur ini hanya tersedia di versi Python (`air_writing_chalk.py`).  
> Pada versi browser (`index.html`), background harus diunggah lewat tombol.

---

## 💡 Tips untuk Hasil Terbaik

| Tips | Penjelasan |
|---|---|
| 💡 Pencahayaan | Pastikan tangan tersinari dengan baik dari depan |
| 🎨 Latar belakang | Gunakan dinding polos agar MediaPipe mudah mendeteksi tangan |
| 📏 Jarak | Posisikan tangan sekitar 40–70 cm dari kamera |
| ✋ Satu tangan dulu | Mulai dengan tangan kanan untuk menggambar |
| 🤏 Pinch warna | Pastikan ujung jempol dan telunjuk benar-benar menyentuh / sangat dekat |
| 🖐️ Clear page | Tahan tangan benar-benar **diam**, jangan goyang |

---

## 🌐 Persyaratan Browser

| Browser | Status |
|---|---|
| Google Chrome 90+ | ✅ Direkomendasikan |
| Microsoft Edge 90+ | ✅ Didukung |
| Firefox | ⚠️ Mungkin lebih lambat (WebGL terbatas) |
| Safari | ⚠️ Perlu uji coba |

> Halaman **wajib** dibuka lewat `http://localhost` atau HTTPS.  
> Membuka langsung lewat `file://` akan gagal karena browser memblokir akses kamera.

---

## 📁 Struktur File

```
📁 airwrite/
   ├── index.html          ← Versi browser (buka lewat localhost)
   ├── air_writing_chalk.py ← Versi Python (jalankan di terminal)
   └── background.png      ← Background custom (opsional)
```

---

## ❓ Troubleshooting

**Kamera tidak muncul / ditolak**
- Pastikan membuka lewat `http://localhost`, bukan `file://`
- Cek Settings browser → Privacy → Camera → izinkan untuk `localhost`
- Pastikan tidak ada aplikasi lain yang sedang menggunakan kamera

**Loading lama / gagal**
- Butuh koneksi internet untuk mengunduh model MediaPipe saat pertama kali
- Coba refresh halaman
- Pastikan browser mendukung WebAssembly

**Tangan tidak terdeteksi**
- Perbaiki pencahayaan — hindari cahaya dari belakang tangan
- Gunakan latar polos (dinding putih/abu-abu)
- Pastikan seluruh tangan terlihat dalam frame kamera

**FPS rendah / lag**
- Tutup tab browser lain yang berat
- Gunakan Chrome untuk performa terbaik
- GPU delegate diaktifkan otomatis jika browser mendukung

---

*Dibuat dengan MediaPipe Tasks Vision (JavaScript/WASM) + HTML Canvas API*
