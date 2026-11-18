from ashen_news.dedupe import canonical_url, normalize_title, titles_similar
from ashen_news.feeds import SNIPPET_MAX, make_snippet, parse_feed


def test_canonical_url_strips_tracking_and_variants():
    a = canonical_url("http://www.Detik.com/berita/d-1/slug/?utm_source=x&fbclid=abc#frag")
    b = canonical_url("https://detik.com/berita/d-1/slug")
    assert a == b == "https://detik.com/berita/d-1/slug"


def test_canonical_url_amp_and_mobile():
    assert canonical_url("https://m.kompas.com/a/b/amp/") == "https://kompas.com/a/b"


def test_canonical_keeps_meaningful_query_sorted():
    assert canonical_url("https://x.com/p?b=2&a=1&utm_medium=z") == "https://x.com/p?a=1&b=2"


def test_title_similarity_syndicated():
    a = normalize_title("Kabut Asap Karhutla Selimuti Pekanbaru, Sekolah Diliburkan")
    b = normalize_title("Kabut asap karhutla selimuti Pekanbaru, sekolah diliburkan!")
    assert titles_similar(a, b)


def test_title_similarity_different():
    a = normalize_title("Banjir bandang terjang Sumbar")
    b = normalize_title("Banjir rob rendam Pekalongan")
    assert not titles_similar(a, b)


def test_snippet_truncated_and_clean():
    raw = "<p>" + ("kata " * 200) + "</p>"
    s = make_snippet(raw)
    assert s is not None and len(s) <= SNIPPET_MAX and s.endswith("…")
    assert "<" not in s


def test_snippet_repeating_title_dropped():
    assert make_snippet("Judul Berita - Kompas.com", "Judul Berita") is None


def test_parse_feed_extracts_thumbnail_from_enclosure_and_html():
    xml = (
        b'<?xml version="1.0"?><rss version="2.0"><channel>'
        b"<item><title>A</title><link>https://x.com/1</link>"
        b'<enclosure url="https://img.x.com/a.jpg" type="image/jpeg"/></item>'
        b"<item><title>B</title><link>https://x.com/2</link>"
        b'<description><![CDATA[<img src="https://img.x.com/b.webp"/>teks]]></description></item>'
        b"</channel></rss>"
    )
    items = parse_feed(xml, "X", "x")
    assert items[0].image_url == "https://img.x.com/a.jpg"
    assert items[1].image_url == "https://img.x.com/b.webp"
