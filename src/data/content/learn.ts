import newsSnapshotJson from "../generated/news.json";

const newsSnapshot = newsSnapshotJson as unknown as NewsSnapshot;

export type NewsCategory =
  | "Semua"
  | "Karhutla & Asap"
  | "Pembalakan Liar"
  | "Banjir & Longsor"
  | "Satwa Terdampak";

export interface VideoChapter {
  time: string;
  seconds: number;
  title: string;
  description: string;
}

export interface VideoShowcaseData {
  eyebrow: string;
  title: string;
  subtitle: string;
  videoUrl: string;
  posterUrl: string;
  duration: string;
  narratorNote: string;
  chapters: VideoChapter[];
}

export type NewsTopic = "karhutla" | "pembalakan" | "banjir" | "satwa";

export interface NewsItem {
  id: string;
  title: string;
  topic: NewsTopic;
  category: Exclude<NewsCategory, "Semua">;
  topicSecondary: NewsTopic | null;
  secondaryCategory: Exclude<NewsCategory, "Semua"> | null;
  ecoLink?: number;
  source: string;
  publishedAt: string;
  location: string | null;
  summary: string | null;
  image?: string | null;
  url: string;
}

export interface NewsSnapshot {
  schemaVersion: number;
  generatedAt: string;
  windowDays: Record<NewsTopic, number>;
  counts: Record<Exclude<NewsCategory, "Semua">, number>;
  items: NewsItem[];
}

export interface LearnContent {
  videoShowcase: VideoShowcaseData;
  categories: NewsCategory[];
  newsHeading: {
    eyebrow: string;
    title: string;
    description: string;
    attribution: string;
  };
  newsMeta: {
    generatedAt: string;
    windowDays: NewsSnapshot["windowDays"];
  };
  newsList: NewsItem[];
}

export const learnContent: LearnContent = {
  videoShowcase: {
    eyebrow: "PANDUAN INTERAKTIF & VOICE OVER",
    title: "MENGENAL MEKANISME SIMULASI 3D ASHEN",
    subtitle:
      "Tonton rekaman demonstrasi singkat (Screen Record & Voice Over) tentang bagaimana model gunung 3D kami memvisualisasikan hubungan antara kebakaran hutan, kabut asap, penebangan liar, banjir, tanah longsor, dan perilaku satwa liar.",
    videoUrl: "/videos/ashen-3d-intro.mp4",
    posterUrl: "/images/hero-fire.png",
    duration: "03:15",
    narratorNote:
      "Tip: Klik bab (chapter) di samping kanan untuk melompat ke penjelasan fitur tertentu pada video.",
    chapters: [
      {
        time: "00:00",
        seconds: 0,
        title: "01. Pengenalan Topografi Gunung & 8 Klaster Desa",
        description:
          "Memahami struktur 96 zona lereng gunung, 80 zona habitat satwa, dan 8 klaster pemukiman di hilir beserta indikator rumah tertinggi."
      },
      {
        time: "00:45",
        seconds: 45,
        title: "02. Simulasi Api, Rembetan Karhutla & Kualitas Udara",
        description:
          "Bagaimana titik api merembet ke zona tetangga, menghasilkan partikel asap pekat, mengubah warna langit, dan memperburuk kualitas udara."
      },
      {
        time: "01:30",
        seconds: 90,
        title: "03. Pembalakan Liar & AI Koridor Satwa (Monyet & Burung)",
        description:
          "Melihat bagaimana 16 monyet dan 10 burung bereaksi saat pohon ditebang: mengungsi, menyeberangi lahan gundul, atau mati kelaparan saat terisolasi."
      },
      {
        time: "02:20",
        seconds: 140,
        title: "04. Musim Hujan: Deformasi Tanah Longsor, Banjir & Reboisasi",
        description:
          "Saat hujan turun di lereng gundul/hangus, tanah mengalami erosi dan longsor, memicu banjir desa—serta bagaimana alat Tanam (Reboisasi) memulihkannya."
      }
    ]
  },
  categories: [
    "Semua",
    "Karhutla & Asap",
    "Pembalakan Liar",
    "Banjir & Longsor",
    "Satwa Terdampak"
  ],
  newsHeading: {
    eyebrow: "ARSIP BERITA & FAKTA LAPANGAN",
    title: "KASUS NYATA DI BALIK SIMULASI KAMI",
    description:
      "Setiap mekanisme di dalam simulasi ASHEN berangkat dari kejadian nyata di berbagai penjuru Indonesia. Berita di bawah dikumpulkan otomatis dari media nasional, lalu dikelompokkan berdasarkan dampak ekologisnya.",
    attribution:
      "Berita dihimpun otomatis melalui RSS publik Antara, CNN Indonesia, Detik, Tempo, dan Mongabay Indonesia. Hak cipta sepenuhnya milik masing-masing media."
  },
  newsMeta: {
    generatedAt: newsSnapshot.generatedAt,
    windowDays: newsSnapshot.windowDays
  },
  newsList: newsSnapshot.items
};
