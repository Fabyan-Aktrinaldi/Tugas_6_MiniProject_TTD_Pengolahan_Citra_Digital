"""
Mini Project Pengolahan Citra Digital - Pertemuan 6
Deteksi keberadaan tanda tangan pejabat (Rektor) pada citra ijazah.

Alur: rotate -> crop -> grayscale -> thresholding (global & Otsu)
      -> morphology (opening, closing) -> hitung fitur -> aturan
      SIGNATURE PRESENT / SIGNATURE ABSENT.
"""
import os
import glob
import csv

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")  # simpan gambar tanpa membuka jendela
import matplotlib.pyplot as plt

# ---------------------------------------------------------------
# KONFIGURASI
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Area (x, y, lebar, tinggi) pada citra SETELAH diputar ke posisi tegak.
# Area tanda tangan Rektor (sampel PRESENT)
ROI_TTD = (510, 1810, 870, 220)

# Area tanpa tanda tangan (sampel ABSENT), ukuran dibuat berbeda-beda
ROI_ABSENT = {
    "kosong_kiri":   (60, 1330, 700, 200),    # latar kosong
    "kosong_tengah": (60, 1580, 650, 170),    # latar kosong
    "foto_kosong":   (1500, 1500, 870, 150),  # latar di atas foto
    "teks_nomor":    (60, 2200, 870, 220),    # hanya teks cetak (kasus sulit)
    "teks_prof":     (0, 2040, 870, 220),     # hanya teks cetak (kasus sulit)
}

# Parameter pipeline
GLOBAL_T = 127           # nilai threshold global (tetap)
BLUR_K = (5, 5)          # Gaussian blur untuk mengurangi noise
KERNEL_OPEN = np.ones((3, 3), np.uint8)   # opening: buang bintik noise
KERNEL_CLOSE = np.ones((9, 9), np.uint8)  # closing: sambung goresan putus
MIN_KONTRAS = 25         # piksel harus minimal segini lebih gelap dari latar

# Aturan keputusan
MIN_RASIO = 0.02         # foreground minimal 2% dari area crop
MIN_LEBAR_KOMPONEN = 0.40  # komponen terhubung terbesar minimal 40% lebar crop


# ---------------------------------------------------------------
# FUNGSI
# ---------------------------------------------------------------
def muat_citra(path):
    """Baca citra lalu putar 90 derajat agar tegak."""
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)


def crop(img, roi):
    x, y, w, h = roi
    return img[y:y + h, x:x + w]


def threshold_global(gray):
    blur = cv2.GaussianBlur(gray, BLUR_K, 0)
    _, m = cv2.threshold(blur, GLOBAL_T, 255, cv2.THRESH_BINARY_INV)
    return m


def threshold_otsu(gray):
    blur = cv2.GaussianBlur(gray, BLUR_K, 0)
    _, m = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Otsu selalu membelah histogram walau tidak ada tinta, jadi tambahkan
    # penjaga: piksel foreground harus nyata lebih gelap dari latar.
    latar = np.median(blur)
    m[(latar - blur) < MIN_KONTRAS] = 0
    return m


def morfologi(mask):
    """Opening (buang noise kecil) lalu closing (sambung goresan)."""
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, KERNEL_OPEN)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, KERNEL_CLOSE)
    return opened, closed


def hitung_fitur(mask):
    """Jumlah piksel foreground, rasio, dan lebar komponen terbesar."""
    jumlah = int(cv2.countNonZero(mask))
    rasio = jumlah / mask.size
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    lebar_terbesar = 0.0
    if n > 1:
        idx = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        lebar_terbesar = stats[idx, cv2.CC_STAT_WIDTH] / mask.shape[1]
    return jumlah, rasio, lebar_terbesar


def keputusan(rasio, lebar_komponen):
    """Aturan sederhana: cukup banyak foreground DAN ada goresan panjang."""
    if rasio >= MIN_RASIO and lebar_komponen >= MIN_LEBAR_KOMPONEN:
        return "SIGNATURE PRESENT"
    return "SIGNATURE ABSENT"


def proses(roi_img):
    """Jalankan seluruh pipeline untuk satu crop. Kembalikan semua tahap."""
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    hasil = {"gray": gray}
    for nama, fungsi in (("global", threshold_global), ("otsu", threshold_otsu)):
        mask = fungsi(gray)
        opened, closed = morfologi(mask)
        jumlah, rasio, lebar = hitung_fitur(closed)
        hasil[nama] = {
            "mask": mask, "opened": opened, "closed": closed,
            "jumlah": jumlah, "rasio": rasio, "lebar": lebar,
            "label": keputusan(rasio, lebar),
        }
    return hasil


def simpan_figure(roi_img, hasil, judul, path):
    """Simpan gambar perbandingan semua tahap (global vs Otsu)."""
    fig, ax = plt.subplots(2, 4, figsize=(16, 5))
    for baris, nama in enumerate(("global", "otsu")):
        h = hasil[nama]
        ax[baris, 0].imshow(cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB))
        ax[baris, 0].set_title("Crop asli")
        ax[baris, 1].imshow(h["mask"], cmap="gray")
        ax[baris, 1].set_title(f"Threshold {nama}")
        ax[baris, 2].imshow(h["opened"], cmap="gray")
        ax[baris, 2].set_title("Opening")
        ax[baris, 3].imshow(h["closed"], cmap="gray")
        ax[baris, 3].set_title(
            f"Closing | {h['jumlah']} px ({h['rasio']*100:.2f}%)\n{h['label']}")
        for a in ax[baris]:
            a.axis("off")
    fig.suptitle(judul)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


# ---------------------------------------------------------------
# PROGRAM UTAMA
# ---------------------------------------------------------------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.jpg")) +
                   glob.glob(os.path.join(DATA_DIR, "*.jpeg")) +
                   glob.glob(os.path.join(DATA_DIR, "*.png")))
    if not files:
        print(f"Tidak ada citra di folder: {DATA_DIR}")
        return

    baris_csv = []
    benar = {"global": 0, "otsu": 0}
    total = 0
    pos_gray_stat = []

    print(f"{'File':<34}{'Sampel':<15}{'Asli':<9}"
          f"{'Global':<20}{'Otsu':<20}")
    print("-" * 98)

    for path in files:
        nama_file = os.path.splitext(os.path.basename(path))[0]
        img = muat_citra(path)

        # daftar sampel: 1 positif + beberapa negatif
        sampel = [("ttd_rektor", ROI_TTD, "SIGNATURE PRESENT")]
        sampel += [(k, v, "SIGNATURE ABSENT") for k, v in ROI_ABSENT.items()]

        for nama_sampel, roi, asli in sampel:
            roi_img = crop(img, roi)
            hasil = proses(roi_img)
            total += 1

            for metode in ("global", "otsu"):
                if hasil[metode]["label"] == asli:
                    benar[metode] += 1

            if nama_sampel == "ttd_rektor":
                g = hasil["gray"]
                pos_gray_stat.append((nama_file, g.min(), g.max(), g.mean()))

            # simpan gambar bukti: tanda tangan + satu kasus sulit (teks)
            if nama_sampel in ("ttd_rektor", "teks_nomor"):
                simpan_figure(roi_img, hasil, f"{nama_file} | {nama_sampel}",
                              os.path.join(OUTPUT_DIR,
                                           f"{nama_file}_{nama_sampel}.png"))

            g_, o_ = hasil["global"], hasil["otsu"]
            print(f"{nama_file:<34}{nama_sampel:<15}{asli[10:]:<9}"
                  f"{g_['label'][10:]:<8}{g_['rasio']*100:>6.2f}%     "
                  f"{o_['label'][10:]:<8}{o_['rasio']*100:>6.2f}%")

            baris_csv.append([
                nama_file, nama_sampel, asli,
                g_["jumlah"], f"{g_['rasio']:.4f}", f"{g_['lebar']:.2f}", g_["label"],
                o_["jumlah"], f"{o_['rasio']:.4f}", f"{o_['lebar']:.2f}", o_["label"],
            ])

    # simpan tabel hasil
    with open(os.path.join(OUTPUT_DIR, "hasil.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "sampel", "label_asli",
                    "global_px", "global_rasio", "global_lebar", "global_hasil",
                    "otsu_px", "otsu_rasio", "otsu_lebar", "otsu_hasil"])
        w.writerows(baris_csv)

    print("\nStatistik grayscale area tanda tangan (min / max / mean):")
    for nama, mn, mx, me in pos_gray_stat:
        print(f"  {nama:<34}{mn:>4} / {mx:>3} / {me:>6.1f}")

    print(f"\nAkurasi dari {total} sampel uji:")
    for metode in ("global", "otsu"):
        print(f"  Threshold {metode:<7}: {benar[metode]}/{total} "
              f"= {benar[metode]/total*100:.1f}%")
    print(f"\nHasil tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()