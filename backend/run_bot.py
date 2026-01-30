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

async def init_and_run():
    """Initialize database and run bot"""
    # Initialize test data
    await db.init_test_data()
    print("✅ Test data initialized")
    
    # Import and run bot
    from bot import main
    main()

if __name__ == "__main__":
    asyncio.run(init_and_run())
