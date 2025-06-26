from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import os
import asyncio # For potential delays

# Assuming AIModule is in src.ai_module and can be imported
# This might need adjustment based on actual project structure and how AIModule is provided
# from ..ai_module import AIModule # If BaseScraper is in a submodule of src

class BaseScraper(ABC):
    """
    Abstract base class for V2 website scrapers with adaptive logic.
    """

    def __init__(self, site_name: str, ai_module: Any, configs_dir: str = "configs"):
        self.site_name = site_name
        self.ai_module = ai_module # Instance of the enhanced AIModule
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Adjust if needed
        self.configs_dir = os.path.join(self.project_root, configs_dir)
        self.site_profile: Optional[Dict[str, Any]] = self._load_site_profile()
        self.selectors: Optional[Dict[str, Any]] = self._load_selectors()
        self.browser_page = None # To be managed by Playwright in subclasses

        if not self.site_profile:
            print(f"CRITICAL: Site profile for {self.site_name} not loaded. Scraper may not function correctly.")
        if not self.selectors:
            print(f"CRITICAL: Selectors for {self.site_name} not loaded. Scraper may not function correctly.")

    def _load_site_profile(self) -> Optional[Dict[str, Any]]:
        profile_path = os.path.join(self.configs_dir, "site_profiles", f"{self.site_name.lower()}_profile.json")
        try:
            with open(profile_path, 'r') as f:
                profile = json.load(f)
                print(f"Successfully loaded site profile for {self.site_name} from {profile_path}")
                return profile
        except FileNotFoundError:
            print(f"Error: Site profile not found for {self.site_name} at {profile_path}")
        except json.JSONDecodeError as e:
            print(f"Error decoding site profile for {self.site_name}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred loading site profile for {self.site_name}: {e}")
        return None

    def _load_selectors(self) -> Optional[Dict[str, Any]]:
        selector_path = os.path.join(self.configs_dir, "selectors", f"{self.site_name.lower()}_selectors.json")
        try:
            with open(selector_path, 'r') as f:
                selectors = json.load(f)
                print(f"Successfully loaded selectors for {self.site_name} from {selector_path}")
                return selectors
        except FileNotFoundError:
            print(f"Error: Selectors not found for {self.site_name} at {selector_path}")
        except json.JSONDecodeError as e:
            print(f"Error decoding selectors for {self.site_name}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred loading selectors for {self.site_name}: {e}")
        return None

    @abstractmethod
    async def initialize_browser(self, playwright_context):
        """Initializes the Playwright browser page for this scraper instance."""
        pass

    @abstractmethod
    async def _construct_search_url(self, query_params: Dict[str, Any]) -> str:
        """Constructs the search URL based on query parameters and site profile."""
        pass

    @abstractmethod
    async def _parse_initial_listings(self, page_content: str) -> List[Dict[str, Any]]:
        """Parses the search results page to extract initial listing data (e.g., URLs)."""
        pass

    @abstractmethod
    async def _check_search_outcome(self, page_content_or_response: Any) -> Dict[str, Any]:
        """Analyzes the page content or response to determine search outcome (e.g., zero results, captcha)."""
        pass
    
    @abstractmethod
    async def _handle_site_obstacles(self):
        """Handles common site obstacles like cookie banners, pop-ups, etc."""
        pass

    async def search_properties(self, user_criteria: Dict[str, Any], max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        V2: Searches the property website using an adaptive loop with AI refinement.
        """
        if not self.site_profile or not self.selectors or not self.ai_module or not self.browser_page:
            print(f"Scraper for {self.site_name} is not properly initialized (profile, selectors, AI, or page missing).")
            return []

        # 1. Initial criteria transformation by AI
        current_query_params = self.ai_module.transform_initial_criteria(user_criteria, self.site_name)
        if not current_query_params:
            print(f"AI failed to transform initial criteria for {self.site_name}. Aborting search for this site.")
            return []
        
        print(f"[{self.site_name}] Initial AI-transformed query params: {current_query_params}")

        all_found_listings = []
        attempt_history = []
        
        for attempt in range(max_retries):
            print(f"[{self.site_name}] Search attempt {attempt + 1}/{max_retries}")
            search_url = await self._construct_search_url(current_query_params)
            print(f"[{self.site_name}] Navigating to: {search_url}")
            
            try:
                await self.browser_page.goto(search_url, timeout=60000) # Increased timeout
                await self._handle_site_obstacles() # Handle cookie banners etc.
                page_content = await self.browser_page.content()
                
                # 2. Check search outcome
                search_outcome = await self._check_search_outcome(self.browser_page) # Pass page for direct inspection
                print(f"[{self.site_name}] Search outcome: {search_outcome}")
                attempt_history.append({"params": current_query_params.copy(), "url": search_url, "outcome": search_outcome})

                if search_outcome.get("status") == "success" or search_outcome.get("status") == "listings_found":
                    listings_on_page = await self._parse_initial_listings(page_content)
                    print(f"[{self.site_name}] Found {len(listings_on_page)} listings on this attempt.")
                    # Basic duplicate check based on URL before adding
                    for listing in listings_on_page:
                        if not any(l['url'] == listing['url'] for l in all_found_listings):
                            all_found_listings.append(listing)
                    # In a real scenario, you might want to paginate here or decide if enough results were found.
                    # For now, we assume one page or that parse_initial_listings handles pagination if simple.
                    break # Exit retry loop on success
                
                elif search_outcome.get("status") == "captcha_detected" or search_outcome.get("status") == "blocked":
                    print(f"[{self.site_name}] CAPTCHA or block detected. Stopping attempts for this site.")
                    break

                # 3. If outcome is not success (e.g., zero_results, error), consult AI for refinement
                if attempt < max_retries - 1:
                    print(f"[{self.site_name}] Consulting AI for query refinement.")
                    refinement_suggestion = self.ai_module.suggest_query_refinement(
                        self.site_name, 
                        current_query_params, 
                        search_outcome, 
                        attempt_history
                    )
                    if refinement_suggestion and refinement_suggestion.get("action") != "stop_attempts":
                        print(f"[{self.site_name}] AI suggested refinement: {refinement_suggestion}")
                        # Implement logic to modify current_query_params based on suggestion
                        # This is a placeholder for the actual modification logic
                        action = refinement_suggestion.get("action")
                        if action == "modify_parameter":
                            param_to_modify = refinement_suggestion.get("parameter")
                            new_value = refinement_suggestion.get("new_value")
                            if param_to_modify and new_value is not None:
                                current_query_params[param_to_modify] = new_value
                            else:
                                print(f"[{self.site_name}] Invalid 'modify_parameter' suggestion from AI.")
                                break # Stop if AI gives bad suggestion
                        elif action == "remove_filter":
                            filter_to_remove = refinement_suggestion.get("filter_name")
                            if filter_to_remove and filter_to_remove in current_query_params:
                                del current_query_params[filter_to_remove]
                            # Or set to a default/empty value if API expects the key
                        # Add more actions like 'add_keyword', 'change_search_strategy'
                        else:
                             print(f"[{self.site_name}] Unknown AI action: {action}. Stopping attempts.")
                             break
                    else:
                        print(f"[{self.site_name}] AI suggested stopping or no refinement provided. Stopping attempts.")
                        break # Stop if AI says so or no suggestion
                else:
                    print(f"[{self.site_name}] Max retries reached.")

            except Exception as e:
                print(f"[{self.site_name}] Error during search attempt {attempt + 1}: {e}")
                attempt_history.append({"params": current_query_params.copy(), "url": search_url, "outcome": {"status": "error", "details": str(e)}})
                if attempt < max_retries - 1:
                    await asyncio.sleep(5) # Wait before retrying on general error
                # Potentially consult AI even on general errors if it can suggest something

        print(f"[{self.site_name}] Finished search attempts. Total unique listings found: {len(all_found_listings)}")
        return all_found_listings

    def _get_full_url(self, base_url: str, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        return base_url + path

    async def close(self):
        if self.browser_page and not self.browser_page.is_closed():
            try:
                await self.browser_page.close()
                print(f"[{self.site_name}] Browser page closed.")
            except Exception as e:
                print(f"[{self.site_name}] Error closing browser page: {e}")

