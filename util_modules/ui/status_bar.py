import streamlit as st
import re
from ..utils.lookup import load_lookup_table, get_lookup_statistics
from ..utils.caching.lookup_cache import get_cached_emis_lookup

# NHS Terminology Server integration
try:
    from ..terminology_server.expansion_ui import render_terminology_server_status
    NHS_TERMINOLOGY_AVAILABLE = True
except ImportError:
    NHS_TERMINOLOGY_AVAILABLE = False

@st.cache_data(ttl=3600, show_spinner=False)
def _get_cached_status_content(lookup_size, version_str, load_source):
    """Cache static status content that doesn't change during session"""
    source_icons = {
        "session": "⚡",
        "cache": "🔐", 
        "github": "📥"
    }
    source_messages = {
        "session": "Session data",
        "cache": "Encrypted cache", 
        "github": "GitHub (fallback)"
    }
    
    icon = source_icons.get(load_source, "📥")
    message = source_messages.get(load_source, "Unknown source")
    
    return f"{icon} Lookup table loaded from {message}: {lookup_size:,} total mappings"

@st.cache_data(ttl=3600, show_spinner=False)
def _get_cached_version_info(version_info_dict):
    """Cache version information that doesn't change during session"""
    if not version_info_dict or len(version_info_dict) == 0:
        return None
    return version_info_dict.copy()

def render_status_bar():
    """Render the status bar in the sidebar with lookup table information."""
    with st.sidebar:
        st.header("🗃️ Lookup Table Status")
        
        # Create status placeholder for dynamic updates
        status_placeholder = st.empty()
        
        try:
            # First try to use cached lookup data
            lookup_df = st.session_state.get('lookup_df')
            emis_guid_col = st.session_state.get('emis_guid_col')
            snomed_code_col = st.session_state.get('snomed_code_col')
            version_info = st.session_state.get('lookup_version_info', {})
            
            load_source = "session"  # Track where data came from
            
            # If not in session state, load lookup table (which will check cache internally)
            if lookup_df is None or emis_guid_col is None or snomed_code_col is None:
                # The load_lookup_table function handles cache checking internally
                lookup_df, emis_guid_col, snomed_code_col, version_info = load_lookup_table()
                
                # Determine the actual source from version_info
                load_source = version_info.get('load_source', 'github') if version_info else 'github'
            
            # Clear status placeholder
            status_placeholder.empty()
                
            # Get lookup statistics
            stats = get_lookup_statistics(lookup_df)
            
            # Use cached status content for better performance
            status_message = _get_cached_status_content(
                stats['total_count'], 
                version_info.get('emis_version', 'Unknown'),
                load_source
            )
            st.success(status_message)
            st.info(f"🩺 SCT Codes: {stats['clinical_count']:,}")
            st.info(f"💊 Medications: {stats['medication_count']:,}")
            
            if stats['other_count'] > 0:
                st.info(f"📊 Other types: {stats['other_count']:,}")
            
            # Display version information if available
            if version_info and len(version_info) > 0:
                with st.sidebar.expander("📊 Version Info", expanded=False):
                    if 'emis_version' in version_info:
                        st.markdown("**🏥 EMIS MKB Release**")
                        st.caption(f"📘 {version_info['emis_version']}")
                        
                        if 'snomed_version' in version_info:
                            # Parse SNOMED version string
                            # Example: "SNOMED Clinical Terms version: 20250201 [R] (February 2025 Release)"
                            snomed_raw = version_info['snomed_version']
                            
                            st.markdown("**📋 SNOMED Clinical Terms**")
                            # Extract the version number and release info
                            match = re.search(r'(\d{8})\s*\[R\]\s*\(([^)]+)\)', snomed_raw)
                            if match:
                                version_num = match.group(1)
                                # Convert version_num (yyyymmdd) to UK format (dd/mm/yyyy)
                                uk_date = f"{version_num[6:8]}/{version_num[4:6]}/{version_num[0:4]}"
                                st.caption(f"📘 {uk_date}")
                            else:
                                st.caption(f"📘 {snomed_raw}")
                        
                        if 'extract_date' in version_info:
                            # Convert extract_date to UK format (dd/mm/yyyy), remove time if present
                            extract_date_raw = version_info['extract_date']
                            
                            st.markdown("**📅 Last DB Update**")
                            # Try to extract just the date part (assume format yyyy-mm-dd or yyyy-mm-ddTHH:MM:SS)
                            date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', extract_date_raw)
                            if date_match:
                                uk_extract_date = f"{date_match.group(3)}/{date_match.group(2)}/{date_match.group(1)}"
                                st.caption(f"📘 {uk_extract_date}")
                            else:
                                st.caption(f"📘 {extract_date_raw}")
                
            # Changelog section - Direct in-app display 
            with st.sidebar.expander("🎯 What's New - v2.1.2", expanded=False):
                st.markdown("""
                    **🧠 Memory Optimization and Performance Fixes - v2.1.2**
                    
                    Comprehensive memory management improvements and performance optimizations addressing export generation issues and dropdown reprocessing.
                    
                    **⚡ Export System Overhaul:**
                    - Converted all export generation from automatic to lazy (button-triggered only)
                    - Eliminated CSV generation on every radio button change in clinical tabs
                    - Removed automatic Excel/JSON generation during report/search selection
                    - Added immediate memory cleanup with garbage collection after downloads
                    
                    **🧠 Memory Management:**
                    - Implemented systematic object deletion and cleanup after export operations
                    - Added session-based caching for sidebar components to prevent re-rendering
                    - Enhanced analysis data caching to eliminate reprocessing on dropdown changes
                    - Reduced export memory consumption by approximately 80% through lazy loading
                    
                    **🔧 Performance Fixes:**
                    - Eliminated complete file reprocessing when switching report/search dropdowns
                    - Removed toast message loops and unnecessary progress indicators during navigation
                    - Fixed search rule visualizer import errors causing application crashes
                    - Restored instant dropdown selection response without processing delays
                    
                    **📊 UI Responsiveness:**
                    - Dropdown selections now execute instantly using cached analysis data
                    - Export operations provide progress spinners and success confirmations
                    - Consolidated scattered imports for proper module organization
                    - Maintained export functionality while improving memory efficiency
                    
                    **🎯 Production Stability:**
                    - Addresses Streamlit Cloud 2.7GB memory constraints through lazy export generation
                    - Prevents memory accumulation across multiple export operations
                    - Improves overall application responsiveness during extended usage sessions
                    - Maintains full export quality while optimizing resource management
                    
                    ✅ **Resolves export-related memory issues and dropdown reprocessing problems**
                    """)
                st.markdown("**[📄 View Full Technical Changelog](https://github.com/triplebob/emis-xml-convertor/blob/main/changelog.md)**")
            
            # Store in session state for later use
            st.session_state.lookup_df = lookup_df
            st.session_state.emis_guid_col = emis_guid_col
            st.session_state.snomed_code_col = snomed_code_col
            
            # Only update version_info if we have valid data (don't overwrite good data with empty dict)
            if version_info and len(version_info) > 0:
                st.session_state.lookup_version_info = version_info
            
            # Add NHS Terminology Server status
            if NHS_TERMINOLOGY_AVAILABLE:
                render_terminology_server_status()
            
            return lookup_df, emis_guid_col, snomed_code_col
                
        except Exception as e:
            st.error(f"❌ Error loading lookup table: {str(e)}")
            st.stop()