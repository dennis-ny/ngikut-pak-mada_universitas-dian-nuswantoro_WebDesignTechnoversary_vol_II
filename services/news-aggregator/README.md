# ashen-news

Script Python yang mengambil berita lingkungan dari RSS beberapa media, memilahnya ke 4 topik
(Karhutla & Asap, Pembalakan Liar, Banjir & Longsor, Satwa Terdampak), lalu menulis
`src/data/generated/news.json` untuk halaman `/belajar`.

Yang disimpan hanya judul, tautan, sumber, tanggal, provinsi, dan cuplikan pendek. Isi artikel tidak diambil.

## Sumber

Antara, CNN Indonesia, Detik, Tempo, dan Mongabay Indonesia (daftar feed ada di `config/sources.yaml`).
Kompas tidak dipakai karena tidak punya RSS yang bisa diverifikasi.

## Pakai

Butuh [uv](https://docs.astral.sh/uv/). Dari folder ini:

```bash
export ASHEN_NEWS_CONTACT="email-atau-url-repo"   # wajib, masuk ke header User-Agent
uv sync

uv run ashen-news fetch --dry-run   # coba fetch tanpa menyimpan
uv run ashen-news fetch             # fetch dan simpan ke data/news.db
uv run ashen-news export            # tulis news.json bila ada perubahan
uv run ashen-news health            # status tiap feed
uv run ashen-news stats             # ringkasan isi DB
uv run pytest -q
```

## Klasifikasi

Kata kunci dan aturan ada di `config/topics.yaml`. Berita yang cuma lolos lewat kata ambigu
(mis. "hotspot wifi", "banjir diskon") dibuang lewat pola `exclude`. Berita yang menyebut
hubungan ekologis (hutan, hulu, gambut, dst.) dapat skor `eco_link` lebih tinggi dan tampil lebih awal.
Saat export, tiap topik dibatasi 2 berita per provinsi supaya satu kejadian tidak mendominasi.

`config/overrides.yaml` bisa dipakai untuk menaikkan (`pin_urls`) atau menyembunyikan (`block_urls`) artikel tertentu.
