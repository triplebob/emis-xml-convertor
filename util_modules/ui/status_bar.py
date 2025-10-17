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
            
            # Show success message with source indicator
            source_icons = {
                "session": "⚡",
                "cache": "🔐", 
                "github": "📥"
            }
            source_messages = {
                "session": "from session",
                "cache": "from encrypted cache",
                "github": "from GitHub"
            }
            
            icon = source_icons.get(load_source, "✅")
            source_msg = source_messages.get(load_source, "")
            
            st.success(f"{icon} Lookup table loaded {source_msg}: {stats['total_count']:,} total mappings")
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
            with st.sidebar.expander("🎯 What's New - v2.1.1", expanded=False):
                st.markdown("""
                    **🚀 Memory & Performance Optimization - v2.1.1**
                    
                    Critical performance improvements addressing memory constraints and threading issues for production deployment.
                    
                    **⚡ Threading Performance:**
                    - Adaptive worker scaling: 8-20 concurrent workers based on workload size
                    - Resolved ThreadPoolExecutor memory warnings and thread explosion
                    - Optimized worker thread authentication with credential passing
                    - Batched processing to prevent memory overflow in large datasets
                    
                    **🧠 Memory Management:**
                    - Session-based expansion result caching to eliminate repeated API calls
                    - Cache-first loading preserves complete 1.5M+ record lookup table
                    - Enhanced garbage collection for large expansion operations
                    - Streamlit Cloud 2.7GB memory limit compliance
                    
                    **🔧 Terminology Server Fixes:**
                    - Fixed worker thread conflicts with Streamlit caching decorators
                    - Resolved expansion failures (0/131 → 131/131 success rate)
                    - Eliminated infinite loading loops during expansion operations
                    - Improved error handling and status reporting for failed connections
                    
                    **📊 Enhanced User Experience:**
                    - Real-time progress tracking with concurrent worker count display
                    - Cache hit/miss statistics during expansion operations
                    - Toast notifications for successful terminology server connections
                    - Persistent expansion results across UI interactions
                    
                    **🎯 Production Readiness:**
                    - Streamlined for Streamlit Cloud deployment constraints
                    - Comprehensive threading orchestrator pattern implementation
                    - Enhanced stability for high-volume terminology expansions
                    - Maintained full backward compatibility with existing workflows
                    
                    ✅ **Resolves production memory issues while improving performance**
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