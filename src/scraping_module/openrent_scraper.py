import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, BrowserContext
import urllib.parse
import re # Import re for regex operations

from .base_scraper import BaseScraper

class OpenRentScraper(BaseScraper):
    """
    V2 Scraper for OpenRent.co.uk with adaptive logic.
    """

    def __init__(self, ai_module: Any, playwright_context: BrowserContext):
        super().__init__(site_name="OpenRent", ai_module=ai_module)
        self.context = playwright_context
        self.browser_page: Optional[Page] = None

    async def initialize_browser(self):
        if not self.context:
            print(f"[{self.site_name}] Error: Playwright BrowserContext not provided.")
            raise ValueError("BrowserContext must be provided to OpenRentScraper.")
        try:
            self.browser_page = await self.context.new_page()
            print(f"[{self.site_name}] New browser page created.")
        except Exception as e:
            print(f"[{self.site_name}] Error creating new browser page: {e}")
            self.browser_page = None

    async def _construct_search_url(self, query_params: Dict[str, Any]) -> str:
        if not self.site_profile:
            print(f"[{self.site_name}] Cannot construct URL: site profile not loaded.")
            return "about:blank"

        base_url = self.site_profile.get("base_search_url", "https://www.openrent.co.uk/properties-to-rent/")
        location_term = query_params.get("location_processed_for_site") or query_params.get("location", "london")
        location_slug = urllib.parse.quote(location_term.lower().replace(" ", "-"))
        
        if not base_url.endswith("/"):
            base_url += "/"
        
        search_path = f"{location_slug}"
        url = urllib.parse.urljoin(base_url, search_path)

        params_to_encode = {}
        if query_params.get("keywords"):
            keywords_str = " ".join(query_params["keywords"]) if isinstance(query_params["keywords"], list) else query_params["keywords"]
            params_to_encode[self.site_profile.get("keywords_parameter", "term")] = keywords_str
        elif query_params.get("location"):
             params_to_encode[self.site_profile.get("keywords_parameter", "term")] = query_params.get("location")

        if query_params.get("price_min") is not None:
            params_to_encode[self.site_profile.get("price_min_parameter", "minPrice")] = query_params["price_min"]
        if query_params.get("price_max") is not None:
            params_to_encode[self.site_profile.get("price_max_parameter", "maxPrice")] = query_params["price_max"]
        if query_params.get("bedrooms_min") is not None:
            params_to_encode[self.site_profile.get("bedrooms_min_parameter", "minBedrooms")] = query_params["bedrooms_min"]
        
        if params_to_encode:
            url += "?" + urllib.parse.urlencode(params_to_encode)
        
        return url

    async def _parse_initial_listings(self, page_content: str) -> List[Dict[str, Any]]:
        if not self.browser_page or not self.selectors:
            print(f"[{self.site_name}] Scraper not ready (no page or selectors).")
            return []
        
        listings = []
        print(f"[{self.site_name}] Attempting direct element targeting for listings.")
        
        configured_container_selector = self.selectors.get("listing_item_container")
        potential_listing_elements = []
        if configured_container_selector:
            try:
                potential_listing_elements = await self.browser_page.query_selector_all(configured_container_selector)
                if potential_listing_elements:
                    print(f"[{self.site_name}] Found {len(potential_listing_elements)} elements using configured container: {configured_container_selector}")
            except Exception as e:
                print(f"[{self.site_name}] Error with configured container selector \'{configured_container_selector}\': {e}")
                potential_listing_elements = []

        if not potential_listing_elements:
            print(f"[{self.site_name}] Configured container selector yielded no results or was invalid. Trying broader search for listing-like elements.")
            property_list_container = await self.browser_page.query_selector("div.property-list")
            if property_list_container:
                potential_listing_elements = await property_list_container.query_selector_all(":scope > div[class*='pli']")
                if potential_listing_elements:
                    print(f"[{self.site_name}] Found {len(potential_listing_elements)} potential listings using direct child targeting of 'div.property-list'.")
            else:
                print(f"[{self.site_name}] Could not find 'div.property-list' container for direct targeting.")

        if not potential_listing_elements:
            print(f"[{self.site_name}] Still no potential listing elements found after direct targeting attempts.")
            return []

        for i, prop_element in enumerate(potential_listing_elements):
            listing_data = {}
            try:
                link_element = await prop_element.query_selector("a[href*='property-to-rent/'], a[href*='room-to-rent/']")
                if not link_element:
                    link_element = await prop_element.query_selector("a.property-title")
                if not link_element:
                    link_element = await prop_element.query_selector("a")
                
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href:
                        listing_data["url"] = self._get_full_url(self.site_profile.get("base_url_for_relative_paths", "https://www.openrent.co.uk"), href)
                    else:
                        print(f"[{self.site_name}] Listing {i+1}: Found link element but no href attribute.")
                        continue
                else:
                    print(f"[{self.site_name}] Listing {i+1}: No link element found.")
                    continue

                price_text_content = await prop_element.inner_text()
                price_match = re.search(r"£\s*([\d,]+(?:\.\d{2})?)\s*(pcm|per month|pw|per week)", price_text_content, re.IGNORECASE)
                if price_match:
                    listing_data["price_text"] = f"£{price_match.group(1)} {price_match.group(2)}".strip()
                else:
                    price_selector = self.selectors.get("listing_price")
                    if price_selector:
                        price_element = await prop_element.query_selector(price_selector)
                        if price_element:
                            listing_data["price_text"] = (await price_element.inner_text()).strip()
                        else: print(f"[{self.site_name}] Listing {i+1}: Price element not found with selector: {price_selector}")
                    else: print(f"[{self.site_name}] Listing {i+1}: No price selector configured and regex failed.")

                title_element = await prop_element.query_selector("a.property-title, h2, h3")
                if title_element:
                    listing_data["title_snippet"] = (await title_element.inner_text()).strip()
                else:
                    title_selector = self.selectors.get("listing_title", self.selectors.get("listing_title_link"))
                    if title_selector:
                        title_el = await prop_element.query_selector(title_selector)
                        if title_el:
                            listing_data["title_snippet"] = (await title_el.inner_text()).strip()
                        else: print(f"[{self.site_name}] Listing {i+1}: Title element not found with selector: {title_selector}")
                    else: print(f"[{self.site_name}] Listing {i+1}: No title selector configured and direct find failed.")
                
                location_element = await prop_element.query_selector("span.address, p.address, div.address")
                if location_element:
                    listing_data["location_snippet"] = (await location_element.inner_text()).strip()
                else:
                    location_selector = self.selectors.get("listing_location")
                    if location_selector:
                        loc_el = await prop_element.query_selector(location_selector)
                        if loc_el:
                            listing_data["location_snippet"] = (await loc_el.inner_text()).strip()
                        else: print(f"[{self.site_name}] Listing {i+1}: Location element not found with selector: {location_selector}")
                    else: print(f"[{self.site_name}] Listing {i+1}: No location selector configured and direct find failed.")

                if listing_data.get("url") and (listing_data.get("price_text") or listing_data.get("title_snippet")):
                    listings.append(listing_data)
                else:
                    print(f"[{self.site_name}] Listing {i+1}: Insufficient data extracted (URL: {listing_data.get('url')}, Price: {listing_data.get('price_text')}, Title: {listing_data.get('title_snippet')}). Skipping.")

            except Exception as e:
                print(f"[{self.site_name}] Error parsing a potential listing element {i+1}: {e}")
        
        print(f"[{self.site_name}] Extracted {len(listings)} listings using direct targeting approach.")
        return listings

    async def _check_search_outcome(self, page: Page) -> Dict[str, Any]:
        if not self.selectors:
            return {"status": "error", "details": "Selectors not loaded."}

        # 1. Check for CAPTCHA
        captcha_indicator = self.selectors.get("captcha_indicator")
        if captcha_indicator:
            try:
                captcha_elements = await page.query_selector_all(captcha_indicator)
                for el in captcha_elements:
                    if await el.is_visible():
                        print(f"[{self.site_name}] CAPTCHA indicator found and visible: {captcha_indicator.split(',')[0]} (or similar)")
                        return {"status": "captcha_detected"}
            except Exception as e:
                print(f"[{self.site_name}] Error checking captcha_indicator selector '{captcha_indicator}': {e}")

        # 2. Check for explicit "Zero Results" indicators
        zero_results_indicator = self.selectors.get("zero_results_indicator")
        if zero_results_indicator:
            try:
                zero_elements = await page.query_selector_all(zero_results_indicator)
                for el in zero_elements:
                    if await el.is_visible():
                        print(f"[{self.site_name}] Zero results indicator found and visible: {zero_results_indicator.split(',')[0]} (or similar)")
                        return {"status": "zero_results"}
                if zero_elements: # Log if found but not visible
                     print(f"[{self.site_name}] Zero results indicators ({zero_results_indicator.split(',')[0]}...) found in DOM but none were visible.")
            except Exception as e:
                print(f"[{self.site_name}] Error checking zero_results_indicator selector '{zero_results_indicator}': {e}")

        # 3. Check for listing items
        listing_item_selector = self.selectors.get("listing_item_container") 
        if listing_item_selector:
            try:
                listing_items = await page.query_selector_all(listing_item_selector)
                if listing_items:
                    print(f"[{self.site_name}] Found {len(listing_items)} listing items using selector: {listing_item_selector}")
                    return {"status": "listings_found"}
                else:
                    print(f"[{self.site_name}] No listing items found using selector: {listing_item_selector}. This might mean zero results.")
                    # If we are here, no visible zero_results_indicator was found, and no captcha.
                    print(f"[{self.site_name}] Assuming zero results as no items found and no explicit zero_results_indicator present or visible.")
                    return {"status": "zero_results", "details": "No listing items found with the primary item selector."}
            except Exception as e:
                print(f"[{self.site_name}] Error checking listing_item_container selector '{listing_item_selector}': {e}")
        else:
            print(f"[{self.site_name}] 'listing_item_container' selector not defined in config. Cannot determine if listings are present.")

        # 4. Fallback: Check page title for errors
        page_title = await page.title()
        if "error" in page_title.lower() or "not found" in page_title.lower() or "problem loading page" in page_title.lower():
            print(f"[{self.site_name}] Page title indicates error: {page_title}")
            return {"status": "error", "details": f"Page title indicates error: {page_title}"}

        # 5. If none of the above, outcome is unknown
        print(f"[{self.site_name}] Could not definitively determine search outcome from page content. Title: {page_title}")
        return {"status": "unknown", "details": "Could not definitively determine search outcome."}
    
    async def _handle_site_obstacles(self):
        if not self.browser_page or not self.selectors:
            return
        cookie_button_selector = self.selectors.get("cookie_banner_accept_button")
        if cookie_button_selector:
            try:
                # Try to click if visible, but don't fail if not found or not clickable immediately
                button = await self.browser_page.query_selector(cookie_button_selector)
                if button and await button.is_visible():
                    await button.click(timeout=3000) # Short timeout for click
                    print(f"[{self.site_name}] Clicked cookie accept button: {cookie_button_selector}")
                    await asyncio.sleep(1) 
            except Exception as e:
                # print(f"[{self.site_name}] Cookie button not found or clickable: {cookie_button_selector} - {e}")
                pass 

    async def close(self):
        if self.browser_page and not self.browser_page.is_closed():
            try:
                await self.browser_page.close()
                print(f"[{self.site_name}] Browser page closed.")
                self.browser_page = None
            except Exception as e:
                print(f"[{self.site_name}] Error closing browser page: {e}")


