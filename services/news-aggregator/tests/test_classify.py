import pytest

from ashen_news.classify import Classifier, LocationMatcher
from ashen_news.config import load_config


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def clf(cfg):
    return Classifier(cfg)


@pytest.mark.parametrize(
    "title,snippet,expected",
    [
        ("Kabut asap karhutla selimuti Pekanbaru, ISPU tembus level berbahaya", None, "karhutla"),
        ("Kebakaran hutan dan lahan meluas di Kalimantan Tengah", None, "karhutla"),
        ("Polisi tangkap pelaku illegal logging di hutan lindung", None, "pembalakan"),
        ("Banjir bandang terjang tiga desa, BPBD data warga terdampak", None, "banjir"),
        ("Tanah longsor tutup akses jalan lintas Sumbar", None, "banjir"),
        ("Harimau sumatera masuk permukiman, warga resah", None, "satwa"),
        ("Bagaimana Nasib Orangutan Kalimantan yang Terkepung Karhutla?", None, "satwa"),
        ("Sedih, Masa Depan Kuskus Papua Terancam Akibat Kepungan Deforestasi", None, "satwa"),
    ],
)
def test_topic_hits(clf, title, snippet, expected):
    assert clf.classify(title, snippet).primary == expected


@pytest.mark.parametrize(
    "title,snippet",
    [
        ("Banjir diskon akhir tahun, belanja hemat di marketplace", None),
        ("Capres dapat banjir dukungan dari relawan", None),
        ("Asap rokok jadi pemicu penyakit paru", None),
        ("Wifi hotspot gratis di terminal", None),
        ("Gajah Mada dan sejarah Majapahit", None),
        ("Timnas Harimau Malaya menang 2-0", None),
        ("Gajah di kebun binatang lahirkan anak", None),  # tanpa konteks dampak
        ("Harga cabai naik jelang Natal", None),
        # Isu konservasi/kebijakan satwa umum tanpa kejadian dampak (wacana relokasi, edukasi umum)
        (
            "Pemerintah Tegaskan Pemindahan Badak Jawa Tergantung Kajian Ilmiah",
            "Ujung Kulon tetap jadi habitat utama hingga syarat ekologis terpenuhi.",
        ),
        (
            "Bakom: Pemerintah Tak Akan Pindahkan Badak Jawa Tanpa Kajian Lengkap",
            "Keselamatan satwa dan habitat layak jadi prioritas utama.",
        ),
        (
            "Di Tengah Wacana Habitat Dipindahkan, Bayi Badak Lahir di Ujung Kulon",
            "Di tengah wacana memindahkan habitat badak dari Ujung Kulon ke Alas Purwo, ada bayi badak lahir.",
        ),
        (
            "Mengenal badak Sumatra, spesies badak terkecil yang terancam punah",
            "Populasi badak di habitat alaminya terus dipantau BKSDA.",
        ),
        (
            "Tiada Konflik, Burung Liar hingga Harimau Sumatera Hidup Damai di Hutan Beutong Ateuh",
            None,
        ),
    ],
)
def test_topic_rejects(clf, title, snippet):
    assert clf.classify(title, snippet).primary is None


def test_secondary_topic(clf):
    c = clf.classify("Banjir bandang dan longsor akibat pembalakan liar di hulu", None)
    assert c.primary in {"banjir", "pembalakan"}
    assert c.secondary in {"banjir", "pembalakan"} and c.secondary != c.primary
    assert c.eco_link >= 2


def test_animal_victim_of_fire_gets_both_topics(clf):
    c = clf.classify("Orangutan mati terisolasi akibat kebakaran lahan gambut", None)
    assert {c.primary, c.secondary} == {"karhutla", "satwa"}
    assert c.eco_link >= 1


def test_lamandau_remains_accepted_with_high_eco_link(clf):
    c = clf.classify(
        "Tim Gabungan Tebang Sawit di Suaka Margasatwa Lamandau",
        "Tim gabungan menebang sekitar 11.180 tanaman sawit seluas 99 hektar di kawasan Suaka Margasatwa "
        "Lamandau, Kabupaten Sukamara, Kalimantan Tengah, 8 November lalu. Penebangan tanaman sawit itu "
        "tindak lanjut penanganan perkara kebakaran hutan di SM Lamandau. Dalam kasus kebakaran hutan dan lahan…",
    )
    assert c.primary == "karhutla"
    assert c.eco_link >= 3


def test_logistics_flood_downranked_not_dropped(clf):
    c1 = clf.classify("Sudin SDA Jakbar petakan titik rawan banjir saat musim hujan", None)
    c2 = clf.classify("Pemerintah salurkan bantuan penanganan banjir di Subulussalam, Aceh", None)
    c3 = clf.classify("BNPB Siapkan Modifikasi Cuaca di Sumut-Aceh Cegah Bencana Banjir", None)
    assert c1.primary == "banjir" and c1.eco_link == -1
    assert c2.primary == "banjir" and c2.eco_link == -1
    assert c3.primary == "banjir" and c3.eco_link == -1


def test_body_only_strong_not_enough(clf):
    # kata kunci kuat hanya di cuplikan = 2 poin < ambang 4
    assert clf.classify("Pemerintah bahas anggaran daerah", "ada kabut asap tipis").primary is None


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Karhutla di Kalimantan Tengah dan Sumatera Selatan", "Kalimantan Tengah & Sumatera Selatan"),
        ("Banjir di Papua Barat", "Papua Barat"),
        ("Longsor di Sumbar", "Sumatera Barat"),
        ("Banjir rendam Jakarta", "DKI Jakarta"),
        ("Hutan terbakar di wilayah tengah", None),
        ("Warga Papua dan Papua Barat", "Papua Barat & Papua"),
    ],
)
def test_location(cfg, title, expected):
    assert LocationMatcher(cfg.provinces).find(title, None) == expected


def test_location_from_snippet_only_when_title_lacks(cfg):
    m = LocationMatcher(cfg.provinces)
    assert m.find("Longsor tutup jalan", "kejadian di Aceh Tengah") == "Aceh"


@pytest.mark.parametrize(
    "title",
    [
        "Berapa batas kualitas udara sehat? Ini standar ISPU dan WHO",  # ISPU tanpa pendamping
        "ISPU Jakarta hari ini kategori sedang",
        "Hotspot baru Starbucks dibuka di Bandung",
        "Asap tebal selimuti jalan tol akibat truk terbakar",
        "Asap dan ISPA menghantui warga kota industri",   # dua kata ambigu tak cukup
        "Hutan Kota UI untuk Sekolah Rakyat",
    ],
)
def test_ambiguous_terms_need_companion(clf, title):
    assert clf.classify(title, None).primary is None


@pytest.mark.parametrize(
    "title",
    [
        "ISPU Pekanbaru berbahaya akibat kabut asap",
        "Hotspot di Riau meningkat, karhutla mengintai",
        "Titik api bertambah, asap tebal selimuti Jambi",
    ],
)
def test_ambiguous_terms_with_companion(clf, title):
    assert clf.classify(title, None).primary == "karhutla"


@pytest.mark.parametrize(
    "title",
    [
        "Polisi tangkap pelaku illegal logging di hutan lindung Jambi",
        "Perambahan hutan di Taman Nasional Tesso Nilo capai 40 ribu hektare",
        "Penebangan liar di Kalimantan, 200 kubik kayu ilegal disita",
        "Alih fungsi hutan jadi sawit marak di Papua",
    ],
)
def test_pembalakan_keywords(clf, title):
    assert clf.classify(title, None).primary == "pembalakan"
