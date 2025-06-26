# Troubleshooting Guide

## 🚨 Common Issues & Solutions

### **Issue: No Results Found**

#### **Symptoms**
- Search completes but returns 0 listings
- Log shows "No listings found"
- CSV/JSON files are empty or contain only headers

#### **Diagnosis Steps**
```bash
# 1. Test with a known working location
python -m src.input_module --location "NW1" --max_price 3000

# 2. Check location expansion
python -c "
import asyncio
from src.main import expand_location_to_postcodes
async def test():
    result = await expand_location_to_postcodes('Your Location', None)
    print(f'Expanded to: {result}')
asyncio.run(test())
"

# 3. Enable debug logging
export LOG_LEVEL=DEBUG
python -m src.input_module --location "NW1" --max_price 2000
```

#### **Solutions**

**A. Location Not Recognized**
```bash
# Use specific postcode instead of area name
python -m src.input_module --location "NW1" --max_price 2000

# Or add your area to location expansion in src/main.py
```

**B. Price Range Too Restrictive**
```bash
# Try broader price range
python -m src.input_module --location "NW1" --max_price 5000

# Remove price filters entirely
python -m src.input_module --location "NW1"
```

**C. Private Filter Too Restrictive**
```bash
# Try without private_only filter
python -m src.input_module --location "NW1" --max_price 2000

# Check if private listings exist
python -m src.input_module --location "NW1" --max_price 2000 --include_agents
```

---

### **Issue: Anti-Bot Detection / Blocked**

#### **Symptoms**
- Browser shows CAPTCHA or "Access Denied"
- Timeout errors after 60 seconds
- Log shows "Anti-bot protection detected"
- Blank pages or unusual content

#### **Diagnosis Steps**
```bash
# 1. Test with minimal scraping
export MAX_PAGES_TO_SCRAPE=1
python -m src.input_module --location "NW1" --max_price 2000

# 2. Check if IP is blocked
curl -I https://www.gumtree.com/

# 3. Test with different location
python -m src.input_module --location "NW2" --max_price 2000
```

#### **Solutions**

**A. Reduce Scraping Intensity**
```python
# In src/scraping_module/gumtree_scraper.py, increase delays:
await asyncio.sleep(random.uniform(5, 10))  # Instead of 2-5 seconds

# Reduce max pages
export MAX_PAGES_TO_SCRAPE=5
```

**B. Change IP Address**
- Use VPN or different network
- Wait 24 hours before retrying
- Use mobile hotspot temporarily

**C. Modify User Agent**
```python
# In src/scraping_module/gumtree_scraper.py, try different user agent:
user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

---

### **Issue: Memory Errors / Crashes**

#### **Symptoms**
- Python crashes with "MemoryError"
- System becomes unresponsive
- Browser processes consume excessive RAM

#### **Solutions**

**A. Reduce Memory Usage**
```bash
# Reduce max pages
export MAX_PAGES_TO_SCRAPE=5

# Close other applications
# Use machine with more RAM (8GB+ recommended)
```

**B. Process Smaller Batches**
```bash
# Instead of "North West London" (11 postcodes), search individually:
python -m src.input_module --location "NW1" --max_price 2000
python -m src.input_module --location "NW2" --max_price 2000
# etc.
```

---

### **Issue: Slow Performance**

#### **Symptoms**
- Searches take 10+ minutes
- Each page takes 30+ seconds to process
- High CPU usage

#### **Solutions**

**A. Optimize Settings**
```python
# Reduce max pages for faster results
export MAX_PAGES_TO_SCRAPE=10

# Use headless mode (should be default)
# Ensure no other browser instances running
```

**B. Network Optimization**
- Use wired internet connection
- Close bandwidth-heavy applications
- Test during off-peak hours

---

### **Issue: Selector Errors**

#### **Symptoms**
- Log shows "Error parsing listing"
- Some listings missing data
- "Element not found" errors

#### **Diagnosis**
```bash
# Test current selectors
python scripts/debug_selectors.py  # If available

# Check if Gumtree changed their HTML structure
# Compare with working HTML sample
```

#### **Solutions**

**A. Update Selectors**
Edit `configs/selectors/gumtree_selectors.json`:
```json
{
  "listing_item_container": "article[data-q=\"search-result\"]",
  "listing_details_link": "a[data-q=\"search-result-anchor\"]",
  "listing_title": "div[data-q=\"tile-title\"]"
}
```

**B. Use Fallback Selectors**
The enhanced scraper includes built-in fallbacks, but you can add more in the code.

---

### **Issue: Installation Problems**

#### **Symptoms**
- `pip install` fails
- `playwright install` fails
- Import errors when running

#### **Solutions**

**A. Python Environment**
```bash
# Ensure Python 3.8+
python --version

# Use virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip
```

**B. Playwright Issues**
```bash
# Install system dependencies (Linux)
sudo apt-get install libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2

# Reinstall Playwright
pip uninstall playwright
pip install playwright
playwright install chromium
```

**C. Permission Issues**
```bash
# Linux/Mac
sudo chown -R $USER:$USER ~/.cache/ms-playwright

# Windows: Run as Administrator
```

---

## 🔍 **Debugging Tools**

### **Enable Debug Logging**
```bash
export LOG_LEVEL=DEBUG
python -m src.input_module --location "NW1" --max_price 2000 2>&1 | tee debug.log
```

### **Test Individual Components**
```python
# Test location expansion
from src.main import expand_location_to_postcodes
result = await expand_location_to_postcodes("North West London", None)
print(result)

# Test scraper initialization
from src.scraping_module.gumtree_scraper import GumtreeScraper
from src.ai_module import AIModule
scraper = GumtreeScraper(AIModule(), None)
```

### **Monitor Resource Usage**
```bash
# Monitor memory and CPU
top -p $(pgrep -f python)

# Monitor network
netstat -i

# Check disk space
df -h
```

### **Browser Debugging**
```python
# In gumtree_scraper.py, enable non-headless mode for debugging:
browser = await p.chromium.launch(headless=False)  # Can see what's happening
```

---

## 📊 **Performance Benchmarks**

### **Expected Performance**
| Metric | Normal | Slow | Very Slow |
|--------|--------|------|-----------|
| **Time per page** | 10-20s | 30-45s | 60s+ |
| **Total search time** | 3-8 min | 10-15 min | 20+ min |
| **Memory usage** | 500MB-1GB | 1-2GB | 2GB+ |
| **Results per page** | 20-25 | 15-20 | <15 |

### **When to Be Concerned**
- ⚠️ More than 60 seconds per page
- ⚠️ More than 20 minutes total search time
- ⚠️ More than 2GB memory usage
- ⚠️ Less than 10 results per page

---

## 🆘 **Getting Help**

### **Before Asking for Help**
1. ✅ Check this troubleshooting guide
2. ✅ Enable debug logging and review logs
3. ✅ Test with minimal parameters (single postcode, high price limit)
4. ✅ Verify your internet connection and IP isn't blocked
5. ✅ Try on a different machine/network if possible

### **Information to Include**
When reporting issues, please include:

```bash
# System information
python --version
pip list | grep -E "(playwright|beautifulsoup4|pandas)"
uname -a  # Linux/Mac
systeminfo  # Windows

# Command that failed
python -m src.input_module --location "NW1" --max_price 2000 --private_only

# Error logs (last 50 lines)
tail -50 logs/property_agent_$(date +%Y-%m-%d).log

# Expected vs actual results
# Expected: 50+ listings
# Actual: 0 listings
```

### **Support Channels**
1. **GitHub Issues**: For bugs and feature requests
2. **Documentation**: Check README.md and docs/
3. **Community**: Stack Overflow with tag `property-scraping`

---

## 🔧 **Advanced Troubleshooting**

### **Network Issues**
```bash
# Test Gumtree connectivity
curl -v https://www.gumtree.com/search?search_category=property-to-rent

# Check DNS resolution
nslookup www.gumtree.com

# Test with different DNS
# Google DNS: 8.8.8.8, 8.8.4.4
# Cloudflare DNS: 1.1.1.1, 1.0.0.1
```

### **Browser Issues**
```bash
# Clear Playwright cache
rm -rf ~/.cache/ms-playwright

# Reinstall browsers
playwright install --force chromium

# Test browser manually
playwright open https://www.gumtree.com
```

### **Configuration Issues**
```bash
# Verify configuration files exist
ls -la configs/site_profiles/gumtree_profile.json
ls -la configs/selectors/gumtree_selectors.json

# Test with minimal configuration
# The enhanced scraper includes built-in defaults
```

---

**Still having issues?** Create a GitHub issue with the information above, and we'll help you get it working! 🚀

