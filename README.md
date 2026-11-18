# ASHEN

**ASHEN** adalah platform visualisasi interaktif berbasis web yang menggambarkan rantai bencana ekologis di Indonesia—mulai dari kebakaran hutan, kabut asap, pembalakan liar, tanah longsor, banjir, hingga dampaknya terhadap satwa liar dan pemukiman warga.

## Halaman Utama

- **Beranda (`/`)** — Narasi visual krisis hutan, perbandingan kondisi hutan terbakar vs hutan sehat, alur rantai bencana, dan ajakan pemulihan ekosistem.
- **Simulasi 3D (`/simulasi`)** — Model gunung 3D interaktif dengan alat **Api**, **Tebang**, **Tanam**, **Hujan**, dan **Reset** untuk mengamati dampak langsung terhadap kualitas udara, tutupan hutan, desa terdampak banjir, dan populasi satwa.
- **Belajar (`/belajar`)** — Video demonstrasi simulasi 3D beserta bab timestamp dan arsip berita lingkungan Indonesia yang dihimpun otomatis dari RSS media nasional.
- **Tentang (`/tentang`)** — Latar belakang proyek dan form saran & masukan.

## Cara Menjalankan

### Menggunakan Docker (Rekomendasi)

Pastikan Docker dan Docker Compose sudah terpasang, lalu jalankan:

```bash
docker compose up --build
```

Setelah container berjalan, buka browser dan akses:

```text
http://localhost:4321
```

Untuk menghentikan container:

```bash
docker compose down
```

### Build Production (Docker)

Jika ingin menjalankan versi production di balik reverse proxy Traefik (menggunakan network eksternal `proxy`):

```bash
docker compose -f compose.prod.yaml up -d --build
```

### Tanpa Docker (Node.js Lokal)

Membutuhkan Node.js v22+:

```bash
npm install
npm run dev
```
