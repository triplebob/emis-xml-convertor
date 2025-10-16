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

def render_status_bar():
    """Render the status bar in the sidebar with lookup table information."""
    with st.sidebar:
        st.header("🗃️ Lookup Table Status")
        
        with st.spinner("Loading lookup table..."):
            try:
                # First try to use cached lookup data
                lookup_df = st.session_state.get('lookup_df')
                emis_guid_col = st.session_state.get('emis_guid_col')
                snomed_code_col = st.session_state.get('snomed_code_col')
                version_info = st.session_state.get('lookup_version_info', {})
                
                # If not in session state, try cache, then fallback to GitHub
                if lookup_df is None or emis_guid_col is None or snomed_code_col is None:
                    # Check if we have cached data
                    cached_data = None
                    if lookup_df is not None and emis_guid_col is not None and snomed_code_col is not None:
                        cached_data = get_cached_emis_lookup(lookup_df, snomed_code_col, emis_guid_col, version_info)
                    
                    if cached_data is None:
                        # Fallback to GitHub API
                        lookup_df, emis_guid_col, snomed_code_col, version_info = load_lookup_table()
                
                # Get lookup statistics
                stats = get_lookup_statistics(lookup_df)
                
                st.success(f"✅ Lookup table loaded: {stats['total_count']:,} total mappings")
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
                with st.sidebar.expander("🎯 What's New - v2.1.0", expanded=False):
                    st.markdown("""
                    **🌳 NHS Terminology Server Integration & Cache Optimization - v2.1.0**
                    
                    Comprehensive NHS England Terminology Server integration with optimized caching architecture.
                    
                    **🆕 NHS Terminology Server Features:**
                    - SNOMED code expansion using NHS England FHIR R4 API
                    - Hierarchical child/descendant concept discovery
                    - EMIS vs Terminology Server child count comparison
                    - Individual code lookup for testing and validation
                    - Multiple export formats: CSV, JSON, XML-ready outputs
                    
                    **📊 Enhanced Export Capabilities:**
                    - Hierarchical JSON export with parent-child relationships
                    - XML Output column for direct EMIS query implementation
                    - Source file tracking in exports for traceability
                    - EMIS Child Count vs Term Server Child Count comparison
                    
                    **⚡ Cache Architecture Overhaul:**
                    - Cache-first approach: local cache → GitHub cache → API fallback
                    - Optimized lookup table loading for faster startup
                    - Session state persistence during download operations
                    - Terminology server results caching for UI performance
                    
                    **🎨 Interface Improvements:**
                    - Real-time connection status monitoring in sidebar
                    - Toast notifications for authentication updates
                    - Results persistence across export operations
                    - Enhanced expansion results table with detailed metrics
                    - Improved filter hierarchy display consistency
                    
                    **🔧 Technical Enhancements:**
                    - Comprehensive codebase audit for GitHub API optimization
                    - Arrow serialization fixes for mixed data types
                    - Enhanced error handling and status reporting
                    - Streamlined UI with removed redundant connection testing
                    
                    ✅ **All improvements maintain full backward compatibility**
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