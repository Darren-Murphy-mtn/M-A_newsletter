# M&A Newsletter Pipeline

Clean, focused pipeline for automated M&A newsletter generation and distribution.

## Flow

```
Cron Job → Scrape Reuters → Identify Deals → OpenAI Summarize → Format Email → Pull Supabase Subscribers → Upload to Resend → Send
```

## Files

| File | Purpose |
|------|---------|
| `ma_main.py` | Main pipeline orchestrator |
| `ma_scraper.py` | Reuters scraping and deal identification |
| `ma_summarizer.py` | OpenAI integration for deal summaries |
| `ma_format_email.py` | HTML email formatting |
| `ma_db_supabase.py` | Supabase subscriber management |
| `ma_sendemail.py` | Resend API integration |
| `requirements.txt` | Dependencies |
| `.env.example` | Environment variables template |

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Set up Supabase database:**
```sql
CREATE TABLE ma_subscribers (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified BOOLEAN DEFAULT TRUE
);
```

4. **Run pipeline:**
```bash
python ma_main.py
```

## Cron Job

Add to crontab for daily execution:
```bash
# Run every morning at 8 AM
0 8 * * * cd /path/to/M&A_newsletter && python ma_main.py
```

## Environment Variables

```env
OPENAI_API_KEY=sk-your-openai-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
RESEND_API_KEY=re_your-resend-key
SENDER_EMAIL=newsletter@yourdomain.com
SENDER_NAME=M&A Newsletter
```

That's it! Clean and focused. 🎯