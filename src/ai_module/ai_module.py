import os
import json
import openai
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

# --- .env Loading & OpenAI Client Initialization ---
# Construct the path to the .env file assuming it's in the project root
# (file is now in src/ai_module/, so we need to go up three levels)
project_root_for_env = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
dotenv_path = os.path.join(project_root_for_env, ".env")

loaded_env = load_dotenv(dotenv_path)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables. AI module will not function.")
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        print("AI_MODULE_DEBUG: OpenAI client initialized successfully.")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}. AI module may not function.")
# --- End .env Loading & OpenAI Client Initialization ---

class AIModule:
    def __init__(self, model_name: str = "gpt-3.5-turbo", site_profiles_dir: str = "configs/site_profiles"):
        """
        Initializes the AI Module for V2 enhancements.
        Args:
            model_name: The OpenAI model to use.
            site_profiles_dir: Directory containing site-specific knowledge profiles (JSON files).
        """
        self.model_name = model_name
        self.client = client
        self.site_profiles = {}
        self.site_profiles_dir = os.path.join(project_root_for_env, site_profiles_dir) # Ensure correct path from project root
        self._load_site_profiles()

        if not self.client:
            print("AI_MODULE_DEBUG: AIModule instantiated, but OpenAI client is not available.")

    def _load_site_profiles(self):
        """Loads site-specific knowledge profiles from JSON files."""
        if not os.path.exists(self.site_profiles_dir):
            print(f"Warning: Site profiles directory not found: {self.site_profiles_dir}")
            return
        for filename in os.listdir(self.site_profiles_dir):
            if filename.endswith("_profile.json"):
                site_name = filename.replace("_profile.json", "") # This will be lowercase, e.g., "openrent"
                try:
                    with open(os.path.join(self.site_profiles_dir, filename), 'r') as f:
                        self.site_profiles[site_name] = json.load(f)
                        print(f"AI_MODULE_DEBUG: Loaded site profile for {site_name}")
                except Exception as e:
                    print(f"Error loading site profile for {site_name}: {e}")

    def get_site_profile(self, site_name: str) -> Optional[Dict[str, Any]]:
        """Returns the loaded profile for a given site (case-insensitive lookup)."""
        # Profiles are stored with lowercase keys (e.g., "openrent")
        return self.site_profiles.get(site_name.lower())

    def _call_openai_api(self, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 500) -> Optional[str]:
        """Helper function to call OpenAI ChatCompletion API and handle common errors."""
        if not self.client:
            print("AI_MODULE_DEBUG: OpenAI call skipped - client not available.")
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except openai.APIError as e:
            print(f"OpenAI API Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during OpenAI API call: {e}")
        return None

    def transform_initial_criteria(self, user_criteria: Dict[str, Any], site_name: str) -> Dict[str, Any]:
        """
        Takes raw user criteria and the target site name, returns an initial set of query parameters
        optimized for that site using site profiles and LLM reasoning.
        """
        site_profile = self.get_site_profile(site_name) # Uses case-insensitive lookup now
        if not site_profile:
            print(f"Warning: No site profile for {site_name} (lookup: {site_name.lower()}). Using raw criteria.")
            return user_criteria # Fallback to raw criteria

        transformed_criteria = user_criteria.copy()
        if 'location' in user_criteria and 'location_format_preference' in site_profile:
            print(f"AI_MODULE_DEBUG: Applying location preference for {site_name}: {site_profile['location_format_preference']}")

        # Load postcode data
        postcode_data_path = os.path.join(project_root_for_env, "..", "London_Postcodes_with_Tube_Zones.csv")
        postcode_data_for_prompt = ""
        if os.path.exists(postcode_data_path):
            with open(postcode_data_path, 'r') as f:
                postcode_data_for_prompt = f.read()
        else:
            print(f"Warning: Postcode data file not found at {postcode_data_path}")

        system_prompt = f"You are an AI assistant helping to optimize property search criteria for the website '{site_name}'. " \
                        f"Use the provided site profile information and user criteria to generate optimized query parameters. " \
                        f"You have access to a comprehensive London postcode database. When a broad location is provided, use the database to map it to the most relevant postcode prefixes. " \
                        f"For example, if 'West London' is provided, you should output relevant postcode prefixes like W1, W2, W3, etc., based on the provided postcode data. " \
                        f"Respond with a JSON object of the optimized criteria."
        
        user_prompt_content = f"User Criteria:\n{json.dumps(user_criteria, indent=2)}\n\n"
        user_prompt_content += f"Site Profile for {site_name}:\n{json.dumps(site_profile, indent=2)}\n\n"
        user_prompt_content += f"London Postcode Data:\n{postcode_data_for_prompt}\n\n"
        user_prompt_content += "Based on the above, provide an optimized set of query parameters as a JSON object. " \
                               "Consider how to best represent location, property type, keywords, price, etc., for this specific site. " \
                               "For location, if a broad area is given, use the provided London Postcode Data to identify and suggest the most appropriate postcode prefixes. " \
                               "If multiple postcode prefixes are relevant, list them as a comma-separated string in the 'search_location' field."
                               
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_content}
        ]

        ai_response_str = self._call_openai_api(messages, temperature=0.1, max_tokens=1000)

        if ai_response_str:
            try:
                optimized_params = json.loads(ai_response_str)
                print(f"AI_MODULE_DEBUG: AI suggested optimized params for {site_name}: {optimized_params}")
                return {**transformed_criteria, **optimized_params}
            except json.JSONDecodeError as e:
                print(f"AI_MODULE_DEBUG: Failed to parse AI response as JSON for {site_name}: {e}. Response: {ai_response_str}")
        
        print(f"AI_MODULE_DEBUG: Using rule-based transformed criteria for {site_name} due to AI response issue.")
        return transformed_criteria

    def suggest_query_refinement(self, site_name: str, current_query_params: Dict[str, Any], search_outcome: Dict[str, Any], attempt_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Called by a scraper when a search is unsatisfactory. Suggests a refinement.
        Output should be a structured suggestion, e.g., {'action': 'modify_parameter', 'parameter': 'location', 'new_value': 'NW9 0AA'}
        """
        site_profile = self.get_site_profile(site_name) # Uses case-insensitive lookup now
        if not site_profile:
            print(f"Warning: No site profile for {site_name} (lookup: {site_name.lower()}) to suggest refinement.")
            return None

        system_prompt = f"You are an AI assistant helping to refine a failed property search query for the website '{site_name}'. " \
                        f"Your goal is to suggest a single, specific, actionable modification to the query parameters to improve results. " \
                        f"Respond with a JSON object representing the suggested action."
        
        user_prompt_content = f"Site: {site_name}\n"
        user_prompt_content += f"Site Profile Information:\n{json.dumps(site_profile, indent=2)}\n\n"
        user_prompt_content += f"Current Query Parameters that failed/yielded poor results:\n{json.dumps(current_query_params, indent=2)}\n\n"
        user_prompt_content += f"Search Outcome:\n{json.dumps(search_outcome, indent=2)}\n\n"
        user_prompt_content += f"Attempt History (previous attempts for this search):\n{json.dumps(attempt_history, indent=2)}\n\n"
        user_prompt_content += "Based on all the above, suggest one specific refinement action as a JSON object. " \
                               "Valid actions include: 'modify_parameter', 'remove_filter', 'add_keyword', 'change_search_strategy', 'stop_attempts'. " \
                               "Example for 'modify_parameter': {'action': 'modify_parameter', 'parameter': 'location', 'new_value': 'NW9 0AA'}. " \
                               "Example for 'remove_filter': {'action': 'remove_filter', 'filter_name': 'bedrooms_min'}. " \
                               "Example for 'stop_attempts': {'action': 'stop_attempts', 'reason': 'max_refinements_reached_or_no_clear_path'}. " \
                               "Prioritize simple, logical changes. If outcome is 'captcha_detected', suggest 'stop_attempts'."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_content}
        ]

        ai_response_str = self._call_openai_api(messages, temperature=0.2, max_tokens=300)

        if ai_response_str:
            try:
                suggestion = json.loads(ai_response_str)
                print(f"AI_MODULE_DEBUG: AI suggested refinement for {site_name}: {suggestion}")
                if 'action' in suggestion:
                    return suggestion
                else:
                    print(f"AI_MODULE_DEBUG: AI suggestion for {site_name} lacks 'action' field: {ai_response_str}")
            except json.JSONDecodeError as e:
                print(f"AI_MODULE_DEBUG: Failed to parse AI refinement suggestion as JSON for {site_name}: {e}. Response: {ai_response_str}")
        
        return None

    def analyze_listing_text(self, text: str, prompt_instruction: str) -> Optional[Dict[str, Any]]:
        if not self.client or not OPENAI_API_KEY:
            print("AI analysis skipped: OpenAI client not available or API key missing.")
            return None
        messages = [
            {"role": "system", "content": "You are an intelligent assistant helping to analyze property listings."},
            {"role": "user", "content": f"{prompt_instruction}\n\nListing Text:\n---BEGIN LISTING TEXT---\n{text}\n---END LISTING TEXT---"}
        ]
        ai_response_content = self._call_openai_api(messages, temperature=0.3, max_tokens=500)
        return {"analysis_text": ai_response_content} if ai_response_content else None

    def check_semantic_match(self, text_to_check: str, keywords: list[str]) -> bool:
        if not self.client or not OPENAI_API_KEY or not keywords:
            return False
        keyword_string = ", ".join([f"'{k}'" for k in keywords])
        prompt = (
            f"Analyze the following property listing text. Does it semantically match or strongly imply any of these concepts/keywords: {keyword_string}? "
            f"Consider synonyms and related phrases. Respond with only 'YES' or 'NO'."
        )
        messages = [
            {"role": "system", "content": "You are an AI assistant that determines semantic matches. Respond with only YES or NO."},
            {"role": "user", "content": f"{prompt}\n\nListing Text:\n---BEGIN LISTING TEXT---\n{text_to_check}\n---END LISTING TEXT---"}
        ]
        ai_response = self._call_openai_api(messages, temperature=0.0, max_tokens=10)
        return ai_response == "YES" if ai_response else False

if __name__ == '__main__':
    print("AI Module V2 direct run for testing (requires .env and site profiles):")
    dummy_profiles_dir = "dummy_configs/site_profiles"
    os.makedirs(os.path.join(project_root_for_env, dummy_profiles_dir), exist_ok=True)
    dummy_profile_path = os.path.join(project_root_for_env, dummy_profiles_dir, "example_profile.json")
    with open(dummy_profile_path, 'w') as f:
        json.dump({"name": "ExampleSite", "location_format_preference": "postcode_prefix", "keywords_parameter": "q"}, f)

    if not OPENAI_API_KEY or not client:
        print("Skipping AIModule V2 example: OpenAI API key not set or client not initialized.")
    else:
        ai_module = AIModule(site_profiles_dir=dummy_profiles_dir)
        print(f"AI Module initialized. Loaded profiles: {ai_module.site_profiles.keys()}")
        sample_user_criteria = {"location": "North West London", "property_type": "flat", "price_max": 1500, "keywords": ["studio"]}
        print("\nTesting transform_initial_criteria...")
        transformed = ai_module.transform_initial_criteria(sample_user_criteria, "example") # site_name "example" matches profile key
        print(f"Transformed criteria for example site: {transformed}")
        print("\nTesting suggest_query_refinement...")
        current_params = {"location": "NW9", "keywords": "studio", "price_max": 1450}
        outcome = {"status": "zero_results", "message": "No listings found matching your criteria."}
        history = []
        suggestion = ai_module.suggest_query_refinement("example", current_params, outcome, history)
        print(f"Refinement suggestion for example site: {suggestion}")

    if os.path.exists(dummy_profile_path):
        os.remove(dummy_profile_path)
    if os.path.exists(os.path.join(project_root_for_env, dummy_profiles_dir)) and not os.listdir(os.path.join(project_root_for_env, dummy_profiles_dir)):
        os.rmdir(os.path.join(project_root_for_env, dummy_profiles_dir))


