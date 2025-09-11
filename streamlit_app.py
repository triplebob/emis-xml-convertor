import streamlit as st
from util_modules.status_bar import render_status_bar
from xml_utils import parse_xml_for_emis_guids
from translator import translate_emis_guids_to_snomed
from util_modules.ui_tabs import render_results_tabs
from util_modules.changelog import render_changelog

# Page configuration
st.set_page_config(
    page_title="EMIS XML to SNOMED Translator",
    page_icon="🏥",
    layout="wide"
)

# Main app
def main():
    st.title("🏥 EMIS XML to SNOMED Code Translator")
    st.markdown("*Built for healthcare teams who need accurate and secure EMIS to SNOMED translation*")
    st.markdown("Upload EMIS XML files and translate internal GUIDs to SNOMED codes using the latest MKB lookup table.")
    
    # Load lookup table and render status bar
    lookup_df, emis_guid_col, snomed_code_col = render_status_bar()
    
    # Get lookup table from session state
    lookup_df = st.session_state.get('lookup_df')
    emis_guid_col = st.session_state.get('emis_guid_col')
    snomed_code_col = st.session_state.get('snomed_code_col')
    
    # Main content area
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📁 Upload XML File")
        uploaded_xml = st.file_uploader(
            "Choose EMIS XML file",
            type=['xml'],
            help="Select an EMIS clinical search XML file"
        )
        
        if uploaded_xml is not None:
            if st.button("🔄 Process XML File", type="primary"):
                with st.spinner("Processing XML and translating GUIDs..."):
                    try:
                        # Read and parse XML
                        xml_content = uploaded_xml.read().decode('utf-8')
                        emis_guids = parse_xml_for_emis_guids(xml_content)
                        
                        if not emis_guids:
                            st.error("No EMIS GUIDs found in the XML file")
                            st.stop()
                        
                        # Translate to SNOMED codes
                        translated_codes = translate_emis_guids_to_snomed(
                            emis_guids, 
                            lookup_df, 
                            emis_guid_col, 
                            snomed_code_col
                        )
                        
                        # Store results in session state
                        st.session_state.results = translated_codes
                        st.session_state.xml_filename = uploaded_xml.name
                        
                        # Count all items
                        standalone_clinical = len(translated_codes['clinical'])
                        standalone_medications = len(translated_codes['medications'])
                        clinical_pseudo = len(translated_codes['clinical_pseudo_members'])
                        medication_pseudo = len(translated_codes['medication_pseudo_members'])
                        refsets = len(translated_codes['refsets'])
                        pseudo_refsets = len(translated_codes['pseudo_refsets'])
                        
                        total_items = standalone_clinical + standalone_medications + clinical_pseudo + medication_pseudo + refsets + pseudo_refsets
                        st.success(f"✅ Processed {total_items} items: {standalone_clinical} standalone clinical, {standalone_medications} standalone medications, {clinical_pseudo} clinical in pseudo-refsets, {medication_pseudo} medications in pseudo-refsets, {refsets} refsets, {pseudo_refsets} pseudo-refsets")
                        
                    except Exception as e:
                        st.error(f"Error processing XML: {str(e)}")
        
        else:
            st.info("📤 Upload an XML file to begin processing")
        
        # Add changelog section
        render_changelog()
    
    with col2:
        st.header("📊 Results")
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