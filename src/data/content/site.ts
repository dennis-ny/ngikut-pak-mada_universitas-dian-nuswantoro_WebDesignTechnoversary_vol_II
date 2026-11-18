export interface NavItem {
  label: string;
  href: string;
}

export interface SiteContent {
  brand: string;
  tagline: string;
  competitionBadge: string;
  liveAqiBadge: {
    location: string;
    value: string;
    status: string;
  };
  navItems: NavItem[];
  ctaSimulasi: {
    label: string;
    href: string;
  };
  footer: {
    statement: string;
    copyright: string;
    locationNote: string;
    institutionNote: string;
    quickLinksTitle: string;
    actionTitle: string;
    actionSubtitle: string;
  };
}

export const siteContent: SiteContent = {
  brand: "ASHEN",
  tagline: "Ketika Hutan Menjadi Abu, Bencana Baru Dimulai",
  competitionBadge: "EDUKASI & SIMULASI EKOLOGI INDONESIA",
  liveAqiBadge: {
    location: "KALIMANTAN & SUMATERA",
    value: "AQI 342",
    status: "BERBAHAYA"
  },
  navItems: [
    { label: "Beranda", href: "/" },
    { label: "Simulasi", href: "/simulasi" },
    { label: "Belajar", href: "/belajar" },
    { label: "Tentang", href: "/tentang" }
  ],
  ctaSimulasi: {
    label: "Simulasi 3D",
    href: "/simulasi"
  },
  footer: {
    statement:
      "Platform visualisasi interaktif rantai bencana ekologis di Indonesia yang menghubungkan krisis kebakaran hutan, pembalakan liar, banjir bandang, tanah longsor, dan terputusnya koridor satwa liar.",
    copyright: "© 2026 ASHEN Project — Technoversary Vol. II",
    locationNote: "Kategori: Isu Lingkungan Hidup",
    institutionNote: "UNIVERSITAS DIAN NUSWANTORO",
    quickLinksTitle: "NAVIGASI",
    actionTitle: "PULIHKAN HUTAN KITA",
    actionSubtitle: "Uji dampak pembakaran, penebangan, hujan, dan reboisasi pada model ekosistem gunung 3D."
  }
};
