export interface HeroCrisisData {
  eyebrow: string;
  headlineTop: string;
  headlineMetric: string;
  description: string;
  image: string;
  primaryCta: { label: string; href: string };
  secondaryCta: { label: string; href: string };
}

export interface NatureStorySlide {
  lines: [string, string, string];
  cardText: string;
}

export interface ComparisonSide {
  label: string;
  metricBig: string;
  image: string;
}

export interface DominoCard {
  number: string;
  badge: string;
  title: string;
  metric: string;
  description: string;
  diagramType: "fire" | "logging" | "flood" | "wildlife";
  image?: string;
}

export interface InspiredNatureData {
  eyebrow: string;
  headlineLines: [string, string];
  body: string;
  image: string;
  cta: { label: string; href: string };
  secondaryCta: { label: string; href: string };
}

export interface HomeContent {
  hero: HeroCrisisData;
  natureStory: {
    bgImage: string;
    slides: [NatureStorySlide, NatureStorySlide, NatureStorySlide, NatureStorySlide];
  };
  beforeAfter: {
    headline: string;
    burned: ComparisonSide;
    healthy: ComparisonSide;
  };
  domino: {
    titleTop: string;
    titleBottom: string;
    subtitle: string;
    cards: DominoCard[];
  };
  inspired: InspiredNatureData;
}

export const homeContent: HomeContent = {
  hero: {
    eyebrow: "ALAM TERANCAM",
    headlineTop: "INDONESIA",
    headlineMetric: "TERBAKAR",
    description:
      "Memperkenalkan ASHEN, simulasi ekosistem hutan 3D interaktif yang memvisualisasikan rantai bencana kebakaran hutan, pembalakan liar, banjir bandang, tanah longsor, hingga krisis ruang hidup satwa.",
    image: "/images/hero-fire.png",
    primaryCta: { label: "Simulasi 3D", href: "/simulasi" },
    secondaryCta: { label: "Belajar", href: "/belajar" }
  },
  natureStory: {
    bgImage: "/images/nature-canopy.jpg",
    slides: [
      {
        lines: [
          "Alam adalah bagian kita,",
          "penjaga napas dan",
          "sumber kehidupan"
        ],
        cardText:
          "Dari udara bersih hingga akar penahan air, hutan menjaga hidup kita."
      },
      {
        lines: [
          "Namun saat ini,",
          "alam kita lukai dengan",
          "api dan gergaji"
        ],
        cardText:
          "Kebakaran dan pembalakan liar menyisakan abu serta asap pekat."
      },
      {
        lines: [
          "Saat hujan datang,",
          "lereng gundul runtuh",
          "memutus ruang satwa"
        ],
        cardText:
          "Tanpa akar pohon, longsor menerjang desa dan satwa terisolasi."
      },
      {
        lines: [
          "Menanam kembali",
          "adalah satu jalan",
          "menjaga masa depan"
        ],
        cardText:
          "Koridor hijau memulihkan daya serap tanah dan rumah bagi satwa."
      }
    ]
  },
  beforeAfter: {
    headline: "GESER UNTUK MELIHAT DAMPAK NYATA",
    burned: {
      label: "Hutan terbakar",
      metricBig: "HANGUS",
      image: "/images/forest-burned.jpg"
    },
    healthy: {
      label: "Hutan hujan sehat",
      metricBig: "RIMBUN",
      image: "/images/forest-healthy.jpg"
    }
  },
  domino: {
    titleTop: "RANTAI",
    titleBottom: "BENCANA",
    subtitle:
      "Empat fase reaksi berantai ekologis yang terjadi di lereng gunung dan disimulasikan secara real-time di ASHEN.",
    cards: [
      {
        number: "01",
        badge: "Karhutla & Asap",
        title: "API & KABUT ASAP",
        metric: "UDARA BERBAHAYA",
        description:
          "Titik api merembet ke petak hutan tetangga, memancarkan asap pekat yang menurunkan kualitas udara ke level berbahaya.",
        diagramType: "fire",
        image: "/images/domino-placeholder.jpg"
      },
      {
        number: "02",
        badge: "Deforestasi",
        title: "PEMBALAKAN LIAR",
        metric: "TANAH GUNDUL",
        description:
          "Penebangan pohon merobohkan tajuk pelindung lereng gunung, menimpa satwa, dan menyisakan tanah gundul.",
        diagramType: "logging",
        image: "/images/domino-placeholder.jpg"
      },
      {
        number: "03",
        badge: "Hidrometeorologi",
        title: "LONGSOR & BANJIR DESA",
        metric: "DESA TERENDAM",
        description:
          "Saat hujan mengguyur lereng gundul, tanah runtuh menjadi longsor dan luapan air merendam desa hingga rumah tertinggi.",
        diagramType: "flood",
        image: "/images/domino-placeholder.jpg"
      },
      {
        number: "04",
        badge: "Biodiversitas",
        title: "ISOLASI KORIDOR SATWA",
        metric: "SATWA TERANCAM",
        description:
          "Monyet dan burung yang terjebak di pulau hutan terisolasi tanpa koridor hijau perlahan mati kelaparan.",
        diagramType: "wildlife",
        image: "/images/domino-placeholder.jpg"
      }
    ]
  },
  inspired: {
    eyebrow: "PEMULIHAN EKOSISTEM",
    headlineLines: ["PULIHKAN", "ALAM KITA"],
    body: "Hutan butuh puluhan tahun untuk pulih dari apa yang dihancurkan api dalam hitungan menit. Lewat reboisasi dan penyambungan koridor hijau, kita mengembalikan daya serap bumi, melindungi desa dari banjir-longsor, serta menyelamatkan satwa dari kepunahan.",
    image: "/images/inspired-sunbeams.jpg",
    cta: { label: "Coba Simulasi 3D", href: "/simulasi" },
    secondaryCta: { label: "Tonton Video & Berita", href: "/belajar" }
  }
};
