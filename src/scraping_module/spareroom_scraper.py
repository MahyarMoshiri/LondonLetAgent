import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, BrowserContext
import urllib.parse

from .base_scraper import BaseScraper

class SpareRoomScraper(BaseScraper):
    """
    V2 Scraper for SpareRoom.co.uk with adaptive logic.
    """

    def __init__(self, ai_module: Any, playwright_context: BrowserContext):
        super().__init__(site_name="SpareRoom", ai_module=ai_module)
        self.context = playwright_context
        self.browser_page: Optional[Page] = None

    async def initialize_browser(self):
        if not self.context:
            print(f"[{self.site_name}] Error: Playwright BrowserContext not provided.")
            raise ValueError("BrowserContext must be provided to SpareRoomScraper.")
        try:
            self.browser_page = await self.context.new_page()
            print(f"[{self.site_name}] New browser page created.")
        except Exception as e:
            print(f"[{self.site_name}] Error creating new browser page: {e}")
            self.browser_page = None

    async def _construct_search_url(self, query_params: Dict[str, Any]) -> str:
        if not self.site_profile or not self.site_profile.get("base_search_url"):
            print(f"[{self.site_name}] Cannot construct URL: site profile or base_search_url not loaded.")
            return "about:blank"

        base_url = self.site_profile["base_search_url"]
        profile_q_params = self.site_profile.get("query_parameters", {})
        
        params_to_encode = {}
        for key, default_value in profile_q_params.items():
            if default_value is not None:
                params_to_encode[key] = default_value
        
        search_terms = []
        if query_params.get("location"):
            search_terms.append(query_params["location"])
        if query_params.get("keywords"):
            keywords_val = query_params["keywords"]
            if isinstance(keywords_val, list):
                search_terms.extend(keywords_val)
            else:
                search_terms.append(str(keywords_val))
        
        if search_terms:
            params_to_encode[profile_q_params.get("search_key", "search")] = " ".join(search_terms)
        elif profile_q_params.get("search_key") in params_to_encode and not params_to_encode[profile_q_params.get("search_key")]:
            del params_to_encode[profile_q_params.get("search_key")]

        if query_params.get("price_min") is not None:
            params_to_encode[profile_q_params.get("min_rent_key", "min_rent")] = query_params["price_min"]
        if query_params.get("price_max") is not None:
            params_to_encode[profile_q_params.get("max_rent_key", "max_rent")] = query_params["price_max"]

        if query_params.get("property_type") and profile_q_params.get("property_type_key"):
            prop_type_mapping = self.site_profile.get("property_type_mapping", {})
            mapped_val = prop_type_mapping.get(str(query_params["property_type"]).lower())
            if mapped_val:
                params_to_encode[profile_q_params["property_type_key"]] = mapped_val
            elif query_params["property_type"]:
                 params_to_encode[profile_q_params["property_type_key"]] = query_params["property_type"]

        adv_type_key = profile_q_params.get("advertiser_type_key", "advertiser_type")
        if query_params.get("private_only"):
            adv_type_mapping = self.site_profile.get("advertiser_type_mapping", {})
            private_values = adv_type_mapping.get("private_only")
            if private_values:
                params_to_encode[adv_type_key] = ",".join(private_values)
        elif query_params.get("advertiser_type"):
             params_to_encode[adv_type_key] = query_params["advertiser_type"]

        final_params = {k: v for k, v in params_to_encode.items() if v is not None}
        
        return f"{base_url}?{urllib.parse.urlencode(final_params)}" if final_params else base_url

    async def _parse_initial_listings(self, page_content: str) -> List[Dict[str, Any]]:
        if not self.browser_page or not self.selectors:
            return []
        
        listings = []
        listing_elements_selector = self.selectors.get("listing_item_container")
        if not listing_elements_selector:
            print(f"[{self.site_name}] Error: listing_item_container selector not found.")
            return []

        listing_elements = await self.browser_page.query_selector_all(listing_elements_selector)

        for prop_element in listing_elements:
            listing_data = {}
            link_selector = self.selectors.get("listing_title_link")
            price_selector = self.selectors.get("listing_price")
            title_selector = self.selectors.get("listing_title_link")
            location_selector = self.selectors.get("listing_location")

            if link_selector:
                link_element = await prop_element.query_selector(link_selector)
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href:
                        listing_data["url"] = self._get_full_url(self.site_profile.get("base_url_for_relative_paths", "https://www.spareroom.co.uk"), href)
            
            if price_selector:
                price_element = await prop_element.query_selector(price_selector)
                if price_element:
                    listing_data["price_text"] = (await price_element.inner_text()).strip()

            if title_selector:
                title_text_element = await prop_element.query_selector(title_selector)
                if title_text_element:
                     listing_data["title_snippet"] = (await title_text_element.inner_text()).strip()

            if location_selector:
                location_element = await prop_element.query_selector(location_selector)
                if location_element:
                    listing_data["location_snippet"] = (await location_element.inner_text()).strip()

            if listing_data.get("url"):
                listings.append(listing_data)
        return listings

    async def _check_search_outcome(self, page: Page) -> Dict[str, Any]:
        if not self.selectors:
            return {"status": "error", "details": "Selectors not loaded."}

        captcha_indicator = self.selectors.get("captcha_indicator")
        if captcha_indicator and await page.query_selector(captcha_indicator):
            if await page.is_visible(captcha_indicator):
                print(f"[{self.site_name}] CAPTCHA indicator found and visible: {captcha_indicator}")
                return {"status": "captcha_detected"}

        zero_results_indicator = self.selectors.get("zero_results_indicator")
        if zero_results_indicator and await page.query_selector(zero_results_indicator):
            if await page.is_visible(zero_results_indicator):
                print(f"[{self.site_name}] Zero results indicator found and visible: {zero_results_indicator}")
                return {"status": "zero_results"}
            else:
                print(f"[{self.site_name}] Zero results indicator found but not visible: {zero_results_indicator}")

        listing_container_selector = self.selectors.get("listing_item_container")
        if listing_container_selector:
            listing_items = await page.query_selector_all(listing_container_selector)
            if listing_items:
                print(f"[{self.site_name}] Found {len(listing_items)} listing items using selector: {listing_container_selector}")
                return {"status": "listings_found"}
            else:
                print(f"[{self.site_name}] No listing items found using selector: {listing_container_selector}. This might mean zero results.")
                if not zero_results_indicator or not await page.query_selector(zero_results_indicator):
                    print(f"[{self.site_name}] Assuming zero results as no items found and no explicit zero_results_indicator present.")
                    return {"status": "zero_results", "details": "No listing items found with the primary item selector."}
        else:
            print(f"[{self.site_name}] Error: listing_item_container selector not defined in config.")
            return {"status": "error", "details": "listing_item_container selector not defined."}

        page_title = await page.title()
        if "error" in page_title.lower() or "problem finding" in page_title.lower() or "problem loading page" in page_title.lower():
            print(f"[{self.site_name}] Page title indicates error: {page_title}")
            return {"status": "error", "details": f"Page title indicates error: {page_title}"}

        print(f"[{self.site_name}] Could not determine search outcome from page content. Title: {page_title}")
        return {"status": "unknown", "details": "Could not determine search outcome from SpareRoom page content."}

    async def _handle_site_obstacles(self):
        if not self.browser_page or not self.selectors:
            return
        cookie_button_selector = self.selectors.get("cookie_banner_accept_button")
        if cookie_button_selector:
            try:
                await self.browser_page.wait_for_selector(cookie_button_selector, timeout=10000, state="visible")
                await self.browser_page.click(cookie_button_selector, timeout=5000)
                print(f"[{self.site_name}] Clicked cookie accept button.")
                await asyncio.sleep(2)
            except Exception as e:
                try:
                    await self.browser_page.keyboard.press("Escape")
                    print(f"[{self.site_name}] Pressed Escape key to dismiss potential overlay.")
                    await asyncio.sleep(1)
                except Exception as esc_e:
                    print(f"[{self.site_name}] Failed to press Escape key: {esc_e}")
                pass

    async def close(self):
        if self.browser_page and not self.browser_page.is_closed():
            try:
                await self.browser_page.close()
                print(f"[{self.site_name}] Browser page closed.")
                self.browser_page = None
            except Exception as e:
                print(f"[{self.site_name}] Error closing browser page: {e}")

