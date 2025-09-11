"""
GUI module for EMIS XML to SNOMED Translator
Handles layout, user interface components, and main application flow
"""

import streamlit as st
from util_modules.status_bar import render_status_bar
from util_modules.changelog import render_changelog
from util_modules.ui_tabs import render_results_tabs


def render_header():
    """Render the main application header and tagline."""
    st.title("🏥 EMIS XML to SNOMED Code Translator")
    st.markdown("*Built for healthcare teams who need accurate and secure EMIS to SNOMED translation*")
    st.markdown("Upload EMIS XML files and translate internal GUIDs to SNOMED codes using the latest MKB lookup table.")


def render_upload_section():
    """Render the XML file upload section with validation."""
    st.header("📁 Upload XML File")
    uploaded_xml = st.file_uploader(
        "Choose EMIS XML file",
        type=['xml'],
        help="Select an EMIS clinical search XML file"
    )
    
    return uploaded_xml


def render_processing_section(uploaded_xml, process_callback):
    """
    Render the processing button and handle XML processing.
    
    Args:
        uploaded_xml: Streamlit uploaded file object
        process_callback: Function to call for processing the XML
    """
    if uploaded_xml is not None:
        if st.button("🔄 Process XML File", type="primary"):
            with st.spinner("Processing XML and translating GUIDs..."):
                try:
                    # Read XML content
                    xml_content = uploaded_xml.read().decode('utf-8')
                    
                    # Call the processing callback
                    process_callback(xml_content, uploaded_xml.name)
                    
                except Exception as e:
                    st.error(f"Error processing XML: {str(e)}")
    else:
        st.info("📤 Upload an XML file to begin processing")


def render_footer():
    """Render the application footer with disclaimers."""
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


def render_main_layout(process_callback):
    """
    Render the main application layout with two-column design.
    
    Args:
        process_callback: Function to handle XML processing
    """
    # Header
    render_header()
    
    # Load lookup table and render status bar
    lookup_df, emis_guid_col, snomed_code_col = render_status_bar()
    
    # Get lookup table from session state
    lookup_df = st.session_state.get('lookup_df')
    emis_guid_col = st.session_state.get('emis_guid_col')
    snomed_code_col = st.session_state.get('snomed_code_col')
    
    # Main content area with two columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Upload section
        uploaded_xml = render_upload_section()
        
        # Processing section
        render_processing_section(uploaded_xml, process_callback)
        
        # Changelog section
        render_changelog()
    
    with col2:
        # Results section
        st.header("📊 Results")
        render_results_tabs(st.session_state.get('results'))
    
    # Footer
    render_footer()


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="EMIS XML to SNOMED Translator",
        page_icon="🏥",
        layout="wide"
    )