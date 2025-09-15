import streamlit as st

def render_changelog():
    """Render the changelog in an expandable container."""
    with st.expander("What's New - Recent Updates"):
        st.markdown("""
        ### Export Filtering & UI Improvements - NEW
        
        **Enhanced Export Options:**
        - **Export Filtering**: Clinical Codes and Medications tabs now include options to export:
          - All Codes (everything)
          - Only Matched (codes that found SNOMED mappings)  
          - Only Unmatched (codes that failed to find mappings)
        - **Live Export Count**: Shows real-time count of items selected for export
        - **Smart Filenames**: Downloads get descriptive names (e.g., `clinical_codes_matched.csv`)
        
        **User Interface Enhancements:**
        - **Cancel Processing**: Added cancel button during long-running processes
        - **Collapsible Sidebar**: Performance Settings and Version Info now collapsible
        - **Toast Notifications**: File size info now appears as subtle notifications
        - **Dynamic Help Text**: Processing strategy help updates based on selection
        
        ---
        
        ### Enhanced Analytics Dashboard
        
        - New Analytics tab with processing metrics and quality indicators
        - Color-coded performance indicators for quick assessment  
        - Export functionality for audit reports (JSON, text, CSV formats)
        
        ### Previous Interface Improvements
        
        - Reorganized layout with cleaner design and full-width results
        - Toast notifications for better user experience
        - Improved typography and spacing throughout
        
        ### Bug Fixes
        
        - Fixed duplicate medications appearing in multiple tabs
        - Fixed EMIS internal codes being misclassified as medications
        - Fixed status bar version information not displaying
        - Fixed oversized text in analytics displays
        
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