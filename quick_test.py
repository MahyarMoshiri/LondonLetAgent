#!/usr/bin/env python3
"""
Quick test script for the Enhanced Property Canvassing Agent
Tests the enhanced multi-page Gumtree scraper with a simple search
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import run_agent_with_criteria
from src.models import UserCriteria
from src.logging_module import setup_logging, get_logger

async def test_enhanced_scraper():
    """Test the enhanced scraper with a simple search"""
    
    # Setup logging
    setup_logging()
    logger = get_logger("QuickTest")
    
    logger.info("🚀 Enhanced Property Canvassing Agent - Quick Test")
    logger.info("=" * 60)
    
    # Create test criteria
    test_criteria = UserCriteria(
        location="NW1",  # Single postcode for quick test
        property_type="flat",
        price_max=2500,
        bedrooms_min=1,
        private_only=True,
        exclude_agents=True
    )
    
    logger.info(f"Test criteria: {test_criteria.dict()}")
    logger.info("Starting enhanced multi-page search...")
    logger.info("Expected: 20-50 listings from multiple pages")
    
    try:
        # Run the enhanced search
        await run_agent_with_criteria(test_criteria)
        
        # Check results
        data_dir = Path("data")
        if data_dir.exists():
            csv_files = list(data_dir.glob("*.csv"))
            json_files = list(data_dir.glob("*.json"))
            
            if csv_files:
                logger.info(f"✅ SUCCESS! Results saved to:")
                for file in csv_files:
                    logger.info(f"   📄 {file}")
                for file in json_files:
                    logger.info(f"   📄 {file}")
                    
                # Quick analysis
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_files[0])
                    total_listings = len(df)
                    private_listings = len(df[df['poster_type'] == 'Private'])
                    
                    logger.info(f"📊 Results Summary:")
                    logger.info(f"   Total listings: {total_listings}")
                    logger.info(f"   Private listings: {private_listings}")
                    logger.info(f"   Success rate: {'✅ EXCELLENT' if total_listings > 20 else '⚠️ LOW'}")
                    
                except Exception as e:
                    logger.warning(f"Could not analyze results: {e}")
            else:
                logger.warning("⚠️ No result files found. Check logs for errors.")
        else:
            logger.warning("⚠️ Data directory not found. Check logs for errors.")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error("Check the troubleshooting guide in docs/TROUBLESHOOTING.md")
        return False
    
    logger.info("=" * 60)
    logger.info("🎉 Quick test completed!")
    logger.info("For full searches, use: python -m src.input_module --location 'North West London' --max_price 2000 --private_only")
    
    return True

if __name__ == "__main__":
    print("Enhanced Property Canvassing Agent - Quick Test")
    print("=" * 50)
    print("This will test the enhanced multi-page scraper with NW1 postcode")
    print("Expected runtime: 2-5 minutes")
    print("Expected results: 20-50 listings")
    print()
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Run the test
    success = asyncio.run(test_enhanced_scraper())
    
    if success:
        print("\n✅ Test completed successfully!")
        print("Check the data/ directory for results.")
    else:
        print("\n❌ Test failed. Check logs for details.")
        sys.exit(1)

