#!/usr/bin/env python3
"""
resend_email_sender.py - Resend API Integration
Handles sending professional HTML emails via Resend API
"""

import os
import logging
import requests
import json
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import time

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class EmailRecipient:
    """Email recipient data structure"""
    email: str
    name: Optional[str] = None


@dataclass
class EmailAttachment:
    """Email attachment data structure"""
    filename: str
    content: bytes
    content_type: str


@dataclass
class EmailResult:
    """Result of email sending operation"""
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    recipient_email: Optional[str] = None


class ResendEmailSender:
    """Professional email sender using Resend API"""

    def __init__(self, api_key: Optional[str] = None,
                 sender_email: Optional[str] = None,
                 sender_name: Optional[str] = None):
        """
        Initialize Resend email sender

        Args:
            api_key: Resend API key (if not provided, uses RESEND_API_KEY env var)
            sender_email: Sender email address (uses SENDER_EMAIL env var if not provided)
            sender_name: Sender name (uses SENDER_NAME env var if not provided)
        """
        logger.info("📧 Initializing Resend Email Sender...")

        # API Configuration
        self.api_key = api_key or os.getenv('RESEND_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Resend API key not provided. Set RESEND_API_KEY environment variable or pass api_key parameter.")

        # Sender Configuration
        self.sender_email = sender_email or os.getenv('SENDER_EMAIL')
        if not self.sender_email:
            raise ValueError(
                "Sender email not provided. Set SENDER_EMAIL environment variable or pass sender_email parameter.")

        self.sender_name = sender_name or os.getenv('SENDER_NAME', 'Finance Newsletter')

        # API Configuration
        self.base_url = "https://api.resend.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Rate limiting (Resend limits)
        self.rate_limit_per_second = 2  # Conservative rate limiting
        self.last_request_time = 0

        # Email settings
        self.default_reply_to = os.getenv('REPLY_TO_EMAIL', self.sender_email)

        logger.info(f"✅ Resend Email Sender initialized")
        logger.info(f"   Sender: {self.sender_name} <{self.sender_email}>")

    def send_newsletter(self,
                        recipients: List[Union[str, EmailRecipient]],
                        subject: str,
                        html_content: str,
                        text_content: Optional[str] = None,
                        attachments: Optional[List[EmailAttachment]] = None,
                        batch_size: int = 50) -> List[EmailResult]:
        """
        Send newsletter to multiple recipients

        Args:
            recipients: List of email addresses or EmailRecipient objects
            subject: Email subject line
            html_content: HTML email content
            text_content: Plain text email content (optional)
            attachments: List of email attachments (optional)
            batch_size: Number of emails to send per batch

        Returns:
            List of EmailResult objects with sending results
        """
        logger.info(f"📬 Starting newsletter send to {len(recipients)} recipients...")

        # Convert recipients to EmailRecipient objects
        recipient_objects = self._normalize_recipients(recipients)

        # Send in batches
        all_results = []
        total_batches = (len(recipient_objects) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(recipient_objects))
            batch_recipients = recipient_objects[start_idx:end_idx]

            logger.info(f"📤 Sending batch {batch_num + 1}/{total_batches} ({len(batch_recipients)} recipients)...")

            batch_results = self._send_batch(
                recipients=batch_recipients,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                attachments=attachments
            )

            all_results.extend(batch_results)

        return all_results

    def _normalize_recipients(self, recipients):
        """Convert recipients to EmailRecipient objects"""
        normalized = []
        for recipient in recipients:
            if isinstance(recipient, str):
                normalized.append(EmailRecipient(email=recipient))
            elif isinstance(recipient, EmailRecipient):
                normalized.append(recipient)
            else:
                # Assume it's a dict or object with email attribute
                email = getattr(recipient, 'email', str(recipient))
                normalized.append(EmailRecipient(email=email))
        return normalized

    def _send_batch(self, recipients, subject, html_content, text_content=None, attachments=None):
        """Send email to a batch of recipients using Resend API"""
        results = []
        
        for recipient in recipients:
            try:
                import requests
                
                payload = {
                    "from": f"{self.sender_name} <{self.sender_email}>",
                    "to": [recipient.email],
                    "subject": subject,
                    "html": html_content,
                }
                
                if text_content:
                    payload["text"] = text_content
                    
                response = requests.post(
                    "https://api.resend.com/emails",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    results.append(EmailResult(
                        success=True,
                        message_id=result_data.get("id"),
                        recipient_email=recipient.email
                    ))
                else:
                    results.append(EmailResult(
                        success=False,
                        error_message=f"HTTP {response.status_code}: {response.text}",
                        recipient_email=recipient.email
                    ))
                    
                # Rate limiting
                import time
                time.sleep(0.5)
                
            except Exception as e:
                results.append(EmailResult(
                    success=False,
                    error_message=str(e),
                    recipient_email=recipient.email
                ))
        
        return results