#!/usr/bin/env python3
"""
upload_to_resend.py - Upload Supabase contacts to Resend before sending newsletter
This script is called by GitHub Actions to sync subscribers before sending
"""

import logging
import sys
import os
from dotenv import load_dotenv
from ma_resend_sync import sync_subscribers

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Upload/sync Supabase contacts to Resend audience"""
    logger.info("🔄 Starting Supabase → Resend contact sync...")
    
    try:
        # Check required environment variables
        required_vars = ['RESEND_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            sys.exit(1)
        
        # Perform sync
        results = sync_subscribers()
        
        if results is None:
            logger.error("❌ Sync failed - check logs above")
            sys.exit(1)
        
        # Log results
        logger.info("📊 Sync Results:")
        logger.info(f"   Added: {results.get('added', 0)}")
        logger.info(f"   Removed: {results.get('removed', 0)}")
        logger.info(f"   Unchanged: {results.get('unchanged', 0)}")
        
        if results.get('errors', 0) > 0:
            logger.warning(f"   Errors: {results['errors']}")
        
        logger.info("✅ Contact sync completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error during sync: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
