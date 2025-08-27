"""
deal_summarizer.py - AI-Powered Deal Summarizer
Standalone component that takes deals and creates professional summaries using OpenAI
"""

import os
from openai import OpenAI
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import json
import time
from datetime import datetime
import requests

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Deal:
    """Deal data structure (matches ma_scraper.py)"""
    title: str
    description: str
    source: str
    url: str
    date: str
    deal_type: str
    amount: Optional[str] = None
    priority_score: float = 0.0


@dataclass
class SummarizedDeal:
    """Enhanced deal with AI-generated summary"""
    title: str
    description: str
    ai_summary: str
    key_points: List[str]
    source: str
    url: str
    date: str
    deal_type: str
    amount: Optional[str] = None
    priority_score: float = 0.0
    companies_involved: List[str] = None
    sector: Optional[str] = None


class DealSummarizer:
    """AI-powered deal summarizer using OpenAI"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the summarizer

        Args:
            api_key: OpenAI API key (if not provided, will use OPENAI_API_KEY env var)
        """
        logger.info("🚀 Initializing Deal Summarizer...")

        # Set up OpenAI API key
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")

        # Configure OpenAI client
        self.client = OpenAI(api_key=self.api_key)

        # Summarization settings
        self.model = "gpt-4"  # Use gpt-3.5-turbo for cost efficiency if needed
        self.max_tokens = 300
        self.temperature = 0.3  # Lower temperature for more consistent, factual summaries

        # Rate limiting
        self.requests_per_minute = 50
        self.last_request_time = 0
        self.request_count = 0
        self.minute_start = time.time()

        logger.info("✅ Deal Summarizer initialized successfully")

    def summarize_deals(self, deals: List[Deal]) -> List[SummarizedDeal]:
        """
        Summarize a list of deals using OpenAI

        Args:
            deals: List of Deal objects to summarize

        Returns:
            List of SummarizedDeal objects with AI-generated summaries
        """
        logger.info(f"📝 Starting summarization for {len(deals)} deals...")

        summarized_deals = []

        for i, deal in enumerate(deals, 1):
            logger.info(f"🔄 Processing deal {i}/{len(deals)}: {deal.title[:50]}...")

            try:
                # Rate limiting
                self._handle_rate_limiting()

                # Generate summary
                summarized_deal = self._summarize_single_deal(deal)
                summarized_deals.append(summarized_deal)

                logger.info(f"✅ Deal {i} summarized successfully")

            except Exception as e:
                logger.error(f"❌ Error summarizing deal {i}: {e}")
                # Create fallback summary
                fallback_summary = self._create_fallback_summary(deal)
                summarized_deals.append(fallback_summary)

        logger.info(f"✅ Summarization complete: {len(summarized_deals)} deals processed")
        return summarized_deals

    def _summarize_single_deal(self, deal: Deal) -> SummarizedDeal:
        """Summarize a single deal using OpenAI"""

        # Create prompt for summarization
        prompt = self._create_summarization_prompt(deal)

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional financial analyst specializing in investment banking, venture capital, and M&A. Provide concise, accurate summaries of financial deals for executive briefings."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.9
            )

            # Parse response
            ai_response = response.choices[0].message.content.strip()
            summary_data = self._parse_ai_response(ai_response)

            # Create SummarizedDeal object
            summarized_deal = SummarizedDeal(
                title=deal.title,
                description=deal.description,
                ai_summary=summary_data['summary'],
                key_points=summary_data['key_points'],
                source=deal.source,
                url=deal.url,
                date=deal.date,
                deal_type=deal.deal_type,
                amount=deal.amount,
                priority_score=deal.priority_score,
                companies_involved=summary_data.get('companies', []),
                sector=summary_data.get('sector')
            )

            return summarized_deal

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _create_summarization_prompt(self, deal: Deal) -> str:
        """Create a structured prompt for deal summarization"""

        prompt = f"""
Please analyze this financial deal and provide a structured summary in JSON format:

DEAL INFORMATION:
Title: {deal.title}
Description: {deal.description}
Deal Type: {deal.deal_type}
Amount: {deal.amount or 'Not specified'}
Source: {deal.source}
Date: {deal.date}

Please provide your response in the following JSON format:
{{
    "summary": "A concise 2-3 sentence summary highlighting the most important aspects of this deal",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "companies": ["Company 1", "Company 2"],
    "sector": "Industry/Sector"
}}

Requirements:
- Summary should be 50-80 words, professional tone
- Key points should be 3-4 bullet points covering: deal structure, strategic rationale, market impact, and financial details
- Extract all company names mentioned
- Identify the primary industry/sector
- Focus on facts, avoid speculation
- Use present tense for recent deals
"""

        return prompt

    def _parse_ai_response(self, response: str) -> Dict:
        """Parse OpenAI response and extract structured data"""

        try:
            # Try to parse as JSON
            if response.strip().startswith('{'):
                return json.loads(response)

            # If not JSON, extract manually
            logger.warning("AI response not in JSON format, parsing manually...")
            return self._manual_parse_response(response)

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, using manual parsing...")
            return self._manual_parse_response(response)

    def _manual_parse_response(self, response: str) -> Dict:
        """Manually parse non-JSON AI response"""

        lines = response.split('\n')

        # Default structure
        result = {
            'summary': '',
            'key_points': [],
            'companies': [],
            'sector': None
        }

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Identify sections
            if 'summary' in line.lower() and ':' in line:
                current_section = 'summary'
                result['summary'] = line.split(':', 1)[1].strip()
            elif 'key points' in line.lower() or 'points' in line.lower():
                current_section = 'key_points'
            elif 'companies' in line.lower():
                current_section = 'companies'
            elif 'sector' in line.lower():
                current_section = 'sector'
                if ':' in line:
                    result['sector'] = line.split(':', 1)[1].strip()

            # Add content to current section
            elif current_section == 'key_points' and (line.startswith('-') or line.startswith('•')):
                result['key_points'].append(line[1:].strip())
            elif current_section == 'companies' and (line.startswith('-') or line.startswith('•')):
                result['companies'].append(line[1:].strip())

        # Fallback summary if empty
        if not result['summary']:
            result['summary'] = f"Recent {result.get('sector', 'business')} deal with potential market impact."

        return result

    def _create_fallback_summary(self, deal: Deal) -> SummarizedDeal:
        """Create a fallback summary when AI summarization fails"""

        logger.info("Creating fallback summary...")

        # Basic summary based on deal type
        deal_type_summaries = {
            'VC': f"Venture capital funding round for growth and expansion.",
            'M&A': f"Merger and acquisition transaction to combine business operations.",
            'IPO': f"Initial public offering to raise capital through public markets.",
            'IB': f"Investment banking transaction for capital raising or advisory services."
        }

        fallback_summary = deal_type_summaries.get(deal.deal_type,
                                                   "Significant financial transaction with market implications.")

        # Add amount if available
        if deal.amount:
            fallback_summary = f"{deal.amount} {fallback_summary}"

        # Extract basic key points
        key_points = [
            f"Deal Type: {deal.deal_type}",
            f"Source: {deal.source}",
            f"Date: {deal.date}"
        ]

        if deal.amount:
            key_points.insert(1, f"Amount: {deal.amount}")

        return SummarizedDeal(
            title=deal.title,
            description=deal.description,
            ai_summary=fallback_summary,
            key_points=key_points,
            source=deal.source,
            url=deal.url,
            date=deal.date,
            deal_type=deal.deal_type,
            amount=deal.amount,
            priority_score=deal.priority_score,
            companies_involved=[],
            sector=None
        )

    def _handle_rate_limiting(self):
        """Handle OpenAI API rate limiting"""

        current_time = time.time()

        # Reset counter every minute
        if current_time - self.minute_start >= 60:
            self.request_count = 0
            self.minute_start = current_time

        # Check if we're at the limit
        if self.request_count >= self.requests_per_minute:
            sleep_time = 60 - (current_time - self.minute_start)
            if sleep_time > 0:
                logger.info(f"⏳ Rate limit reached, sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
                self.request_count = 0
                self.minute_start = time.time()

        # Add small delay between requests
        if current_time - self.last_request_time < 1.2:  # Min 1.2 seconds between requests
            time.sleep(1.2 - (current_time - self.last_request_time))

        self.request_count += 1
        self.last_request_time = time.time()

    def create_newsletter_content(self, summarized_deals: List[SummarizedDeal]) -> Dict[str, str]:
        """
        Create structured newsletter content from summarized deals

        Args:
            summarized_deals: List of SummarizedDeal objects

        Returns:
            Dictionary with newsletter sections
        """
        logger.info("📰 Creating newsletter content...")

        # Group deals by type
        deals_by_type = {}
        for deal in summarized_deals:
            if deal.deal_type not in deals_by_type:
                deals_by_type[deal.deal_type] = []
            deals_by_type[deal.deal_type].append(deal)

        # Create newsletter sections
        newsletter_content = {
            'headline': self._create_headline(summarized_deals),
            'executive_summary': self._create_executive_summary(summarized_deals),
            'deal_sections': {},
            'market_insights': self._create_market_insights(summarized_deals)
        }

        # Create sections for each deal type
        for deal_type, deals in deals_by_type.items():
            newsletter_content['deal_sections'][deal_type] = self._create_deal_section(deal_type, deals)

        logger.info("✅ Newsletter content created successfully")
        return newsletter_content

    def _create_headline(self, deals: List[SummarizedDeal]) -> str:
        """Create newsletter headline"""

        total_deals = len(deals)
        deal_types = list(set(deal.deal_type for deal in deals))

        if len(deal_types) == 1:
            return f"Top {total_deals} {deal_types[0]} Deals This Week"
        else:
            return f"Weekly Finance Roundup: {total_deals} Key Deals Across {', '.join(deal_types)}"

    def _create_executive_summary(self, deals: List[SummarizedDeal]) -> str:
        """Create executive summary"""

        total_deals = len(deals)
        deal_types = {}
        total_amount = 0

        for deal in deals:
            deal_types[deal.deal_type] = deal_types.get(deal.deal_type, 0) + 1

            # Try to extract numeric amount for total
            if deal.amount:
                try:
                    amount_str = deal.amount.replace('$', '').replace(',', '')
                    if 'billion' in amount_str.lower():
                        num = float(amount_str.split()[0])
                        total_amount += num * 1000  # Convert to millions
                    elif 'million' in amount_str.lower():
                        num = float(amount_str.split()[0])
                        total_amount += num
                except:
                    pass

        summary = f"This week we tracked {total_deals} significant deals across "
        summary += ", ".join([f"{count} {deal_type}" for deal_type, count in deal_types.items()])

        if total_amount > 0:
            if total_amount >= 1000:
                summary += f" with combined disclosed value exceeding ${total_amount / 1000:.1f} billion."
            else:
                summary += f" with combined disclosed value of ${total_amount:.0f} million."
        else:
            summary += "."

        return summary

    def _create_deal_section(self, deal_type: str, deals: List[SummarizedDeal]) -> List[Dict]:
        """Create formatted section for specific deal type"""

        section_deals = []

        for deal in deals:
            deal_info = {
                'title': deal.title,
                'summary': deal.ai_summary,
                'key_points': deal.key_points,
                'amount': deal.amount,
                'companies': deal.companies_involved or [],
                'sector': deal.sector,
                'source': deal.source,
                'url': deal.url,
                'date': deal.date
            }
            section_deals.append(deal_info)

        return section_deals

    def _create_market_insights(self, deals: List[SummarizedDeal]) -> str:
        """Create market insights section"""

        sectors = {}
        for deal in deals:
            if deal.sector:
                sectors[deal.sector] = sectors.get(deal.sector, 0) + 1

        if sectors:
            top_sector = max(sectors, key=sectors.get)
            insights = f"This week showed particularly strong activity in {top_sector} "
            insights += f"with {sectors[top_sector]} deals. "

            if len(sectors) > 1:
                other_sectors = [s for s in sectors.keys() if s != top_sector]
                insights += f"Other active sectors include {', '.join(other_sectors[:2])}."
        else:
            insights = "Deal activity remained diversified across multiple sectors this week."

        return insights


def main():
    """Test function for the summarizer"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    logger.info("🧪 Testing Deal Summarizer...")

    # Create sample deals for testing
    sample_deals = [
        Deal(
            title="TechCorp Raises $50M Series B Led by Venture Partners",
            description="TechCorp, a leading AI startup, announced a $50 million Series B funding round led by Venture Partners to accelerate product development and market expansion.",
            source="TechCrunch",
            url="https://example.com/deal1",
            date="2024-01-15",
            deal_type="VC",
            amount="$50 million"
        ),
        Deal(
            title="MegaCorp Acquires StartupCo for $2.3 Billion",
            description="MegaCorp announced the acquisition of StartupCo for $2.3 billion to strengthen its position in the cloud computing market.",
            source="Reuters",
            url="https://example.com/deal2",
            date="2024-01-14",
            deal_type="M&A",
            amount="$2.3 billion"
        )
    ]

    try:
        # Initialize summarizer (requires OPENAI_API_KEY environment variable)
        summarizer = DealSummarizer()

        # Summarize deals
        summarized_deals = summarizer.summarize_deals(sample_deals)

        # Create newsletter content
        newsletter_content = summarizer.create_newsletter_content(summarized_deals)

        logger.info("✅ Test completed successfully")
        logger.info(f"Newsletter headline: {newsletter_content['headline']}")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.info("Note: Make sure OPENAI_API_KEY environment variable is set")


if __name__ == "__main__":
    main()