export interface TeamMemberCompact {
  name: string;
  role: string;
}

export interface AboutContent {
  hero: {
    eyebrow: string;
    title: string;
    subtitle: string;
  };
  team: {
    label: string;
    institution: string;
    members: TeamMemberCompact[];
  };
  feedback: {
    eyebrow: string;
    title: string;
    description: string;
    topics: string[];
  };
}

export const aboutContent: AboutContent = {
  hero: {
    eyebrow: "TENTANG PROYEK & PENGEMBANG",
    title: "MEMBANGUN EMPATI EKOLOGIS LEWAT INTERAKSI 3D",
    subtitle:
      "ASHEN lahir dari keresahan melihat bencana kebakaran hutan, kabut asap, banjir bandang, tanah longsor, dan kematian satwa liar yang terus berulang setiap tahun di Indonesia."
  },
  team: {
    label: "TIM PENGEMBANG",
    institution: "Teknik Informatika - Universitas Dian Nuswantoro",
    members: [
      { name: "Dennis Noor Yahya", role: "Lead Developer, Simulasi 3D & UI/UX" },
      { name: "Triana Miftakhul Janah", role: "Riset Konten, Narasi & Voice Over" },
      { name: "Moh. Rizal Aji Permana", role: "Quality Assurance & Pengujian" }
    ]
  },
  feedback: {
    eyebrow: "RUANG PARTISIPASI",
    title: "SARAN & MASUKAN UNTUK ASHEN",
    description:
      "Punya ide skenario baru untuk simulasi gunung 3D, koreksi data ekologi, atau masukan tampilan? Pilih topik dan tulis langsung di sini.",
    topics: ["Simulasi 3D", "Materi & Berita", "Tampilan Web", "Ide Fitur"]
  }
};
