#!/usr/bin/env python3
"""
ma_resend_sync.py - Sync subscribers between Supabase and Resend
Keeps both systems synchronized for optimal email delivery
"""

import os
import logging
import resend
from typing import List, Dict, Optional, Set
from dotenv import load_dotenv
from ma_db_supabase import get_all_subscribers, get_db

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseResendSync:
    """
    Synchronizes subscribers between Supabase and Resend audience
    """
    
    def __init__(self):
        """Initialize the sync service"""
        # Resend API setup
        self.resend_api_key = os.getenv('RESEND_API_KEY')
        self.audience_id = os.getenv('RESEND_AUDIENCE_ID', 'be4260f0-3872-4164-aa96-60e5aad08f0f')
        
        if not self.resend_api_key:
            raise ValueError("RESEND_API_KEY not found in environment variables")
        
        # Set resend API key
        resend.api_key = self.resend_api_key
        
        logger.info("✅ Supabase-Resend Sync initialized")
        logger.info(f"   Audience ID: {self.audience_id}")
    
    def get_resend_contacts(self) -> Set[str]:
        """Get all email addresses from Resend audience"""
        try:
            logger.info("📥 Fetching contacts from Resend audience...")
            
            # Use newer Resend SDK
            response = resend.Contacts.list(audience_id=self.audience_id)
            
            emails = set()
            if hasattr(response, 'data') and response.data:
                for contact in response.data:
                    if hasattr(contact, 'email'):
                        emails.add(contact.email.lower())
                    elif isinstance(contact, dict) and 'email' in contact:
                        emails.add(contact['email'].lower())
                
            logger.info(f"✅ Found {len(emails)} contacts in Resend audience")
            return emails
            
        except Exception as e:
            logger.error(f"❌ Error fetching Resend contacts: {e}")
            return set()
    
    def get_supabase_subscribers(self) -> Set[str]:
        """Get all email addresses from Supabase"""
        try:
            logger.info("📥 Fetching subscribers from Supabase...")
            subscribers = get_all_subscribers()
            emails = {email.lower() for email in subscribers}
            logger.info(f"✅ Found {len(emails)} subscribers in Supabase")
            return emails
        except Exception as e:
            logger.error(f"❌ Error fetching Supabase subscribers: {e}")
            return set()
    
    def add_contact_to_resend(self, email: str, first_name: str = "", last_name: str = "") -> bool:
        """Add a single contact to Resend audience using newer SDK"""
        try:
            logger.debug(f"Adding {email} to Resend audience...")
            
            # Use newer Resend API as shown by user
            params: resend.Contacts.CreateParams = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "unsubscribed": False,
                "audience_id": self.audience_id,
            }
            
            response = resend.Contacts.create(params)
            logger.debug(f"✅ Added {email} to Resend")
            return True
            
        except Exception as e:
            # Don't fail on duplicates - that's expected
            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                logger.debug(f"📝 {email} already exists in Resend (skipping)")
                return True
            else:
                logger.error(f"❌ Error adding {email} to Resend: {e}")
                return False
    
    def remove_contact_from_resend(self, email: str) -> bool:
        """Remove a contact from Resend audience"""
        try:
            logger.debug(f"Removing {email} from Resend audience...")
            
            # Get contact first, then remove by ID
            contact_response = resend.Contacts.get(email=email, audience_id=self.audience_id)
            
            if contact_response and hasattr(contact_response, 'id'):
                resend.Contacts.remove(id=contact_response.id, audience_id=self.audience_id)
                logger.debug(f"✅ Removed {email} from Resend")
                return True
            else:
                logger.debug(f"📝 {email} not found in Resend (already removed)")
                return True
                
        except Exception as e:
            if 'not found' in str(e).lower():
                logger.debug(f"📝 {email} not found in Resend (already removed)")
                return True
            else:
                logger.error(f"❌ Error removing {email} from Resend: {e}")
                return False
    
    def sync_supabase_to_resend(self) -> Dict[str, int]:
        """
        Sync subscribers from Supabase to Resend
        Returns dict with counts of operations performed
        """
        logger.info("🔄 Starting Supabase → Resend sync...")
        
        # Get current state
        supabase_emails = self.get_supabase_subscribers()
        resend_emails = self.get_resend_contacts()
        
        # Find differences
        to_add = supabase_emails - resend_emails  # In Supabase but not in Resend
        to_remove = resend_emails - supabase_emails  # In Resend but not in Supabase
        
        results = {
            'added': 0,
            'removed': 0,
            'errors': 0,
            'unchanged': len(supabase_emails & resend_emails)
        }
        
        logger.info(f"📊 Sync plan: +{len(to_add)} add, -{len(to_remove)} remove, ={results['unchanged']} unchanged")
        
        # Add missing contacts to Resend
        if to_add:
            logger.info(f"➕ Adding {len(to_add)} new contacts to Resend...")
            for email in to_add:
                if self.add_contact_to_resend(email):
                    results['added'] += 1
                else:
                    results['errors'] += 1
        
        # Remove contacts from Resend that aren't in Supabase
        if to_remove:
            logger.info(f"➖ Removing {len(to_remove)} contacts from Resend...")
            for email in to_remove:
                if self.remove_contact_from_resend(email):
                    results['removed'] += 1
                else:
                    results['errors'] += 1
        
        logger.info("✅ Sync complete!")
        logger.info(f"   Added: {results['added']}")
        logger.info(f"   Removed: {results['removed']}")
        logger.info(f"   Unchanged: {results['unchanged']}")
        if results['errors'] > 0:
            logger.warning(f"   Errors: {results['errors']}")
        
        return results
    
    def get_sync_status(self) -> Dict:
        """Get current sync status between Supabase and Resend"""
        supabase_emails = self.get_supabase_subscribers()
        resend_emails = self.get_resend_contacts()
        
        in_both = supabase_emails & resend_emails
        only_supabase = supabase_emails - resend_emails
        only_resend = resend_emails - supabase_emails
        
        status = {
            'supabase_count': len(supabase_emails),
            'resend_count': len(resend_emails),
            'in_sync_count': len(in_both),
            'only_in_supabase': len(only_supabase),
            'only_in_resend': len(only_resend),
            'sync_percentage': round((len(in_both) / max(len(supabase_emails), 1)) * 100, 1)
        }
        
        return status

def sync_subscribers():
    """Convenience function to sync subscribers"""
    try:
        sync_service = SupabaseResendSync()
        results = sync_service.sync_supabase_to_resend()
        return results
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        return None

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    try:
        # Test sync
        sync_service = SupabaseResendSync()
        
        # Show current status
        status = sync_service.get_sync_status()
        print("\n📊 Current Sync Status:")
        print(f"   Supabase subscribers: {status['supabase_count']}")
        print(f"   Resend contacts: {status['resend_count']}")  
        print(f"   In sync: {status['in_sync_count']}")
        print(f"   Only in Supabase: {status['only_in_supabase']}")
        print(f"   Only in Resend: {status['only_in_resend']}")
        print(f"   Sync percentage: {status['sync_percentage']}%")
        
        # Perform sync
        print("\n🔄 Performing sync...")
        results = sync_service.sync_supabase_to_resend()
        
        if results:
            print("✅ Sync completed successfully!")
        else:
            print("❌ Sync failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure to set these environment variables:")
        print("   RESEND_API_KEY=re_your_api_key")
        print("   RESEND_AUDIENCE_ID=your_audience_id (optional)")
        print("   Plus your Supabase credentials")