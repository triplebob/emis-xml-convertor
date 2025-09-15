"""
EMIS XML to SNOMED Code Translator - Streamlit Cloud Optimized
"""

import streamlit as st
from util_modules.status_bar import render_status_bar
from xml_utils import parse_xml_for_emis_guids
from translator import translate_emis_guids_to_snomed
from util_modules.ui_tabs import render_results_tabs
from util_modules.changelog import render_changelog
from util_modules.debug_logger import get_debug_logger, render_debug_controls
from util_modules.performance_optimizer import render_performance_controls, display_performance_metrics
from audit import create_processing_stats
import time
import psutil
import os

# Page configuration
st.set_page_config(
    page_title="EMIS Search XML to SNOMED Translator",
    page_icon="🏥",
    layout="wide"
)


# Main app
def main():
    # Load lookup table and render status bar first
    try:
        lookup_df, emis_guid_col, snomed_code_col = render_status_bar()
    except Exception as e:
        st.error(f"Status bar failed: {e}")
        return
    
    try:
        # Initialize debug logger
        debug_logger = get_debug_logger()
        
        # Render performance controls in sidebar (near top)
        perf_settings = render_performance_controls()
        
        # Render debug controls in sidebar (at bottom)
        render_debug_controls()
    
    except Exception as e:
        st.sidebar.error(f"Error in performance features: {str(e)}")
        st.sidebar.info("Running in basic mode")
        debug_logger = None
        perf_settings = {'strategy': 'Memory Optimized', 'max_workers': 1, 'memory_optimize': True, 'show_metrics': False, 'show_progress': True}
    
    # Get lookup table from session state
    lookup_df = st.session_state.get('lookup_df')
    emis_guid_column = st.session_state.get('emis_guid_col')
    snomed_code_column = st.session_state.get('snomed_code_col')
    
    # Header and upload section in columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Medium-sized title using header
        st.header("🏥 EMIS Search XML to SNOMED Code Translator")
        st.markdown("*Built for healthcare teams who need accurate and secure EMIS to SNOMED translation*")
        st.markdown("Upload EMIS XML files and translate internal GUIDs to SNOMED codes using the latest MKB lookup table.")
    
    with col2:
        st.subheader("📁 Upload XML File")
        uploaded_xml = st.file_uploader(
            "Choose EMIS XML file",
            type=['xml'],
            help="Select an EMIS clinical search XML file"
        )
        
        if uploaded_xml is not None:
            # Initialize processing state
            if 'is_processing' not in st.session_state:
                st.session_state.is_processing = False
            
            # Show process button or cancel button based on state
            if not st.session_state.is_processing:
                if st.button("🔄 Process XML File", type="primary"):
                    st.session_state.is_processing = True
                    st.rerun()
            else:
                if st.button("🛑 Cancel Processing", type="secondary"):
                    st.session_state.is_processing = False
                    st.success("Processing cancelled")
                    st.rerun()
                
                # Show file info as toast notification
                file_size_mb = uploaded_xml.size / (1024 * 1024)
                if file_size_mb > 10:
                    st.toast(f"Large file detected ({file_size_mb:.1f} MB). Processing optimized for cloud.", icon="⚠️")
                elif file_size_mb > 1:
                    st.toast(f"Medium file ({file_size_mb:.1f} MB). Using memory-efficient processing.", icon="📁")
                
                # Process the file
                try:
                    # Read XML content
                    xml_content = uploaded_xml.read().decode('utf-8')
                    
                    # Cloud-optimized processing with progress tracking
                    with st.spinner("Processing XML and translating GUIDs..."):
                        start_time = time.time()
                        
                        # Track memory usage
                        process = psutil.Process(os.getpid())
                        memory_start = process.memory_info().rss / 1024 / 1024  # MB
                        
                        # Show progress if enabled
                        if perf_settings.get('show_progress', True):
                            progress_bar = st.progress(0)
                            progress_bar.progress(10)
                        
                        # Log processing start
                        if debug_logger:
                            debug_logger.log_xml_processing_start(uploaded_xml.name, uploaded_xml.size)
                            debug_logger.log_user_action("process_xml_file", {"filename": uploaded_xml.name})
                        
                        # Parse XML with memory optimization
                        emis_guids = parse_xml_for_emis_guids(xml_content)
                        
                        if perf_settings.get('show_progress', True):
                            progress_bar.progress(40)
                        
                        # Show progress as toast notification
                        st.toast(f"🔍 Found {len(emis_guids)} GUIDs, translating to SNOMED...", icon="🔍")
                        
                        # Log parsing results
                        if debug_logger:
                            debug_logger.log_xml_parsing_result(emis_guids)
                        
                        if not emis_guids:
                            if debug_logger:
                                debug_logger.log_error(Exception("No EMIS GUIDs found"), "XML parsing")
                            st.error("No EMIS GUIDs found in the XML file")
                            return
                        
                        # Translate to SNOMED codes
                        translated_codes = translate_emis_guids_to_snomed(
                            emis_guids, 
                            lookup_df, 
                            emis_guid_column, 
                            snomed_code_column
                        )
                        
                        if perf_settings.get('show_progress', True):
                            progress_bar.progress(80)
                        
                        # Show progress as toast notification
                        st.toast("📊 Creating audit statistics...", icon="📊")
                        
                        # Log classification results
                        if debug_logger:
                            debug_logger.log_classification_results(translated_codes)
                        
                        # Calculate processing time and memory usage
                        processing_time = time.time() - start_time
                        memory_end = process.memory_info().rss / 1024 / 1024  # MB
                        memory_peak = max(memory_start, memory_end)
                        
                        # Create audit statistics
                        audit_stats = create_processing_stats(
                            uploaded_xml.name,
                            xml_content,
                            emis_guids,
                            translated_codes,
                            processing_time
                        )
                        
                        if perf_settings.get('show_progress', True):
                            progress_bar.progress(100)
                        
                        # Store results in session state
                        st.session_state.results = translated_codes
                        st.session_state.xml_filename = uploaded_xml.name
                        st.session_state.audit_stats = audit_stats
                        
                        # Calculate success rate for logging
                        total_found = sum(1 for item in translated_codes.get('clinical', []) if item.get('Mapping Found') == 'Found')
                        total_found += sum(1 for item in translated_codes.get('medications', []) if item.get('Mapping Found') == 'Found')
                        total_items = len(translated_codes['clinical']) + len(translated_codes['medications'])
                        success_rate = (total_found / total_items * 100) if total_items > 0 else 100
                        
                        # Log processing completion
                        if debug_logger:
                            debug_logger.log_processing_complete(processing_time, success_rate)
                        
                        # Clear progress indicators
                        if perf_settings.get('show_progress', True):
                            progress_bar.empty()
                        
                        # Show success with toast notification
                        total_display_items = len(translated_codes['clinical']) + len(translated_codes['medications']) + len(translated_codes.get('clinical_pseudo_members', [])) + len(translated_codes.get('medication_pseudo_members', [])) + len(translated_codes['refsets']) + len(translated_codes.get('pseudo_refsets', []))
                        st.toast(f"✅ Processing complete! {total_display_items} items processed successfully.", icon="✅")
                        
                        # Show performance metrics if enabled
                        if perf_settings.get('show_metrics', False):
                            metrics = {
                                'total_time': processing_time,
                                'processing_strategy': perf_settings.get('strategy', 'Memory Optimized'),
                                'items_processed': total_display_items,
                                'success_rate': success_rate,
                                'memory_peak_mb': memory_peak
                            }
                            display_performance_metrics(metrics)
                        
                        # Reset processing state on completion
                        st.session_state.is_processing = False
                        st.rerun()
                
                except Exception as e:
                    if debug_logger:
                        debug_logger.log_error(e, "XML processing")
                    st.error(f"Error processing XML: {str(e)}")
                    # Reset processing state on error
                    st.session_state.is_processing = False
                    st.rerun()
        
        else:
            st.info("📤 Upload an XML file to begin processing")
        
        # Add changelog section
        render_changelog()
    
    # Full-width results section
    st.subheader("📊 Results")
    render_results_tabs(st.session_state.get('results'))

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
        <p>EMIS XML to SNOMED Code Translator | Upload XML files to translate into SNOMED clinical codes</p>
        <p style='font-size: 0.8em; margin-top: 10px;'>
        EMIS and EMIS Web are trademarks of Optum Inc. This application is not affiliated with, 
        endorsed by, or sponsored by Optum Inc or any of its subsidiaries.
        </p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()