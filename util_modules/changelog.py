import streamlit as st

def render_changelog():
    """Render the changelog in an expandable container."""
    with st.expander("What's New - Recent Updates"):
        st.markdown("""
        ### Advanced Modular Architecture Refactoring - COMPLETED
        
        Based on colleague suggestions, completely reorganized codebase into focused, reusable modules:
        
        **New Core Modules:**
        - `gui.py` - Layout and UI components with clean separation of concerns
        - `xml_utils.py` - XML parsing and classification logic 
        - `lookup.py` - Lookup table operations 
        - `audit.py` - Provenance tracking and validation statistics (NEW)
        
        **Support Module Organization:**
        - Created `util_modules/` subdirectory for utility components
        - Moved support modules to organized structure
        - Updated all import statements across the codebase
        
        **Benefits:** Cleaner separation, improved maintainability, professional code organization
        
        ### Duplicate Medication Issue - FIXED
        
        - **Problem**: Same medication appearing in both clinical and medication tabs
        - **Solution**: Added prioritization logic - medications matched from the lookup table as medications will always take priority over clinical classification  
        
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
        
        **User Benefit:** Users now see the complete picture of how their search will behave and what codes will be included.
        
        ### Changelog System - ADDED
        
        - **New Feature**: Added this expandable "What's New" section in the app interface
        - **Location**: Positioned below the XML upload section for easy discovery  
        - **Content**: Shows recent updates, fixes, and enhancements
        - **User Benefit**: Users can quickly see latest improvements without checking external documentation
        
        ### Status Bar Version Information - FIXED
        
        - **Problem**: Version information section not displaying despite valid JSON data being available
        - **Root Cause**: Empty dictionary was evaluating to False in boolean context when version loading failed
        - **Solution**: Enhanced JSON loading with robust error handling and improved boolean checking
        - **Additional Fix**: Added UK date formatting and visual alignment improvements
        - **Result**: Status bar now properly displays EMIS MKB Release, SNOMED Clinical Terms Version, and Extract Date
        - **User Benefit**: Users can now see exactly which version of the lookup table they're using
        
        ### EMIS Internal Codes Misclassification - FIXED
        
        - **Problem**: EMIS internal status codes (like "C" for "Current") appearing in medications tab
        - **Root Cause**: Medication categorization logic didn't exclude EMISINTERNAL code system
        - **Solution**: Added explicit exclusion for EMISINTERNAL codes in medication detection logic
        - **Result**: EMIS internal codes (status, dates, etc.) no longer appear as medications
        - **User Benefit**: Cleaner results with only actual medications in the medications tab
        """)
        
        # Link to full changelog
        st.markdown("---")
        st.markdown("**[View Full Changelog](https://github.com/triplebob/emis-xml-convertor/blob/main/changelog.md)**")