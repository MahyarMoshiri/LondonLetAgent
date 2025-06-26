# Enhanced Property Canvassing Agent - Setup Guide

## 🚀 Quick Start (5 minutes)

### Step 1: Environment Setup
```bash
# Ensure Python 3.8+ is installed
python --version

# Clone the repository
git clone <your-repo-url>
cd property_canvassing_agent_enhanced

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers (required for scraping)
playwright install chromium

# Verify installation
playwright --version
```

### Step 3: Test Installation
```bash
# Create data directory
mkdir -p data

# Run a quick test
python -m src.input_module --location "NW1" --max_price 1500 --private_only

# Check results
ls data/
```

## 🔧 Advanced Configuration

### Environment Variables
Create a `.env` file for optional configuration:
```bash
# .env file
LOG_LEVEL=INFO
MAX_PAGES_TO_SCRAPE=15
OPENAI_API_KEY=your_key_here  # Optional, for AI features
```

### Custom Configuration Files

#### Site Profile (`configs/site_profiles/gumtree_profile.json`)
```json
{
  "base_search_url": "https://www.gumtree.com/search",
  "seller_type_options": {
    "private_only": "private"
  },
  "query_parameters": {
    "search_category_key": "search_category",
    "search_category_value": "property-to-rent"
  }
}
```

#### Selectors (`configs/selectors/gumtree_selectors.json`)
```json
{
  "listing_item_container": "article[data-q=\"search-result\"]",
  "listing_details_link": "a[data-q=\"search-result-anchor\"]",
  "listing_title": "div[data-q=\"tile-title\"]",
  "listing_description_spans": "div[data-q=\"tile-description\"] span",
  "listing_location": "div[data-q=\"tile-location\"]",
  "listing_price": "div[data-testid=\"price\"]",
  "listing_posted_date": "div[data-q=\"tile-datePosted\"]"
}
```

## 🎯 Usage Examples

### Basic Searches
```bash
# Search North West London for private rentals under £2000
python -m src.input_module --location "North West London" --max_price 2000 --private_only

# Search specific postcode for flats
python -m src.input_module --location "NW1" --property_type "flat" --bedrooms_min 1

# Search with keywords
python -m src.input_module --location "Camden" --keywords "modern,garden" --max_price 2500
```

### Advanced Searches
```bash
# Comprehensive search with all filters
python -m src.input_module \
  --location "East London" \
  --property_type "flat" \
  --min_price 1200 \
  --max_price 2500 \
  --bedrooms_min 2 \
  --keywords "modern,balcony,parking" \
  --private_only \
  --exclude_agents

# Multiple location search (run separately)
python -m src.input_module --location "NW1" --max_price 2000 --private_only
python -m src.input_module --location "NW2" --max_price 2000 --private_only
python -m src.input_module --location "NW3" --max_price 2000 --private_only
```

### Programmatic Usage
```python
import asyncio
from src.main import run_agent_with_criteria
from src.models import UserCriteria

async def search_properties():
    criteria = UserCriteria(
        location="North West London",
        property_type="flat",
        price_min=1000,
        price_max=2200,
        bedrooms_min=1,
        keywords=["modern", "transport"],
        private_only=True,
        exclude_agents=True
    )
    
    await run_agent_with_criteria(criteria)

# Run the search
asyncio.run(search_properties())
```

## 📊 Performance Tuning

### For Maximum Results
```python
# In your code or environment
MAX_PAGES_TO_SCRAPE = 20  # Scrape up to 20 pages (500+ listings)
```

### For Faster Searches
```python
MAX_PAGES_TO_SCRAPE = 5   # Scrape only 5 pages (125+ listings)
```

### For Anti-Bot Avoidance
```python
MAX_PAGES_TO_SCRAPE = 10  # Conservative approach
# Add longer delays between requests
```

## 🔍 Location Expansion

The enhanced agent automatically expands location searches:

### Supported Expansions
- **"North West London"** → NW1, NW2, NW3, NW4, NW5, NW6, NW7, NW8, NW9, NW10, NW11
- **"North London"** → N1, N2, N3, ..., N22
- **"East London"** → E1, E2, E3, ..., E20
- **"South West London"** → SW1, SW2, SW3, ..., SW20
- **"South East London"** → SE1, SE2, SE3, ..., SE28
- **"West London"** → W1, W2, W3, ..., W14
- **"Central London"** → W1, WC1, WC2, EC1, EC2, EC3, EC4, SW1

### Specific Areas
- **"Camden"** → NW1, NW3, NW5
- **"Islington"** → N1, N5, N7
- **"Hackney"** → E2, E5, E8, E9
- **"Kensington"** → W8, W10, W11, SW3, SW5, SW7

### Custom Expansion
To add your own location expansions, edit `src/main.py`:
```python
london_areas = {
    "your_area": ["POSTCODE1", "POSTCODE2", "POSTCODE3"],
    # ... existing areas
}
```

## 📁 Output Management

### File Naming
Files are automatically named with timestamps:
```
gumtree_properties_enhanced_1640995200.csv
gumtree_properties_enhanced_1640995200.json
```

### Custom Output Directory
```python
# In src/main.py, modify:
output_module = OutputModule("your_custom_directory")
```

### Data Processing
```python
import pandas as pd

# Load results
df = pd.read_csv("data/gumtree_properties_enhanced_1640995200.csv")

# Filter private listings only
private_df = df[df['poster_type'] == 'Private']

# Filter by price range
affordable_df = df[df['normalized_price'] <= 2000]

# Group by location
location_counts = df.groupby('location').size()
```

## 🛠 Maintenance

### Updating Selectors
If Gumtree changes their website structure:

1. **Test current selectors**:
```bash
python scripts/test_selectors.py
```

2. **Update selectors** in `configs/selectors/gumtree_selectors.json`

3. **Test with live data**:
```bash
python -m src.input_module --location "NW1" --max_price 1500
```

### Monitoring Performance
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m src.input_module --location "NW1" --max_price 1500

# Check logs
tail -f logs/property_agent_$(date +%Y-%m-%d).log
```

### Regular Maintenance Tasks
1. **Weekly**: Test with a small search to ensure functionality
2. **Monthly**: Update Playwright browsers: `playwright install chromium`
3. **Quarterly**: Review and update location expansions
4. **As needed**: Update selectors if Gumtree changes their UI

## 🚨 Troubleshooting

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed troubleshooting guide.

## 📞 Support

1. **Check logs**: `logs/property_agent_YYYY-MM-DD.log`
2. **Test with minimal search**: `python -m src.input_module --location "NW1" --max_price 1500`
3. **Verify selectors**: Run selector test script
4. **Check GitHub issues**: Look for similar problems
5. **Create new issue**: Include logs and search parameters

---

**Ready to get started?** Run your first enhanced search:
```bash
python -m src.input_module --location "North West London" --max_price 2000 --private_only
```

