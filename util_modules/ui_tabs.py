import streamlit as st
import pandas as pd
import io
from datetime import datetime
import json
from .ui_helpers import (
    render_section_with_data, 
    render_metrics_row, 
    render_success_rate_metric,
    render_download_button,
    get_success_highlighting_function,
    get_warning_highlighting_function,
    create_expandable_sections,
    render_info_section
)

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
    
    # Processing summary from main app
    if hasattr(st.session_state, 'xml_filename'):
        # Calculate all items including pseudo-refset members
        standalone_clinical = len(results['clinical'])
        standalone_medications = len(results['medications'])
        clinical_pseudo = len(results.get('clinical_pseudo_members', []))
        medication_pseudo = len(results.get('medication_pseudo_members', []))
        total_items = standalone_clinical + standalone_medications + clinical_pseudo + medication_pseudo + refset_count + pseudo_refset_count
        
        st.success(f"✅ Processed {total_items} items: {standalone_clinical} standalone clinical, {standalone_medications} standalone medications, {clinical_pseudo} clinical in pseudo-refsets, {medication_pseudo} medications in pseudo-refsets, {refset_count} refsets, {pseudo_refset_count} pseudo-refsets")
    
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
    # Standalone clinical codes section
    render_section_with_data(
        title="📋 Standalone Clinical Codes",
        data=results['clinical'],
        info_text="These are clinical codes that are NOT part of any pseudo-refset and can be used directly.",
        empty_message="No standalone clinical codes found in this XML file",
        download_label="📥 Download Standalone Clinical Codes CSV",
        filename_prefix="standalone_clinical_codes",
        highlighting_function=get_success_highlighting_function()
    )
    
    # Pseudo-refset member clinical codes section
    st.subheader("⚠️ Clinical Codes in Pseudo-Refsets")
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
        st.dataframe(styled_pseudo_clinical, width='stretch')
    else:
        st.success("✅ No clinical codes found in pseudo-refsets")

def render_medications_tab(results):
    # Standalone medications section
    render_section_with_data(
        title="💊 Standalone Medications",
        data=results['medications'],
        info_text="These are medications that are NOT part of any pseudo-refset and can be used directly.",
        empty_message="No standalone medications found in this XML file",
        download_label="📥 Download Standalone Medications CSV",
        filename_prefix="standalone_medications",
        highlighting_function=get_success_highlighting_function()
    )
    
    # Pseudo-refset member medications section  
    render_info_section(
        title="⚠️ Medications in Pseudo-Refsets",
        content="These medications are part of pseudo-refsets (refsets EMIS does not natively support yet), and can only be used by listing all member codes. Export these from the 'Pseudo-Refset Members' tab.",
        section_type="warning"
    )
    
    # Add helpful tooltip information
    with st.expander("ℹ️ Medication Type Flags Help"):
        st.markdown("""
        **Medication Type Flags:**
        - **SCT_CONST** (Constituent): Active ingredients or components
        - **SCT_DRGGRP** (Drug Group): Groups of related medications  
        - **SCT_PREP** (Preparation): Specific medication preparations
        - **Standard Medication**: General medication codes from lookup table
        """)
    
    st.info("**Tip:** Use the Analytics tab to view detailed mapping statistics and quality metrics.")
    
    if results.get('medication_pseudo_members'):
        medication_pseudo_df = pd.DataFrame(results['medication_pseudo_members'])
        
        # Color code pseudo-refset members differently
        def highlight_pseudo_medications(row):
            if row['Mapping Found'] == 'Found':
                return ['background-color: #fff3cd'] * len(row)  # Light yellow/orange
            else:
                return ['background-color: #f8cecc'] * len(row)  # Light red/orange
        
        styled_pseudo_medications = medication_pseudo_df.style.apply(highlight_pseudo_medications, axis=1)
        st.dataframe(styled_pseudo_medications, width='stretch')
    else:
        st.success("✅ No medications found in pseudo-refsets")

def render_refsets_tab(results):
    if results['refsets']:
        refsets_df = pd.DataFrame(results['refsets'])
        
        # Refsets are always green (automatically mapped)
        def highlight_refsets(row):
            return ['background-color: #d4edda'] * len(row)  # Light green
        
        styled_refsets = refsets_df.style.apply(highlight_refsets, axis=1)
        st.dataframe(styled_refsets, width='stretch')
        
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
    render_info_section(
        title="⚠️ Pseudo-Refset Containers",
        content="",  # We'll use expandable help section instead
        section_type="info"
    )
    
    # Add comprehensive help section
    with st.expander("ℹ️ Understanding Pseudo-Refsets - Click to expand"):
        st.markdown("""
        ### What are Pseudo-Refsets?
        
        **Definition:**
        - ValueSet containers that hold multiple clinical codes
        - **NOT** stored in the EMIS database as referenceable refsets
        - Cannot be referenced directly by their SNOMED code in EMIS clinical searches
        
        **Usage Limitations:**
        - Can only be used by manually listing ALL member codes
        - You cannot reference them directly by their container SNOMED code
        - EMIS does not natively support these as queryable refsets yet
        
        **Common Patterns:**
        - ValueSets with '_COD' suffix (e.g., 'ASTTRT_COD')
        - Complex clinical groupings that don't map to standard SNOMED refsets
        - Legacy EMIS value sets that predate current refset standards
        
        **How to Use:**
        1. Export the pseudo-refset members from the 'Pseudo-Refset Members' tab
        2. Use the individual member codes directly in your EMIS searches
        3. Consider creating custom EMIS searches with the member codes
        """)
    
    st.info("💡 **Pro Tip:** See the 'Pseudo-Refset Members' tab to view and export all codes within each pseudo-refset.")
    
    if results.get('pseudo_refsets'):
        pseudo_refsets_df = pd.DataFrame(results['pseudo_refsets'])
        
        # Pseudo-refsets are highlighted in orange (warning)
        def highlight_pseudo_refsets(row):
            return ['background-color: #fff3cd'] * len(row)  # Light orange/yellow
        
        styled_pseudo_refsets = pseudo_refsets_df.style.apply(highlight_pseudo_refsets, axis=1)
        st.dataframe(styled_pseudo_refsets, width='stretch')
        
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
    st.subheader("📝 Individual Codes from Pseudo-Refsets")
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
                        st.dataframe(styled_members, width='stretch')
                        
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
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📋 Summary", "🏥 Clinical Codes", "💊 Medications", "📊 Refsets", "⚠️ Pseudo-Refsets", "📝 Pseudo-Refset Members", "📊 Analytics"])
        
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
        
        with tab7:
            render_analytics_tab()
    else:
        st.info("Results will appear here after processing an XML file")


def render_analytics_tab():
    """Render the analytics tab with audit statistics and export capability."""
    if 'audit_stats' not in st.session_state:
        st.info("🔍 Analytics will appear here after processing an XML file")
        return
    
    audit_stats = st.session_state.audit_stats
    
    st.subheader("📊 Processing Analytics & Quality Metrics")
    
    # File and Processing Information
    st.write("### 📁 File Information")
    
    # Filename in full width
    st.info(f"**Filename:** {audit_stats['xml_stats']['filename']}")
    
    # Metrics in columns with color coding
    col1, col2, col3 = st.columns(3)
    
    with col1:
        file_size_mb = audit_stats['xml_stats']['file_size_bytes'] / (1024 * 1024)
        if file_size_mb > 10:
            st.error(f"**File Size:** {audit_stats['xml_stats']['file_size_bytes']:,} bytes ({file_size_mb:.1f} MB)")
        elif file_size_mb > 1:
            st.warning(f"**File Size:** {audit_stats['xml_stats']['file_size_bytes']:,} bytes ({file_size_mb:.1f} MB)")
        else:
            st.success(f"**File Size:** {audit_stats['xml_stats']['file_size_bytes']:,} bytes ({file_size_mb:.1f} MB)")
    
    with col2:
        processing_time = audit_stats['xml_stats']['processing_time_seconds']
        if processing_time > 60:
            st.error(f"**Processing Time:** {processing_time:.2f}s")
        elif processing_time > 30:
            st.warning(f"**Processing Time:** {processing_time:.2f}s")
        else:
            st.success(f"**Processing Time:** {processing_time:.2f}s")
    
    with col3:
        st.info(f"**Processed:** {audit_stats['xml_stats']['processing_timestamp']}")
    
    # XML Structure Analysis
    st.write("### 🏗️ XML Structure Analysis")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        valuesets = audit_stats['xml_structure']['total_valuesets']
        if valuesets > 50:
            st.error(f"**Total ValueSets:** {valuesets}")
        elif valuesets > 20:
            st.warning(f"**Total ValueSets:** {valuesets}")
        else:
            st.success(f"**Total ValueSets:** {valuesets}")
    
    with col2:
        unique_guids = audit_stats['xml_structure']['unique_emis_guids']
        if unique_guids > 1000:
            st.error(f"**Unique EMIS GUIDs:** {unique_guids:,}")
        elif unique_guids > 500:
            st.warning(f"**Unique EMIS GUIDs:** {unique_guids:,}")
        else:
            st.success(f"**Unique EMIS GUIDs:** {unique_guids:,}")
    
    with col3:
        total_refs = audit_stats['xml_structure']['total_guid_occurrences']
        if total_refs > 2000:
            st.info(f"**Total GUID References:** {total_refs:,}")
        else:
            st.success(f"**Total GUID References:** {total_refs:,}")
    
    with col4:
        dup_rate = audit_stats['xml_structure']['duplicate_guid_ratio']
        if dup_rate > 20:
            st.error(f"**Duplication Rate:** {dup_rate}%")
        elif dup_rate > 10:
            st.warning(f"**Duplication Rate:** {dup_rate}%")
        else:
            st.success(f"**Duplication Rate:** {dup_rate}%")
    
    # Translation Accuracy
    st.write("### 🎯 Translation Accuracy")
    trans_accuracy = audit_stats['translation_accuracy']
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Standalone Codes**")
        
        # Clinical codes
        clinical_rate = trans_accuracy['clinical_codes']['success_rate']
        clinical_text = f"**Clinical Codes:** {clinical_rate}% ({trans_accuracy['clinical_codes']['found']}/{trans_accuracy['clinical_codes']['total']} found)"
        if clinical_rate >= 90:
            st.success(clinical_text)
        elif clinical_rate >= 70:
            st.warning(clinical_text)
        else:
            st.error(clinical_text)
        
        # Medications
        med_rate = trans_accuracy['medications']['success_rate']
        med_text = f"**Medications:** {med_rate}% ({trans_accuracy['medications']['found']}/{trans_accuracy['medications']['total']} found)"
        if med_rate >= 90:
            st.success(med_text)
        elif med_rate >= 70:
            st.warning(med_text)
        else:
            st.error(med_text)
    
    with col2:
        st.markdown("**Pseudo-Refset Members**")
        
        # Clinical members
        clinical_pseudo_rate = trans_accuracy['pseudo_refset_clinical']['success_rate']
        clinical_pseudo_text = f"**Clinical Members:** {clinical_pseudo_rate}% ({trans_accuracy['pseudo_refset_clinical']['found']}/{trans_accuracy['pseudo_refset_clinical']['total']} found)"
        if clinical_pseudo_rate >= 90:
            st.success(clinical_pseudo_text)
        elif clinical_pseudo_rate >= 70:
            st.warning(clinical_pseudo_text)
        else:
            st.error(clinical_pseudo_text)
        
        # Medication members
        med_pseudo_rate = trans_accuracy['pseudo_refset_medications']['success_rate']
        med_pseudo_text = f"**Medication Members:** {med_pseudo_rate}% ({trans_accuracy['pseudo_refset_medications']['found']}/{trans_accuracy['pseudo_refset_medications']['total']} found)"
        if med_pseudo_rate >= 90:
            st.success(med_pseudo_text)
        elif med_pseudo_rate >= 70:
            st.warning(med_pseudo_text)
        else:
            st.error(med_pseudo_text)
    
    # Overall success rate
    overall_rate = trans_accuracy['overall']['success_rate']
    overall_text = f"**Overall Success Rate:** {overall_rate}% ({trans_accuracy['overall']['found']}/{trans_accuracy['overall']['total']} total codes found)"
    if overall_rate >= 90:
        st.success(overall_text)
    elif overall_rate >= 70:
        st.warning(overall_text)
    else:
        st.error(overall_text)
    
    # Code System Breakdown and Quality Indicators side by side
    breakdown_col, quality_col = st.columns([1, 2])
    
    with breakdown_col:
        st.write("### ⚙️ Code System Breakdown")
        code_systems_df = pd.DataFrame(list(audit_stats['code_systems'].items()), 
                                      columns=['Code System', 'Count'])
        code_systems_df = code_systems_df.sort_values('Count', ascending=False)
        st.dataframe(code_systems_df, width='stretch')
    
    with quality_col:
        st.write("### ✅ Quality Indicators")
        quality = audit_stats['quality_metrics']
        
        col1, col2 = st.columns(2)
        with col1:
            # Include children flags
            include_children = quality['has_include_children_flags']
            if include_children > 0:
                st.success(f"**Include Children Flags:** {include_children}")
            else:
                st.info(f"**Include Children Flags:** {include_children}")
            
            # Display names present
            display_names = quality['has_display_names']
            total_guids = audit_stats['xml_structure']['unique_emis_guids']
            if total_guids > 0:
                display_percentage = (display_names / total_guids) * 100
                if display_percentage >= 90:
                    st.success(f"**Display Names Present:** {display_names} ({display_percentage:.0f}%)")
                elif display_percentage >= 70:
                    st.warning(f"**Display Names Present:** {display_names} ({display_percentage:.0f}%)")
                else:
                    st.error(f"**Display Names Present:** {display_names} ({display_percentage:.0f}%)")
            else:
                st.info(f"**Display Names Present:** {display_names}")
            
            # EMISINTERNAL codes (should be excluded)
            emis_internal = quality['emisinternal_codes_excluded']
            if emis_internal > 0:
                st.warning(f"**EMISINTERNAL Codes (Excluded):** {emis_internal}")
            else:
                st.success(f"**EMISINTERNAL Codes (Excluded):** {emis_internal}")
        
        with col2:
            # Table context
            table_context = quality['has_table_context']
            if table_context > 0:
                st.success(f"**Table Context Available:** {table_context}")
            else:
                st.info(f"**Table Context Available:** {table_context}")
            
            # Column context
            column_context = quality['has_column_context']
            if column_context > 0:
                st.success(f"**Column Context Available:** {column_context}")
            else:
                st.info(f"**Column Context Available:** {column_context}")
            
            # Add a spacer to balance the layout
            st.write("")
    
    # Export Functionality
    st.write("### 📤 Export Analytics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export detailed JSON
        audit_json = json.dumps(audit_stats, indent=2, default=str)
        st.download_button(
            label="📄 Download Detailed JSON Report",
            data=audit_json,
            file_name=f"analytics_{audit_stats['xml_stats']['filename']}.json",
            mime="application/json"
        )
    
    with col2:
        # Export summary report
        from audit import create_validation_report
        summary_report = create_validation_report(audit_stats)
        st.download_button(
            label="📋 Download Summary Report",
            data=summary_report,
            file_name=f"processing_report_{audit_stats['xml_stats']['filename']}.txt",
            mime="text/plain"
        )
    
    with col3:
        # Export metrics as CSV
        metrics_data = []
        
        # Add file info
        metrics_data.append(['Category', 'Metric', 'Value'])
        metrics_data.append(['File Info', 'Filename', audit_stats['xml_stats']['filename']])
        metrics_data.append(['File Info', 'Size (bytes)', audit_stats['xml_stats']['file_size_bytes']])
        metrics_data.append(['File Info', 'Processing Time (seconds)', audit_stats['xml_stats']['processing_time_seconds']])
        
        # Add structure info
        for key, value in audit_stats['xml_structure'].items():
            metrics_data.append(['XML Structure', key, value])
        
        # Add translation accuracy
        for category, stats in audit_stats['translation_accuracy'].items():
            for metric, value in stats.items():
                metrics_data.append(['Translation Accuracy', f"{category}_{metric}", value])
        
        # Add quality metrics
        for key, value in audit_stats['quality_metrics'].items():
            metrics_data.append(['Quality Metrics', key, value])
        
        metrics_df = pd.DataFrame(metrics_data[1:], columns=metrics_data[0])
        csv_buffer = io.StringIO()
        metrics_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📊 Download Metrics CSV",
            data=csv_buffer.getvalue(),
            file_name=f"metrics_{audit_stats['xml_stats']['filename']}.csv",
            mime="text/csv"
        )