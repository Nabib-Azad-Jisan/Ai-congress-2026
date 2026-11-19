from datetime import date
from time import monotonic

import pytest

from app import farmer_chat_sources as sources


ORIGINAL_READ = sources._read


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(sources, "_today", lambda: date(2026, 11, 19))
    monkeypatch.setattr(sources, "_read", lambda url, deadline: "")


def make_bulletin(district="গাজীপুর", issued="১৮.১১.২০২৬", end="২২.১১.২০২৬"):
    return f"""
    <h2>District AGROMETEOROLOGICAL ADVISORY SERVICE BULLETIN 18 November 2026</h2>
    <div id="Weather_data_container"><p>জেলা: {district}</p>
    <p>তারিখ : {issued}</p><p>{issued} থেকে {end} পর্যন্ত কৃষি আবহাওয়া বিষয়ক বুলেটিন</p>
    <table><tr><td>আবহাওয়ার স্থিতিমাপ</td><td>১৮.১১.২০২৬</td></tr>
    <tr><td>বৃষ্টিপাত (মি.মি)</td><td>৯৯.০</td></tr></table>
    <p>আগামী ৫ দিনের আবহাওয়ার পূর্বাভাস</p>
    <table><tr><td>আবহাওয়ার স্থিতিমাপ</td><td>১৮.১১.২০২৬</td><td>১৯.১১.২০২৬</td><td>সীমা</td></tr>
    <tr><td>বৃষ্টিপাত (মি.মি)</td><td>০.০</td><td>০.১</td><td>০-১</td></tr></table></div>
    <div class="AiContent" id="AiContent"><p>সম্ভাব্য বৃষ্টিপাতের ক্ষতিকর প্রভাব থেকে ফসল রক্ষার জন্য</p>
    <ul><li>জমির নিষ্কাশন নালা পরিষ্কার রাখুন যেন জমিতে অতিরিক্ত পানি জমে না থাকতে পারে।</li>
    <li>রাসায়নিক সার প্রয়োগ করুন।</li></ul></div>
    """


def test_weather_checks_body_and_forecast_dates(monkeypatch):
    monkeypatch.setattr(sources, "_read", lambda url, deadline: make_bulletin())
    result = sources.collect_sources("weather", "Tomato", "Gazipur, Bangladesh", "en")[0]
    assert result["as_of"] == "2026-11-18"
    assert result["valid_until"] == "2026-11-22"
    assert result["status"] == "dated_bulletin"
    assert "0.1 mm" in result["detail"] and "drain" in result["detail"].lower()
    assert "99.0" not in result["detail"] and "রাসায়নিক" not in result["detail"]


@pytest.mark.parametrize("district,issued,end", [
    ("ঢাকা", "১৮.১১.২০২৬", "২২.১১.২০২৬"),
    ("গাজীপুর", "২৫.১১.২০২৬", "২৯.১১.২০২৬"),
    ("গাজীপুর", "১৪.১১.২০২৬", "১৮.১১.২০২৬"),
])
def test_rejects_misfiled_future_or_conflicting_issue(monkeypatch, district, issued, end):
    monkeypatch.setattr(sources, "_read", lambda url, deadline: make_bulletin(district, issued, end))
    result = sources.collect_sources("weather", "rice", "গাজীপুর", "bn")[0]
    assert result["status"] == "directory"
    assert "0.1" not in result["detail"]


def test_expired_issue_never_supplies_current_advice(monkeypatch):
    monkeypatch.setattr(sources, "_today", lambda: date(2026, 12, 1))
    monkeypatch.setattr(sources, "_read", lambda url, deadline: make_bulletin())
    result = sources.collect_sources("weather", "Tomato", "Gazipur", "en")[0]
    assert result["status"] == "expired_bulletin"
    assert "drain" not in result["detail"].lower()


def test_calendar_validates_pdf_identity_duration_and_months(monkeypatch):
    url = "https://www.bamis.gov.bd/res/public/calendars/2023/03/16/26454.pdf"
    page = f'<h2>Tomato - Dhaka Region - Crop weather calendar</h2><a href="{url}" download="English.pdf">Download</a>'
    pdf = ("Crop Weather Calendar of Rabi seasonTomato: Dhaka region (Districts: Gazipur, Tangail) "
           "Region: Dhaka Tomato-Rabi season Duration: 120-150 days Month September October November "
           "December January February Std.Week/Normal")
    monkeypatch.setattr(sources, "_read", lambda link, deadline: pdf if link.endswith(".pdf") else page)
    result = sources.collect_sources("calendar", "টমেটো", "Gazipur", "en")[0]
    assert result["status"] == "seasonal_reference" and result["url"] == url
    assert "September" in result["detail"] and "February" in result["detail"]
    assert "120" in result["detail"] and "150" in result["detail"]
    monkeypatch.setattr(sources, "_read", lambda link, deadline: pdf.replace("Tomato", "Rice") if link.endswith(".pdf") else page)
    assert sources.collect_sources("calendar", "tomato", "Gazipur", "en")[0]["status"] == "directory"


def test_no_silent_rice_season_or_unknown_location():
    options = sources.collect_sources("calendar", "rice", "Gazipur", "en")
    assert all(item["status"] == "directory" for item in options)
    assert all(name in " ".join(item["detail"] for item in options) for name in ("Aman", "Aus", "Boro"))
    assert sources.collect_sources("weather", "rice", "Delhi", "en")[0]["status"] == "directory"


def test_market_requires_named_market_unit_date_and_trade_type():
    source = sources.collect_sources("market", "tomato", "Dhaka", "en")[0]
    assert source["status"] == "directory" and source["url"].startswith("https://market.dam.gov.bd/")
    assert "wholesale" in source["detail"] and "verified" in source["detail"].lower()
    assert "BDT" not in source["detail"]


def test_storage_selects_crop_class_and_handles_unlisted_crops():
    assert "grain" in sources.collect_sources("storage", "Boro rice", "Gazipur", "en")[0]["detail"]
    assert "shade" in sources.collect_sources("storage", "Tomato", "Gazipur", "en")[0]["detail"]
    assert sources.collect_sources("storage", "cotton", "Gazipur", "en")[0]["status"] == "directory"


def test_archive_fallback_picks_newest_dated_document_and_checks_body(monkeypatch):
    archive = "".join(f'<tr><td>{day} November 2026</td><td><a href="{sources.BAMIS}/bulletin/view/{doc}">Bulletin</a></td></tr>'
                      for day, doc in [(15, 44), (21, 46), (18, 45)])
    calls = []

    def read(url, deadline):
        calls.append(url)
        if "/archive/" in url:
            return archive
        return make_bulletin() if url.endswith("/view/45/") else ""

    monkeypatch.setattr(sources, "_read", read)
    result = sources.collect_sources("weather", "rice", "Gazipur", "en")[0]
    assert result["url"].endswith("/view/45/") and result["as_of"] == "2026-11-18"
    assert not any("/view/46/" in url for url in calls)


def test_stage_advice_preserves_crop_and_stage(monkeypatch):
    advice = """
    <p><strong>ধান বোরো</strong></p><ul><li><strong>পর্যায়</strong>:বীজতলা</li>
    <li>উঁচু জায়গায় বীজতলা তৈরি করুন এবং জমি থেকে পানি নিষ্কাশনের ব্যবস্থা রাখুন।</li></ul>
    """
    page = make_bulletin().split('<div class="AiContent"')[0] + f'<div id="AiContent">{advice}</div>'
    monkeypatch.setattr(sources, "_read", lambda url, deadline: page)
    assert "higher ground" in sources.collect_sources("briefing", "Boro rice", "Gazipur", "en")[0]["detail"]
    assert "higher ground" not in sources.collect_sources("briefing", "rice", "Gazipur", "en")[0]["detail"]
    assert "higher ground" not in sources.collect_sources("briefing", "wheat", "Gazipur", "en")[0]["detail"]


def test_calendar_ignores_untrusted_download_links(monkeypatch):
    visited = []

    def read(url, deadline):
        visited.append(url)
        return '<a href="https://example.org/unverified.pdf" download="Boro.pdf">Download</a>'

    monkeypatch.setattr(sources, "_read", read)
    result = sources.collect_sources("calendar", "Boro", "Comilla", "en")
    assert result[0]["status"] == "directory"
    assert len(visited) == 1 and visited[0].endswith("/75/12/")


def test_reader_caches_and_uses_only_approved_urls(monkeypatch):
    # This test exercises the real cache wrapper, replacing the transport itself.
    calls = []
    monkeypatch.setattr(sources, "_download", lambda url, deadline, pdf: calls.append(url) or "document")
    reader = ORIGINAL_READ
    url = sources.BAMIS + "/en/bulletin/district/current/19/"
    sources._CACHE.clear()
    try:
        assert reader(url, monotonic() + 1) == "document"
        assert reader(url, monotonic() + 1) == "document"
        assert reader(sources.BAMIS + ".example.net/en/calendar/1/74/9/", monotonic() + 1) == ""
        assert reader(sources.BAMIS + "/en/calendar/1/74/9/", monotonic() - 1) == ""
        assert calls == [url]
    finally:
        sources._CACHE.clear()


def test_transport_stops_reading_an_oversize_page(monkeypatch):
    class OversizePage:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raise_for_status(self):
            pass

        def iter_bytes(self, chunk_size):
            for _ in range(14):
                yield b" " * chunk_size
            pytest.fail("response continued streaming past the HTML limit")

    monkeypatch.setattr(sources.httpx, "stream", lambda *args, **kwargs: OversizePage())
    assert sources._download(sources.BULLETINS, monotonic() + 1, pdf=False) == ""
