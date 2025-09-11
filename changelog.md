# Changelog

## Latest Updates

### Advanced Modular Architecture Refactoring - COMPLETED

Based on colleague suggestions, completely reorganized codebase into focused, reusable modules:

**New Core Modules:**
- `gui.py` - Layout and UI components with clean separation of concerns
- `xml_utils.py` - XML parsing and classification logic 
- `lookup.py` - Lookup table operations 
- `audit.py` - Provenance tracking and validation statistics (NEW)

**Support Module Organization:**
- Created `util_modules/` subdirectory for utility components
- Moved `github_loader.py`, `status_bar.py`, `ui_tabs.py`, `changelog.py` to `util_modules/`
- Added `__init__.py` for proper Python package structure
- Updated all import statements across the codebase

**Benefits:**
- Cleaner separation between core business logic and UI utilities
- Improved maintainability and testability
- Enhanced reusability of individual components

### Duplicate Medication Issue - FIXED

- **Problem**: Same medication appearing in both clinical and medication tabs
- **Solution**: Added prioritization logic - medications matched from the lookup table as medications will always take priority over clinical classification
- **Result**: No more duplicates, medications stay in medications tab only

### Clinical Codes Enhancement - ADDED

Now clinical codes display these essential columns:

**From XML:**

- **Include Children**: Shows if search is configured to include child codes (`<includeChildren>true</includeChildren>`)
- **Table Context**: Shows the source table container (e.g., MEDICATION_ISSUES)
- **Column Context**: Shows the column (e.g., DRUGCODE)

**From Lookup Table:**

- **Has Qualifier**: Shows if code has qualifier flag (can accept a numeric value as an additional search entity - for example blood pressure)
- **Is Parent**: Shows if code can have children (is compatible with Include Children)
- **Descendants**: Count of child codes that will be included if Include Children = True
- **Code Type**: Clinical code type (e.g., "Finding", "Procedure", etc.)

**User Benefit:**
Users now see the complete picture of how their search will behave and what codes will be included.

### Changelog System - ADDED

- **New Feature**: Added expandable "What's New" section in the app interface
- **Location**: Positioned below the XML upload section for easy discovery
- **Content**: Shows recent updates, fixes, and enhancements
- **Files**: Created `changelog.md` for detailed history and `changelog.py` for in-app display
- **User Benefit**: Users can quickly see latest improvements without checking external documentation

### Status Bar Version Information - FIXED

- **Problem**: Version information section not displaying despite valid JSON data being available
- **Root Cause**: Empty dictionary `{}` was evaluating to `False` in boolean context when version loading failed
- **Solution**: Enhanced JSON loading with robust error handling and improved boolean checking
- **Additional Fix**: Added UK date formatting and visual alignment improvements
- **Result**: Status bar now properly displays EMIS MKB Release, SNOMED Clinical Terms Version, and Extract Date
- **User Benefit**: Users can now see exactly which version of the lookup table they're using

### EMIS Internal Codes Misclassification - FIXED

- **Problem**: EMIS internal status codes (like "C" for "Current") appearing in medications tab
- **Root Cause**: Medication categorization logic didn't exclude `EMISINTERNAL` code system
- **Example**: Status code "C" from `<codeSystem>EMISINTERNAL</codeSystem>` was classified as "Standard Medication"
- **Solution**: Added explicit exclusion for `EMISINTERNAL` codes in medication detection logic
- **Result**: EMIS internal codes (status, dates, etc.) no longer appear as medications
- **User Benefit**: Cleaner results with only actual medications in the medications tab

---

## Previous Versions

### Initial Modular Architecture - COMPLETED

- Initial refactoring into basic modules (later enhanced with advanced architecture):
  - `data_loader.py` - Lookup table loading and statistics (now `lookup.py`)
  - `xml_parser.py` - XML parsing and EMIS GUID extraction (now `xml_utils.py`)
  - `translator.py` - GUID to SNOMED translation logic
  - `ui_tabs.py` - Results tabs and UI components (now in `util_modules/`)
  - `status_bar.py` - Sidebar status and lookup table display (now in `util_modules/`)

### Status Bar Improvements - COMPLETED

- Separated clinical and medication counts onto individual lines
- Added proper SNOMED version formatting
- Improved JSON data display from lookup table

### Live Application Launch - COMPLETED

- Application now live at: https://emis-xml-convertor.streamlit.app/
- Updated README with prominent live app link
- No installation required for end users