from typing import List, Dict, Any, Optional
import re

# Assuming ai_module.py is in the same directory or accessible via PYTHONPATH
from .ai_module import AIModule # If in the same package
# If AIModule is not available (e.g. API key missing), it should degrade gracefully.

# Keywords that often indicate an agent or company rather than a private individual
AGENT_INDICATIVE_KEYWORDS = [
    "lettings", "estate agent", "estates", "property management", "properties",
    "management services", "lettings negotiator", "lettings manager",
    "real estate", "realty", "associates", "partners", "group", "limited", "ltd", "plc",
    "developments", "investments", "lettings co", "property co", "housing association"
]

# Keywords that might be used by users to specifically request private landlords
PRIVATE_LANDLORD_USER_KEYWORDS = [
    "private landlord", "direct from landlord", "no agents", "no agencies"
]

class FilteringModule:
    def __init__(self, ai_module: Optional[AIModule] = None):
        """
        Initializes the Filtering Module.
        Args:
            ai_module: An instance of the AIModule for semantic processing. Optional.
        """
        self.ai_module = ai_module if ai_module and ai_module.client else None # Ensure client is valid
        if self.ai_module:
            print("FilteringModule initialized with AI capabilities.")
        else:
            print("FilteringModule initialized WITHOUT AI capabilities (AIModule not provided or not functional).")

    def _is_likely_agent_by_text(self, text_to_check: Optional[str]) -> bool:
        """Checks if a given text string likely indicates an agent based on keywords."""
        if not text_to_check:
            return False
        text_lower = text_to_check.lower()
        for keyword in AGENT_INDICATIVE_KEYWORDS:
            if keyword in text_lower:
                return True
        if re.search(r"\b(?:lettings|estates|properties|management)\b", text_lower, re.IGNORECASE):
            return True
        return False

    def _matches_keywords(self, listing: Dict[str, Any], keywords: List[str]) -> bool:
        """
        Checks if the listing matches the provided keywords.
        Uses simple string matching first, then attempts semantic matching if AI module is available.
        Currently checks against 'title_snippet'. This should be expanded to full description when available.
        """
        if not keywords:
            return True # No keywords to match, so it passes this filter

        text_to_search = listing.get("title_snippet", "").lower()
        # Add more fields to search in, like description, once available
        # e.g., text_to_search += listing.get("description", "").lower()

        # Simple keyword check first
        for kw in keywords:
            if kw.lower() in text_to_search:
                return True # Found a direct match

        # If no direct match and AI module is available, try semantic matching
        if self.ai_module:
            print(f"Attempting semantic match for keywords: {keywords} in title: {listing.get('title_snippet')}")
            # For semantic matching, it's better to use more complete text if available.
            # Using title_snippet for now as a placeholder.
            if self.ai_module.check_semantic_match(listing.get("title_snippet", ""), keywords):
                print(f"Semantic match found for keywords: {keywords}")
                return True
            else:
                print(f"No semantic match for keywords: {keywords}")

        return False # No match found

    def process_listings(self, listings: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filters listings based on user criteria, including keyword matching and private landlord identification.
        Adds 'is_private_landlord_guess' and 'is_agent_flagged' fields to each listing.
        """
        processed_listings = []
        user_wants_private_only = criteria.get("private_only", False)
        user_wants_to_exclude_agents = criteria.get("exclude_agents", False)
        user_keywords = criteria.get("keywords", [])

        for listing_original in listings:
            listing = listing_original.copy() # Work on a copy to avoid modifying original list items directly
            listing["is_private_landlord_guess"] = False
            listing["is_agent_flagged"] = False

            is_agent_by_scraper = False
            is_private_by_scraper = False

            advertiser_type_snippet = listing.get("advertiser_type_snippet", "").lower()
            if "agent" in advertiser_type_snippet or "agency" in advertiser_type_snippet:
                is_agent_by_scraper = True
            elif "landlord" in advertiser_type_snippet or "private advertiser" in advertiser_type_snippet:
                is_private_by_scraper = True
            
            poster_name_snippet = listing.get("poster_name_snippet", "")
            if self._is_likely_agent_by_text(poster_name_snippet):
                is_agent_by_scraper = True
            
            # --- Keyword Matching (Simple and Semantic) ---
            if user_keywords:
                if not self._matches_keywords(listing, user_keywords):
                    continue # Skip if keywords don't match

            # --- Private Landlord / Agent Logic ---
            if is_agent_by_scraper:
                listing["is_private_landlord_guess"] = False
                listing["is_agent_flagged"] = True
                if user_wants_private_only:
                    continue 
            elif is_private_by_scraper:
                listing["is_private_landlord_guess"] = True
            else: # No strong signal from scraper-provided fields
                # Fallback: OpenRent is generally private
                if listing.get("source_site") == "OpenRent":
                    listing["is_private_landlord_guess"] = True
                # If Gumtree was searched with seller_type=private, that's a strong signal
                # This should ideally be passed from the scraper or inferred from search URL used.
                # For now, we rely on the explicit fields or general site nature.

            # --- Final Filtering based on user preferences for agent/private ---
            if user_wants_private_only and not listing["is_private_landlord_guess"]:
                continue
            
            # If user wants to exclude agents and it's flagged (and not also a private guess, which is unlikely)
            if user_wants_to_exclude_agents and listing["is_agent_flagged"] and not listing["is_private_landlord_guess"]:
                 # As per user: "flag separately" - so we don't filter out here, but the main app can use the flag.
                 # However, if the goal is to *present* only non-agent listings when exclude_agents is true,
                 # then we should filter here. Let's assume for now the flag is for presentation, and actual exclusion
                 # for `private_only` is stricter.
                 # Re-evaluating: if exclude_agents is true, and it IS an agent, it should be excluded from final results.
                 # The `is_agent_flagged` is the important output for this. The main loop will use this.
                 # For now, if `private_only` is set, that's the stricter filter.
                 # If `exclude_agents` is set and `private_only` is NOT, then we only exclude if it's an agent AND not somehow also private.
                if not user_wants_private_only: # if private_only is true, agent listings are already gone
                    if listing["is_agent_flagged"] and not listing["is_private_landlord_guess"]:
                        continue # Exclude non-private agents if exclude_agents is true
            
            # Placeholder for other criteria filtering (price, bedrooms)
            # This would involve parsing price_text, comparing numbers, etc.
            # For V1, this detailed filtering can be added here or in a subsequent step.

            processed_listings.append(listing)

        return processed_listings

# Example usage (conceptual)
if __name__ == '__main__':
    # This example needs AIModule to be available and configured with an API key to test semantic search.
    # Ensure .env file with OPENAI_API_KEY is in the parent directory of src/
    try:
        ai_module_instance = AIModule()
        if not ai_module_instance.client:
            print("AI Module client not initialized, semantic search will be skipped in example.")
            ai_module_instance = None
    except Exception as e:
        print(f"Could not initialize AIModule for example: {e}")
        ai_module_instance = None

    filter_module = FilteringModule(ai_module=ai_module_instance)
    
    sample_listings = [
        {"url": "http://example.com/1", "title_snippet": "Lovely 2 bed flat by Private Landlord with a beautiful garden", "advertiser_type_snippet": "Private advertiser", "poster_name_snippet": "John Doe", "source_site": "SpareRoom"},
        {"url": "http://example.com/2", "title_snippet": "Amazing Apartment by XYZ Lettings, pet friendly", "advertiser_type_snippet": "Agent", "poster_name_snippet": "XYZ Lettings Ltd", "source_site": "SpareRoom"},
        {"url": "http://example.com/3", "title_snippet": "Studio Flat to Rent, includes parking space", "poster_name_snippet": "Quick Properties", "source_site": "Gumtree"},
        {"url": "http://example.com/4", "title_snippet": "Room in shared house, quiet area", "source_site": "OpenRent"},
        {"url": "http://example.com/5", "title_snippet": "Victorian house with large yard for lease", "source_site": "Gumtree"} # For semantic 'garden'
    ]

    criteria_with_keywords_semantic = {
        "private_only": False, 
        "exclude_agents": False, 
        "keywords": ["garden", "pets allowed"]
    }
    print("\nCriteria with Keywords (expecting semantic matches where AI is active):")
    filtered_semantic = filter_module.process_listings([l.copy() for l in sample_listings], criteria_with_keywords_semantic)
    for l in filtered_semantic: 
        print(f"  URL: {l.get('url')}, Title: {l.get('title_snippet')}, Private: {l.get('is_private_landlord_guess')}, Agent: {l.get('is_agent_flagged')}")

    criteria_private_keywords = {
        "private_only": True, 
        "exclude_agents": True, 
        "keywords": ["garden"]
    }
    print("\nCriteria Private Only with Keywords:")
    filtered_private_keywords = filter_module.process_listings([l.copy() for l in sample_listings], criteria_private_keywords)
    for l in filtered_private_keywords: 
        print(f"  URL: {l.get('url')}, Title: {l.get('title_snippet')}, Private: {l.get('is_private_landlord_guess')}, Agent: {l.get('is_agent_flagged')}")

