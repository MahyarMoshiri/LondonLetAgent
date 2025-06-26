#!/usr/bin/env python3
"""
Enhanced Gumtree scraper with multi-page support integrated into the property canvassing agent
"""

import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, BrowserContext
import urllib.parse
import re
import logging
import random
import json
import os

from .base_scraper import BaseScraper

class GumtreeScraper(BaseScraper):
    """
    Enhanced Gumtree scraper with multi-page support and anti-bot measures
    Maintains compatibility with the existing property canvassing agent architecture
    """

    def __init__(self, ai_module: Any, playwright_context: BrowserContext):
        super().__init__(site_name="Gumtree", ai_module=ai_module)
        self.context = playwright_context
        self.browser_page: Optional[Page] = None
        self.private_only_requested = False
        self.logger = logging.getLogger("GumtreeScraper")
        self.max_pages_to_scrape = 15  # Default max pages for production use
        
        # Override the base class configuration loading with enhanced fallbacks
        self._load_enhanced_configurations()

    def _load_enhanced_configurations(self):
        """Load site profile and selectors with enhanced fallback defaults"""
        try:
            # Try to load from configs directory
            config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'configs')
            
            # Load site profile
            site_profile_path = os.path.join(config_dir, 'site_profiles', 'gumtree_profile.json')
            if os.path.exists(site_profile_path):
                with open(site_profile_path, 'r') as f:
                    self.site_profile = json.load(f)
            else:
                self.site_profile = self._get_default_site_profile()
            
            # Load selectors
            selectors_path = os.path.join(config_dir, 'selectors', 'gumtree_selectors.json')
            if os.path.exists(selectors_path):
                with open(selectors_path, 'r') as f:
                    self.selectors = json.load(f)
            else:
                self.selectors = self._get_default_selectors()
                
            self.logger.info("Enhanced configuration loaded successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to load configuration files: {e}. Using enhanced defaults.")
            self.site_profile = self._get_default_site_profile()
            self.selectors = self._get_default_selectors()

    def _get_default_site_profile(self):
        """Enhanced default site profile configuration"""
        return {
            "base_search_url": "https://www.gumtree.com/search",
            "seller_type_options": {"private_only": "private"},
            "query_parameters": {
                "search_category_key": "search_category",
                "search_category_value": "property-to-rent"
            }
        }

    def _get_default_selectors(self):
        """Enhanced default selectors configuration"""
        return {
            "listing_item_container": 'article[data-q="search-result"]',
            "listing_details_link": 'a[data-q="search-result-anchor"]',
            "listing_title": 'div[data-q="tile-title"]',
            "listing_description_spans": 'div[data-q="tile-description"] span',
            "listing_location": 'div[data-q="tile-location"]',
            "listing_price": 'div[data-testid="price"]',
            "listing_posted_date": 'div[data-q="tile-datePosted"]'
        }

    async def initialize_browser(self, playwright_context=None):
        """Initialize browser page with anti-bot measures"""
        # Use provided context or the one from constructor
        context = playwright_context or self.context
        
        if not context:
            self.logger.error("Error: Playwright BrowserContext not provided.")
            raise ValueError("BrowserContext must be provided to GumtreeScraper.")
        
        try:
            self.browser_page = await context.new_page()
            
            # Set enhanced headers for anti-bot protection
            await self.browser_page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Upgrade-Insecure-Requests': '1'
            })
            
            self.logger.info("Browser page created with enhanced anti-bot measures.")
        except Exception as e:
            self.logger.error(f"Error creating browser page: {e}")
            self.browser_page = None

    async def _construct_search_url(self, query_params: Dict[str, Any], page_number: int = 1) -> str:
        """Construct search URL with page parameter for multi-page scraping"""
        if not self.site_profile or not self.site_profile.get("base_search_url"):
            self.logger.error("Cannot construct URL: site profile or base_search_url not loaded.")
            return "about:blank"

        self.private_only_requested = query_params.get("private_only", False)
        base_url = self.site_profile["base_search_url"]
        
        params_to_encode = {
            "search_category": "property-to-rent",
            "distance": "3"
        }

        if query_params.get("location"):
            params_to_encode["search_location"] = query_params["location"]
        
        if query_params.get("price_max") is not None:
            params_to_encode["max_price"] = query_params["price_max"]
        
        if query_params.get("price_min") is not None:
            params_to_encode["min_price"] = query_params["price_min"]

        # Fixed seller type filter - this was the original bug
        if query_params.get("private_only"):
            seller_options = self.site_profile.get("seller_type_options", {})
            private_value = seller_options.get("private_only", "private")
            params_to_encode["seller_type"] = private_value
            self.logger.debug(f"Setting seller type filter to private: seller_type={private_value}")
        elif query_params.get("seller_type"):
            params_to_encode["seller_type"] = query_params["seller_type"]
        
        # Add page parameter for pagination
        if page_number > 1:
            params_to_encode["page"] = page_number
        
        final_params = {k: v for k, v in params_to_encode.items() if v is not None and v != ""}
        search_url = f"{base_url}?{urllib.parse.urlencode(final_params)}"
        
        return search_url

    async def _parse_initial_listings(self, page_content: str) -> List[Dict[str, Any]]:
        """Parse listings from current page using the existing data structure"""
        if not self.browser_page or not self.selectors:
            return []
        
        listings = []
        listing_container_selector = self.selectors.get("listing_item_container")
        
        try:
            listing_elements = await self.browser_page.query_selector_all(listing_container_selector)
            self.logger.debug(f"Found {len(listing_elements)} potential listing elements")

            for i, article_element in enumerate(listing_elements):
                try:
                    listing_data = {}
                    
                    # Property Link (essential)
                    link_element = await article_element.query_selector(self.selectors.get("listing_details_link"))
                    if not link_element:
                        continue
                    
                    href = await link_element.get_attribute("href")
                    if not href:
                        continue
                    
                    listing_data["url"] = f"https://www.gumtree.com{href}" if not href.startswith("http") else href
                    
                    # Title
                    title_element = await article_element.query_selector(self.selectors.get("listing_title"))
                    listing_data["title"] = (await title_element.text_content() or "").strip() if title_element else None
                    
                    # Description spans (poster type, date available, property type, beds)
                    desc_span_elements = await article_element.query_selector_all(self.selectors.get("listing_description_spans"))
                    
                    poster_type = (await desc_span_elements[0].text_content() or "").strip() if len(desc_span_elements) > 0 else None
                    listing_data["poster_type"] = poster_type
                    listing_data["advertiser_type_snippet"] = poster_type
                    listing_data["source_site"] = "Gumtree"
                    
                    # Parse date available
                    if len(desc_span_elements) > 1:
                        raw_date_available = (await desc_span_elements[1].text_content() or "").strip()
                        listing_data["date_available"] = raw_date_available.replace("Date available:", "").strip()
                    else:
                        listing_data["date_available"] = None
                    
                    listing_data["property_type"] = (await desc_span_elements[2].text_content() or "").strip() if len(desc_span_elements) > 2 else None
                    listing_data["beds"] = (await desc_span_elements[3].text_content() or "").strip() if len(desc_span_elements) > 3 else None
                    
                    # Location
                    location_element = await article_element.query_selector(self.selectors.get("listing_location"))
                    listing_data["location"] = (await location_element.text_content() or "").strip() if location_element else None
                    
                    # Price with normalization
                    price_element = await article_element.query_selector(self.selectors.get("listing_price"))
                    if price_element:
                        price_text = (await price_element.text_content() or "").strip()
                        listing_data["price"] = price_text
                        
                        # Add price normalization for compatibility
                        normalized_price = self._normalize_price(price_text)
                        listing_data["normalized_price"] = normalized_price.get("monthly_price")
                        listing_data["price_period"] = normalized_price.get("period")
                        listing_data["price_value"] = normalized_price.get("value")
                    else:
                        listing_data["price"] = None
                        listing_data["normalized_price"] = None
                        listing_data["price_period"] = None
                        listing_data["price_value"] = None
                    
                    # Date Posted
                    date_posted_element = await article_element.query_selector(self.selectors.get("listing_posted_date"))
                    listing_data["date_posted"] = (await date_posted_element.text_content() or "").strip() if date_posted_element else None
                    
                    # Apply filtering
                    should_include = True
                    
                    # Filter by private_only
                    if self.private_only_requested:
                        if not (poster_type and poster_type.lower() == "private"):
                            should_include = False
                            self.logger.debug(f"Skipping non-private listing: {listing_data.get('url')} (poster_type: '{poster_type}')")
                    
                    # Filter by price_max (post-processing filter to ensure Gumtree's filtering worked)
                    if should_include and hasattr(self, 'current_price_max') and self.current_price_max:
                        normalized_price = listing_data.get("normalized_price")
                        if normalized_price and normalized_price > self.current_price_max:
                            should_include = False
                            self.logger.debug(f"Skipping over-priced listing: {listing_data.get('url')} (£{normalized_price} > £{self.current_price_max})")
                    
                    if should_include:
                        listings.append(listing_data)
                        
                except Exception as e:
                    self.logger.debug(f"Error parsing listing {i+1}: {e}")
                    continue
            
            return listings
            
        except Exception as e:
            self.logger.error(f"Error parsing listings from page: {e}")
            return []

    async def _check_search_outcome(self, page_content_or_response: Any) -> Dict[str, Any]:
        """Analyze the page to determine search outcome"""
        try:
            # Check if we have listings
            listing_elements = await self.browser_page.query_selector_all(self.selectors.get("listing_item_container"))
            
            if len(listing_elements) > 0:
                return {"status": "listings_found", "count": len(listing_elements)}
            
            # Check for common error indicators
            page_text = await self.browser_page.text_content('body')
            
            if any(term in page_text.lower() for term in ['captcha', 'blocked', 'access denied']):
                return {"status": "blocked", "details": "Anti-bot protection detected"}
            
            if any(term in page_text.lower() for term in ['no results', 'no ads found', '0 ads']):
                return {"status": "zero_results", "details": "No listings found for current criteria"}
            
            return {"status": "unknown", "details": "Could not determine search outcome"}
            
        except Exception as e:
            return {"status": "error", "details": str(e)}

    async def _handle_site_obstacles(self):
        """Handle common site obstacles like cookie banners"""
        if not self.browser_page:
            return
        
        try:
            # Wait for page to stabilize
            await asyncio.sleep(random.uniform(2, 4))
            
            # Check for and handle cookie banners
            cookie_selectors = [
                'button[data-testid="cookie-accept"]',
                'button[id*="cookie"]',
                'button[class*="cookie"]',
                '.cookie-banner button',
                '#cookie-banner button'
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_button = await self.browser_page.query_selector(selector)
                    if cookie_button:
                        await cookie_button.click()
                        await asyncio.sleep(1)
                        self.logger.debug("Accepted cookies")
                        break
                except:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error handling site obstacles: {e}")

    def _normalize_price(self, price_text: str) -> Dict[str, Any]:
        """Normalize price to monthly equivalent"""
        if not price_text:
            return {"monthly_price": None, "period": None, "value": None}
        
        # Extract numeric value
        price_match = re.search(r'£(\d+(?:,\d+)?)', price_text.replace(',', ''))
        if not price_match:
            return {"monthly_price": None, "period": None, "value": None}
        
        value = int(price_match.group(1).replace(',', ''))
        
        # Determine period and convert to monthly
        if 'pw' in price_text.lower() or 'week' in price_text.lower():
            monthly_price = value * 52 / 12  # Convert weekly to monthly
            period = "weekly"
        elif 'pm' in price_text.lower() or 'month' in price_text.lower():
            monthly_price = value
            period = "monthly"
        else:
            monthly_price = value  # Assume monthly if unclear
            period = "monthly"
        
        return {
            "monthly_price": round(monthly_price),
            "period": period,
            "value": value
        }

    async def _detect_total_pages(self, first_page_url: str) -> int:
        """Detect total pages from pagination"""
        try:
            await self.browser_page.goto(first_page_url, wait_until="networkidle", timeout=30000)
            await self._handle_site_obstacles()
            
            # Look for pagination indicators
            page_links = await self.browser_page.query_selector_all('a[href*="page="]')
            max_page = 1
            
            for link in page_links:
                href = await link.get_attribute("href")
                if href:
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        max_page = max(max_page, page_num)
            
            # Also check numbered links
            numbered_links = await self.browser_page.query_selector_all('a')
            for link in numbered_links:
                text = await link.text_content()
                if text and text.strip().isdigit():
                    page_num = int(text.strip())
                    if 1 <= page_num <= 50:  # Reasonable bounds
                        max_page = max(max_page, page_num)
            
            total_pages = min(max_page, self.max_pages_to_scrape)
            self.logger.info(f"Detected {max_page} total pages, will scrape {total_pages}")
            return total_pages
            
        except Exception as e:
            self.logger.error(f"Error detecting total pages: {e}")
            return 1

    async def search_properties(self, user_criteria: Dict[str, Any], max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Enhanced search method with multi-page support
        Overrides the base class method to add multi-page functionality
        """
        self.logger.info(f"🚀 Enhanced search_properties called with criteria: {user_criteria}")
        
        if not self.browser_page:
            self.logger.info("Browser page not initialized, initializing now...")
            await self.initialize_browser()
            if not self.browser_page:
                self.logger.error("Failed to initialize browser.")
                return []
            self.logger.info("✅ Browser page initialized successfully")

        # Use AI module to transform criteria if available
        if self.ai_module:
            self.logger.info("Using AI module to transform criteria...")
            current_query_params = self.ai_module.transform_initial_criteria(user_criteria, self.site_name)
        else:
            self.logger.info("No AI module available, using criteria directly...")
            current_query_params = user_criteria
            
        if not current_query_params:
            self.logger.error("Failed to transform criteria for search.")
            return []

        self.logger.info(f"[{self.site_name}] ✅ AI-transformed query params: {current_query_params}")

        # Store price_max for post-processing filtering
        self.current_price_max = current_query_params.get("price_max") or user_criteria.get("price_max")
        if self.current_price_max:
            self.logger.info(f"Price filtering enabled: max £{self.current_price_max} per month")

        all_listings = []
        seen_urls = set()
        
        # Detect total pages
        self.logger.info("🔍 Detecting total pages...")
        first_page_url = await self._construct_search_url(current_query_params, 1)
        self.logger.info(f"First page URL: {first_page_url}")
        total_pages = await self._detect_total_pages(first_page_url)
        
        self.logger.info(f"🎯 Starting multi-page scrape for location '{current_query_params.get('location')}': {total_pages} pages")
        
        # Scrape each page
        for page_num in range(1, total_pages + 1):
            try:
                self.logger.info(f"Scraping page {page_num}/{total_pages} for location '{current_query_params.get('location')}'")
                
                page_url = await self._construct_search_url(current_query_params, page_num)
                
                # Navigate with retry logic
                max_nav_retries = 3
                for attempt in range(max_nav_retries):
                    try:
                        await self.browser_page.goto(page_url, wait_until="networkidle", timeout=30000)
                        break
                    except Exception as e:
                        if attempt == max_nav_retries - 1:
                            raise e
                        await asyncio.sleep(random.uniform(3, 6))
                
                # Handle site obstacles
                await self._handle_site_obstacles()
                
                # Check search outcome
                search_outcome = await self._check_search_outcome(self.browser_page)
                
                if search_outcome.get("status") == "blocked":
                    self.logger.warning(f"Anti-bot protection detected on page {page_num}, stopping")
                    break
                
                # Parse listings
                page_content = await self.browser_page.content()
                page_listings = await self._parse_initial_listings(page_content)
                
                # Add unique listings
                new_count = 0
                for listing in page_listings:
                    if listing.get("url") and listing["url"] not in seen_urls:
                        seen_urls.add(listing["url"])
                        all_listings.append(listing)
                        new_count += 1
                
                self.logger.info(f"Page {page_num}: {len(page_listings)} listings, {new_count} new. Total: {len(all_listings)}")
                
                # Stop if no listings found
                if len(page_listings) == 0:
                    self.logger.info(f"No listings on page {page_num}, stopping pagination")
                    break
                
                # Rate limiting between pages
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                self.logger.error(f"Error on page {page_num}: {e}")
                continue
        
        self.logger.info(f"Multi-page scraping completed for '{current_query_params.get('location')}'. Total listings: {len(all_listings)}")
        return all_listings

    # Maintain compatibility with existing interface
    async def search(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compatibility method that calls the enhanced search_properties method"""
        return await self.search_properties(query_params)

    async def close(self):
        """Close browser page"""
        if self.browser_page and not self.browser_page.is_closed():
            try:
                await self.browser_page.close()
                self.browser_page = None
                self.logger.info("Browser page closed.")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")

