from datetime import datetime, timedelta, UTC
from types import SimpleNamespace

import pytest

import newsletter_automation as na


def test_published_to_datetime_converts_struct_time_tuple():
    parsed = (2026, 9, 18, 14, 30, 0, 4, 261, 0)
    converted = na.published_to_datetime(parsed)
    assert converted == datetime(2026, 9, 18, 14, 30, 0, tzinfo=UTC)


def test_published_to_datetime_empty_is_none():
    assert na.published_to_datetime(None) is None
    assert na.published_to_datetime(()) is None


def test_is_recent_compares_datetime_not_struct_time():
    cutoff = datetime(2026, 9, 17, tzinfo=UTC)
    recent = (2026, 9, 18, 12, 0, 0, 4, 261, 0)
    old = (2026, 9, 10, 12, 0, 0, 3, 253, 0)
    assert na.is_recent(recent, cutoff) is True
    assert na.is_recent(old, cutoff) is False


def test_headlines_from_entries_skips_old_and_excluded():
    cutoff = datetime.now(UTC) - timedelta(days=2)
    now = datetime.now(UTC)
    recent = now.timetuple()
    old = (now - timedelta(days=10)).timetuple()
    entries = [
        SimpleNamespace(title="Sports merger announced", link="https://a", summary="x", published_parsed=recent),
        SimpleNamespace(title="Old acquisition news", link="https://b", summary="x", published_parsed=old),
        SimpleNamespace(title="Football coach buyout rumors", link="https://d", summary="x", published_parsed=recent),
        SimpleNamespace(title="Acme acquisition of Beta", link="https://c", summary="deal", published_parsed=recent),
    ]
    headlines = na.headlines_from_entries(entries, cutoff=cutoff)
    assert [h["title"] for h in headlines] == ["Acme acquisition of Beta"]


def test_rank_headlines_keeps_corporate_deals_only():
    headlines = [
        {"title": "Market open higher on tech stocks", "link": "1", "summary": ""},
        {"title": "Acme announces acquisition of Beta", "link": "2", "summary": ""},
        {"title": "Taboola To Acquire Dianomi - Pulse 2.0", "link": "3", "summary": ""},
        {"title": "Trump hails Greenland security deal that falls short of takeover - WaPo", "link": "4", "summary": ""},
        {"title": "Red Lake Nation Responds to Federal Takeover of Child Welfare Services", "link": "5", "summary": ""},
    ]
    ranked = na.rank_headlines(headlines)
    titles = [h["title"] for h in ranked]
    assert titles[0] == "Acme announces acquisition of Beta"
    assert "Taboola To Acquire Dianomi - Pulse 2.0" in titles
    assert all("Greenland" not in title for title in titles)
    assert all("Child Welfare" not in title for title in titles)
    assert all("Market open" not in title for title in titles)


def test_fallback_summary_skips_title_echo():
    article = {
        "title": "Acme acquisition of Beta - DealBook",
        "summary": "Acme acquisition of Beta DealBook",
    }
    blurb = na.fallback_summary(article)
    assert "DealBook" in blurb
    assert blurb != article["summary"]


def test_fallback_summary_uses_real_snippet():
    article = {"title": "Acme acquisition of Beta", "summary": "Acme will buy Beta for $2 billion."}
    assert na.fallback_summary(article) == "Acme will buy Beta for $2 billion."


def test_newsletter_html_is_not_plain_text():
    html = na.create_html_email_for_subscriber(
        [{
            "title": "Acme to acquire Beta",
            "source": "Reuters",
            "link": "https://example.com/deal",
            "summary": "Acme agreed to buy Beta for $2 billion to expand in payments.",
        }],
        "murphyd519@gmail.com",
        "token",
        sent_at=datetime(2026, 9, 19, tzinfo=UTC),
    )
    assert "<table" in html
    assert "M&amp;A Newsletter" in html
    assert "Read the story" in html
    assert "REUTERS" in html
    assert "#102033" in html
    assert "<em>" not in html
    assert "Saturday, September 19, 2026" in html
    assert "https://example.com/deal" in html


def test_parse_recipient_allowlist_dedupes_and_lowercases():
    assert na.parse_recipient_allowlist(" murphyd519@gmail.com, MURPHYD519@gmail.com ,") == [
        "murphyd519@gmail.com"
    ]


def test_resolve_send_recipients_allowlist_only():
    subscribers = [
        {"email": "alice@example.com", "unsubscribe_token": "a"},
        {"email": "murphyd519@gmail.com", "unsubscribe_token": "mine"},
        {"email": "bob@example.com", "unsubscribe_token": "b"},
    ]
    resolved = na.resolve_send_recipients(
        subscribers,
        ["murphyd519@gmail.com"],
        send_all=False,
    )
    assert [row["email"] for row in resolved] == ["murphyd519@gmail.com"]
    assert resolved[0]["unsubscribe_token"] == "mine"


def test_resolve_send_recipients_adds_placeholder_if_missing():
    resolved = na.resolve_send_recipients(
        [{"email": "someone@else.com", "unsubscribe_token": "x"}],
        ["murphyd519@gmail.com"],
        send_all=False,
    )
    assert resolved == [{"email": "murphyd519@gmail.com", "unsubscribe_token": "local-test"}]


def test_resolve_send_recipients_empty_allowlist_fails_closed():
    with pytest.raises(RuntimeError, match="allowlist is empty"):
        na.resolve_send_recipients(
            [{"email": "alice@example.com", "unsubscribe_token": "a"}],
            [],
            send_all=False,
        )


def test_resolve_send_recipients_send_all_keeps_full_list():
    subscribers = [
        {"email": "alice@example.com", "unsubscribe_token": "a"},
        {"email": "bob@example.com", "unsubscribe_token": "b"},
    ]
    resolved = na.resolve_send_recipients(subscribers, ["murphyd519@gmail.com"], send_all=True)
    assert resolved == subscribers
