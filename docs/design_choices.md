# Design Choices, Limitations, and V1.5 (Refined) Decisions

This document outlines the key design choices made during the development of Version 1 (V1) and the subsequent V1.5 refinement phase (incorporating adaptive AI-driven capabilities) of the AI-Powered Property Canvassing Agent. It also covers known limitations and the rationale behind certain decisions.

## 1. Core Architecture (V1 Baseline)

The application was initially designed as a modular Python application with distinct components:

*   **Input Module (`input_module.py`):** CLI using `click`.
*   **Scraping Modules (`scraping_module/`):** `playwright` for web scraping, with site-specific classes.
*   **AI Module (`ai_module.py`):** Optional OpenAI API integration for semantic matching.
*   **Filtering Module (`filtering_module.py`):** Logic to filter listings based on user criteria.
*   **Extraction Module (`extraction_module.py`):** `playwright` for detailed listing page data extraction.
*   **Output Module (`output_module.py`):** `pandas` for CSV and `json` for JSON output.
*   **Logging Module (`logging_module.py`):** Python `logging` for console and file logs.
*   **Main Orchestrator (`main.py`):** Coordinates the workflow.
*   **Data Models (`models.py`):** Pydantic models for structured data (e.g., `UserCriteria`, `PropertyListing`).

## 2. V1.5 Refinements: Adaptive AI-Driven Capabilities

The V1.5 phase focused on addressing limitations identified in V1, primarily by making the agent more intelligent and adaptive in handling search queries and interacting with websites.

### 2.1. Externalized Configuration

*   **Site Profiles (`configs/site_profiles/<site_name>_profile.json`):** JSON files now store site-specific information such as base URLs, query parameter names, location formatting preferences, known API endpoints (if any), and search heuristics. This allows for easier updates without code changes.
*   **CSS Selectors (`configs/selectors/<site_name>_selectors.json`):** CSS selectors for scraping are now externalized into JSON files. This is crucial for maintainability, as selectors are the most frequent point of breakage when websites update.
*   **Rationale:** Externalizing these configurations makes the agent more robust and easier to maintain by non-developers or when quick fixes are needed due to website changes.

### 2.2. Enhanced AI Module (`ai_module.py`)

*   **AI-Driven Query Transformation:** The AI module (if an OpenAI API key is provided) is now responsible for transforming user input (e.g., general location like "Northwest London") into site-specific, optimized query parameters based on the site profiles. For example, it can suggest breaking down a broad location into specific postcodes for Gumtree.
*   **Adaptive Query Refinement:** If an initial search on a website yields poor results (e.g., zero listings, errors), the scraper consults the AI module. The AI, using the site profile and the context of the failed query, can suggest modifications (e.g., broadening location, trying alternative keywords, adjusting property type interpretation).
*   **OpenAI Best Practices:** Efforts were made to align with OpenAI guidance for structuring prompts and handling API interactions, though continuous refinement of prompts is always beneficial.
*   **Fallback Mechanism:** If the OpenAI API key is not available or AI interaction fails, the scrapers fall back to using rule-based query construction based on the site profiles and user criteria directly.

### 2.3. Refactored Scraper Modules (`scraping_module/`)

*   **Configuration Loading:** Scrapers now load their respective site profiles and selectors from the JSON configuration files at initialization.
*   **Adaptive Search Loop:** Each scraper implements an adaptive search loop:
    1.  Construct initial search query (potentially AI-transformed).
    2.  Execute search and parse results.
    3.  Validate search outcome (e.g., check for zero results, CAPTCHAs, errors).
    4.  If the outcome is unsatisfactory, consult the AI module for refinement suggestions.
    5.  If refinement is suggested, modify the query and retry (up to a configurable number of attempts).
*   **Improved Obstacle Handling:** Basic handling for common obstacles like cookie banners is driven by selectors defined in the configuration files.

### 2.4. Main Orchestrator (`main.py`) and Input Module (`input_module.py`)

*   The `main.py` orchestrates the flow, now passing the AI module instance and Playwright browser context to each scraper.
*   The `input_module.py` now uses Pydantic models for criteria validation and passes a structured `UserCriteria` object to the main orchestrator.

## 3. Key Technology Choices (V1 & V1.5)

*   **Python, Playwright, OpenAI API, Click, Pandas:** Choices remain consistent from V1.
*   **Pydantic:** Introduced more formally in V1.5 for data validation and settings management (e.g., `UserCriteria` model), improving data integrity.
*   **JSON for Configurations:** Chosen for its human-readability and ease of parsing by Python.

## 4. Design Decisions for V1.5 Functionality

*   **Focus on Adaptability:** The core goal of V1.5 was to move away from rigid scraping logic towards a more adaptive system that can better handle website variations and improve search success.
*   **AI as a Strategic Enhancer:** AI is used to augment the scraping process, not as the sole driver, allowing for fallback mechanisms and use without AI if preferred.
*   **Maintainability of Configurations:** Externalizing site-specific details (profiles, selectors) was a key decision to reduce the need for code changes when websites evolve.

## 5. Known Limitations (V1 & V1.5)

*   **Scraping Fragility:** While externalizing selectors helps, web scraping remains inherently susceptible to website changes. The agent will still require ongoing maintenance of the selector and site profile JSON files.
*   **Anti-Bot Measures:** Advanced anti-bot measures can still block the agent. The V1.5 enhancements do not include sophisticated evasion techniques like advanced proxy rotation or CAPTCHA solving services.
*   **AI Performance and Cost:** The effectiveness of AI-driven query transformation and refinement depends on the quality of prompts, the capabilities of the chosen OpenAI model, and the information in site profiles. Use of the OpenAI API incurs costs.
*   **Complexity of Site Profiles:** Creating and maintaining accurate and comprehensive site profiles requires a good understanding of each target website's search functionality and URL structure.
*   **Dynamic Content & Complex Interactions:** While Playwright handles JavaScript, very complex interactions or non-standard content loading mechanisms might still pose challenges and require custom logic within individual scrapers beyond what the current adaptive loop handles.
*   **Rate Limiting:** No sophisticated rate limiting is implemented. Aggressive scraping could lead to IP blocks.
*   **Current Test Outcome (No Listings Found):** The latest integration test run, while structurally successful (no code errors, configs loaded), did not find listings. This could be due to:
    *   Outdated selectors/site profile details for the specific test criteria.
    *   The AI module not being active (due to no API key in the test environment), thus not performing optimal query transformations.
    *   Actual lack of listings matching the specific test criteria on the websites at the time of the test.
    *   Subtle issues in how the adaptive logic or query parameters are being applied by the scrapers, requiring further debugging with live site interaction.

## 6. Future Considerations (Post-V1.5)

*   **GUI for Configuration Management:** A simple interface to manage site profiles and selectors could make maintenance easier.
*   **Enhanced AI Prompts and Few-Shot Learning:** Refining AI prompts and potentially providing examples in site profiles could improve AI performance.
*   **Visual Scraping / More Resilient Selectors:** Exploring techniques less reliant on specific CSS paths.
*   **Feedback Loop for AI:** Allowing the agent to learn from successful/failed scraping attempts to auto-refine site profiles or AI prompts (a more advanced AI task).
*   **Database Integration:** For storing results, tracking changes, and managing scraping state.

This document reflects the state of the project after the V1.5 refinements. Continuous monitoring and updating of configurations will be necessary for sustained performance.

