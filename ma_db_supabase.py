#!/usr/bin/env python3
"""
ma_db_supabase.py - Supabase Database Integration for M&A Newsletter
Replaces SQLite with Supabase for subscriber management
"""

import os
import logging
from datetime import datetime
from typing import List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class MASupabaseDB:
    """
    M&A Newsletter Supabase Database Manager
    Handles all subscriber operations via Supabase
    """
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Use service role for server operations
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables."
            )
        
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("✅ Connected to Supabase database")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {e}")
            raise
    
    def init_db(self):
        """
        Initialize the Supabase database table
        Note: Run this SQL in Supabase Dashboard > SQL Editor:
        
        CREATE TABLE IF NOT EXISTS ma_subscribers (
            id BIGSERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            verified BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Enable Row Level Security
        ALTER TABLE ma_subscribers ENABLE ROW LEVEL SECURITY;
        
        -- Create policies for service role access
        CREATE POLICY "Service role can do anything" ON ma_subscribers
            FOR ALL USING (auth.role() = 'service_role');
        """
        logger.info("⚠️  Initialize the database table in Supabase Dashboard:")
        logger.info("   Go to Supabase Dashboard > SQL Editor and run:")
        logger.info("""
        CREATE TABLE IF NOT EXISTS ma_subscribers (
            id BIGSERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            verified BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        ALTER TABLE ma_subscribers ENABLE ROW LEVEL SECURITY;
        CREATE POLICY "Service role can do anything" ON ma_subscribers
            FOR ALL USING (auth.role() = 'service_role');
        """)
    
    def get_all_subscribers(self) -> List[str]:
        """
        Get all active subscribers (not unsubscribed)
        
        Returns:
            List of subscriber email addresses
        """
        try:
            response = self.supabase.table('ma_subscribers').select('email').eq('unsubscribed', False).execute()
            
            emails = [row['email'] for row in response.data]
            logger.info(f"📧 Retrieved {len(emails)} active subscribers")
            return emails
            
        except Exception as e:
            logger.error(f"❌ Error fetching subscribers: {e}")
            return []
    
    def add_subscriber(self, email: str) -> bool:
        """
        Add a new subscriber (for testing purposes)
        Note: In production, subscribers are added via Portfolio repo
        
        Args:
            email: Subscriber email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase.table('ma_subscribers').insert({
                'email': email.lower().strip(),
                'date_joined': datetime.now().isoformat(),
                'verified': True
            }).execute()
            
            logger.info(f"✅ Added subscriber: {email}")
            return True
            
        except Exception as e:
            if 'duplicate key' in str(e).lower():
                logger.warning(f"⚠️  {email} is already subscribed")
            else:
                logger.error(f"❌ Error adding subscriber {email}: {e}")
            return False
    
    def remove_subscriber(self, email: str) -> bool:
        """
        Remove a subscriber
        
        Args:
            email: Subscriber email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase.table('ma_subscribers').delete().eq('email', email.lower().strip()).execute()
            
            logger.info(f"🗑️  Removed subscriber: {email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing subscriber {email}: {e}")
            return False
    
    def get_subscriber_count(self) -> int:
        """
        Get total count of active subscribers (not unsubscribed)
        
        Returns:
            Number of active subscribers
        """
        try:
            response = self.supabase.table('ma_subscribers').select('id', count='exact').eq('unsubscribed', False).execute()
            count = response.count or 0
            logger.info(f"📊 Total active subscribers: {count}")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error getting subscriber count: {e}")
            return 0
    
    def test_connection(self) -> bool:
        """
        Test the Supabase connection
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            # Try to query the table
            response = self.supabase.table('ma_subscribers').select('id').limit(1).execute()
            logger.info("✅ Supabase connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Supabase connection test failed: {e}")
            return False

# Convenience functions for backward compatibility
_db_instance = None

def get_db() -> MASupabaseDB:
    """Get the database instance (singleton)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = MASupabaseDB()
    return _db_instance

def init_db():
    """Initialize database"""
    db = get_db()
    db.init_db()

def add_subscriber(email: str) -> bool:
    """Add subscriber"""
    db = get_db()
    return db.add_subscriber(email)

def get_all_subscribers() -> List[str]:
    """Get all subscribers"""
    db = get_db()
    return db.get_all_subscribers()

def remove_subscriber(email: str) -> bool:
    """Remove subscriber"""
    db = get_db()
    return db.remove_subscriber(email)

def get_subscriber_count() -> int:
    """Get subscriber count"""
    db = get_db()
    return db.get_subscriber_count()

if __name__ == "__main__":
    # Test the connection
    logging.basicConfig(level=logging.INFO)
    
    try:
        db = MASupabaseDB()
        
        # Test connection
        if db.test_connection():
            print("🎉 Supabase integration working!")
            
            # Show current stats
            count = db.get_subscriber_count()
            print(f"📊 Current subscribers: {count}")
            
            # Get sample of subscribers (for testing)
            subscribers = db.get_all_subscribers()
            if subscribers:
                print(f"📧 Sample subscribers: {subscribers[:3]}...")
            else:
                print("📧 No subscribers found")
        else:
            print("❌ Supabase connection failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure to set these environment variables:")
        print("   SUPABASE_URL=https://your-project-ref.supabase.co")
        print("   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key")