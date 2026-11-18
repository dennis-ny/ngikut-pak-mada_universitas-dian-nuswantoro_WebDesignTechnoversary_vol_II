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
    posterUrl: "/images/video-poster.jpg",
    duration: "02:05",
    narratorNote:
      "Tip: Klik bab (chapter) di samping kanan untuk melompat ke penjelasan fitur tertentu pada video.",
    chapters: [
      {
        time: "00:00",
        seconds: 0,
        title: "01. Intro: Pulau Gunung & Ekosistem Sehat",
        description:
          "Pengenalan pulau gunung hijau yang masih asri, udara bersih, satwa liar di dalam hutan, dan desa-desa di sekitarnya."
      },
      {
        time: "00:21",
        seconds: 21,
        title: "02. Demo Kebakaran Hutan & Kabut Asap",
        description:
          "Simulasi api menyala dan merembet ke petak tetangga, asap menebal, kualitas udara memburuk, hingga satwa kehilangan habitat."
      },
      {
        time: "00:56",
        seconds: 56,
        title: "03. Demo Hujan: Banjir & Tanah Longsor",
        description:
          "Saat hujan turun di lereng yang gundul dan hangus pasca kebakaran, tanah longsor terjadi dan luapan air merendam desa."
      },
      {
        time: "01:30",
        seconds: 90,
        title: "04. Tanam & Jaga Hutan (Reboisasi)",
        description:
          "Memulihkan lereng gundul dengan penanaman pohon kembali untuk menjaga tanah, satwa, dan keselamatan warga sekitar."
      },
      {
        time: "01:53",
        seconds: 113,
        title: "05. Closing: Menjaga Bumi untuk Masa Depan",
        description:
          "Ajakan menjaga, melindungi, dan merawat hutan demi kehidupan yang lebih baik bagi generasi mendatang."
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
