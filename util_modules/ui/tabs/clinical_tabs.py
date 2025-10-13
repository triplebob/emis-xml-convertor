"""
Clinical data tab rendering functions.

This module handles rendering of all clinical data related tabs:
- Summary tab with statistics
- Clinical codes tab
- Medications tab  
- Refsets tab
- Pseudo refsets tab
- Pseudo refset members tab
- Clinical codes main tab (aggregated view)
- Results tabs (wrapper for all clinical tabs)
"""

from .common_imports import *
from .base_tab import BaseTab, TabRenderer
from .tab_helpers import (
    _reprocess_with_new_mode,
    _lookup_snomed_for_ui,
    _deduplicate_clinical_data_by_emis_guid,
    _add_source_info_to_clinical_data,
    ensure_analysis_cached,
    get_unified_clinical_data
)

# Import report functions from the dedicated report_tabs module
try:
    from .report_tabs import (
        render_list_reports_tab,
        render_audit_reports_tab,
        render_aggregate_reports_tab
    )
except ImportError:
    # Fallback functions if imports fail
    def render_list_reports_tab(xml_content, xml_filename):
        st.info("🔄 List Reports tab under refactoring - functionality will be restored shortly")
    
    def render_audit_reports_tab(xml_content, xml_filename):
        st.info("🔄 Audit Reports tab under refactoring - functionality will be restored shortly")
    
    def render_aggregate_reports_tab(xml_content, xml_filename):
        st.info("🔄 Aggregate Reports tab under refactoring - functionality will be restored shortly")

# Import functions from the new modular tabs structure
from .analytics_tab import render_analytics_tab
from .analysis_tabs import render_search_analysis_tab


def render_summary_tab(results):
    """Render the summary tab with statistics."""
    # Get comprehensive clinical code counts including report codes
    search_clinical_count = len(results['clinical'])
    medication_count = len(results['medications'])
    clinical_pseudo_count = len(results.get('clinical_pseudo_members', []))
    medication_pseudo_count = len(results.get('medication_pseudo_members', []))
    refset_count = len(results['refsets'])
    pseudo_refset_count = len(results.get('pseudo_refsets', []))
    
    # Calculate report code counts
    report_results = st.session_state.get('report_results')
    report_clinical_count = 0
    if report_results and hasattr(report_results, 'clinical_codes'):
        report_clinical_count = len(report_results.clinical_codes)
    
    # Total clinical codes (search + report)
    total_clinical_count = search_clinical_count + report_clinical_count
    total_count = total_clinical_count + medication_count + refset_count + pseudo_refset_count
    
    col1_summary, col2_summary, col3_summary, col4_summary, col5_summary = st.columns(5)
    
    with col1_summary:
        st.metric("Total Containers", total_count)
    with col2_summary:
        st.metric("Total Clinical Codes", total_clinical_count, delta=f"+{report_clinical_count} from reports" if report_clinical_count > 0 else None)
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
        total_items = search_clinical_count + report_clinical_count + standalone_medications + clinical_pseudo + medication_pseudo + refset_count + pseudo_refset_count
        
        st.success(f"✅ Processed {total_items} items: {search_clinical_count} search clinical codes, {report_clinical_count} report clinical codes, {standalone_medications} standalone medications, {clinical_pseudo} clinical in pseudo-refsets, {medication_pseudo} medications in pseudo-refsets, {refset_count} refsets, {pseudo_refset_count} pseudo-refsets")
    
    # Clinical codes breakdown
    if search_clinical_count > 0 or report_clinical_count > 0:
        st.subheader("📊 Clinical Codes Breakdown")
        col1_breakdown, col2_breakdown, col3_breakdown = st.columns(3)
        
        with col1_breakdown:
            st.metric("From Searches", search_clinical_count)
        with col2_breakdown:
            st.metric("From Reports", report_clinical_count)
        with col3_breakdown:
            search_pct = (search_clinical_count / total_clinical_count * 100) if total_clinical_count > 0 else 0
            st.metric("Search %", f"{search_pct:.1f}%")
    
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
    if search_clinical_count > 0:
        clinical_found = len([c for c in results['clinical'] if c['Mapping Found'] == 'Found'])
        st.info(f"Search clinical codes mapping success: {clinical_found}/{search_clinical_count} ({clinical_found/search_clinical_count*100:.1f}%)")
    
    if medication_count > 0:
        med_found = len([m for m in results['medications'] if m['Mapping Found'] == 'Found'])
        st.info(f"Standalone medications mapping success: {med_found}/{medication_count} ({med_found/medication_count*100:.1f}%)")


# Placeholder for other functions - will be filled in subsequent steps
def render_clinical_codes_tab(results=None):
    
    # Switch to unified parsing approach using orchestrated analysis
    from .tab_helpers import get_unified_clinical_data
    
    unified_results = get_unified_clinical_data()
    if not unified_results:
        st.write("❌ No analysis data found - please run XML analysis first")
        return
    
    # Get clinical data from unified analysis (already has source tracking and filtering)
    clinical_data = unified_results.get('clinical_codes', [])
    pseudo_members_data = unified_results.get('clinical_pseudo_members', [])
    pseudo_refsets_data = unified_results.get('pseudo_refsets', [])
    
    # Source tracking is always enabled in unified parsing (columns hidden based on mode)
    show_code_sources = True
        
    # Deduplication mode toggle for clinical codes
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 📋 Standalone Clinical Codes" + (" (with source tracking)" if show_code_sources else ""))
    with col2:
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        dedup_mode = st.selectbox(
            "Code Display Mode (will trigger reprocessing):",
            options=['unique_codes', 'unique_per_entity'],
            format_func=lambda x: {
                'unique_codes': '🔀 Unique Codes', 
                'unique_per_entity': '📍 Per Source'
            }[x],
            index=0 if current_mode == 'unique_codes' else 1,
            key="clinical_deduplication_mode",
            help="🔀 Unique Codes: Show each code once\n📍 Per Source: Show codes per search/report"
        )
        
        # Check if mode changed and trigger reprocessing
        if dedup_mode != current_mode:
            st.session_state.current_deduplication_mode = dedup_mode
            # Trigger reprocessing with new mode if we have the necessary data
            if ('emis_guids' in st.session_state and 'lookup_df' in st.session_state):
                _reprocess_with_new_mode(dedup_mode)
    
    # Apply deduplication in unique codes mode only
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    if current_mode == 'unique_codes' and clinical_data:
        clinical_data = _deduplicate_clinical_data_by_emis_guid(clinical_data)
    
    # Standalone clinical codes section
    render_section_with_data(
        title="",  # Empty title since we rendered it above
        data=clinical_data,
        info_text="These are clinical codes that are NOT part of any pseudo-refset and can be used directly. " + 
                  ("Use the Mode toggle above to switch between 'Unique Codes' (show each code once across entire XML) and 'Per Source' (show codes per search/report with source tracking)." if current_mode == 'unique_per_entity' else 
                   "Currently showing unique codes only (one instance per code across entire XML). Use the Mode toggle to show per-source tracking."),
        empty_message="No standalone clinical codes found in this XML file",
        download_label="📥 Download Standalone Clinical Codes CSV",
        filename_prefix="standalone_clinical_codes",
        highlighting_function=get_success_highlighting_function()
    )
    
    # Check for pseudo-refset members and show appropriate message
    pseudo_members_count = len(pseudo_members_data)
    
    if pseudo_members_count > 0:
        # Show info directing users to dedicated tab
        st.info(f"⚠️ **{pseudo_members_count} clinical codes are part of pseudo-refsets** - View and export them from the 'Pseudo-Refset Members' tab.")
    else:
        # Show success when no pseudo-refset members exist
        st.success("✅ **All clinical codes are properly mapped!** This means all codes in your XML are either standard refsets (directly usable in EMIS) or standalone codes (also directly usable).")


def render_medications_tab(results):
    # Deduplication mode toggle for medications
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 💊 Standalone Medications")
    with col2:
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        dedup_mode = st.selectbox(
            "Code Display Mode (will trigger reprocessing):",
            options=['unique_codes', 'unique_per_entity'],
            format_func=lambda x: {
                'unique_codes': '🔀 Unique Codes', 
                'unique_per_entity': '📍 Per Source'
            }[x],
            index=0 if current_mode == 'unique_codes' else 1,
            key="medication_deduplication_mode",
            help="🔀 Unique Codes: Show each code once\n📍 Per Source: Show codes per search/report"
        )
        
        # Check if mode changed and trigger reprocessing
        if dedup_mode != current_mode:
            st.session_state.current_deduplication_mode = dedup_mode
            # Trigger reprocessing with new mode if we have the necessary data
            if ('emis_guids' in st.session_state and 'lookup_df' in st.session_state):
                _reprocess_with_new_mode(dedup_mode)
    
    # Switch to unified parsing approach using orchestrated analysis (like clinical codes tab)
    unified_results = get_unified_clinical_data()
    if not unified_results:
        st.write("❌ No analysis data found - please run XML analysis first")
        return
    
    # Get medications data from unified analysis (already standardized and categorized with _original_fields)
    medications_data = unified_results.get('medications', [])
    
    # Apply deduplication based on current mode
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    if current_mode == 'unique_codes' and medications_data:
        # Deduplicate by EMIS GUID - keep only one instance per medication code
        unique_medications = {}
        for medication in medications_data:
            emis_guid = medication.get('EMIS GUID', '')
            if emis_guid and emis_guid not in unique_medications:
                unique_medications[emis_guid] = medication
        medications_data = list(unique_medications.values())
        
    # Determine what medications we have
    has_standalone = len(medications_data) > 0
    has_pseudo = results.get('medication_pseudo_members') and len(results.get('medication_pseudo_members', [])) > 0
    
    if has_standalone or has_pseudo:
        # Show standalone medications if they exist
        if has_standalone:
            # Filter out Has Qualifier column for medications - not relevant since medications have unique SNOMED codes for different strengths
            medications_data_filtered = []
            for medication in medications_data:
                filtered_med = {k: v for k, v in medication.items() if k != 'Has Qualifier'}
                medications_data_filtered.append(filtered_med)
            
            # Show info text
            st.info("These are medications that are NOT part of any pseudo-refset and can be used directly.")
            
            # Custom rendering for medications with simplified download options
            df = pd.DataFrame(medications_data_filtered)
            
            # Apply column filtering like other sections
            display_df = df.copy()
            
            # Always hide certain columns
            always_hidden = ['ValueSet GUID', 'VALUESET GUID']
            for col in always_hidden:
                if col in display_df.columns:
                    display_df = display_df.drop(columns=[col])
            
            # Hide raw duplicate columns that have formatted versions
            raw_columns_to_hide = ['source_guid', 'source_name', 'source_container', 'source_type', 'report_type']
            for col in raw_columns_to_hide:
                if col in display_df.columns:
                    display_df = display_df.drop(columns=[col])
            
            # Hide internal categorization flags
            internal_flags_to_hide = ['is_refset', 'is_pseudo', 'is_medication', 'is_pseudorefset', 'is_pseudomember']
            for col in internal_flags_to_hide:
                if col in display_df.columns:
                    display_df = display_df.drop(columns=[col])
            
            # Hide debug columns unless debug mode is enabled
            show_debug = st.session_state.get('debug_mode', False)
            if not show_debug and '_original_fields' in display_df.columns:
                display_df = display_df.drop(columns=['_original_fields'])
            
            # Hide source columns in unique_codes mode for display only
            current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
            if current_mode == 'unique_codes':
                columns_to_hide = ['Source Type', 'Source Name', 'Source Container', 'Source GUID']
                for col in columns_to_hide:
                    if col in display_df.columns:
                        display_df = display_df.drop(columns=[col])
            
            # Add emojis for UI display
            if 'EMIS GUID' in display_df.columns:
                display_df['EMIS GUID'] = '🔍 ' + display_df['EMIS GUID'].astype(str)
            if 'SNOMED Code' in display_df.columns:
                display_df['SNOMED Code'] = '🩺 ' + display_df['SNOMED Code'].astype(str)
            if 'Source Type' in display_df.columns:
                display_df['Source Type'] = display_df['Source Type'].apply(lambda x: 
                    x if ('🔍' in str(x) or '📊' in str(x) or '📋' in str(x) or '📈' in str(x)) else (
                        f"🔍 {x}" if x and x == "Search" else
                        f"📊 {x}" if x and "Aggregate" in str(x) else
                        f"📋 {x}" if x and "List" in str(x) else
                        f"📈 {x}" if x and "Audit" in str(x) else
                        f"📊 {x}" if x else x
                    )
                )
            
            # Apply highlighting and display
            styled_df = display_df.style.apply(get_success_highlighting_function(), axis=1)
            st.dataframe(styled_df, width='stretch', hide_index=True)
            
            # Simplified download options - say "medications" instead of "codes"
            col1, col2 = st.columns([1, 2])
            
            with col1:
                has_source_tracking = 'Source GUID' in df.columns or 'Source Type' in df.columns
                
                if has_source_tracking:
                    export_filter = st.radio(
                        "Download Options:",
                        ["All Medications", "Only Matched", "Only Unmatched", "Only Medications from Searches", "Only Medications from Reports"],
                        key="medications_export_filter"
                    )
                else:
                    export_filter = st.radio(
                        "Download Options:",
                        ["All Medications", "Only Matched", "Only Unmatched"],
                        key="medications_export_filter_simple"
                    )
            
            with col2:
                # Filter data based on selection
                filtered_df = df.copy()
                
                if export_filter == "Only Matched":
                    # Filter for codes with successful mapping
                    if 'Mapping Found' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df['Mapping Found'] == 'Found']
                elif export_filter == "Only Unmatched":
                    # Filter for codes without successful mapping
                    if 'Mapping Found' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df['Mapping Found'] != 'Found']
                elif export_filter == "Only Medications from Searches" and has_source_tracking:
                    # Filter for search sources
                    if 'Source Type' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df['Source Type'].str.contains('Search', na=False)]
                    elif 'source_type' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df['source_type'] == 'search']
                elif export_filter == "Only Medications from Reports" and has_source_tracking:
                    # Filter for report sources 
                    if 'Source Type' in filtered_df.columns:
                        filtered_df = filtered_df[~filtered_df['Source Type'].str.contains('Search', na=False)]
                    elif 'source_type' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df['source_type'] == 'report']
                
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
                
                if export_filter == "Only Matched":
                    filename = f"medications_matched_{xml_filename}_{timestamp}.csv"
                elif export_filter == "Only Unmatched":
                    filename = f"medications_unmatched_{xml_filename}_{timestamp}.csv"
                elif export_filter == "Only Medications from Searches":
                    filename = f"medications_searches_{xml_filename}_{timestamp}.csv"
                elif export_filter == "Only Medications from Reports":
                    filename = f"medications_reports_{xml_filename}_{timestamp}.csv"
                else:
                    filename = f"medications_all_{xml_filename}_{timestamp}.csv"
                
                # Create download
                if not filtered_df.empty:
                    csv_buffer = io.StringIO()
                    filtered_df.to_csv(csv_buffer, index=False)
                    
                    st.download_button(
                        label=f"📥 Download {export_filter}",
                        data=csv_buffer.getvalue(),
                        file_name=filename,
                        mime="text/csv",
                        key="medications_download"
                    )
                else:
                    st.info(f"No data available for {export_filter}")
        
        # Show pseudo-refset medications section if they exist
        if has_pseudo:
            render_info_section(
                title="⚠️ Medications in Pseudo-Refsets",
                content="These medications are part of pseudo-refsets (refsets EMIS does not natively support yet), and can only be used by listing all member codes. Export these from the 'Pseudo-Refset Members' tab.",
                section_type="warning"
            )
    else:
        # No medications found at all
        render_info_section(
            title="",
            content="No medications found in this XML file. This file contains only clinical codes and/or refsets.",
            section_type="info"
        )
    
    # Show help sections only when medications exist
    if has_standalone or has_pseudo:
        # Add helpful tooltip information
        with st.expander("ℹ️ Medication Type Flags Help"):
            st.markdown("""
            **Medication Type Flags:**
            - **SCT_CONST** (Constituent): Active ingredients or components
            - **SCT_DRGGRP** (Drug Group): Groups of related medications  
            - **SCT_PREP** (Preparation): Specific medication preparations
            - **Standard Medication**: General medication codes from lookup table
            """)
        
        
        # Show pseudo-medications data if they exist
        if has_pseudo:
            medication_pseudo_df = pd.DataFrame(results['medication_pseudo_members'])
            
            # Color code pseudo-refset members differently
            def highlight_pseudo_medications(row):
                if row['Mapping Found'] == 'Found':
                    return ['background-color: #fff3cd'] * len(row)  # Light yellow/orange
                else:
                    return ['background-color: #f8cecc'] * len(row)  # Light red/orange
            
            styled_pseudo_medications = medication_pseudo_df.style.apply(highlight_pseudo_medications, axis=1)
            st.dataframe(styled_pseudo_medications, width='stretch')


def render_refsets_tab(results):
    # Deduplication mode toggle for refsets
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 📊 Refsets")
    with col2:
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        dedup_mode = st.selectbox(
            "Code Display Mode (will trigger reprocessing):",
            options=['unique_codes', 'unique_per_entity'],
            format_func=lambda x: {
                'unique_codes': '🔀 Unique Codes', 
                'unique_per_entity': '📍 Per Source'
            }[x],
            index=0 if current_mode == 'unique_codes' else 1,
            key="refsets_deduplication_mode",
            help="🔀 Unique Codes: Show each refset once\n📍 Per Source: Show refsets per search/report"
        )
        
        # Check if mode changed and trigger reprocessing
        if dedup_mode != current_mode:
            st.session_state.current_deduplication_mode = dedup_mode
            # Trigger reprocessing with new mode if we have the necessary data
            if ('emis_guids' in st.session_state and 'lookup_df' in st.session_state):
                _reprocess_with_new_mode(dedup_mode)
    
    # Switch to unified parsing approach using orchestrated analysis (like clinical codes tab)
    unified_results = get_unified_clinical_data()
    if not unified_results:
        st.write("❌ No analysis data found - please run XML analysis first")
        return
    
    # Get refsets data from unified analysis (already standardized with _original_fields)
    refsets_data = unified_results.get('refsets', [])
    
    # Apply deduplication based on current mode
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    if current_mode == 'unique_codes' and refsets_data:
        # Deduplicate by EMIS GUID - keep only one instance per refset code
        unique_refsets = {}
        for refset in refsets_data:
            emis_guid = refset.get('EMIS GUID', '')
            if emis_guid and emis_guid not in unique_refsets:
                unique_refsets[emis_guid] = refset
        refsets_data = list(unique_refsets.values())
    
    # Refsets section with proper source tracking display
    if refsets_data:
        # Filter out Descendants and Has Qualifier columns for refsets - not relevant since refsets are container concepts, not individual codes with hierarchies or qualifiers
        refsets_data_filtered = []
        for refset in refsets_data:
            filtered_refset = {k: v for k, v in refset.items() if k not in ['Descendants', 'Has Qualifier']}
            refsets_data_filtered.append(filtered_refset)
        
        def highlight_refsets(row):
            return ['background-color: #d4edda'] * len(row)  # Light green for refsets
        
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        
        # Show info text
        if current_mode == 'unique_per_entity':
            st.info("These are true refsets that EMIS recognizes natively. They can be used directly by their SNOMED code in EMIS clinical searches. Use the Mode toggle above to switch between 'Unique Codes' and 'Per Source' to see source tracking.")
        else:
            st.info("These are true refsets that EMIS recognizes natively. They can be used directly by their SNOMED code in EMIS clinical searches. Currently showing unique refsets only. Use the Mode toggle to show per-source tracking.")
        
        # Custom rendering for refsets with simplified download options like pseudo-refsets
        df = pd.DataFrame(refsets_data_filtered)
        
        # Apply column filtering like other sections
        display_df = df.copy()
        
        # Always hide certain columns
        always_hidden = ['ValueSet GUID', 'VALUESET GUID']
        for col in always_hidden:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
        
        # Hide raw duplicate columns that have formatted versions
        raw_columns_to_hide = ['source_guid', 'source_name', 'source_container', 'source_type', 'report_type']
        for col in raw_columns_to_hide:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
        
        # Hide internal categorization flags
        internal_flags_to_hide = ['is_refset', 'is_pseudo', 'is_medication', 'is_pseudorefset', 'is_pseudomember']
        for col in internal_flags_to_hide:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
        
        # Hide debug columns unless debug mode is enabled
        show_debug = st.session_state.get('debug_mode', False)
        if not show_debug and '_original_fields' in display_df.columns:
            display_df = display_df.drop(columns=['_original_fields'])
        
        # Hide source columns in unique_codes mode for display only
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        if current_mode == 'unique_codes':
            columns_to_hide = ['Source Type', 'Source Name', 'Source Container', 'Source GUID']
            for col in columns_to_hide:
                if col in display_df.columns:
                    display_df = display_df.drop(columns=[col])
        
        # Add emojis for UI display
        if 'EMIS GUID' in display_df.columns:
            display_df['EMIS GUID'] = '🔍 ' + display_df['EMIS GUID'].astype(str)
        if 'SNOMED Code' in display_df.columns:
            display_df['SNOMED Code'] = '🩺 ' + display_df['SNOMED Code'].astype(str)
        if 'Source Type' in display_df.columns:
            display_df['Source Type'] = display_df['Source Type'].apply(lambda x: 
                x if ('🔍' in str(x) or '📊' in str(x) or '📋' in str(x) or '📈' in str(x)) else (
                    f"🔍 {x}" if x and x == "Search" else
                    f"📊 {x}" if x and "Aggregate" in str(x) else
                    f"📋 {x}" if x and "List" in str(x) else
                    f"📈 {x}" if x and "Audit" in str(x) else
                    f"📊 {x}" if x else x
                )
            )
        
        # Apply highlighting and display
        styled_df = display_df.style.apply(highlight_refsets, axis=1)
        st.dataframe(styled_df, width='stretch', hide_index=True)
        
        # Simplified download options - only 3 options like pseudo-refsets tab
        col1, col2 = st.columns([1, 2])
        
        with col1:
            has_source_tracking = 'Source GUID' in df.columns or 'Source Type' in df.columns
            
            if has_source_tracking:
                export_filter = st.radio(
                    "Download Options:",
                    ["All Refsets", "Only Refsets from Searches", "Only Refsets from Reports"],
                    key="refsets_export_filter"
                )
            else:
                export_filter = "All Refsets"
        
        with col2:
            # Filter data based on selection
            filtered_df = df.copy()
            
            if export_filter == "Only Refsets from Searches" and has_source_tracking:
                # Filter for search sources
                if 'Source Type' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['Source Type'].str.contains('Search', na=False)]
                elif 'source_type' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['source_type'] == 'search']
            elif export_filter == "Only Refsets from Reports" and has_source_tracking:
                # Filter for report sources 
                if 'Source Type' in filtered_df.columns:
                    filtered_df = filtered_df[~filtered_df['Source Type'].str.contains('Search', na=False)]
                elif 'source_type' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['source_type'] == 'report']
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
            
            if export_filter == "Only Refsets from Searches":
                filename = f"refsets_searches_{xml_filename}_{timestamp}.csv"
            elif export_filter == "Only Refsets from Reports":
                filename = f"refsets_reports_{xml_filename}_{timestamp}.csv"
            else:
                filename = f"refsets_all_{xml_filename}_{timestamp}.csv"
            
            # Create download
            if not filtered_df.empty:
                csv_buffer = io.StringIO()
                filtered_df.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label=f"📥 Download {export_filter}",
                    data=csv_buffer.getvalue(),
                    file_name=filename,
                    mime="text/csv",
                    key="refsets_download"
                )
            else:
                st.info(f"No data available for {export_filter}")
    else:
        st.info("No refsets found in this XML file")


def render_pseudo_refsets_tab(results):
    # Switch to unified parsing approach using orchestrated analysis
    unified_results = get_unified_clinical_data()
    if not unified_results:
        st.write("❌ No analysis data found - please run XML analysis first")
        return
    
    # Get pseudo-refsets data from unified analysis
    pseudo_refsets_data = unified_results.get('pseudo_refsets', [])
    
    # Apply deduplication based on current mode
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    if current_mode == 'unique_codes' and pseudo_refsets_data:
        # Deduplicate by EMIS GUID - keep only one instance per pseudo-refset
        unique_pseudo_refsets = {}
        for pseudo_refset in pseudo_refsets_data:
            emis_guid = pseudo_refset.get('EMIS GUID', '')
            if emis_guid and emis_guid not in unique_pseudo_refsets:
                unique_pseudo_refsets[emis_guid] = pseudo_refset
        pseudo_refsets_data = list(unique_pseudo_refsets.values())
    
    # Deduplication mode toggle for pseudo-refsets
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### ⚠️ All Pseudo-Refsets")
    with col2:
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        dedup_mode = st.selectbox(
            "Code Display Mode (will trigger reprocessing):",
            options=['unique_codes', 'unique_per_entity'],
            format_func=lambda x: {
                'unique_codes': '🔀 Unique Codes', 
                'unique_per_entity': '📍 Per Source'
            }[x],
            index=0 if current_mode == 'unique_codes' else 1,
            key="pseudo_refsets_deduplication_mode",
            help="🔀 Unique Codes: Show each pseudo-refset once\n📍 Per Source: Show pseudo-refsets per search/report"
        )
        
        # Check if mode changed and trigger reprocessing
        if dedup_mode != current_mode:
            st.session_state.current_deduplication_mode = dedup_mode
            # Trigger reprocessing with new mode if we have the necessary data
            if ('emis_guids' in st.session_state and 'lookup_df' in st.session_state):
                _reprocess_with_new_mode(dedup_mode)
    
    # Show appropriate dynamic message based on pseudo-refsets and mode
    if not pseudo_refsets_data:
        st.success("✅ No pseudo-refsets found - all ValueSets are standard refsets or standalone codes (directly usable in EMIS).")
    else:
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        if current_mode == 'unique_codes':
            st.info("ℹ️ These are ValueSet containers that hold multiple clinical codes but are NOT stored in the EMIS database as referenceable refsets. Currently showing unique pseudo-refsets only. Use the Mode toggle to show per-source tracking.")
        else:
            st.info("ℹ️ These are ValueSet containers that hold multiple clinical codes but are NOT stored in the EMIS database as referenceable refsets. Currently showing per-source tracking. Use the Mode toggle to show unique codes only.")
    
    # Pseudo-refsets are already generated in unified parsing
    # Apply deduplication based on mode for pseudo-refsets
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    display_pseudo_refsets = pseudo_refsets_data.copy()
    
    if current_mode == 'unique_codes' and display_pseudo_refsets:
        # Deduplicate by ValueSet GUID
        seen_guids = set()
        unique_pseudo_refsets = []
        for refset in display_pseudo_refsets:
            vs_guid = refset.get('ValueSet GUID')
            if vs_guid and vs_guid not in seen_guids:
                seen_guids.add(vs_guid)
                unique_pseudo_refsets.append(refset)
        display_pseudo_refsets = unique_pseudo_refsets
    
    # Render pseudo-refsets section with simplified table and downloads
    if display_pseudo_refsets:
        # Filter out unnecessary columns for pseudo-refsets display
        display_data = []
        for refset in display_pseudo_refsets:
            filtered_refset = {k: v for k, v in refset.items() if k not in ['Descendants', 'Has Qualifier']}
            display_data.append(filtered_refset)
        
        # Custom rendering for pseudo-refsets with simplified download options
        df = pd.DataFrame(display_data)
        
        # Apply column filtering like other sections
        display_df = df.copy()
        
        # Always hide certain columns
        always_hidden = ['ValueSet GUID', 'VALUESET GUID']
        for col in always_hidden:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
        
        # Hide raw duplicate columns that have formatted versions
        raw_columns_to_hide = ['source_guid', 'source_name', 'source_container', 'source_type', 'report_type']
        for col in raw_columns_to_hide:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
        
        # Hide internal categorization flags
        internal_flags_to_hide = ['is_refset', 'is_pseudo', 'is_medication', 'is_pseudorefset', 'is_pseudomember']
        for col in internal_flags_to_hide:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
        
        # Hide debug columns unless debug mode is enabled
        show_debug = st.session_state.get('debug_mode', False)
        if not show_debug and '_original_fields' in display_df.columns:
            display_df = display_df.drop(columns=['_original_fields'])
        
        # Hide source columns in unique_codes mode for display only
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        if current_mode == 'unique_codes':
            columns_to_hide = ['Source Type', 'Source Name', 'Source Container', 'Source GUID']
            for col in columns_to_hide:
                if col in display_df.columns:
                    display_df = display_df.drop(columns=[col])
        
        # Add emojis for UI display
        if 'EMIS GUID' in display_df.columns:
            display_df['EMIS GUID'] = '🔍 ' + display_df['EMIS GUID'].astype(str)
        if 'SNOMED Code' in display_df.columns:
            display_df['SNOMED Code'] = '🩺 ' + display_df['SNOMED Code'].astype(str)
        if 'Source Type' in display_df.columns:
            display_df['Source Type'] = display_df['Source Type'].apply(lambda x: 
                x if ('🔍' in str(x) or '📊' in str(x) or '📋' in str(x) or '📈' in str(x)) else (
                    f"🔍 {x}" if x and x == "Search" else
                    f"📊 {x}" if x and "Aggregate" in str(x) else
                    f"📋 {x}" if x and "List" in str(x) else
                    f"📈 {x}" if x and "Audit" in str(x) else
                    f"📊 {x}" if x else x
                )
            )
        
        # Apply highlighting and display
        styled_df = display_df.style.apply(get_warning_highlighting_function(), axis=1)
        st.dataframe(styled_df, width='stretch', hide_index=True)
        
        # Simplified download options - only 3 options instead of 5
        col1, col2 = st.columns([1, 2])
        
        with col1:
            has_source_tracking = 'Source GUID' in df.columns or 'Source Type' in df.columns
            
            if has_source_tracking:
                export_filter = st.radio(
                    "Download Options:",
                    ["All Pseudo-Refsets", "All Pseudo from Searches", "All Pseudo from Reports"],
                    key="pseudo_refsets_export_filter"
                )
            else:
                export_filter = "All Pseudo-Refsets"
        
        with col2:
            # Filter data based on selection
            filtered_df = df.copy()
            
            if export_filter == "All Pseudo from Searches" and has_source_tracking:
                # Filter for search sources
                if 'Source Type' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['Source Type'].str.contains('Search', na=False)]
                elif 'source_type' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['source_type'] == 'search']
            elif export_filter == "All Pseudo from Reports" and has_source_tracking:
                # Filter for report sources 
                if 'Source Type' in filtered_df.columns:
                    filtered_df = filtered_df[~filtered_df['Source Type'].str.contains('Search', na=False)]
                elif 'source_type' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['source_type'] == 'report']
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
            
            if export_filter == "All Pseudo from Searches":
                filename = f"pseudo_refsets_searches_{xml_filename}_{timestamp}.csv"
            elif export_filter == "All Pseudo from Reports":
                filename = f"pseudo_refsets_reports_{xml_filename}_{timestamp}.csv"
            else:
                filename = f"pseudo_refsets_all_{xml_filename}_{timestamp}.csv"
            
            # Create download
            if not filtered_df.empty:
                csv_buffer = io.StringIO()
                filtered_df.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label=f"📥 Download {export_filter}",
                    data=csv_buffer.getvalue(),
                    file_name=filename,
                    mime="text/csv",
                    key="pseudo_refsets_download"
                )
            else:
                st.info(f"No data available for {export_filter}")
        
        # Remove the render_section_with_data call since we handled it above
        
        st.warning("""
        **Important Usage Notes:**
        - These pseudo-refset containers cannot be referenced directly in EMIS clinical searches
        - To use them, you must manually list all individual member codes within each valueset
        - View the 'Pseudo-Refset Members' tab to see all member codes for each container
        """)
    # No else needed - the info box above already handles the no pseudo-refsets case


def render_pseudo_refset_members_tab(results):
    # Switch to unified parsing approach using orchestrated analysis
    from .tab_helpers import get_unified_clinical_data
    
    unified_results = get_unified_clinical_data()
    if not unified_results:
        st.write("❌ No analysis data found - please run XML analysis first")
        return
    
    # Get pseudo-refset members data from unified analysis
    pseudo_members_data = unified_results.get('clinical_pseudo_members', [])
    
    # Deduplication mode toggle for pseudo-refset members
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 📝 Pseudo-Refset Member Codes")
    with col2:
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        dedup_mode = st.selectbox(
            "Code Display Mode (will trigger reprocessing):",
            options=['unique_codes', 'unique_per_entity'],
            format_func=lambda x: {
                'unique_codes': '🔀 Unique Codes', 
                'unique_per_entity': '📍 Per Source'
            }[x],
            index=0 if current_mode == 'unique_codes' else 1,
            key="pseudo_members_deduplication_mode",
            help="🔀 Unique Codes: Show each code once\n📍 Per Source: Show codes per search/report"
        )
        
        # Check if mode changed and trigger reprocessing
        if dedup_mode != current_mode:
            st.session_state.current_deduplication_mode = dedup_mode
            # Trigger reprocessing with new mode if we have the necessary data
            if ('emis_guids' in st.session_state and 'lookup_df' in st.session_state):
                from .tab_helpers import _reprocess_with_new_mode
                _reprocess_with_new_mode(dedup_mode)
    
    # Apply deduplication based on current mode
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    if current_mode == 'unique_codes' and pseudo_members_data:
        from .tab_helpers import _deduplicate_clinical_data_by_emis_guid
        pseudo_members_data = _deduplicate_clinical_data_by_emis_guid(pseudo_members_data)
    
    # Show appropriate dynamic message based on pseudo-members and mode
    if not pseudo_members_data:
        st.success("✅ No pseudo-refset member codes found - all codes are either standard refsets (directly usable in EMIS) or standalone codes (also directly usable).")
        return
    else:
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        if current_mode == 'unique_codes':
            st.info("⚠️ These clinical codes are part of pseudo-refsets (refsets EMIS does not natively support yet), and can only be used by listing all member codes. Currently showing unique codes only. Use the Mode toggle to show per-source tracking.")
        else:
            st.info("⚠️ These clinical codes are part of pseudo-refsets (refsets EMIS does not natively support yet), and can only be used by listing all member codes. Currently showing per-source tracking. Use the Mode toggle to show unique codes only.")
    
    # Custom rendering for pseudo-members with simplified download options like other tabs
    df = pd.DataFrame(pseudo_members_data)
    
    # Apply column filtering like other sections
    display_df = df.copy()
    
    # Always hide certain columns
    always_hidden = ['ValueSet GUID', 'VALUESET GUID']
    for col in always_hidden:
        if col in display_df.columns:
            display_df = display_df.drop(columns=[col])
    
    # Hide raw duplicate columns that have formatted versions
    raw_columns_to_hide = ['source_guid', 'source_name', 'source_container', 'source_type', 'report_type']
    for col in raw_columns_to_hide:
        if col in display_df.columns:
            display_df = display_df.drop(columns=[col])
    
    # Hide internal categorization flags
    internal_flags_to_hide = ['is_refset', 'is_pseudo', 'is_medication', 'is_pseudorefset', 'is_pseudomember']
    for col in internal_flags_to_hide:
        if col in display_df.columns:
            display_df = display_df.drop(columns=[col])
    
    # Hide debug columns unless debug mode is enabled
    show_debug = st.session_state.get('debug_mode', False)
    if not show_debug and '_original_fields' in display_df.columns:
        display_df = display_df.drop(columns=['_original_fields'])
    
    # Hide source columns in unique_codes mode for display only
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    if current_mode == 'unique_codes':
        columns_to_hide = ['Source Type', 'Source Name', 'Source Container', 'Source GUID']
        for col in columns_to_hide:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])
    
    # Add emojis for UI display
    if 'EMIS GUID' in display_df.columns:
        display_df['EMIS GUID'] = '🔍 ' + display_df['EMIS GUID'].astype(str)
    if 'SNOMED Code' in display_df.columns:
        display_df['SNOMED Code'] = '🩺 ' + display_df['SNOMED Code'].astype(str)
    if 'Source Type' in display_df.columns:
        display_df['Source Type'] = display_df['Source Type'].apply(lambda x: 
            x if ('🔍' in str(x) or '📊' in str(x) or '📋' in str(x) or '📈' in str(x)) else (
                f"🔍 {x}" if x and x == "Search" else
                f"📊 {x}" if x and "Aggregate" in str(x) else
                f"📋 {x}" if x and "List" in str(x) else
                f"📈 {x}" if x and "Audit" in str(x) else
                f"📊 {x}" if x else x
            )
        )
    
    # Apply highlighting and display
    def highlight_pseudo_members(row):
        if row['Mapping Found'] == 'Found':
            return ['background-color: #fff3cd'] * len(row)  # Light yellow/orange
        else:
            return ['background-color: #f8cecc'] * len(row)  # Light red/orange
    
    styled_df = display_df.style.apply(highlight_pseudo_members, axis=1)
    st.dataframe(styled_df, width='stretch', hide_index=True)
    
    # Simplified download options - only 3 options like other tabs
    col1, col2 = st.columns([1, 2])
    
    with col1:
        has_source_tracking = 'Source GUID' in df.columns or 'Source Type' in df.columns
        
        if has_source_tracking:
            export_filter = st.radio(
                "Download Options:",
                ["All Pseudo-Member Codes", "Only Matched", "Only Unmatched", "Only Pseudo-Members from Searches", "Only Pseudo-Members from Reports"],
                key="pseudo_members_export_filter"
            )
        else:
            export_filter = st.radio(
                "Download Options:",
                ["All Pseudo-Member Codes", "Only Matched", "Only Unmatched"],
                key="pseudo_members_export_filter_simple"
            )
    
    with col2:
        # Filter data based on selection
        filtered_df = df.copy()
        
        if export_filter == "Only Matched":
            # Filter for codes with successful mapping
            if 'Mapping Found' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Mapping Found'] == 'Found']
        elif export_filter == "Only Unmatched":
            # Filter for codes without successful mapping
            if 'Mapping Found' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Mapping Found'] != 'Found']
        elif export_filter == "Only Pseudo-Members from Searches" and has_source_tracking:
            # Filter for search sources
            if 'Source Type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Source Type'].str.contains('Search', na=False)]
            elif 'source_type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['source_type'] == 'search']
        elif export_filter == "Only Pseudo-Members from Reports" and has_source_tracking:
            # Filter for report sources 
            if 'Source Type' in filtered_df.columns:
                filtered_df = filtered_df[~filtered_df['Source Type'].str.contains('Search', na=False)]
            elif 'source_type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['source_type'] == 'report']
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
        
        if export_filter == "Only Matched":
            filename = f"pseudo_members_matched_{xml_filename}_{timestamp}.csv"
        elif export_filter == "Only Unmatched":
            filename = f"pseudo_members_unmatched_{xml_filename}_{timestamp}.csv"
        elif export_filter == "Only Pseudo-Members from Searches":
            filename = f"pseudo_members_searches_{xml_filename}_{timestamp}.csv"
        elif export_filter == "Only Pseudo-Members from Reports":
            filename = f"pseudo_members_reports_{xml_filename}_{timestamp}.csv"
        else:
            filename = f"pseudo_members_all_{xml_filename}_{timestamp}.csv"
        
        # Create download
        if not filtered_df.empty:
            csv_buffer = io.StringIO()
            filtered_df.to_csv(csv_buffer, index=False)
            
            st.download_button(
                label=f"📥 Download {export_filter}",
                data=csv_buffer.getvalue(),
                file_name=filename,
                mime="text/csv",
                key="pseudo_members_download"
            )
        else:
            st.info(f"No data available for {export_filter}")
    
    # Add helpful information about pseudo-refsets
    st.warning("""
    **Important Usage Notes:**
    - These codes are part of pseudo-refsets (ValueSets that EMIS does not recognize natively)
    - To use these codes in EMIS clinical searches, you must manually list all individual member codes
    - Pseudo-refset containers cannot be referenced directly by their container SNOMED code
    - View the pseudo-refset containers in the 'All Pseudo-Refsets' tab
    """)


def render_clinical_codes_main_tab(results):
    """Render the Clinical Codes main tab (formerly XML Contents)"""
    # Clinical Codes Configuration
    # Always enable report codes and source tracking - no longer configurable
    st.session_state.clinical_include_report_codes = True
    st.session_state.clinical_show_code_sources = True
    
    # Clinical codes sub-tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Summary", 
        "🏥 Clinical Codes", 
        "💊 Medications", 
        "📊 Refsets", 
        "⚠️ Pseudo-Refsets", 
        "📝 Pseudo-Refset Members", 
        "📊 Analytics"
    ])
    
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


def render_results_tabs(results):
    """Render all result tabs with new 5-tab structure."""
    if 'results' in st.session_state and st.session_state.results:
        results = st.session_state.results
        
        # Create new 5-tab main structure
        main_tab1, main_tab2, main_tab3, main_tab4, main_tab5 = st.tabs([
            "🏥 Clinical Codes", 
            "🔍 Search Analysis", 
            "📋 List Reports", 
            "📊 Audit Reports", 
            "📈 Aggregate Reports"
        ])
        
        with main_tab1:
            render_clinical_codes_main_tab(results)
        
        with main_tab2:
            xml_content = getattr(st.session_state, 'xml_content', None)
            xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
            render_search_analysis_tab(xml_content, xml_filename)
        
        with main_tab3:
            xml_content = getattr(st.session_state, 'xml_content', None)
            xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
            render_list_reports_tab(xml_content, xml_filename)
        
        with main_tab4:
            xml_content = getattr(st.session_state, 'xml_content', None)
            xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
            render_audit_reports_tab(xml_content, xml_filename)
        
        with main_tab5:
            xml_content = getattr(st.session_state, 'xml_content', None)
            xml_filename = getattr(st.session_state, 'xml_filename', 'unknown.xml')
            render_aggregate_reports_tab(xml_content, xml_filename)
    else:
        st.info("Results will appear here after processing an XML file")