#!/usr/bin/env python3
"""
Script to run the Telegram bot
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / '.env')

import database as db

async def init_data():
    """Initialize database"""
    await db.init_test_data()
    print("✅ Test data initialized")

if __name__ == "__main__":
    # Initialize test data first
    asyncio.run(init_data())
    
    # Now import and run bot (it has its own event loop)
    from bot import main
    main()
