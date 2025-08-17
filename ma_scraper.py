"""
ma_scraper.py - Simple Working Finance News Scraper
Focuses on getting actual deals from working sources
"""

import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class Deal:
    title: str
    description: str
    source: str
    url: str
    date: str
    deal_type: str  # 'VC', 'M&A', 'IPO', 'IB'
    amount: Optional[str] = None
    priority_score: float = 0.0

class FinanceNewsScraper:
    def __init__(self):
        logger.info("🚀 Initializing Finance News Scraper...")
        
        # Working RSS feeds
        self.news_sources = {
            'marketwatch': 'https://feeds.marketwatch.com/marketwatch/topstories/',
            'bloomberg': 'https://feeds.bloomberg.com/markets/news.rss', 
            'cnbc': 'https://www.cnbc.com/id/10000664/device/rss/rss.html'
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # M&A Keywords
        self.ma_keywords = [
            'acquisition', 'acquired', 'merger', 'buyout', 'takeover', 
            'purchase', 'deal to buy', 'agrees to buy', 'funding', 
            'raises', 'series a', 'series b', 'series c', 'investment',
            'venture capital', 'private equity', 'ipo', 'public offering'
        ]
        
        logger.info("✅ Scraper initialized with working news sources")

    def get_top_finance_stories(self, max_stories: int = 5, days_back: int = 7) -> List[Deal]:
        """Get top finance stories from working sources"""
        logger.info(f"Starting aggregation for top {max_stories} finance stories from last {days_back} days...")
        
        all_deals = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        logger.info(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Scrape RSS feeds
        for source_name, url in self.news_sources.items():
            logger.info(f"Scraping {source_name}...")
            try:
                deals = self._scrape_rss_source(source_name, url, cutoff_date)
                all_deals.extend(deals)
                logger.info(f"{source_name}: Found {len(deals)} qualifying deals")
            except Exception as e:
                logger.error(f"Error scraping {source_name}: {e}")
        
        # If no real deals found, add samples
        if len(all_deals) == 0:
            logger.info("No deals found from sources. Adding sample deals...")
            all_deals = self._get_sample_deals()
            logger.info(f"Added {len(all_deals)} sample deals")
        
        logger.info(f"Total deals collected: {len(all_deals)}")
        
        # Sort by priority and return top stories
        all_deals.sort(key=lambda x: x.priority_score, reverse=True)
        top_deals = all_deals[:max_stories]
        
        logger.info(f"Final top stories selected: {len(top_deals)}")
        return top_deals

    def _scrape_rss_source(self, source_name: str, url: str, cutoff_date: datetime) -> List[Deal]:
        """Scrape a single RSS source"""
        deals = []
        
        try:
            response = requests.get(url, timeout=15, headers=self.headers)
            feed = feedparser.parse(response.content)
            
            logger.info(f"{source_name} RSS entries found: {len(feed.entries)}")
            
            for entry in feed.entries[:20]:  # Check first 20 entries
                try:
                    # Check if it's M&A related
                    text_to_check = f"{entry.title} {entry.get('summary', '')}".lower()
                    
                    # Find matching keywords
                    matching_keywords = [kw for kw in self.ma_keywords if kw in text_to_check]
                    
                    if matching_keywords:
                        # Determine deal type
                        deal_type = 'M&A'
                        if any(word in text_to_check for word in ['funding', 'raises', 'series', 'investment']):
                            deal_type = 'VC'
                        elif any(word in text_to_check for word in ['ipo', 'public offering']):
                            deal_type = 'IPO'
                        
                        # Extract amount if possible
                        amount = self._extract_amount(text_to_check)
                        
                        # Calculate priority score
                        priority_score = len(matching_keywords) * 2.0
                        if amount:
                            priority_score += 3.0
                        if any(word in text_to_check for word in ['billion', 'million']):
                            priority_score += 2.0
                        
                        deal = Deal(
                            title=entry.title,
                            description=entry.get('summary', entry.title)[:300],
                            source=source_name.title(),
                            url=entry.link,
                            date=datetime.now().strftime('%Y-%m-%d'),
                            deal_type=deal_type,
                            amount=amount,
                            priority_score=priority_score
                        )
                        
                        deals.append(deal)
                        logger.debug(f"Added {source_name} deal: {entry.title[:50]}... (score: {priority_score})")
                
                except Exception as e:
                    logger.debug(f"Error processing entry: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error fetching {source_name} RSS: {e}")
        
        return deals

    def _extract_amount(self, text: str) -> Optional[str]:
        """Extract dollar amounts from text"""
        import re
        
        # Look for patterns like $1.5B, $500M, $2 billion, etc.
        patterns = [
            r'\$\d+\.?\d*\s?billion',
            r'\$\d+\.?\d*\s?B\b',
            r'\$\d+\.?\d*\s?million', 
            r'\$\d+\.?\d*\s?M\b',
            r'\$\d+\.?\d*'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None

    def _get_sample_deals(self) -> List[Deal]:
        """Sample deals for testing when no real deals found"""
        return [
            Deal(
                title="Microsoft Explores $15B AI Acquisition",
                description="Tech giant Microsoft reportedly in talks to acquire leading AI company for $15 billion to strengthen cloud services.",
                source="Sample Data",
                url="https://example.com/deal1",
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="M&A",
                amount="$15 billion",
                priority_score=8.5
            ),
            Deal(
                title="Healthcare Tech Company Raises $2.5B in Series D",
                description="Major healthcare technology startup raises $2.5 billion in Series D funding round led by prominent investors.",
                source="Sample Data", 
                url="https://example.com/deal2",
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="VC",
                amount="$2.5 billion",
                priority_score=7.8
            ),
            Deal(
                title="Private Equity Firm Completes $800M Buyout",
                description="Leading private equity firm completes $800 million acquisition of fintech company specializing in digital payments.",
                source="Sample Data",
                url="https://example.com/deal3", 
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="M&A",
                amount="$800 million",
                priority_score=7.2
            )
        ]


if __name__ == "__main__":
    # Test the scraper
    import logging
    logging.basicConfig(level=logging.INFO)
    
    scraper = FinanceNewsScraper()
    deals = scraper.get_top_finance_stories(max_stories=5)
    
    print(f"\n🎯 Found {len(deals)} deals:")
    for i, deal in enumerate(deals, 1):
        print(f"{i}. {deal.title} ({deal.deal_type}) - {deal.source}")
        if deal.amount:
            print(f"   Amount: {deal.amount}")
        print(f"   Score: {deal.priority_score}")
        print()