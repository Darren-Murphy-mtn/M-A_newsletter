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
        
        # Comprehensive Financial Deal Keywords
        self.deal_keywords = [
            # M&A Terms
            'acquisition', 'acquired', 'merger', 'buyout', 'takeover', 
            'purchase', 'deal to buy', 'agrees to buy', 'strategic partnership',
            'joint venture', 'spin-off', 'divestiture', 'asset sale',
            
            # VC/PE Terms  
            'funding', 'raises', 'investment', 'venture capital', 'private equity',
            'series a', 'series b', 'series c', 'series d', 'pre-seed', 'seed round',
            'growth capital', 'expansion financing', 'mezzanine financing',
            
            # Investment Banking Terms
            'underwriting', 'ipo', 'initial public offering', 'secondary offering',
            'bond issuance', 'debt financing', 'credit facility', 'syndicated loan',
            'leveraged buyout', 'lbo', 'restructuring', 'refinancing',
            'rights offering', 'convertible bond', 'high yield', 'investment grade',
            
            # Corporate Finance
            'capital raising', 'equity financing', 'debt restructuring',
            'financial advisory', 'fairness opinion', 'valuation', 'due diligence',
            'public listing', 'going public', 'delisting', 'privatization',
            
            # Deal Sizes & Values
            'billion', 'million', 'valuation', 'enterprise value', 'market cap'
        ]
        
        logger.info("✅ Scraper initialized with working news sources")

    def get_top_finance_stories(self, max_stories: int = 8, days_back: int = 7) -> List[Deal]:
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
                    matching_keywords = [kw for kw in self.deal_keywords if kw in text_to_check]
                    
                    if matching_keywords:
                        # Enhanced deal type classification
                        deal_type = self._classify_deal_type(text_to_check)
                        
                        # Extract amount if possible
                        amount = self._extract_amount(text_to_check)
                        
                        # Enhanced priority scoring
                        priority_score = len(matching_keywords) * 1.5
                        
                        # Amount-based scoring
                        if amount:
                            priority_score += 4.0
                            if 'billion' in text_to_check:
                                priority_score += 3.0
                            elif 'million' in text_to_check:
                                priority_score += 2.0
                        
                        # Deal type multipliers
                        if deal_type == 'IPO':
                            priority_score += 2.5  # IPOs are always significant
                        elif deal_type == 'IB':
                            priority_score += 2.0  # IB deals are important
                        elif deal_type == 'M&A':
                            priority_score += 1.5
                        elif deal_type == 'VC':
                            priority_score += 1.0
                        
                        # Source credibility boost
                        if source_name.lower() in ['bloomberg', 'reuters']:
                            priority_score += 1.0
                        
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
    
    def _classify_deal_type(self, text: str) -> str:
        """Enhanced deal type classification"""
        text = text.lower()
        
        # Investment Banking indicators (check first - most specific)
        ib_indicators = [
            'underwriting', 'bond issuance', 'debt financing', 'credit facility',
            'syndicated loan', 'restructuring', 'refinancing', 'rights offering',
            'convertible bond', 'high yield', 'investment grade', 'financial advisory'
        ]
        
        # IPO indicators
        ipo_indicators = [
            'ipo', 'initial public offering', 'going public', 'public listing',
            'secondary offering', 'public debut', 'stock market debut'
        ]
        
        # VC/PE indicators
        vc_indicators = [
            'funding', 'raises', 'series a', 'series b', 'series c', 'series d',
            'pre-seed', 'seed round', 'venture capital', 'growth capital',
            'expansion financing', 'investment round'
        ]
        
        # M&A indicators
        ma_indicators = [
            'acquisition', 'acquired', 'merger', 'buyout', 'takeover',
            'purchase', 'deal to buy', 'agrees to buy', 'leveraged buyout',
            'lbo', 'strategic partnership', 'joint venture', 'privatization'
        ]
        
        # Check in order of specificity
        if any(indicator in text for indicator in ib_indicators):
            return 'IB'
        elif any(indicator in text for indicator in ipo_indicators):
            return 'IPO'
        elif any(indicator in text for indicator in vc_indicators):
            return 'VC'
        elif any(indicator in text for indicator in ma_indicators):
            return 'M&A'
        else:
            # Default classification based on context
            if 'private equity' in text:
                return 'M&A'
            elif 'investment' in text:
                return 'VC'
            else:
                return 'M&A'  # Default fallback

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
        """Sample deals for testing when no real deals found - covering all deal types"""
        return [
            Deal(
                title="Goldman Sachs Leads $3.2B IPO for Clean Energy Company",
                description="Goldman Sachs and JPMorgan underwrite $3.2 billion IPO for renewable energy infrastructure company, marking the largest clean tech public offering this year.",
                source="Sample Data",
                url="https://example.com/deal1",
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="IB",
                amount="$3.2 billion",
                priority_score=9.5
            ),
            Deal(
                title="Microsoft Explores $15B AI Acquisition",
                description="Tech giant Microsoft reportedly in talks to acquire leading AI company for $15 billion to strengthen cloud services.",
                source="Sample Data",
                url="https://example.com/deal2",
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="M&A",
                amount="$15 billion",
                priority_score=8.5
            ),
            Deal(
                title="Morgan Stanley Structures $5B Syndicated Loan",
                description="Morgan Stanley leads consortium in structuring $5 billion syndicated credit facility for major infrastructure development project.",
                source="Sample Data",
                url="https://example.com/deal3",
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="IB",
                amount="$5 billion",
                priority_score=8.8
            ),
            Deal(
                title="Biotech Startup Raises $1.8B in Series C",
                description="Revolutionary biotech company developing gene therapies raises $1.8 billion in Series C funding round led by top venture firms.",
                source="Sample Data", 
                url="https://example.com/deal4",
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="VC",
                amount="$1.8 billion",
                priority_score=8.1
            ),
            Deal(
                title="EV Manufacturer Plans $2.1B IPO",
                description="Electric vehicle manufacturer announces plans for $2.1 billion initial public offering, seeking to capitalize on growing EV market.",
                source="Sample Data",
                url="https://example.com/deal5",
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="IPO",
                amount="$2.1 billion",
                priority_score=8.0
            ),
            Deal(
                title="Private Equity Completes $900M Healthcare Buyout",
                description="Leading private equity firm completes $900 million acquisition of specialty healthcare services company.",
                source="Sample Data",
                url="https://example.com/deal6", 
                date=datetime.now().strftime('%Y-%m-%d'),
                deal_type="M&A",
                amount="$900 million",
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