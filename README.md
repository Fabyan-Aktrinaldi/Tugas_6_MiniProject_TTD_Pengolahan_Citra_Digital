# Mini Project: Deteksi Tanda Tangan pada Ijazah

Tugas Pertemuan 6 mata kuliah Pengolahan Citra Digital.
Program ini mendeteksi apakah area tanda tangan pejabat (Rektor) pada citra ijazah
**ada** (`SIGNATURE PRESENT`) atau **tidak ada** (`SIGNATURE ABSENT`)
menggunakan thresholding, operasi morfologi, dan aturan sederhana berbasis fitur area.

## Alur Program

1. Citra diputar 90 derajat agar tegak (file asli tersimpan miring).
2. Area tanda tangan di-crop.
3. Konversi ke grayscale.
4. Thresholding dengan dua metode: **global threshold** (T = 127) dan **Otsu**.
5. Operasi morfologi: **opening** (buang bintik noise) lalu **closing** (sambung goresan yang putus).
6. Hitung karakteristik area: jumlah piksel foreground, rasio foreground, dan lebar komponen terhubung terbesar.
7. Aturan keputusan, lalu hasil dibandingkan antara kedua metode.

## Aturan SIGNATURE PRESENT / ABSENT

Sebuah area dinyatakan `SIGNATURE PRESENT` jika **kedua** syarat ini terpenuhi:

- rasio foreground minimal **2%** dari luas crop, dan
- komponen terhubung terbesar selebar minimal **40%** dari lebar crop.

Syarat kedua dipakai karena rasio saja tidak cukup. Teks cetak (misalnya "Nomor ijazah ...")
punya rasio foreground yang mirip bahkan lebih besar dari tanda tangan, tetapi
terdiri dari banyak huruf kecil yang terpisah. Tanda tangan berupa goresan panjang yang menyambung.

Khusus Otsu, ada penjaga tambahan: piksel foreground harus minimal 25 tingkat abu lebih gelap
dari median latar. Tanpa penjaga ini, Otsu tetap membelah histogram pada area kosong
dan menganggap pola latar sebagai foreground.

## Struktur Folder

```
miniproject_ttd/
├── data/             # taruh citra ijazah (.jpg/.png) di sini
├── output/           # dibuat otomatis: gambar tiap tahap + hasil.csv
├── main.py
├── requirements.txt
└── README.md
```

## Cara Menjalankan

1. Pastikan Python 3.9+ sudah terpasang.
2. Install library:
   ```
   pip install -r requirements.txt
   ```
3. Letakkan citra ijazah di folder `data/`.
4. Jalankan dari dalam folder `miniproject_ttd`:
   ```
   python main.py
   ```
5. Hasil muncul di terminal (tabel per sampel dan akurasi), sedangkan gambar tiap tahap
   dan `hasil.csv` tersimpan di folder `output/`.

## Data Uji

Ada 9 citra ijazah dengan degradasi berbeda (kualitas tinggi, kontras rendah, blur, noise tinggi,
resolusi rendah, pudar, pergeseran warna, artefak JPEG, dan gabungan).
Dari tiap citra diambil 6 sampel:

- 1 sampel **PRESENT**: area tanda tangan Rektor.
- 5 sampel **ABSENT**: dua area latar kosong, satu area latar di atas foto, dan dua area yang hanya berisi teks cetak (kasus sulit).

Total 54 sampel uji.

## Hasil

| Metode | Benar | Akurasi |
|---|---|---|
| Global threshold (T = 127) | 52 / 54 | 96,3% |
| Otsu | 54 / 54 | 100% |

Global threshold salah pada dua citra:

- `02_LowContrast`: tinta tidak cukup gelap sehingga hampir semua goresan jatuh di atas T = 127 dan rasio foreground hanya sekitar 0,27%.
- `03_Blurred`: goresan yang kabur menjadi pudar dan terputus, jadi komponen terbesarnya tidak cukup panjang.

Otsu benar di semua kasus karena nilai ambangnya menyesuaikan histogram tiap crop.

## Analisis

**Mengapa thresholding diperlukan sebelum analisis keberadaan tanda tangan?**
Citra grayscale berisi banyak tingkat keabuan (latar kertas, pola latar, tinta, noise), sehingga
sulit mengukur "apakah ada tinta" secara langsung. Thresholding memisahkan objek (tinta tanda tangan)
dari latar menjadi citra biner. Dari citra biner ini fitur seperti jumlah piksel foreground, rasio, dan
ukuran komponen terhubung bisa dihitung dengan jelas, lalu dipakai dalam aturan keputusan.

**Apa masalahnya jika threshold terlalu tinggi atau terlalu rendah?**

- **Terlalu tinggi**: piksel latar yang agak gelap (pola latar, bayangan, noise) ikut menjadi foreground.
  Rasio foreground membengkak, area kosong bisa salah dibaca `PRESENT` (false positive).
- **Terlalu rendah**: goresan yang tipis atau pudar tidak lolos threshold dan hilang atau terputus.
  Tanda tangan yang sebenarnya ada bisa salah dibaca `ABSENT` (false negative).
  Ini terlihat pada citra `02_LowContrast` dan `03_Blurred` untuk global threshold tetap.

Karena itu threshold yang adaptif terhadap histogram (Otsu) lebih stabil dibanding nilai tetap
ketika kondisi pencahayaan dan kualitas citra berubah-ubah.

## Catatan

- Koordinat crop ditentukan manual dengan `cv2.selectROI` pada citra yang sudah diputar (ukuran 3506 x 2481 piksel).
  Jika memakai citra dengan ukuran atau tata letak berbeda, sesuaikan `ROI_TTD` dan `ROI_ABSENT` di `main.py`.
- Aturan dan parameter dikalibrasi dari 9 citra uji ini, jadi belum tentu berlaku untuk jenis dokumen lain.