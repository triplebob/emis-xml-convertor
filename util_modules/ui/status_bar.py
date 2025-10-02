import streamlit as st
import re
from ..utils.lookup import load_lookup_table, get_lookup_statistics

def render_status_bar():
    """Render the status bar in the sidebar with lookup table information."""
    with st.sidebar:
        st.header("🗃️ Lookup Table Status")
        
        with st.spinner("Loading lookup table..."):
            try:
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
                with st.sidebar.expander("🎯 What's New - v2.0.0", expanded=False):
                    st.markdown("""
                    **🔧 Complete Application Rebuild**
                    
                    The Unofficial EMIS XML Toolkit represents a complete transformation into a comprehensive EMIS XML analysis platform.
                    
                    **📊 New 5-Tab Interface:**
                    - **Clinical Codes**: Enhanced with refset support
                    - **Search Analysis**: Rule logic browser (NEW)
                    - **List Reports**: Column structure analysis (NEW)  
                    - **Audit Reports**: Multi-population analysis (NEW)
                    - **Aggregate Reports**: Statistical analysis (NEW)
                    
                    **🔍 Advanced Features:**
                    - Folder navigation and dependency visualization
                    - Complex EMIS pattern support (baseCriteriaGroup, linked criteria)
                    - SNOMED refset handling with direct code translation
                    - Comprehensive export system (Excel, CSV, JSON)
                    
                    **⚡ Performance:**
                    - Single XML parse (eliminates redundant processing)
                    - Dictionary-based lookups (100x faster)
                    - Progress tracking for large files
                    
                    ✅ **No Breaking Changes** - All existing workflows preserved
                    """)
                    st.markdown("**[📄 View Full Technical Changelog](https://github.com/triplebob/emis-xml-convertor/blob/main/changelog.md)**")
                
                # Store in session state for later use
                st.session_state.lookup_df = lookup_df
                st.session_state.emis_guid_col = emis_guid_col
                st.session_state.snomed_code_col = snomed_code_col
                st.session_state.version_info = version_info
                
                return lookup_df, emis_guid_col, snomed_code_col
                
            except Exception as e:
                st.error(f"❌ Error loading lookup table: {str(e)}")
                st.stop()