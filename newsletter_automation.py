import argparse
import os
import requests
import feedparser
from openai import OpenAI
from datetime import datetime, timedelta, UTC
from html import escape
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json
from urllib.parse import quote
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client

# ── load environment variables ───────────────────────────
load_dotenv(dotenv_path=Path('.') / '.env')

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

REQUIRED_ENV = [
    "EMAIL_SENDER",
    "RESEND_API_KEY",
    "OPENAI_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]
missing_names = [name for name in REQUIRED_ENV if not os.getenv(name)]
if missing_names:
    raise RuntimeError("Missing required variables in .env: " + ", ".join(missing_names))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# keyword exclude list
EXCLUDE_KEYWORDS = [
    'sports', 'science', 'lifestyle', 'pictures', 'graphics', 'entertainment', 'gaming',
    'football', 'coach', 'nba', 'nfl', 'mlb', 'nhl', 'ncaa', 'soccer', 'school district',
]

NON_DEAL_PHRASES = [
    'child welfare', 'federal takeover', 'greenland', 'security deal',
    'orchard', 'run club', 'topic takeover', 'ambulance',
]

STRONG_MA_PHRASES = [
    'to acquire', 'acquisition of', 'agrees to buy', 'acquires ', 'acquired ',
    'merger with', 'take-private', 'take private', 'buyout of', 'takeover bid',
]

RECENT_DAYS = 2
CUTOFF_DT = datetime.now(UTC) - timedelta(days=RECENT_DAYS)

CI = os.getenv("CI") == "true"   # GitHub sets CI=true

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

RSS_FEEDS = [
    (
        "Google News M&A",
        "https://news.google.com/rss/search?q=%22to+acquire%22+OR+%22acquisition+of%22+OR+%22merger+with%22+OR+%22agrees+to+buy%22+when:2d&hl=en-US&gl=US&ceid=US:en",
    ),
    (
        "Google News deals",
        "https://news.google.com/rss/search?q=merger+OR+acquisition+OR+buyout+when:2d&hl=en-US&gl=US&ceid=US:en",
    ),
    (
        "PR Newswire M&A",
        "https://www.prnewswire.com/rss/mergers-and-acquisitions-list.rss",
    ),
]


def get_db_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def parse_recipient_allowlist(raw=None):
    source = EMAIL_RECIPIENTS if raw is None else raw
    emails = []
    seen = set()
    for part in (source or "").split(","):
        email = part.strip().lower()
        if email and email not in seen:
            seen.add(email)
            emails.append(email)
    return emails


def resolve_send_recipients(subscribers, allowlist, send_all=False):
    """Pick who actually receives mail. Default is allowlist-only."""
    if send_all:
        return list(subscribers or [])
    if not allowlist:
        raise RuntimeError("EMAIL_RECIPIENTS allowlist is empty; refusing to send.")

    by_email = {}
    for sub in subscribers or []:
        email = (sub.get("email") or "").strip().lower()
        if email:
            by_email[email] = sub

    resolved = []
    for email in allowlist:
        if email in by_email:
            resolved.append(by_email[email])
        else:
            resolved.append({"email": email, "unsubscribe_token": "local-test"})
    return resolved


def get_recipient_emails():
    subscribers = supabase.table("subscribers").select("email,unsubscribe_token").eq("unsubscribed", False).execute()
    emails = [row["email"] for row in subscribers.data]
    return list(dict.fromkeys(emails))


def published_to_datetime(published_parsed):
    if not published_parsed:
        return None
    try:
        return datetime(*published_parsed[:6], tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def is_recent(published_parsed, cutoff=None):
    cutoff = CUTOFF_DT if cutoff is None else cutoff
    published_dt = published_to_datetime(published_parsed)
    if published_dt is None:
        return False
    return published_dt > cutoff


def headlines_from_entries(entries, cutoff=None, limit=15):
    headlines = []
    for entry in (entries or [])[:limit]:
        title = getattr(entry, "title", "") or ""
        if any(k in title.lower() for k in EXCLUDE_KEYWORDS):
            continue
        published = getattr(entry, "published_parsed", None)
        if not is_recent(published, cutoff):
            continue
        raw_summary = getattr(entry, "summary", "") or ""
        headlines.append({
            "title": title,
            "link": getattr(entry, "link", "") or "",
            "summary": BeautifulSoup(raw_summary, "html.parser").get_text(" ", strip=True),
        })
    return headlines


def fetch_rss_feed(url, cutoff=None, limit=25):
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching RSS {url}: {e}")
        return []
    feed = feedparser.parse(resp.content)
    entries = [] if not feed.entries else feed.entries
    return headlines_from_entries(entries, cutoff=cutoff, limit=limit)


def fetch_reuters_html():
    url = "https://www.reuters.com/markets/deals/"
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print("Error fetching HTML:", e)
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    cards = soup.find_all('div', attrs={'data-testid': 'MediaStoryCard'})
    headlines = []
    for card in cards[:20]:
        a_tag = card.find('a', attrs={'data-testid': 'Heading'})
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        if any(k in title.lower() for k in EXCLUDE_KEYWORDS):
            continue
        link = a_tag.get('href')
        if link and not link.startswith('http'):
            link = 'https://www.reuters.com' + link
        summary_tag = card.find('p')
        summary = summary_tag.get_text(strip=True) if summary_tag else ''
        headlines.append({"title": title, "link": link, "summary": summary})
    return headlines


def get_headlines():
    for source_name, url in RSS_FEEDS:
        try:
            headlines = fetch_rss_feed(url)
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")
            continue
        if headlines:
            print(f"Fetched {len(headlines)} headlines from {source_name}")
            return headlines[:10]
        print(f"{source_name} returned no recent headlines")

    print("RSS empty, falling back to HTML scrape")
    headlines = fetch_reuters_html()
    print("Fetched", len(headlines), "headlines from HTML")
    if not headlines:
        print("No headlines from RSS or HTML scrape")
    return headlines[:10]


def split_headline_source(title):
    raw = (title or "").strip()
    if " - " not in raw:
        return raw, ""
    core, source = raw.rsplit(" - ", 1)
    if 1 < len(source) <= 42:
        return core.strip(), source.strip()
    return raw, ""


def is_corporate_ma(title):
    t = (title or "").lower()
    if any(k in t for k in EXCLUDE_KEYWORDS):
        return False
    if any(phrase in t for phrase in NON_DEAL_PHRASES):
        return False
    return any(phrase in t for phrase in STRONG_MA_PHRASES)


def ma_score(title):
    t = (title or "").lower()
    score = 0
    strong_phrases = [
        ("to acquire", 5),
        ("acquisition of", 5),
        ("agrees to buy", 5),
        ("acquires ", 4),
        ("acquired ", 3),
        ("merger with", 5),
        ("take-private", 5),
        ("take private", 5),
        ("buyout of", 4),
        ("takeover bid", 4),
    ]
    for phrase, points in strong_phrases:
        if phrase in t:
            score += points
    weak_keywords = ['acquisition', 'merger', 'buyout', 'takeover', 'deal', 'm&a']
    score += sum(1 for keyword in weak_keywords if keyword in t)
    return score


def rank_headlines(headlines):
    scored = [
        (headline, ma_score(headline.get('title', '')))
        for headline in headlines
        if is_corporate_ma(headline.get('title', ''))
    ]
    if not scored:
        scored = [(headline, ma_score(headline.get('title', ''))) for headline in headlines]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [h[0] for h in scored[:5]]


def _normalize_text(value):
    return " ".join((value or "").lower().split())


def is_title_echo(title, summary):
    if not (summary or "").strip():
        return True
    core, source = split_headline_source(title)
    candidates = [
        _normalize_text(title),
        _normalize_text(core),
        _normalize_text(f"{core} {source}".strip()),
    ]
    normalized = _normalize_text(summary)
    if normalized in candidates:
        return True
    core_norm = _normalize_text(core)
    return bool(core_norm) and core_norm in normalized and len(normalized) <= len(core_norm) + 24


def blurb_from_headline(title):
    core, source = split_headline_source(title)
    attribution = f" Reporting via {source}." if source else ""
    lowered = core.lower()
    if any(flag in lowered for flag in ("not moving forward", "calls off", "called off", "scraps", "terminat")):
        return (
            f"{core} appears to be a deal that stalled or was withdrawn.{attribution} "
            "The linked story has the parties, timing, and why it fell apart."
        )
    if "advises" in lowered and "acquisition" in lowered:
        return (
            f"{core}.{attribution} This is deal counsel coverage — useful for who is advising, "
            "but tap through for the actual transaction terms."
        )
    return (
        f"{core}.{attribution} Open the story for counterparties, price if disclosed, "
        "and the strategic rationale behind the move."
    )


def fallback_summary(article):
    title = article.get("title") or ""
    snippet = (article.get("summary") or "").strip()
    if snippet and not is_title_echo(title, snippet):
        return snippet[:800]
    return blurb_from_headline(title)


def summarize_headlines(headlines):
    summaries = []
    for article in headlines:
        title = article.get("title") or ""
        headline, source = split_headline_source(title)
        prompt = (
            f"Write a concise 5-7 sentence summary suitable for an M&A newsletter. including stats and numbers where applicable. "
            f"Focus on the companies involved, deal value (if mentioned), and strategic rationale.\n\n"
            f"Headline: {title}\n"
            f"Extracted snippet: {article['summary']}\n"
        )
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial news analyst specializing in M&A. Were providing a breif overview of a deal/decision in a newsletter summary. When you get the artcile produce a summary that covers what the deal/decision is, the context of the deal/decision in the space, the motivation behind the deal/decision for either company, and the potential impact of the deal/decision. Provide a 4-7 sentence summary for a newsletter."},
                    {"role": "user", "content": prompt}
                ]
            )
            summary = response.choices[0].message.content.strip()
        except Exception:
            print("Warning: OpenAI summary failed, using newsletter blurb instead.")
            summary = fallback_summary(article)
        summaries.append({
            "title": headline or title,
            "source": source,
            "link": article["link"],
            "summary": summary
        })
    return summaries


def get_active_subscribers():
    try:
        result = supabase.table("subscribers").select("email,unsubscribe_token").eq("unsubscribed", False).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Warning: could not load subscribers: {e}")
        return []


def _format_issue_date(sent_at=None):
    sent_at = sent_at or datetime.now(UTC)
    return f"{sent_at.strftime('%A, %B')} {sent_at.day}, {sent_at.strftime('%Y')}"


def create_html_email_for_subscriber(summaries, email, token, sent_at=None):
    issue_date = _format_issue_date(sent_at)
    unsub_url = (
        "https://manewsletter-production.up.railway.app/unsubscribe"
        f"?email={quote(email)}&token={quote(str(token))}"
    )
    story_count = len(summaries)
    intro = (
        f"{story_count} deal{'s' if story_count != 1 else ''} worth knowing today, "
        "with the parties, context, and a link to the full report."
    )

    stories_html = []
    for index, article in enumerate(summaries, start=1):
        title = escape(article.get("title") or "Untitled deal")
        source = escape(article.get("source") or "")
        summary = escape(article.get("summary") or "")
        link = escape(article.get("link") or "#", quote=True)
        kicker = source.upper() if source else f"DEAL {index:02d}"
        divider = "" if index == story_count else (
            '<tr><td style="padding:0 0 28px 0;border-bottom:1px solid #eadfce;"></td></tr>'
            '<tr><td style="padding:0;font-size:0;line-height:0;height:28px;">&nbsp;</td></tr>'
        )
        stories_html.append(f"""
            <tr>
              <td style="padding:0 0 10px 0;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#b0892e;font-weight:700;">
                {kicker}
              </td>
            </tr>
            <tr>
              <td style="padding:0 0 12px 0;font-family:Georgia,'Times New Roman',serif;font-size:22px;line-height:1.3;color:#102033;font-weight:700;word-wrap:break-word;">
                {title}
              </td>
            </tr>
            <tr>
              <td style="padding:0 0 16px 0;font-family:Georgia,'Times New Roman',serif;font-size:16px;line-height:1.65;color:#3a3228;">
                {summary}
              </td>
            </tr>
            <tr>
              <td style="padding:0 0 8px 0;">
                <a href="{link}" style="display:inline-block;background:#102033;color:#f7f1e3;text-decoration:none;font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:0.04em;font-weight:700;padding:12px 18px;border-radius:4px;">
                  Read the story
                </a>
              </td>
            </tr>
            {divider}
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>M&amp;A Newsletter</title>
</head>
<body style="margin:0;padding:0;background:#d9d1c3;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#d9d1c3;margin:0;padding:0;">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:#f7f1e3;">
          <tr>
            <td style="background:#102033;padding:28px 36px 24px 36px;">
              <p style="margin:0 0 8px 0;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:#d4b15a;font-weight:700;">
                Daily briefing
              </p>
              <h1 style="margin:0 0 8px 0;font-family:Georgia,'Times New Roman',serif;font-size:32px;line-height:1.15;color:#f7f1e3;font-weight:700;">
                M&amp;A Newsletter
              </h1>
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#c9c1b0;">
                {escape(issue_date)}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 36px 8px 36px;font-family:Georgia,'Times New Roman',serif;font-size:17px;line-height:1.6;color:#3a3228;">
              {escape(intro)}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 36px 8px 36px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                {''.join(stories_html)}
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#102033;padding:24px 36px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.6;color:#c9c1b0;">
              You are receiving this because you subscribed to the M&amp;A Newsletter.
              <br>
              <a href="{escape(unsub_url, quote=True)}" style="color:#d4b15a;text-decoration:underline;">Unsubscribe</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_newsletter_to_all(summaries, dry_run=False, send_all=False):
    allowlist = parse_recipient_allowlist()
    if not send_all and not allowlist:
        raise RuntimeError("EMAIL_RECIPIENTS allowlist is empty; refusing to send.")

    subscribers = get_active_subscribers()
    recipients = resolve_send_recipients(subscribers, allowlist, send_all=send_all)
    if not recipients:
        print("No recipients after allowlist filter.")
        return []

    intended = [sub["email"] for sub in recipients]
    print("Intended recipients:", ", ".join(intended))

    sent = []
    for sub in recipients:
        email = sub["email"]
        token = sub.get("unsubscribe_token") or "local-test"
        html_content = create_html_email_for_subscriber(summaries, email, token)
        if dry_run:
            print(f"DRY RUN: would send to {email}")
            sent.append(email)
            continue
        data = {
            "from": f"M&A Newsletter <{EMAIL_SENDER}>",
            "to": [email],
            "subject": "M&A Deals – {}".format(datetime.now(UTC).strftime('%b %d, %Y')),
            "html": html_content
        }
        print(f"Sending to: {email}")
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json=data
        )
        print(f"Sent to {email}: {response.status_code}")
        if response.status_code >= 400:
            print(f"Resend error for {email}: {response.text}")
        sent.append(email)
    return sent


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Scrape, summarize, and send the M&A newsletter")
    parser.add_argument("--dry-run", action="store_true", help="Build the email but do not send")
    parser.add_argument(
        "--all-subscribers",
        action="store_true",
        help="Send to every active Supabase subscriber (default is EMAIL_RECIPIENTS only)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    headlines = get_headlines()
    if not headlines:
        print("No headlines found")
        return
    ranked_headlines = rank_headlines(headlines)
    summaries = summarize_headlines(ranked_headlines)
    send_newsletter_to_all(summaries, dry_run=args.dry_run, send_all=args.all_subscribers)


if __name__ == "__main__":
    main()
