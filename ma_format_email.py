"""
Creates the HTML emails for finance newsletters
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SummarizedDeal:
    """Deal data structure (matches deal_summarizer.py)"""
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


class HTMLEmailFormatter:
    def __init__(self, company_name: str = "Finance Insights",
                 company_logo_url: Optional[str] = None,
                 brand_color: str = "#1a365d"):
        """
        Initialize the HTML formatter

        Args:
            company_name: Name of my newsletter
            company_logo_url: URL to my logo (I probably won't make one lol)
            brand_color: Primary brand color (hex code)
        """
        logger.info("Initializing Email Formatter")

        self.company_name = company_name
        self.company_logo_url = company_logo_url
        self.brand_color = brand_color

        # Deal type styling
        self.deal_type_colors = {
            'VC': '#10b981',  # Green
            'M&A': '#3b82f6',  # Blue
            'IPO': '#8b5cf6',  # Purple
            'IB': '#f59e0b'  # Orange
        }

        self.deal_type_icons = {
            'VC': '🚀',
            'M&A': '🤝',
            'IPO': '📈',
            'IB': '🏦'
        }

        logger.info(" Email Formatter initialized")

    def create_newsletter_html(self, newsletter_content: Dict,
                               recipient_name: Optional[str] = None) -> str:
        """
        Create complete HTML newsletter email

        Args:
            newsletter_content: Dictionary from deal_summarizer.create_newsletter_content()
            recipient_name: Optional personalization name

        Returns:
            Complete HTML email string
        """
        logger.info("Creating newsletter email...")

        # Get current date for newsletter
        current_date = datetime.now().strftime("%B %d, %Y")

        # Build HTML email
        html_email = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{newsletter_content.get('headline', 'Finance Newsletter')}</title>
    <style>
        {self._get_email_styles()}
    </style>
</head>
<body>
    <div class="email-container">
        {self._create_header(current_date)}
        {self._create_greeting(recipient_name)}
        {self._create_executive_summary(newsletter_content)}
        {self._create_deals_sections(newsletter_content.get('deal_sections', {}))}
        {self._create_market_insights(newsletter_content)}
        {self._create_footer()}
    </div>
</body>
</html>
"""

        logger.info("Newsletter email created successfully")
        return html_email

    def _get_email_styles(self) -> str:
        """Get comprehensive CSS styles for the email"""

        return f"""
        /* Reset and base styles */
        body, table, td, p, a, li, blockquote {{
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333333;
            background-color: #f8fafc;
        }}

        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        /* Header styles */
        .header {{
            background: linear-gradient(135deg, {self.brand_color} 0%, #2d3748 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}

        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}

        .header .date {{
            margin-top: 8px;
            font-size: 14px;
            opacity: 0.9;
        }}

        .logo {{
            max-height: 40px;
            margin-bottom: 15px;
        }}

        /* Content styles */
        .content {{
            padding: 30px 20px;
        }}

        .greeting {{
            font-size: 16px;
            margin-bottom: 25px;
            color: #4a5568;
        }}

        .executive-summary {{
            background-color: #f7fafc;
            border-left: 4px solid {self.brand_color};
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 0 8px 8px 0;
        }}

        .executive-summary h2 {{
            margin: 0 0 15px 0;
            color: {self.brand_color};
            font-size: 20px;
            font-weight: 600;
        }}

        .executive-summary p {{
            margin: 0;
            font-size: 16px;
            line-height: 1.7;
        }}

        /* Deal sections */
        .deal-section {{
            margin-bottom: 35px;
        }}

        .deal-section-header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }}

        .deal-section-header h3 {{
            margin: 0;
            font-size: 22px;
            font-weight: 600;
            color: #2d3748;
        }}

        .deal-section-icon {{
            font-size: 24px;
            margin-right: 10px;
        }}

        /* Individual deal cards */
        .deal-card {{
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: box-shadow 0.3s ease;
        }}

        .deal-card:hover {{
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }}

        .deal-title {{
            font-size: 18px;
            font-weight: 600;
            color: #1a202c;
            margin: 0 0 12px 0;
            line-height: 1.4;
        }}

        .deal-title a {{
            color: #1a202c;
            text-decoration: none;
        }}

        .deal-title a:hover {{
            color: {self.brand_color};
        }}

        .deal-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 15px;
            font-size: 14px;
        }}

        .deal-tag {{
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .deal-tag.vc {{
            background-color: #d1fae5;
            color: #065f46;
        }}

        .deal-tag.ma {{
            background-color: #dbeafe;
            color: #1e40af;
        }}

        .deal-tag.ipo {{
            background-color: #ede9fe;
            color: #6b21a8;
        }}

        .deal-tag.ib {{
            background-color: #fef3c7;
            color: #92400e;
        }}

        .deal-amount {{
            font-weight: 700;
            color: #059669;
            font-size: 16px;
        }}

        .deal-source {{
            color: #6b7280;
            font-size: 13px;
        }}

        .deal-date {{
            color: #6b7280;
            font-size: 13px;
        }}

        .deal-summary {{
            margin: 15px 0;
            font-size: 15px;
            line-height: 1.6;
            color: #374151;
        }}

        .deal-points {{
            margin: 15px 0;
        }}

        .deal-points ul {{
            margin: 0;
            padding-left: 20px;
        }}

        .deal-points li {{
            margin-bottom: 8px;
            color: #4b5563;
            font-size: 14px;
        }}

        .companies-involved {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #f3f4f6;
        }}

        .companies-involved h5 {{
            margin: 0 0 8px 0;
            font-size: 13px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .companies-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .company-tag {{
            background-color: #f3f4f6;
            color: #374151;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
        }}

        /* Market insights */
        .market-insights {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin: 30px 0;
        }}

        .market-insights h3 {{
            margin: 0 0 15px 0;
            font-size: 20px;
            font-weight: 600;
        }}

        .market-insights p {{
            margin: 0;
            font-size: 16px;
            line-height: 1.6;
            opacity: 0.95;
        }}

        /* Footer */
        .footer {{
            background-color: #f8fafc;
            padding: 25px 20px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}

        .footer p {{
            margin: 0;
            font-size: 14px;
            color: #6b7280;
        }}

        .footer a {{
            color: {self.brand_color};
            text-decoration: none;
        }}

        .footer a:hover {{
            text-decoration: underline;
        }}

        /* Responsive design */
        @media only screen and (max-width: 600px) {{
            .email-container {{
                width: 100% !important;
                max-width: 100% !important;
            }}

            .content {{
                padding: 20px 15px !important;
            }}

            .header {{
                padding: 20px 15px !important;
            }}

            .header h1 {{
                font-size: 24px !important;
            }}

            .deal-card {{
                padding: 20px !important;
            }}

            .deal-meta {{
                flex-direction: column !important;
                gap: 8px !important;
            }}
        }}
        """

    def _create_header(self, current_date: str) -> str:
        """Create email header section"""

        logo_html = ""
        if self.company_logo_url:
            logo_html = f'<img src="{self.company_logo_url}" alt="{self.company_name}" class="logo">'

        return f"""
        <div class="header">
            {logo_html}
            <h1>{self.company_name} Finance Brief</h1>
            <div class="date">{current_date}</div>
        </div>
        """

    def _create_greeting(self, recipient_name: Optional[str]) -> str:
        """Create personalized greeting"""

        greeting = "Good morning"
        if recipient_name:
            greeting += f", {recipient_name}"

        return f"""
        <div class="content">
            <div class="greeting">
                {greeting}! Here's your weekly roundup of the most important deals in investment banking, venture capital, and M&A.
            </div>
        """

    def _create_executive_summary(self, newsletter_content: Dict) -> str:
        """Create executive summary section"""

        headline = newsletter_content.get('headline', 'Weekly Finance Update')
        summary = newsletter_content.get('executive_summary',
                                         'Key financial deals and market movements from this week.')

        return f"""
            <div class="executive-summary">
                <h2>{headline}</h2>
                <p>{summary}</p>
            </div>
        """

    def _create_deals_sections(self, deal_sections: Dict) -> str:
        """Create sections for each deal type"""

        sections_html = ""

        # Order sections by priority
        section_order = ['M&A', 'IPO', 'VC', 'IB']

        for deal_type in section_order:
            if deal_type in deal_sections:
                deals = deal_sections[deal_type]
                sections_html += self._create_single_deal_section(deal_type, deals)

        # Add any remaining sections not in the priority order
        for deal_type, deals in deal_sections.items():
            if deal_type not in section_order:
                sections_html += self._create_single_deal_section(deal_type, deals)

        return sections_html

    def _create_single_deal_section(self, deal_type: str, deals: List[Dict]) -> str:
        """Create HTML for a single deal type section"""

        icon = self.deal_type_icons.get(deal_type, '💼')

        # Section header
        section_html = f"""
            <div class="deal-section">
                <div class="deal-section-header">
                    <span class="deal-section-icon">{icon}</span>
                    <h3>{self._get_deal_type_name(deal_type)} ({len(deals)})</h3>
                </div>
        """

        # Individual deal cards
        for deal in deals:
            section_html += self._create_deal_card(deal, deal_type)

        section_html += "</div>"

        return section_html

    def _create_deal_card(self, deal: Dict, deal_type: str) -> str:
        """Create HTML for individual deal card"""

        # Deal title with link
        title_html = f'<h4 class="deal-title"><a href="{deal["url"]}" target="_blank">{deal["title"]}</a></h4>'

        # Deal metadata
        meta_items = []

        # Deal type tag
        tag_class = deal_type.lower().replace('&', '').replace('_', '')
        meta_items.append(f'<span class="deal-tag {tag_class}">{deal_type}</span>')

        # Amount
        if deal.get('amount'):
            meta_items.append(f'<span class="deal-amount">{deal["amount"]}</span>')

        # Source and date
        meta_items.append(f'<span class="deal-source">{deal["source"]}</span>')
        meta_items.append(f'<span class="deal-date">{deal["date"]}</span>')

        meta_html = f'<div class="deal-meta">{"".join(meta_items)}</div>'

        # AI summary
        summary_html = f'<div class="deal-summary">{deal["summary"]}</div>'

        # Key points
        points_html = ""
        if deal.get('key_points'):
            points_list = "".join([f"<li>{point}</li>" for point in deal['key_points']])
            points_html = f'<div class="deal-points"><ul>{points_list}</ul></div>'

        # Companies involved
        companies_html = ""
        if deal.get('companies') and len(deal['companies']) > 0:
            company_tags = "".join([f'<span class="company-tag">{company}</span>' for company in deal['companies']])
            companies_html = f"""
                <div class="companies-involved">
                    <h5>Companies Involved</h5>
                    <div class="companies-list">{company_tags}</div>
                </div>
            """

        return f"""
            <div class="deal-card">
                {title_html}
                {meta_html}
                {summary_html}
                {points_html}
                {companies_html}
            </div>
        """

    def _create_market_insights(self, newsletter_content: Dict) -> str:
        """Create market insights section"""

        insights = newsletter_content.get('market_insights',
                                          'Market activity continues to show strong momentum across sectors.')

        return f"""
            <div class="market-insights">
                <h3> Market Insights</h3>
                <p>{insights}</p>
            </div>
        """

    def _create_footer(self) -> str:
        """Create email footer"""

        return """
        </div>
        <div class="footer">
            <p>This newsletter was generated automatically from verified financial news sources.</p>
            <p>Questions? Reply to this email or contact our team.</p>
            <p><a href="#" target="_blank">Unsubscribe</a> | <a href="#" target="_blank">Update Preferences</a></p>
        </div>
        """

    def _get_deal_type_name(self, deal_type: str) -> str:
        """Get full name for deal type"""

        names = {
            'VC': 'Venture Capital',
            'M&A': 'Mergers & Acquisitions',
            'IPO': 'Initial Public Offerings',
            'IB': 'Investment Banking'
        }

        return names.get(deal_type, deal_type)

    def create_text_version(self, newsletter_content: Dict,
                            recipient_name: Optional[str] = None) -> str:
        """
        Create plain text version of the newsletter

        Args:
            newsletter_content: Dictionary from deal_summarizer.create_newsletter_content()
            recipient_name: Optional personalization name

        Returns:
            Plain text email string
        """
        logger.info("Creating plain text newsletter version...")

        current_date = datetime.now().strftime("%B %d, %Y")

        # Build text email
        text_lines = []
        text_lines.append(f"{self.company_name} Finance Brief - {current_date}")
        text_lines.append("=" * 60)
        text_lines.append("")

        # Greeting
        greeting = "Good morning"
        if recipient_name:
            greeting += f", {recipient_name}"
        text_lines.append(f"{greeting}!")
        text_lines.append("")

        # Executive summary
        headline = newsletter_content.get('headline', 'Weekly Finance Update')
        summary = newsletter_content.get('executive_summary', 'Key financial deals and market movements.')

        text_lines.append(f"EXECUTIVE SUMMARY: {headline}")
        text_lines.append("-" * 40)
        text_lines.append(summary)
        text_lines.append("")

        # Deal sections
        deal_sections = newsletter_content.get('deal_sections', {})
        for deal_type, deals in deal_sections.items():
            text_lines.append(f"{self._get_deal_type_name(deal_type).upper()} ({len(deals)} deals)")
            text_lines.append("-" * 40)

            for i, deal in enumerate(deals, 1):
                text_lines.append(f"{i}. {deal['title']}")
                if deal.get('amount'):
                    text_lines.append(f"   Amount: {deal['amount']}")
                text_lines.append(f"   Summary: {deal['summary']}")
                text_lines.append(f"   Source: {deal['source']} | Date: {deal['date']}")
                text_lines.append(f"   Link: {deal['url']}")
                text_lines.append("")

        # Market insights
        insights = newsletter_content.get('market_insights', '')
        if insights:
            text_lines.append("MARKET INSIGHTS")
            text_lines.append("-" * 40)
            text_lines.append(insights)
            text_lines.append("")

        # Footer
        text_lines.append("=" * 60)
        text_lines.append("This newsletter was generated automatically from verified financial news sources.")
        text_lines.append("Questions? Reply to this email or contact our team.")

        logger.info("Plain text newsletter created successfully")
        return "\n".join(text_lines)


def main():
    """Test function for the HTML formatter"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    logger.info("🧪 Testing HTML Email Formatter...")

    # Sample newsletter content
    sample_content = {
        'headline': 'Weekly Finance Roundup: 5 Key Deals Across VC, M&A',
        'executive_summary': 'This week we tracked 5 significant deals across 2 VC, 2 M&A, 1 IPO with combined disclosed value exceeding $3.2 billion.',
        'deal_sections': {
            'VC': [
                {
                    'title': 'TechCorp Raises $50M Series B Led by Venture Partners',
                    'summary': 'TechCorp secured $50 million in Series B funding to accelerate AI product development and international expansion.',
                    'key_points': ['Series B round led by Venture Partners', 'Funding for AI product development',
                                   'International expansion plans'],
                    'amount': '$50 million',
                    'companies': ['TechCorp', 'Venture Partners'],
                    'sector': 'Artificial Intelligence',
                    'source': 'TechCrunch',
                    'url': 'https://example.com/deal1',
                    'date': '2024-01-15'
                }
            ],
            'M&A': [
                {
                    'title': 'MegaCorp Acquires StartupCo for $2.3 Billion',
                    'summary': 'MegaCorp announced acquisition of StartupCo for $2.3 billion to strengthen cloud computing capabilities.',
                    'key_points': ['Strategic acquisition for cloud computing', '$2.3 billion transaction value',
                                   'Strengthens market position'],
                    'amount': '$2.3 billion',
                    'companies': ['MegaCorp', 'StartupCo'],
                    'sector': 'Cloud Computing',
                    'source': 'Reuters',
                    'url': 'https://example.com/deal2',
                    'date': '2024-01-14'
                }
            ]
        },
        'market_insights': 'This week showed particularly strong activity in Technology with 3 deals. Deal flow remains robust across all sectors.'
    }

    # Test HTML formatter
    formatter = HTMLEmailFormatter(
        company_name="Finance Insights Pro",
        brand_color="#1a365d"
    )

    html_email = formatter.create_newsletter_html(sample_content, "John Doe")
    text_email = formatter.create_text_version(sample_content, "John Doe")

    logger.info("Test completed successfully")
    logger.info(f"HTML email length: {len(html_email)} characters")
    logger.info(f"Text email length: {len(text_email)} characters")

    # Optionally save to files for testing
    with open("test_newsletter.html", "w") as f:
        f.write(html_email)

    with open("test_newsletter.txt", "w") as f:
        f.write(text_email)

    logger.info("Test files saved: test_newsletter.html and test_newsletter.txt")


if __name__ == "__main__":
    main()