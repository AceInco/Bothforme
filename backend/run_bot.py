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
from bot import main, Application, BOT_TOKEN, Update
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init(application):
    """Initialize test data after bot starts"""
    await db.init_test_data()
    logger.info("✅ Test data initialized")

if __name__ == "__main__":
    # Create new event loop
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    # Run bot
    main()
