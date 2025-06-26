import pandas as pd
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

class OutputModule:
    def __init__(self, output_dir: str = "data"):
        """
        Initializes the Output Module.
        Args:
            output_dir: The directory where output files will be saved.
        """
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Define the desired CSV column order and mapping from internal keys
        # User requested: Bedrooms, Area, Postcode, Size, Price, Key_Features, Poster_Name, Link, Is_Agent_Flagged
        self.csv_column_map = {
            "link": "Link",
            "location_postcode": "Postcode/Area", # Combining Area and Postcode for now
            "price": "Price",
            "bedrooms": "Bedrooms",
            "size_sqft": "Size (sqft)", # User requested Size
            "key_features_text": "Key Features",
            "poster_name": "Poster Name",
            "is_agent_flagged": "Is Agent Flagged",
            "is_private_landlord_guess": "Is Private Landlord (Guess)", # Adding this for clarity
            "source_site": "Source Site",
            "price_text": "Original Price Text" # Good to keep original price text
        }
        self.csv_columns_ordered = [
            "Link", "Postcode/Area", "Price", "Bedrooms", "Size (sqft)", 
            "Key Features", "Poster Name", "Is Agent Flagged", 
            "Is Private Landlord (Guess)", "Source Site", "Original Price Text"
        ]

    def _generate_filename(self, base_name: str, extension: str) -> str:
        """Generates a filename with a timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"{base_name}_{timestamp}.{extension}")

    def save_to_csv(self, listings_data: List[Dict[str, Any]], filename_base: str = "property_listings") -> Optional[str]:
        """
        Saves the list of extracted property data to a CSV file.

        Args:
            listings_data: A list of dictionaries, where each dictionary is an extracted property.
            filename_base: The base name for the output file (timestamp and extension will be added).
        
        Returns:
            The path to the saved CSV file, or None if an error occurred or no data.
        """
        if not listings_data:
            print("No data provided to save to CSV.")
            return None

        try:
            # Prepare data for DataFrame, renaming columns as per map
            df_data = []
            for item in listings_data:
                renamed_item = {self.csv_column_map.get(k, k): v for k, v in item.items()}
                df_data.append(renamed_item)
            
            df = pd.DataFrame(df_data)
            
            # Reorder columns and include only those specified (if they exist in the df)
            final_columns = [col for col in self.csv_columns_ordered if col in df.columns]
            df = df[final_columns]

            filepath = self._generate_filename(filename_base, "csv")
            df.to_csv(filepath, index=False, encoding="utf-8-sig") # utf-8-sig for Excel compatibility            print(f"Data successfully saved to CSV: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving data to CSV: {e}")
            return None

    def save_to_json(self, listings_data: List[Dict[str, Any]], filename_base: str = "property_listings") -> Optional[str]:
        """
        Saves the list of extracted property data to a JSON file.

        Args:
            listings_data: A list of dictionaries, where each dictionary is an extracted property.
            filename_base: The base name for the output file (timestamp and extension will be added).

        Returns:
            The path to the saved JSON file, or None if an error occurred or no data.
        """
        if not listings_data:
            print("No data provided to save to JSON.")
            return None
        
        filepath = self._generate_filename(filename_base, "json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(listings_data, f, indent=4, ensure_ascii=False)
            print(f"Data successfully saved to JSON: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving data to JSON: {e}")
            return None

# Example Usage (conceptual)
if __name__ == "__main__":
    output_module = OutputModule(output_dir="../data") # Assuming execution from src/
    
    sample_data = [
        {
            "link": "http://example.com/1", 
            "location_postcode": "London, E1", 
            "price": 1500.0, 
            "price_text": "£1500 pcm",
            "bedrooms": 2, 
            "size_sqft": 750,
            "key_features_text": "Garden; Parking; Furnished", 
            "poster_name": "John Doe (Private Landlord)",
            "is_agent_flagged": False,
            "is_private_landlord_guess": True,
            "source_site": "OpenRent",
            "description": "A lovely 2 bed flat..."
        },
        {
            "link": "http://example.com/2", 
            "location_postcode": "Manchester, M14", 
            "price": 800.0, 
            "price_text": "£800 per month",
            "bedrooms": 1, 
            "size_sqft": None,
            "key_features_text": "Close to uni; All bills inc.", 
            "poster_name": "ABC Lettings",
            "is_agent_flagged": True,
            "is_private_landlord_guess": False,
            "source_site": "Gumtree",
            "error": None
        }
    ]

    csv_file = output_module.save_to_csv(sample_data)
    if csv_file:
        print(f"CSV saved to: {os.path.abspath(csv_file)}")

    json_file = output_module.save_to_json(sample_data)
    if json_file:
        print(f"JSON saved to: {os.path.abspath(json_file)}")

    # Test with no data
    output_module.save_to_csv([])
    output_module.save_to_json([])

