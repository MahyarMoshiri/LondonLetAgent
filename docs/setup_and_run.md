# Setup and Running the AI Property Canvassing Agent (V1.5 - Refined)

This document provides instructions on how to set up and run the AI Property Canvassing Agent (refined version with adaptive capabilities) on your local machine (Windows, macOS, Linux) and using Docker for cloud deployment.

## 1. Prerequisites

*   **Python:** Version 3.9 or higher. You can download it from [python.org](https://www.python.org/downloads/). Ensure Python and Pip (Python package installer) are added to your system's PATH.
*   **Git:** (Optional, but recommended for cloning the project) You can download it from [git-scm.com](https://git-scm.com/downloads).
*   **Docker:** (Optional, for containerized deployment, e.g., on Google Cloud) You can download it from [docker.com](https://www.docker.com/products/docker-desktop).
*   **OpenAI API Key:** (Optional but Recommended for full functionality) You will need an API key from OpenAI to use the ChatGPT functionalities for AI-driven query transformation and refinement. You can obtain one from the [OpenAI platform](https://platform.openai.com/account/api-keys). If an API key is not provided, the agent will still function but will rely on basic rule-based query construction and will not be able to adapt its search queries using AI.

## 2. Local Setup (Windows, macOS, Linux)

### 2.1. Clone the Repository (if applicable)

If you have Git installed, clone the project repository:
```bash
git clone <repository_url> # Replace <repository_url> with the actual URL
cd property_canvassing_agent
```
If you downloaded the source code as a ZIP file, extract it and navigate to the project's root directory (`property_canvassing_agent`).

### 2.2. Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

*   **On macOS and Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
*   **On Windows (Command Prompt):**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
*   **On Windows (PowerShell):**
    ```bash
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

After activation, your command prompt should be prefixed with `(venv)`.

### 2.3. Install Dependencies

With the virtual environment activated, install the required Python packages from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 2.4. Install Playwright Browsers

The application uses Playwright for web scraping. After installing dependencies, run:

```bash
playwright install chromium
```
(Or `playwright install` for all default browsers).

### 2.5. Set Up OpenAI API Key (Optional but Recommended)

1.  In the project's root directory (`property_canvassing_agent`), create a file named `.env` (if it doesn't exist).
2.  Add your OpenAI API key to this file:
    ```
    OPENAI_API_KEY="sk-YourActualApiKeyHere"
    ```
3.  If you do not wish to use OpenAI features, the AI module will operate in a fallback mode.
4.  **Important:** Ensure the `.env` file is listed in your `.gitignore` file.

### 2.6. Configuration Files (Site Profiles and Selectors) - NEW for V1.5

The refined agent uses JSON configuration files to manage site-specific parameters and CSS selectors. These are located in the `property_canvassing_agent/configs/` directory:

*   `configs/site_profiles/<site_name>_profile.json`: Contains base URLs, query parameter names, location format preferences, and search heuristics for each supported website.
*   `configs/selectors/<site_name>_selectors.json`: Contains CSS selectors for extracting data from search result pages and detail pages for each site.

**Important:**
*   These files **must be valid JSON**. Do not use comments (e.g., `//` or `/* */`) or trailing commas.
*   If scraping issues occur (e.g., no listings found, incorrect data extracted), these files are the first place to check and update, as website structures change frequently.

### 2.7. Running the Application (Refined V1.5 - CLI)

Navigate to the project's root directory (`property_canvassing_agent`) and ensure your virtual environment is activated.

Run the agent using the following command structure (note: this command should be run from the directory *containing* the `property_canvassing_agent` folder, e.g., `/home/ubuntu` if your project is at `/home/ubuntu/property_canvassing_agent`):

```bash
python -m src.input_module --location "North west london" --property-type "any" --price-max 1500
```

**CLI Options (remain the same as V1):**

*   `--location TEXT`: Target location. **Required.**
*   `--property-type TEXT`: Type of property.
*   `--price-min INTEGER`: Minimum price.
*   `--price-max INTEGER`: Maximum price.
*   `--bedrooms-min INTEGER`: Minimum number of bedrooms.
*   `--keywords TEXT`: Specific keywords (multiple allowed).
*   `--private-only`: Flag for private landlords only.
*   `--exclude-agents`: Flag to exclude agent listings.

## 3. Docker Setup (for Cloud Deployment)

(Instructions remain similar to V1, ensure the `configs` directory is included in the Docker image if not already part of the `COPY` instruction in the `Dockerfile`.)

### 3.1. Build the Docker Image
```bash
docker build -t property-canvassing-agent .
```

### 3.2. Run the Docker Container
```bash
docker run -e OPENAI_API_KEY="your_key" property-canvassing-agent --location "London"
```
Or using `--env-file ./docker.env`.

## 4. Logging and Output

*   **Logging:** Console output and timestamped log files in `property_canvassing_agent/data/logs/`.
*   **Output:** Listings saved in `property_canvassing_agent/data/` (CSV and JSON), timestamped.

## 5. Troubleshooting (Refined for V1.5)

### 5.1. Scraping Issues / No Listings Found
*   **Check Configuration Files:** The primary cause of issues will likely be outdated site profiles (`configs/site_profiles/`) or CSS selectors (`configs/selectors/`). Ensure these are valid JSON and accurately reflect the current website structure.
*   **AI Module (if API key provided):** The AI module attempts to optimize queries. If it's not working as expected, check its logs and the prompts used (if visible in debug logs).
*   **Anti-Bot Measures:** Websites may block scraping. Playwright helps, but advanced measures may still be an issue.
*   **Network Issues:** Standard network troubleshooting.

### 5.2. `ModuleNotFoundError`
Ensure you are in the correct directory when running the `python -m ...` command (the parent directory of `property_canvassing_agent`) and that your virtual environment is activated.

### 5.3. OpenAI API Key Issues
Verify `.env` file placement, name, and key correctness.

### 5.4. JSON Configuration Errors
If the application fails to start or scrapers don't initialize, check the console logs for errors related to parsing JSON files in the `configs/` directory. Ensure all JSON files are valid (no comments, correct quoting, no trailing commas).

This document will be updated as the project evolves.

