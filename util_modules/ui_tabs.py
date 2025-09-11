import streamlit as st
import pandas as pd
import io
from datetime import datetime

def render_summary_tab(results):
    """Render the summary tab with statistics."""
    # Summary statistics
    clinical_count = len(results['clinical'])
    medication_count = len(results['medications'])
    clinical_pseudo_count = len(results.get('clinical_pseudo_members', []))
    medication_pseudo_count = len(results.get('medication_pseudo_members', []))
    refset_count = len(results['refsets'])
    pseudo_refset_count = len(results.get('pseudo_refsets', []))
    
    total_count = clinical_count + medication_count + refset_count + pseudo_refset_count
    
    col1_summary, col2_summary, col3_summary, col4_summary, col5_summary = st.columns(5)
    
    with col1_summary:
        st.metric("Total Containers", total_count)
    with col2_summary:
        st.metric("Standalone Clinical", clinical_count)
    with col3_summary:
        st.metric("Standalone Medications", medication_count)
    with col4_summary:
        st.metric("True Refsets", refset_count)
    with col5_summary:
        st.metric("Pseudo-Refsets", pseudo_refset_count, delta_color="inverse")
    
    # Additional info rows with counts
    col1_extra, col2_extra = st.columns(2)
    
    with col1_extra:
        if clinical_pseudo_count > 0:
            st.info(f"📋 {clinical_pseudo_count} clinical codes are part of pseudo-refsets")
        else:
            st.success("📋 0 clinical codes in pseudo-refsets")
    
    with col2_extra:
        if medication_pseudo_count > 0:
            st.info(f"💊 {medication_pseudo_count} medications are part of pseudo-refsets")
        else:
            st.success("💊 0 medications in pseudo-refsets")
    
    # Success rates
    if clinical_count > 0:
        clinical_found = len([c for c in results['clinical'] if c['Mapping Found'] == 'Found'])
        st.info(f"Standalone clinical codes mapping success: {clinical_found}/{clinical_count} ({clinical_found/clinical_count*100:.1f}%)")
    
    if medication_count > 0:
        med_found = len([m for m in results['medications'] if m['Mapping Found'] == 'Found'])
        st.info(f"Standalone medications mapping success: {med_found}/{medication_count} ({med_found/medication_count*100:.1f}%)")
    
    if refset_count > 0:
        st.info(f"True refsets: {refset_count} (automatically mapped)")
    
    if pseudo_refset_count > 0:
        st.warning(f"⚠️ Pseudo-refsets found: {pseudo_refset_count} - These cannot be referenced directly in EMIS by SNOMED code")

def render_clinical_codes_tab(results):
    """Render the clinical codes tab."""
    st.subheader("Clinical Codes")
    
    # Standalone clinical codes section
    st.markdown("### 📋 Standalone Clinical Codes")
    st.info("These are clinical codes that are NOT part of any pseudo-refset and can be used directly.")
    
    if results['clinical']:
        clinical_df = pd.DataFrame(results['clinical'])
        
        # Color code based on mapping success
        def highlight_clinical(row):
            if row['Mapping Found'] == 'Found':
                return ['background-color: #d4edda'] * len(row)  # Light green
            else:
                return ['background-color: #f8d7da'] * len(row)  # Light red
        
        styled_clinical = clinical_df.style.apply(highlight_clinical, axis=1)
        st.dataframe(styled_clinical, use_container_width=True)
        
        # Download standalone clinical codes only
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"standalone_clinical_codes_{st.session_state.xml_filename}_{timestamp}.csv"
        
        csv_buffer = io.StringIO()
        clinical_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download Standalone Clinical Codes CSV",
            data=csv_buffer.getvalue(),
            file_name=filename,
            mime="text/csv"
        )
    else:
        st.info("No standalone clinical codes found in this XML file")
    
    # Pseudo-refset member clinical codes section
    st.markdown("### ⚠️ Clinical Codes in Pseudo-Refsets")
    st.warning("These clinical codes are part of pseudo-refsets (refsets EMIS does not natively support yet), and can only be used by listing all member codes. Export these from the 'Pseudo-Refset Members' tab.")
    
    if results.get('clinical_pseudo_members'):
        clinical_pseudo_df = pd.DataFrame(results['clinical_pseudo_members'])
        
        # Color code pseudo-refset members differently
        def highlight_pseudo_clinical(row):
            if row['Mapping Found'] == 'Found':
                return ['background-color: #fff3cd'] * len(row)  # Light yellow/orange
            else:
                return ['background-color: #f8cecc'] * len(row)  # Light red/orange
        
        styled_pseudo_clinical = clinical_pseudo_df.style.apply(highlight_pseudo_clinical, axis=1)
        st.dataframe(styled_pseudo_clinical, use_container_width=True)
    else:
        st.success("✅ No clinical codes found in pseudo-refsets")

def render_medications_tab(results):
    """Render the medications tab."""
    st.subheader("Medications")
    
    # Standalone medications section
    st.markdown("### 💊 Standalone Medications")
    st.info("These are medications that are NOT part of any pseudo-refset and can be used directly.")
    
    if results['medications']:
        medications_df = pd.DataFrame(results['medications'])
        
        # Color code based on mapping success
        def highlight_medications(row):
            if row['Mapping Found'] == 'Found':
                return ['background-color: #d4edda'] * len(row)  # Light green
            else:
                return ['background-color: #f8d7da'] * len(row)  # Light red
        
        styled_medications = medications_df.style.apply(highlight_medications, axis=1)
        st.dataframe(styled_medications, use_container_width=True)
        
        # Download standalone medications only
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"standalone_medications_{st.session_state.xml_filename}_{timestamp}.csv"
        
        csv_buffer = io.StringIO()
        medications_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download Standalone Medications CSV",
            data=csv_buffer.getvalue(),
            file_name=filename,
            mime="text/csv"
        )
    else:
        st.info("No standalone medications found in this XML file")
    
    # Pseudo-refset member medications section  
    st.markdown("### ⚠️ Medications in Pseudo-Refsets")
    st.warning("These medications are part of pseudo-refsets (refsets EMIS does not natively support yet), and can only be used by listing all member codes. Export these from the 'Pseudo-Refset Members' tab.")
    st.info("**Medication Type Flags:** SCT_CONST (Constituent), SCT_DRGGRP (Drug Group), SCT_PREP (Preparation)")
    
    if results.get('medication_pseudo_members'):
        medication_pseudo_df = pd.DataFrame(results['medication_pseudo_members'])
        
        # Color code pseudo-refset members differently
        def highlight_pseudo_medications(row):
            if row['Mapping Found'] == 'Found':
                return ['background-color: #fff3cd'] * len(row)  # Light yellow/orange
            else:
                return ['background-color: #f8cecc'] * len(row)  # Light red/orange
        
        styled_pseudo_medications = medication_pseudo_df.style.apply(highlight_pseudo_medications, axis=1)
        st.dataframe(styled_pseudo_medications, use_container_width=True)
    else:
        st.success("✅ No medications found in pseudo-refsets")

def render_refsets_tab(results):
    """Render the refsets tab."""
    st.subheader("Refsets")
    if results['refsets']:
        refsets_df = pd.DataFrame(results['refsets'])
        
        # Refsets are always green (automatically mapped)
        def highlight_refsets(row):
            return ['background-color: #d4edda'] * len(row)  # Light green
        
        styled_refsets = refsets_df.style.apply(highlight_refsets, axis=1)
        st.dataframe(styled_refsets, use_container_width=True)
        
        # Download refsets
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"refsets_{st.session_state.xml_filename}_{timestamp}.csv"
        
        csv_buffer = io.StringIO()
        refsets_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download Refsets CSV",
            data=csv_buffer.getvalue(),
            file_name=filename,
            mime="text/csv"
        )
    else:
        st.info("No refsets found in this XML file")

def render_pseudo_refsets_tab(results):
    """Render the pseudo-refsets tab."""
    st.subheader("Pseudo-Refset Containers ⚠️")
    st.info("""
    **What are Pseudo-Refsets?**
    - These are valueSet containers that hold multiple clinical codes but are NOT stored in the EMIS database as referenceable refsets
    - They can only be used by manually listing all their member codes - you cannot reference them directly by their native SNOMED code as EMIS does not natively support them yet 
    - Common examples: valuesets with '_COD' suffix like 'ASTTRT_COD'
    - See the 'Pseudo-Refset Members' tab to view all codes within each pseudo-refset
    """)
    
    if results.get('pseudo_refsets'):
        pseudo_refsets_df = pd.DataFrame(results['pseudo_refsets'])
        
        # Pseudo-refsets are highlighted in orange (warning)
        def highlight_pseudo_refsets(row):
            return ['background-color: #fff3cd'] * len(row)  # Light orange/yellow
        
        styled_pseudo_refsets = pseudo_refsets_df.style.apply(highlight_pseudo_refsets, axis=1)
        st.dataframe(styled_pseudo_refsets, use_container_width=True)
        
        # Download pseudo-refsets
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pseudo_refset_containers_{st.session_state.xml_filename}_{timestamp}.csv"
        
        csv_buffer = io.StringIO()
        pseudo_refsets_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download Pseudo-Refset Containers CSV",
            data=csv_buffer.getvalue(),
            file_name=filename,
            mime="text/csv"
        )
        
        st.warning("""
        **Important Usage Notes:**
        - These pseudo-refset containers cannot be referenced directly in EMIS clinical searches
        - To use them, you must manually list all individual member codes within each valueset
        - View the 'Pseudo-Refset Members' tab to see all member codes for each container
        """)
    else:
        st.success("✅ No pseudo-refsets found - all codes are properly mapped!")

def render_pseudo_refset_members_tab(results):
    """Render the pseudo-refset members tab."""
    st.subheader("Pseudo-Refset Member Codes")
    st.info("These are the individual clinical codes contained within each pseudo-refset. These codes were moved here from the Clinical Codes tab as within the uploaded search XML ruleset they belong to pseudo-refsets.")
    
    if results.get('pseudo_refset_members'):
        # Create expandable sections for each pseudo-refset
        for valueset_guid, members in results['pseudo_refset_members'].items():
            if members:  # Only show if there are members
                # Get the pseudo-refset info for the title
                pseudo_refset_info = next((pr for pr in results['pseudo_refsets'] if pr['ValueSet GUID'] == valueset_guid), None)
                if pseudo_refset_info:
                    refset_name = pseudo_refset_info['ValueSet Description']
                    member_count = len(members)
                    
                    with st.expander(f"🔍 {refset_name} ({member_count} member codes)"):
                        members_df = pd.DataFrame(members)
                        
                        # Color code based on mapping success
                        def highlight_members(row):
                            if row['Mapping Found'] == 'Found':
                                return ['background-color: #d4edda'] * len(row)  # Light green
                            else:
                                return ['background-color: #f8d7da'] * len(row)  # Light red
                        
                        styled_members = members_df.style.apply(highlight_members, axis=1)
                        st.dataframe(styled_members, use_container_width=True)
                        
                        # Individual download for this pseudo-refset's members
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        safe_name = refset_name.replace(' ', '_').replace('/', '_')
                        filename = f"members_{safe_name}_{timestamp}.csv"
                        
                        csv_buffer = io.StringIO()
                        members_df.to_csv(csv_buffer, index=False)
                        
                        st.download_button(
                            label=f"📥 Download {refset_name} Members",
                            data=csv_buffer.getvalue(),
                            file_name=filename,
                            mime="text/csv",
                            key=f"download_{valueset_guid}"
                        )
        
        # Download all pseudo-refset members combined
        st.subheader("Download All Members")
        all_members = []
        for members in results['pseudo_refset_members'].values():
            all_members.extend(members)
        
        if all_members:
            all_members_df = pd.DataFrame(all_members)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"all_pseudo_refset_members_{st.session_state.xml_filename}_{timestamp}.csv"
            
            csv_buffer = io.StringIO()
            all_members_df.to_csv(csv_buffer, index=False)
            
            st.download_button(
                label="📥 Download All Pseudo-Refset Members CSV",
                data=csv_buffer.getvalue(),
                file_name=filename,
                mime="text/csv"
            )
    else:
        st.info("No pseudo-refset members found.")

def render_results_tabs(results):
    """Render all result tabs."""
    if 'results' in st.session_state:
        results = st.session_state.results
        
        # Create tabs for different types
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Summary", "🏥 Clinical Codes", "💊 Medications", "📊 Refsets", "⚠️ Pseudo-Refsets", "📝 Pseudo-Refset Members"])
        
        with tab1:
            render_summary_tab(results)
        
        with tab2:
            render_clinical_codes_tab(results)
        
        with tab3:
            render_medications_tab(results)
        
        with tab4:
            render_refsets_tab(results)
        
        with tab5:
            render_pseudo_refsets_tab(results)
        
        with tab6:
            render_pseudo_refset_members_tab(results)
    else:
        st.info("Results will appear here after processing an XML file")