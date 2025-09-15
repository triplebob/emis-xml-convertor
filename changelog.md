# Changelog

## Latest Updates

### Export Filtering & UI Improvements - ADDED

**Enhanced Export Options:**
- **Export Filtering**: Clinical Codes and Medications tabs now include radio buttons to export:
  - All Codes (everything)
  - Only Matched (codes that found SNOMED mappings)
  - Only Unmatched (codes that failed to find mappings)
- **Live Export Count**: Shows "📊 X of Y items selected for export" with real-time feedback
- **Smart Filenames**: Downloads get descriptive names (e.g., `clinical_codes_matched_20241212.csv`)

**User Interface Enhancements:**
- **Cancel Processing**: Added cancel button that replaces process button during execution
- **Collapsible Sidebar**: Performance Settings and Version Info are now collapsible for cleaner interface
- **Dynamic Help Text**: Processing strategy help text updates based on selection
- **Improved File Notifications**: File size information now appears as toast notifications instead of full-width bars

**User Benefit:** Users can now export exactly the data they need and have better control over long-running processes with a cleaner, more organized interface.

---

### Enhanced Analytics Dashboard - ADDED
- New Analytics tab with comprehensive processing metrics and quality indicators
- Color-coded performance indicators for quick assessment
- Export functionality for audit reports (JSON, text, CSV formats)
- Improved layout with better space utilization

### Interface Improvements - UPDATED
- Reorganized layout with cleaner header design and improved column structure
- Results section now spans full width for better viewing
- Toast notifications replace persistent success messages
- Better typography hierarchy with appropriately sized headings

### Bug Fixes
- Fixed duplicate medications appearing in multiple tabs
- Fixed EMIS internal codes being misclassified as medications
- Fixed status bar version information not displaying
- Fixed oversized metrics in analytics tab

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