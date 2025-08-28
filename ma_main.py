
#!/usr/bin/env python3
"""
Financial Markets Newsletter Pipeline - Comprehensive Coverage
Flow: Cron -> Scrape News Sources -> Identify Deals (M&A, VC, IB, IPO) -> OpenAI Summarize -> Format -> Supabase Subscribers -> Resend -> Send
"""

import logging
import os
from dotenv import load_dotenv

from ma_scraper import FinanceNewsScraper
from ma_summarizer import DealSummarizer
from ma_format_email import HTMLEmailFormatter
from ma_sendemail import ResendEmailSender, EmailRecipient
from ma_db_supabase import get_all_subscribers, get_subscriber_count
from ma_resend_sync import SupabaseResendSync

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_ma_newsletter_pipeline():
    """
    Main Financial Markets Newsletter Pipeline
    Cron -> Scrape -> Identify (M&A, VC, IB, IPO) -> Summarize -> Format -> Get Subscribers -> Send
    """
    logger.info("🚀 Financial Markets Newsletter Pipeline Starting...")

    # Step 1: Scrape Reuters for deals
    logger.info("📰 Scraping financial news sources for deals...")
    scraper = FinanceNewsScraper()
    deals = scraper.get_top_finance_stories(max_stories=8)  # Get more diverse deals
    
    if not deals:
        logger.warning("❌ No deals found. Exiting pipeline.")
        return False
    logger.info(f"✅ Scraped {len(deals)} deals from financial news sources")

    # Step 2: Send to OpenAI for summarization
    logger.info("🤖 Sending deals to OpenAI for summarization...")
    summarizer = DealSummarizer()
    summarized = summarizer.summarize_deals(deals)
    
    if not summarized:
        logger.warning("❌ No summaries generated. Exiting pipeline.")
        return False
    logger.info(f"✅ OpenAI summarized {len(summarized)} deals")

    # Step 3: Format email content
    logger.info("📧 Formatting email content...")
    content = summarizer.create_newsletter_content(summarized)
    formatter = HTMLEmailFormatter(company_name="Financial Markets Newsletter", brand_color="#1a365d")
    html_email = formatter.create_newsletter_html(content)
    text_email = formatter.create_text_version(content)
    logger.info("✅ Email formatted")

    # Step 4: Pull subscribers from Supabase (with optional Resend sync)
    logger.info("👥 Pulling subscribers from Supabase...")
    
    # Try to sync with Resend if API key has permissions
    sync_enabled = os.getenv('ENABLE_RESEND_SYNC', 'false').lower() == 'true'
    
    if sync_enabled:
        logger.info("🔄 Attempting Resend sync...")
        try:
            sync_service = SupabaseResendSync()
            sync_results = sync_service.sync_supabase_to_resend()
            logger.info(f"✅ Sync complete: +{sync_results['added']} -{sync_results['removed']} ={sync_results['unchanged']}")
        except Exception as e:
            if "restricted" in str(e).lower() or "401" in str(e):
                logger.info("📝 Resend sync disabled (API key restricted to sending only)")
            else:
                logger.warning(f"⚠️  Resend sync failed: {e}")
            logger.info("📧 Continuing with Supabase-only mode...")
    
    # Get subscribers from Supabase (our source of truth)
    subscriber_emails = get_all_subscribers()
    
    if not subscriber_emails:
        logger.warning("❌ No subscribers found in Supabase. Exiting pipeline.")
        return False
    
    subscriber_count = len(subscriber_emails)
    logger.info(f"✅ Found {subscriber_count} subscribers")

    # Step 5: Upload to Resend and send
    logger.info("📤 Sending via Resend...")
    sender = ResendEmailSender()
    recipients = [EmailRecipient(email=email) for email in subscriber_emails]
    # Create a more inclusive and deliverable subject line
    deals_count = len(summarized)
    subject = f"📊 {deals_count} Key Financial Deals This Week - {content.get('headline', 'Weekly Financial Markets Newsletter')}"

    results = sender.send_newsletter(
        recipients=recipients,
        subject=subject,
        html_content=html_email,
        text_content=text_email
    )

    # Step 6: Log results
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    logger.info(f"📊 Pipeline Complete: {successful}/{len(results)} emails sent successfully")
    
    if failed > 0:
        logger.warning(f"⚠️  {failed} emails failed to send")
        
    return successful > 0


if __name__ == "__main__":
    success = run_ma_newsletter_pipeline()
    exit(0 if success else 1)
