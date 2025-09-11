import streamlit as st
import re
from lookup import load_lookup_table, get_lookup_statistics

def render_status_bar():
    """Render the status bar in the sidebar with lookup table information."""
    with st.sidebar:
        st.header("📋 Lookup Table Status")
        st.markdown("Using the latest MKB EMIS GUID to SNOMED mapping table.")
        
        with st.spinner("Loading lookup table..."):
            try:
                lookup_df, emis_guid_col, snomed_code_col, version_info = load_lookup_table()
                
                # Get lookup statistics
                stats = get_lookup_statistics(lookup_df)
                
                st.success(f"✅ Lookup table loaded: {stats['total_count']:,} total mappings")
                st.info(f"🏥 Clinical: {stats['clinical_count']:,}")
                st.info(f"💊 Medications: {stats['medication_count']:,}")
                
                if stats['other_count'] > 0:
                    st.info(f"📊 Other types: {stats['other_count']:,}")
                
                # Display version information if available
                if version_info and len(version_info) > 0:
                    st.markdown("---")
                    st.subheader("📊 Version Information")
                    
                    if 'emis_version' in version_info:
                        st.info(f"🏥 EMIS MKB Release: {version_info['emis_version']}")
                    
                    if 'snomed_version' in version_info:
                        # Parse SNOMED version string
                        # Example: "SNOMED Clinical Terms version: 20250201 [R] (February 2025 Release)"
                        snomed_raw = version_info['snomed_version']
                        
                        # Extract the version number and release info
                        match = re.search(r'(\d{8})\s*\[R\]\s*\(([^)]+)\)', snomed_raw)
                        if match:
                            version_num = match.group(1)
                            # Convert version_num (yyyymmdd) to UK format (dd/mm/yyyy)
                            uk_date = f"{version_num[6:8]}/{version_num[4:6]}/{version_num[0:4]}"
                            st.info(f"📋 SNOMED Clinical Terms\n\u2003\u2002Version {uk_date}")
                        else:
                            st.info(f"📋 SNOMED Clinical Terms\n\u2003{snomed_raw}")
                    
                    if 'extract_date' in version_info:
                        # Convert extract_date to UK format (dd/mm/yyyy), remove time if present
                        extract_date_raw = version_info['extract_date']
                        # Try to extract just the date part (assume format yyyy-mm-dd or yyyy-mm-ddTHH:MM:SS)
                        date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', extract_date_raw)
                        if date_match:
                            uk_extract_date = f"{date_match.group(3)}/{date_match.group(2)}/{date_match.group(1)}"
                            st.info(f"📅\u2003Date of Extraction:\n\u2003\u2003\u2002\u2002{uk_extract_date}")
                        else:
                            st.info(f"📅 Date of Extraction:\n\u2003\u2003\u2002{extract_date_raw}")
                
                # Store in session state for later use
                st.session_state.lookup_df = lookup_df
                st.session_state.emis_guid_col = emis_guid_col
                st.session_state.snomed_code_col = snomed_code_col
                
                return lookup_df, emis_guid_col, snomed_code_col
                
            except Exception as e:
                st.error(f"❌ Error loading lookup table: {str(e)}")
                st.stop()