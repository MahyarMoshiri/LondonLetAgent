import asyncio
from typing import Dict, Any, Optional
from playwright.async_api import Page, BrowserContext
# from .ai_module import AIModule # Optional: if AI is needed for complex extraction
import re

def parse_price(price_text: Optional[str]) -> Optional[float]:
    if not price_text:
        return None
    # Remove currency symbols, commas, and text like /pcm or /pw
    cleaned_price = re.sub(r"[^\d.]", "", price_text.split("/")[0].split(" ")[0])
    try:
        return float(cleaned_price)
    except ValueError:
        return None

def parse_bedrooms(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    # Look for patterns like "2 bed", "3 bedrooms", "Studio"
    text_lower = text.lower()
    if "studio" in text_lower:
        return 0 # Convention for studio
    match = re.search(r"(\d+)\s*(bed|bedroom|bedrooms)", text_lower)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None

class ExtractionModule:
    def __init__(self, browser_context: BrowserContext, ai_module: Optional[Any] = None):
        """
        Initializes the Extraction Module.
        Args:
            browser_context: An active Playwright BrowserContext to create new pages.
            ai_module: Optional AIModule for complex data extraction tasks.
        """
        self.browser_context = browser_context
        self.ai_module = ai_module
        # Define site-specific selectors here. These are HIGHLY LIKELY TO CHANGE and are placeholders.
        # These selectors would be for the individual property listing pages, not the search results pages.
        self.site_selectors = {
            "OpenRent": {
                "location_postcode": ".property-title h1", # Example, might contain full address
                "price": ".property-price strong", # Example
                "key_features": ".property-features ul li", # Example, list of features
                "poster_name": ".landlord-name", # Example
                "description": ".property-description", # Example
                "bedrooms": ".property-title h1" # Often in title or features
            },
            "Gumtree": {
                "location_postcode": "span[itemprop=\"address\"]", # Example
                "price": "span.ad-price", # Example
                "key_features": ".vip-details dl", # Example, list of attributes
                "poster_name": ".seller-name a", # Example
                "description": ".ad-description", # Example
                "bedrooms": ".attributes__item--bedrooms .attributes__value" # Example
            },
            "SpareRoom": {
                "location_postcode": "h1.heading", # Example, often contains area
                "price": "strong.room-list-price, #roomdetails strong.price", # Example
                "key_features": "ul.feature-list li, div#details_property_info li", # Example
                "poster_name": "p.advertiser_name_link a, a.contactablename", # Example
                "description": "div.property_description_content", # Example
                "bedrooms": "h1.heading" # Often in title or features
            }
        }

    async def extract_listing_details(self, listing_url: str, source_site: str) -> Dict[str, Any]:
        """
        Visits a property listing URL and extracts detailed information.

        Args:
            listing_url: The URL of the individual property listing.
            source_site: The name of the website (e.g., "OpenRent", "Gumtree", "SpareRoom") 
                         to use the correct selectors.

        Returns:
            A dictionary containing extracted details. 
            Keys: "link", "location_postcode", "price", "key_features_text", "poster_name", "bedrooms", "size_sqft"
        """
        if source_site not in self.site_selectors:
            print(f"Warning: No selectors defined for site {source_site}. Cannot extract details.")
            return {"link": listing_url, "error": "Unsupported site for extraction"}

        page: Optional[Page] = None
        extracted_data = {"link": listing_url, "source_site": source_site}

        try:
            page = await self.browser_context.new_page()
            await page.goto(listing_url, wait_until="domcontentloaded", timeout=60000)
            
            selectors = self.site_selectors[source_site]

            # Location/Postcode
            if selectors.get("location_postcode"):
                loc_element = await page.query_selector(selectors["location_postcode"])
                if loc_element:
                    extracted_data["location_postcode"] = (await loc_element.inner_text()).strip()
            
            # Price
            if selectors.get("price"):
                price_element = await page.query_selector(selectors["price"])
                if price_element:
                    price_text = (await price_element.inner_text()).strip()
                    extracted_data["price_text"] = price_text # Store raw text
                    extracted_data["price"] = parse_price(price_text) # Store parsed numeric price
            
            # Key Features (as a single string for now, or list)
            if selectors.get("key_features"):
                feature_elements = await page.query_selector_all(selectors["key_features"])
                features = []
                for el in feature_elements:
                    features.append((await el.inner_text()).strip())
                extracted_data["key_features_list"] = features
                extracted_data["key_features_text"] = "; ".join(features) if features else None

            # Poster Name
            if selectors.get("poster_name"):
                poster_element = await page.query_selector(selectors["poster_name"])
                if poster_element:
                    extracted_data["poster_name"] = (await poster_element.inner_text()).strip()

            # Description (useful for AI analysis or more detailed keyword search)
            description_text = None
            if selectors.get("description"):
                desc_element = await page.query_selector(selectors["description"])
                if desc_element:
                    description_text = (await desc_element.inner_text()).strip()
                    extracted_data["description"] = description_text
            
            # Bedrooms (try to parse from various sources)
            bedrooms = None
            if selectors.get("bedrooms"):
                # Try specific bedroom selector first
                bedrooms_el = await page.query_selector(selectors["bedrooms"])
                if bedrooms_el:
                    bedrooms = parse_bedrooms(await bedrooms_el.inner_text())
            
            if bedrooms is None and extracted_data.get("location_postcode"): # Often in title/heading
                bedrooms = parse_bedrooms(extracted_data["location_postcode"])
            
            if bedrooms is None and extracted_data.get("key_features_text"):
                bedrooms = parse_bedrooms(extracted_data["key_features_text"])
            
            if bedrooms is None and description_text:
                bedrooms = parse_bedrooms(description_text)
            extracted_data["bedrooms"] = bedrooms

            # Size (sqft/sqm) - This is often hard to find consistently. Placeholder.
            extracted_data["size_sqft"] = None # Needs specific selectors or AI extraction

            # If AI module is available, could use it to enhance extraction
            # if self.ai_module and description_text:
            #     ai_analysis = self.ai_module.analyze_listing_text(description_text, "Extract number of bathrooms, parking availability, and if pets are allowed.")
            #     if ai_analysis and ai_analysis.get("analysis_text"):
            #         extracted_data["ai_enhanced_features"] = ai_analysis["analysis_text"]

        except Exception as e:
            print(f"Error extracting details from {listing_url}: {e}")
            extracted_data["error"] = str(e)
        finally:
            if page:
                await page.close()
        
        return extracted_data

# Example (conceptual - would be called by the main orchestrator)
# async def main_test_extraction():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         context = await browser.new_context()
#         extractor = ExtractionModule(browser_context=context)

#         # Replace with actual URLs from a previous scraping step
#         test_url_openrent = "https://www.openrent.co.uk/property-to-rent/london/3-bed-flat-example-12345"
#         test_url_gumtree = "https://www.gumtree.com/p/property-to-rent/2-bedroom-flat-in-example-area/123456789"
        
#         details_openrent = await extractor.extract_listing_details(test_url_openrent, "OpenRent")
#         print(f"OpenRent Details: {details_openrent}")

#         details_gumtree = await extractor.extract_listing_details(test_url_gumtree, "Gumtree")
#         print(f"Gumtree Details: {details_gumtree}")

#         await context.close()
#         await browser.close()

# if __name__ == "__main__":
#     asyncio.run(main_test_extraction())

