import asyncio
import os
from playwright.async_api import async_playwright
from typing import List, Optional

# Import UserCriteria from the new models.py
from .models import UserCriteria 
from .ai_module import AIModule
from .scraping_module.gumtree_scraper import GumtreeScraper
from .output_module import OutputModule
from .logging_module import setup_logging, get_logger

async def run_agent_with_criteria(criteria: UserCriteria):
    """
    Enhanced orchestration logic for the Gumtree agent with multi-page scraping support.
    """
    logger = get_logger("PropertyAgentOrchestrator")
    logger.info(f"Starting enhanced Gumtree agent with criteria: {criteria.model_dump()}")

    all_final_listings = []
    output_module = OutputModule("data")
    ai_module = AIModule()

    # Initialize Playwright with enhanced browser settings
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        )
        shared_context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
            accept_downloads=False,
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        )
        logger.info("Enhanced browser context initialized with anti-bot measures.")

        scraper_instance = None 
        try:
            logger.info("Initializing enhanced Gumtree scraper...")
            scraper_instance = GumtreeScraper(ai_module=ai_module, playwright_context=shared_context)
            
            # Configure multi-page settings
            scraper_instance.max_pages_to_scrape = 15  # Configurable max pages
            
            await scraper_instance.initialize_browser() 
            
            # Process location for expanded search if needed
            expanded_locations = await expand_location_to_postcodes(criteria.location, ai_module)
            logger.info(f"Expanded location '{criteria.location}' to {len(expanded_locations)} search locations: {expanded_locations}")
            
            all_site_listings = []
            
            # Search with each expanded location using enhanced multi-page scraping
            for location in expanded_locations:
                # Create a copy of criteria with the current location
                current_criteria = criteria.model_dump()
                current_criteria["location"] = location
                
                logger.info(f"Starting enhanced Gumtree search with location: {location}...")
                
                # Use the enhanced search_properties method with multi-page support
                site_listings = await scraper_instance.search_properties(current_criteria) 
                logger.info(f"Found {len(site_listings)} listings from Gumtree with location '{location}' (multi-page).")
                
                all_site_listings.extend(site_listings)
            
            logger.info(f"Total listings found across all expanded locations: {len(all_site_listings)}")
            all_final_listings.extend(all_site_listings)

        except Exception as e:
            logger.error(f"Error during enhanced Gumtree scraping: {e}", exc_info=True)
        finally:
            if scraper_instance:
                await scraper_instance.close() 
            logger.info("Finished with enhanced Gumtree scraper.")
        
        await shared_context.close()
        await browser.close()
        logger.info("Browser and context closed.")

    if all_final_listings:
        logger.info(f"Total listings found: {len(all_final_listings)}")
        # Enhanced deduplication based on URL
        unique_listings_by_url = {listing.get("url"): listing for listing in all_final_listings if listing.get("url")}.values()
        unique_listings = list(unique_listings_by_url)
        logger.info(f"Total unique listings after deduplication: {len(unique_listings)}")
        
        # Save with enhanced metadata
        timestamp = asyncio.get_event_loop().time()
        filename_base = f"gumtree_properties_enhanced_{int(timestamp)}"
        
        output_module.save_to_csv(unique_listings, f"{filename_base}.csv")
        output_module.save_to_json(unique_listings, f"{filename_base}.json")
        
        # Log summary statistics
        private_count = sum(1 for listing in unique_listings if listing.get("poster_type", "").lower() == "private")
        logger.info(f"Summary: {len(unique_listings)} total listings, {private_count} private listings")
        
    else:
        logger.warning("No listings found. This may indicate:")
        logger.warning("- Anti-bot protection is blocking requests")
        logger.warning("- Search criteria are too restrictive")
        logger.warning("- Network connectivity issues")
        logger.warning("- Gumtree website changes requiring selector updates")

    logger.info("Enhanced Gumtree agent run completed.")

async def expand_location_to_postcodes(location: str, ai_module: AIModule) -> List[str]:
    """
    Enhanced location expansion with better coverage and AI integration.
    
    Expands a general location into specific postcodes or areas for more comprehensive searching.
    """
    logger = get_logger("LocationExpander")
    
    # Enhanced dictionary of London areas and their postcode prefixes
    london_areas = {
        "north west london": ["NW1", "NW2", "NW3", "NW4", "NW5", "NW6", "NW7", "NW8", "NW9", "NW10", "NW11"],
        "north london": ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "N10", "N11", "N12", "N13", "N14", "N15", "N16", "N17", "N18", "N19", "N20", "N21", "N22"],
        "west london": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11", "W12", "W13", "W14"],
        "south west london": ["SW1", "SW2", "SW3", "SW4", "SW5", "SW6", "SW7", "SW8", "SW9", "SW10", "SW11", "SW12", "SW13", "SW14", "SW15", "SW16", "SW17", "SW18", "SW19", "SW20"],
        "south east london": ["SE1", "SE2", "SE3", "SE4", "SE5", "SE6", "SE7", "SE8", "SE9", "SE10", "SE11", "SE12", "SE13", "SE14", "SE15", "SE16", "SE17", "SE18", "SE19", "SE20", "SE21", "SE22", "SE23", "SE24", "SE25", "SE26", "SE27", "SE28"],
        "east london": ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12", "E13", "E14", "E15", "E16", "E17", "E18", "E20"],
        "central london": ["W1", "WC1", "WC2", "EC1", "EC2", "EC3", "EC4", "SW1"],
        # Add more specific areas
        "camden": ["NW1", "NW3", "NW5"],
        "islington": ["N1", "N5", "N7"],
        "hackney": ["E2", "E5", "E8", "E9"],
        "tower hamlets": ["E1", "E3", "E14"],
        "southwark": ["SE1", "SE15", "SE16", "SE17"],
        "lambeth": ["SE11", "SE24", "SW2", "SW4", "SW8", "SW9"],
        "wandsworth": ["SW11", "SW12", "SW15", "SW17", "SW18", "SW19"],
        "hammersmith": ["W6", "W12", "W14"],
        "kensington": ["W8", "W10", "W11", "SW3", "SW5", "SW7"],
        "westminster": ["W1", "SW1", "WC1", "WC2"]
    }
    
    # Check if the location is a specific postcode already
    location_lower = location.lower().strip()
    
    # If it's already a specific postcode or area, return it as is
    if any(location_lower.startswith(prefix.lower()) for area_postcodes in london_areas.values() for prefix in area_postcodes):
        logger.info(f"Location '{location}' appears to be a specific postcode or area already, using as is.")
        return [location]
    
    # Check if it's a known London area (exact match first, then partial)
    for area, postcodes in london_areas.items():
        if location_lower == area or area in location_lower or location_lower in area:
            logger.info(f"Expanded '{location}' to {len(postcodes)} postcodes: {postcodes}")
            return postcodes
    
    # Try AI-assisted expansion if available
    if ai_module:
        try:
            # This would be an enhancement to the AI module
            ai_expansion = getattr(ai_module, 'expand_location', None)
            if ai_expansion:
                expanded = ai_expansion(location)
                if expanded and len(expanded) > 1:
                    logger.info(f"AI expanded '{location}' to: {expanded}")
                    return expanded
        except Exception as e:
            logger.debug(f"AI expansion failed: {e}")
    
    # If we can't match it to a known area, return the original location
    logger.info(f"Could not expand '{location}' to specific postcodes, using as is.")
    return [location]

async def main_test_orchestrator():
    """Enhanced test orchestrator with better error handling and logging"""
    setup_logging()
    logger = get_logger("PropertyAgentMainTest")
    logger.info("Enhanced Gumtree Property Canvassing Agent - Main Orchestrator Test")
    
    # Mock criteria for testing main.py directly
    class MockTestUserCriteria(UserCriteria):
        location: str = "North West London"
        property_type: Optional[str] = "flat"
        price_min: Optional[int] = None
        price_max: Optional[int] = 2200
        bedrooms_min: Optional[int] = 1
        keywords: Optional[List[str]] = ["modern"]
        private_only: bool = True
        exclude_agents: bool = True

    test_criteria = MockTestUserCriteria()
    
    try:
        await run_agent_with_criteria(test_criteria)
        logger.info("Enhanced orchestrator test completed successfully.")
    except Exception as e:
        logger.error(f"Enhanced orchestrator test failed: {e}", exc_info=True)
    
    logger.info("For actual agent runs, use: python -m property_canvassing_agent.src.input_module --location \"North West London\" ...")

if __name__ == "__main__":
    # This allows main.py to be run directly for simple tests of the enhanced orchestrator logic.
    # The primary entry point for the user is input_module.py.
    asyncio.run(main_test_orchestrator())
