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
from ..core import ReportClassifier, FolderManager, SearchManager
from ..export_handlers.report_export import ReportExportHandler
from ..core.translator import translate_emis_to_snomed
# render_search_rule_tab moved to render_xml_structure_tabs in this file


def _reprocess_with_new_mode(deduplication_mode):
    """Reprocess results with new deduplication mode - isolated update that preserves other session data"""
    try:
        # Get necessary data from session state
        emis_guids = st.session_state.get('emis_guids')
        lookup_df = st.session_state.get('lookup_df')
        emis_guid_col = st.session_state.get('emis_guid_col')
        snomed_code_col = st.session_state.get('snomed_code_col')
        
        if all([emis_guids, lookup_df is not None, emis_guid_col, snomed_code_col]):
            # Show processing message
            with st.spinner(f"Reprocessing with {deduplication_mode} mode..."):
                # Re-translate with new mode
                translated_codes = translate_emis_to_snomed(
                    emis_guids, 
                    lookup_df, 
                    emis_guid_col, 
                    snomed_code_col,
                    deduplication_mode
                )
                
                # CRITICAL: Preserve XML structure analysis data that report tabs depend on
                # Store ALL report analysis data before clinical codes update
                xml_structure_analysis = st.session_state.get('xml_structure_analysis')
                search_analysis = st.session_state.get('search_analysis')
                search_results = st.session_state.get('search_results') 
                report_results = st.session_state.get('report_results')
                
                # Update ONLY the clinical codes translation results
                st.session_state.results = translated_codes
                
                # Restore ALL report structure data - this must not be touched by clinical code updates
                if xml_structure_analysis is not None:
                    st.session_state.xml_structure_analysis = xml_structure_analysis
                if search_analysis is not None:
                    st.session_state.search_analysis = search_analysis
                if search_results is not None:
                    st.session_state.search_results = search_results
                if report_results is not None:
                    st.session_state.report_results = report_results
                
                # Show success message
                mode_name = "Unique Codes" if deduplication_mode == 'unique_codes' else "Unique Per Source"
                st.toast(f"✅ Reprocessed with {mode_name} mode", icon="🔄")
                
                # Use experimental_rerun to avoid interfering with other tabs
                st.rerun()
    except Exception as e:
        st.error(f"Error reprocessing with new mode: {str(e)}")




def _lookup_snomed_for_ui(emis_guid: str) -> str:
    """Lookup SNOMED code for given EMIS GUID for UI display"""
    # Get lookup table from session state
    lookup_df = st.session_state.get('lookup_df')
    emis_guid_col = st.session_state.get('emis_guid_col')
    snomed_code_col = st.session_state.get('snomed_code_col')
    
    if lookup_df is None or emis_guid_col is None or snomed_code_col is None:
        return 'Lookup unavailable'
    
    if not emis_guid or emis_guid == 'N/A':
        return 'N/A'
    
    # Lookup the SNOMED code
    try:
        matching_rows = lookup_df[lookup_df[emis_guid_col].astype(str).str.strip() == str(emis_guid).strip()]
        if not matching_rows.empty:
            snomed_code = str(matching_rows.iloc[0][snomed_code_col]).strip()
            return snomed_code if snomed_code and snomed_code != 'nan' else 'Not found'
        else:
            return 'Not found'
    except Exception:
        return 'Lookup error'


def _deduplicate_clinical_data_by_emis_guid(clinical_data):
    """
    Deduplicate clinical data by EMIS GUID, prioritizing entries with actual ValueSet GUID over N/A
    This mirrors the deduplication logic in the export handler
    
    Args:
        clinical_data: List of clinical code dictionaries
        
    Returns:
        List of deduplicated clinical codes
    """
    if not clinical_data:
        return clinical_data
    
    # Group codes by EMIS GUID
    emis_guid_groups = {}
    for code in clinical_data:
        emis_guid = code.get('EMIS GUID', 'unknown')
        if emis_guid not in emis_guid_groups:
            emis_guid_groups[emis_guid] = []
        emis_guid_groups[emis_guid].append(code)
    
    # For each group, select the best entry
    deduplicated_codes = []
    for emis_guid, codes_group in emis_guid_groups.items():
        if len(codes_group) == 1:
            # Only one entry, keep it
            deduplicated_codes.append(codes_group[0])
        else:
            # Multiple entries, select the best one
            best_code = _select_best_clinical_code_entry(codes_group)
            deduplicated_codes.append(best_code)
    
    return deduplicated_codes


def _select_best_clinical_code_entry(codes_group):
    """
    Select the best clinical code entry from a group of duplicates
    
    Priority:
    1. Has actual ValueSet GUID (not N/A)
    2. Has ValueSet Description (not N/A)
    3. Has SNOMED Description (not N/A)
    4. Has Table/Column Context
    """
    def calculate_completeness_score(entry):
        score = 0
        
        # ValueSet GUID - HIGHEST priority (actual GUID vs N/A)
        vs_guid = entry.get('ValueSet GUID', 'N/A')
        if vs_guid and vs_guid != 'N/A' and vs_guid.strip():
            score += 20  # Highest priority for actual ValueSet GUID
        
        # ValueSet Description - high priority
        vs_desc = entry.get('ValueSet Description', 'N/A')
        if vs_desc and vs_desc != 'N/A' and vs_desc.strip():
            score += 10
        
        # SNOMED Description - medium priority
        snomed_desc = entry.get('SNOMED Description', 'N/A')
        if snomed_desc and snomed_desc != 'N/A' and snomed_desc != 'No display name in XML' and snomed_desc.strip():
            score += 5
        
        # Table Context - lower priority
        table_ctx = entry.get('Table Context', 'N/A')
        if table_ctx and table_ctx != 'N/A' and table_ctx.strip():
            score += 2
        
        # Column Context - lowest priority  
        col_ctx = entry.get('Column Context', 'N/A')
        if col_ctx and col_ctx != 'N/A' and col_ctx.strip():
            score += 1
        
        return score
    
    # Find the entry with the highest completeness score
    best_entry = codes_group[0]
    best_score = calculate_completeness_score(best_entry)
    
    for entry in codes_group[1:]:
        entry_score = calculate_completeness_score(entry)
        if entry_score > best_score:
            best_entry = entry
            best_score = entry_score
    
    return best_entry


def _filter_report_codes_from_analysis(analysis):
    """Filter out report codes from analysis when configurable integration is disabled"""
    # Create a copy of the analysis with report criteria removed from searches
    filtered_reports = []
    
    for report in analysis.reports:
        # Create a copy of the report
        filtered_report = report
        
        # If this report has aggregate criteria (built-in filters), remove them from criteria_groups
        if hasattr(report, 'aggregate_criteria') and report.aggregate_criteria:
            # Remove the aggregate criteria that were added to criteria_groups
            filtered_criteria_groups = []
            for group in report.criteria_groups:
                # Keep only original search criteria, not the added aggregate criteria
                if group.id != 'aggregate_filters':
                    filtered_criteria_groups.append(group)
            
            # Update the report with filtered criteria
            filtered_report.criteria_groups = filtered_criteria_groups
        
        filtered_reports.append(filtered_report)
    
    # Update the analysis object
    analysis.reports = filtered_reports
    return analysis


def _convert_analysis_codes_to_translation_format(analysis_codes):
    """Convert analysis clinical codes to translation format for display"""
    translated_codes = []
    
    # Get the lookup table from session state for SNOMED translation
    lookup_df = st.session_state.get('lookup_df')
    emis_guid_col = st.session_state.get('emis_guid_col')
    snomed_code_col = st.session_state.get('snomed_code_col')
    snomed_desc_col = st.session_state.get('snomed_desc_col')
    
    
    # Quick validation
    if lookup_df is None or emis_guid_col is None:
        # If no lookup table, just return basic format without SNOMED lookup
        for code in analysis_codes:
            translated_codes.append({
                'ValueSet GUID': 'N/A',
                'ValueSet Description': 'N/A', 
                'Code System': code.get('code_system', 'SNOMED_CONCEPT'),
                'EMIS GUID': code.get('code_value', code.get('emis_guid', '')),
                'SNOMED Code': 'Lookup unavailable',
                'SNOMED Description': 'Lookup unavailable',
                'Mapping Found': 'Lookup unavailable',
                'Pseudo-Refset Member': 'Yes' if code.get('is_refset', False) else 'No',
                'Table Context': 'N/A',
                'Column Context': 'N/A', 
                'Include Children': 'Yes' if code.get('include_children', False) else 'No',
                'Has Qualifier': '0',
                'Is Parent': '0',
                'Descendants': '0',
                'Code Type': 'Finding',
                'source_type': code.get('source_type', 'report'),
                'report_type': code.get('report_type', code.get('source_report_type', 'unknown')),
                'source_name': code.get('source_report_name', code.get('source_name', 'Unknown Report'))
            })
        return translated_codes
    
    # Create a lookup dictionary for faster access (one-time setup)
    try:
        # Convert lookup table to dictionary with string keys for consistent lookup
        # Convert all EMIS GUIDs to strings for consistent comparison
        lookup_df_copy = lookup_df.copy()
        lookup_df_copy[emis_guid_col] = lookup_df_copy[emis_guid_col].astype(str).str.strip()
        
        # Create dictionaries for all available fields
        lookup_dict = lookup_df_copy.set_index(emis_guid_col)[snomed_code_col].to_dict()
        desc_dict = lookup_df_copy.set_index(emis_guid_col)[snomed_desc_col].to_dict() if snomed_desc_col and snomed_desc_col in lookup_df_copy.columns else {}
        
        # Additional enrichment dictionaries
        code_type_dict = lookup_df_copy.set_index(emis_guid_col)['CodeType'].to_dict() if 'CodeType' in lookup_df_copy.columns else {}
        has_qualifier_dict = lookup_df_copy.set_index(emis_guid_col)['HasQualifier'].to_dict() if 'HasQualifier' in lookup_df_copy.columns else {}
        is_parent_dict = lookup_df_copy.set_index(emis_guid_col)['IsParent'].to_dict() if 'IsParent' in lookup_df_copy.columns else {}
        descendants_dict = lookup_df_copy.set_index(emis_guid_col)['Descendants'].to_dict() if 'Descendants' in lookup_df_copy.columns else {}
        
    except Exception:
        # Fallback to basic format if lookup fails
        lookup_dict = {}
        desc_dict = {}
        code_type_dict = {}
        has_qualifier_dict = {}
        is_parent_dict = {}
        descendants_dict = {}
    
    for i, code in enumerate(analysis_codes):
        emis_guid = code.get('code_value', code.get('emis_guid', '')).strip()
        
        # Fast dictionary lookup
        snomed_code = 'N/A'
        snomed_desc = 'N/A' 
        mapping_found = 'Not found'
        
        
        # Default enriched values
        code_type = 'Finding'
        has_qualifier = '0'
        is_parent = '0'
        descendants = '0'
        
        if emis_guid and emis_guid != 'N/A':
            # Try dictionary lookup
            if emis_guid in lookup_dict:
                snomed_value = lookup_dict[emis_guid]
                if isinstance(snomed_value, float) and snomed_value.is_integer():
                    snomed_code = str(int(snomed_value))
                else:
                    snomed_code = str(snomed_value).strip()
                
                # Get SNOMED description - use display_name from original data if no lookup desc
                if emis_guid in desc_dict and desc_dict[emis_guid] != 'N/A':
                    snomed_desc = str(desc_dict[emis_guid]).strip()
                else:
                    # Fallback to display_name from the original report data
                    snomed_desc = code.get('display_name', 'N/A')
                
                # Get enriched metadata
                code_type = str(code_type_dict.get(emis_guid, 'Finding')).strip()
                has_qualifier = str(has_qualifier_dict.get(emis_guid, '0')).strip()
                is_parent = str(is_parent_dict.get(emis_guid, '0')).strip()
                descendants = str(descendants_dict.get(emis_guid, '0')).strip()
                
                mapping_found = 'Found'
        
        # Convert to translation format
        translated_code = {
            'ValueSet GUID': 'N/A',  # Analysis codes don't have value set GUIDs
            'ValueSet Description': 'N/A',
            'Code System': code.get('code_system', 'SNOMED_CONCEPT'),
            'EMIS GUID': emis_guid,
            'SNOMED Code': snomed_code,
            'SNOMED Description': snomed_desc,
            'Mapping Found': mapping_found,
            'Pseudo-Refset Member': 'Yes' if code.get('is_refset', False) else 'No',
            'Table Context': 'EVENTS',  # Reports typically use EVENTS table
            'Column Context': 'READCODE',  # Reports typically use READCODE column
            'Include Children': 'Yes' if code.get('include_children', False) else 'No',
            'Has Qualifier': has_qualifier,
            'Is Parent': is_parent,
            'Descendants': descendants,
            'Code Type': code_type,
            # Source tracking from analysis - use source_report_name for report codes
            'source_type': code.get('source_type', 'report'),
            'report_type': code.get('report_type', code.get('source_report_type', 'unknown')),
            'source_name': code.get('source_report_name', code.get('source_name', 'Unknown Report'))
        }
        
        translated_codes.append(translated_code)
    
    return translated_codes


def _build_report_type_caption(report_results):
    """Build a caption showing report type counts with proper plurality"""
    if not report_results or not hasattr(report_results, 'report_breakdown'):
        return "audit/list/aggregate reports"
    
    # Count each report type
    type_counts = {}
    for report_type, reports in report_results.report_breakdown.items():
        if reports:  # Only include types that have reports
            type_counts[report_type] = len(reports)
    
    if not type_counts:
        return "audit/list/aggregate reports"
    
    # Build caption parts with proper plurality
    caption_parts = []
    for report_type, count in type_counts.items():
        # Proper plurality handling
        if count == 1:
            caption_parts.append(f"1 {report_type} report")
        else:
            caption_parts.append(f"{count} {report_type} reports")
    
    # Join with proper grammar
    if len(caption_parts) == 1:
        return caption_parts[0]
    elif len(caption_parts) == 2:
        return f"{caption_parts[0]} and {caption_parts[1]}"
    else:
        # Oxford comma for 3 or more items
        return ", ".join(caption_parts[:-1]) + f", and {caption_parts[-1]}"



def _add_source_info_to_clinical_data(clinical_data):
    """Add source tracking information to clinical codes data"""
    import copy
    enhanced_data = []
    
    for code_entry in clinical_data:
        enhanced_entry = copy.deepcopy(code_entry)  # Proper deep copy
        
        # Extract source information from the original data if available
        source_type = code_entry.get('source_type', 'search')  # Default to search for legacy data
        report_type = code_entry.get('report_type', 'search')  # Default to search for legacy data
        source_name = code_entry.get('source_name', 'Unknown')  # Actual search/report name
        
        # Determine the main source category 
        if source_type == 'search':
            source_category = "Search"
        elif source_type == 'report':
            # Map report types to meaningful names
            source_category = {
                'aggregate': 'Aggregate Report',
                'list': 'List Report', 
                'audit': 'Audit Report'
            }.get(report_type, f'{report_type.title()} Report')
        else:
            source_category = source_type.title()
        
        # Add processed columns with proper data separation and NO emojis (for clean CSV export)
        enhanced_entry['Source'] = source_category  # Category (Search, List Report, etc.)
        enhanced_entry['Source Type'] = source_name if source_name != 'Unknown' else 'Not specified'  # Actual name of search/report
        
        # Remove raw tracking fields now that we've processed them into display columns
        enhanced_entry.pop('source_type', None)
        enhanced_entry.pop('report_type', None) 
        enhanced_entry.pop('source_name', None)
        
        enhanced_data.append(enhanced_entry)
    
    return enhanced_data

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
    
    if refset_count > 0:
        st.info(f"True refsets: {refset_count} (automatically mapped)")
    
    if pseudo_refset_count > 0:
        st.warning(f"⚠️ Pseudo-refsets found: {pseudo_refset_count} - These cannot be referenced directly in EMIS by SNOMED code")

def render_clinical_codes_tab(results):
    if not results:
        st.write("❌ No results data found")
        return
    
    # Always enable source tracking - we'll hide columns visually in unique_codes mode
    show_code_sources = True
    include_report_codes = True
    
    # Get clinical data from translation results - make deep copies to avoid modifying original data
    import copy
    clinical_data = []
    
    try:
        if results['clinical']:
            for item in results['clinical']:
                clinical_data.append(copy.deepcopy(item))  # Proper deep copy
    except Exception as e:
        st.error(f"Error processing clinical data: {e}")
        return
    
    # Add source tracking to translation results (which don't have it by default)
    if show_code_sources and clinical_data:
        # Get search/report names from XML analysis
        search_name_map = {}
        analysis = st.session_state.get('search_analysis')
        
        if analysis:
            # Build a map from search/report names to determine source type
            # Map by search/report name from the ValueSet Description
            if hasattr(analysis, 'searches'):
                for search in analysis.searches:
                    search_name = getattr(search, 'name', '')
                    if search_name:
                        search_name_map[search_name] = {
                            'source_type': 'search',
                            'report_type': 'search',
                            'source_name': search_name
                        }
            
            if hasattr(analysis, 'reports'):
                for report in analysis.reports:
                    report_name = getattr(report, 'name', '')
                    report_type = getattr(report, 'report_type', 'unknown')
                    if report_name:
                        search_name_map[report_name] = {
                            'source_type': 'report',
                            'report_type': report_type,
                            'source_name': report_name
                        }
        
        # Add source tracking based on ValueSet Description (which contains search/report name)
        for item in clinical_data:
            if 'source_type' not in item:
                valueset_description = item.get('ValueSet Description', '')
                
                # Look up source info by ValueSet Description (search/report name)
                source_info = search_name_map.get(valueset_description)
                if source_info:
                    item['source_type'] = source_info['source_type']
                    item['report_type'] = source_info['report_type']  
                    item['source_name'] = source_info['source_name']
                else:
                    # Every search/report in EMIS must have a name - use the ValueSet Description
                    item['source_type'] = 'search'
                    item['report_type'] = 'search'
                    item['source_name'] = valueset_description or 'Search Name Missing'
                    
    
    # Add clinical codes from analysis (which have proper source tracking) if enabled  
    if include_report_codes:
        # Get the properly parsed clinical codes from the analyzers
        report_results = st.session_state.get('report_results')
        search_results = st.session_state.get('search_results')
        
        report_codes_added = 0
        search_codes_added = 0
        
        # Add report codes (already extracted by ReportAnalyzer)
        if report_results and hasattr(report_results, 'clinical_codes'):
            report_clinical_codes = report_results.clinical_codes
            if report_clinical_codes:
                translated_report_codes = _convert_analysis_codes_to_translation_format(report_clinical_codes)
                
                clinical_data.extend(translated_report_codes)
                report_codes_added = len(translated_report_codes)
        
        # Add search codes mapping for source name enrichment
        if search_results and hasattr(search_results, 'searches'):
            # Extract search codes and create GUID -> search name mapping
            search_guid_to_name = {}
            for search in search_results.searches:
                for group in search.criteria_groups:
                    for criterion in group.criteria:
                        for value_set in criterion.value_sets:
                            for value in value_set.get('values', []):
                                emis_guid = value.get('value', '')
                                if emis_guid:
                                    search_guid_to_name[emis_guid] = search.name
            
            # Enrich existing search codes with proper source names
            for code in clinical_data:
                if code.get('source_type') == 'search' and code.get('source_name') in ['Unknown', 'N/A', '']:
                    emis_guid = code.get('EMIS GUID', '')
                    if emis_guid in search_guid_to_name:
                        code['source_name'] = search_guid_to_name[emis_guid]
                        search_codes_added += 1
        
    
    # If report codes should be excluded, filter them out (legacy fallback)
    if not include_report_codes and clinical_data:
        st.sidebar.write("FILTERING OUT REPORT CODES")
        # Filter out codes that came from reports (fallback for codes already in translation)
        clinical_data = [code for code in clinical_data if code.get('source_type', 'search') == 'search']
        st.sidebar.write(f"After filtering: {len(clinical_data)}")
    
    
    # Filter out EMISINTERNAL codes (not medical codes)
    clinical_data = [code for code in clinical_data if code.get('Code System', '').upper() != 'EMISINTERNAL']
    
    # Add source tracking columns if enabled (this function now handles raw field cleanup internally)
    if show_code_sources and clinical_data:
        clinical_data = _add_source_info_to_clinical_data(clinical_data)
    
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
    
    # Dynamic pseudo-refset member clinical codes section
    pseudo_members_count = len(results.get('clinical_pseudo_members', []))
    
    if pseudo_members_count > 0:
        # Show warning when pseudo-refset members exist
        render_info_section(
            title="⚠️ Clinical Codes in Pseudo-Refsets",
            content="These clinical codes are part of pseudo-refsets (refsets EMIS does not natively support yet), and can only be used by listing all member codes. Export these from the 'Pseudo-Refset Members' tab.",
            section_type="warning"
        )
        
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
        # Show success when no pseudo-refset members exist
        render_info_section(
            title="✅ No Clinical Codes in Pseudo-Refsets",
            content="All clinical codes are properly mapped! This means all codes in your XML are either standard refsets (directly usable in EMIS) or standalone codes (also directly usable).",
            section_type="success"
        )

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
    
    # Determine what medications we have
    has_standalone = results['medications'] and len(results['medications']) > 0
    has_pseudo = results.get('medication_pseudo_members') and len(results.get('medication_pseudo_members', [])) > 0
    
    if has_standalone or has_pseudo:
        # Show standalone medications if they exist
        if has_standalone:
            render_section_with_data(
                title="",  # Empty title since we rendered it above
                data=results['medications'],
                info_text="These are medications that are NOT part of any pseudo-refset and can be used directly.",
                empty_message="No standalone medications found in this XML file",
                download_label="📥 Download Standalone Medications CSV",
                filename_prefix="standalone_medications",
                highlighting_function=get_success_highlighting_function()
            )
        
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
        
        st.info("**Tip:** Use the Analytics tab to view detailed mapping statistics and quality metrics.")
        
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
    
    if results['refsets']:
        refsets_df = pd.DataFrame(results['refsets'])
        
        # Refsets are always green (automatically mapped)
        def highlight_refsets(row):
            return ['background-color: #d4edda'] * len(row)  # Light green
        
        styled_refsets = refsets_df.style.apply(highlight_refsets, axis=1)
        
        # Add emojis to individual code values
        if "VALUESET GUID" in refsets_df.columns:
            refsets_df["VALUESET GUID"] = refsets_df["VALUESET GUID"].apply(lambda x: f"🔍 {x}")
        if "SNOMED Code" in refsets_df.columns:
            refsets_df["SNOMED Code"] = refsets_df["SNOMED Code"].apply(lambda x: f"🩺 {x}")
        
        # Configure column display
        column_config = {}
        if "Description" in refsets_df.columns:
            column_config["Description"] = st.column_config.TextColumn(
                "📝 Description",
                width="large"
            )
        if "Scope" in refsets_df.columns:
            column_config["Scope"] = st.column_config.TextColumn(
                "🔗 Scope",
                width="small"
            )
        if "Is Refset" in refsets_df.columns:
            column_config["Is Refset"] = st.column_config.TextColumn(
                "🎯 Refset",
                width="small"
            )
        
        st.dataframe(
            styled_refsets, 
            width='stretch',
            column_config=column_config if column_config else None
        )
        
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
    # Deduplication mode toggle for pseudo-refsets
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### ⚠️ Pseudo-Refset Containers")
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
    
    # Show appropriate info based on whether pseudo-refsets were found
    if results.get('pseudo_refsets'):
        render_info_section(
            title="",  # Empty since we rendered above
            content="These are ValueSet containers that hold multiple clinical codes but are NOT stored in the EMIS database as referenceable refsets. See the expandable help section below for usage details.",
            section_type="info"
        )
    else:
        render_info_section(
            title="",  # Empty since we rendered above
            content="No pseudo-refsets found - all codes are properly mapped! This means all ValueSets in your XML are either standard refsets (directly usable in EMIS) or standalone codes (also directly usable).",
            section_type="info"
        )
    
    # Add comprehensive help section - only when pseudo-refsets exist
    if results.get('pseudo_refsets'):
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
        
        # Add emojis to individual code values
        if "VALUESET GUID" in pseudo_refsets_df.columns:
            pseudo_refsets_df["VALUESET GUID"] = pseudo_refsets_df["VALUESET GUID"].apply(lambda x: f"🔍 {x}")
        if "SNOMED Code" in pseudo_refsets_df.columns:
            pseudo_refsets_df["SNOMED Code"] = pseudo_refsets_df["SNOMED Code"].apply(lambda x: f"🩺 {x}")
        
        # Configure column display
        column_config = {}
        if "Description" in pseudo_refsets_df.columns:
            column_config["Description"] = st.column_config.TextColumn(
                "📝 Description",
                width="large"
            )
        if "Scope" in pseudo_refsets_df.columns:
            column_config["Scope"] = st.column_config.TextColumn(
                "🔗 Scope",
                width="small"
            )
        if "Is Refset" in pseudo_refsets_df.columns:
            column_config["Is Refset"] = st.column_config.TextColumn(
                "🎯 Refset",
                width="small"
            )
        
        st.dataframe(
            styled_pseudo_refsets, 
            width='stretch',
            column_config=column_config if column_config else None
        )
        
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
    # No else needed - the info box above already handles the no pseudo-refsets case

def render_pseudo_refset_members_tab(results):
    st.subheader("📝 Individual Codes from Pseudo-Refsets")
    
    # Check if we have any pseudo-refset members
    has_members = results.get('pseudo_refset_members') and any(
        members for members in results['pseudo_refset_members'].values()
    )
    
    if has_members:
        st.info("These are the individual clinical codes contained within each pseudo-refset. These codes were moved here from the Clinical Codes tab as within the uploaded search XML ruleset they belong to pseudo-refsets.")
    else:
        st.info("No pseudo-refset members found - all codes are either standard refsets (directly usable in EMIS) or standalone codes.")
        return  # Exit early, no need to process further
    
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
    # No else needed - handled above with early return

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


def render_search_analysis_tab(xml_content: str, xml_filename: str):
    """Render the Search Analysis tab (focused on search logic only)"""
    if not xml_content:
        st.info("📋 Upload and process an XML file to see search analysis")
        return
    
    try:
        # Use cached analysis from session state if available
        analysis = st.session_state.get('search_analysis')
        
        if analysis is None:
            # Fallback: analyze if not cached (shouldn't happen in normal flow)
            from ..analysis.xml_structure_analyzer import analyze_search_rules
            with st.spinner("Analyzing search structures..."):
                analysis = analyze_search_rules(xml_content)
                st.session_state.search_analysis = analysis
        
        from ..core.report_classifier import ReportClassifier
        
        # Filter to search reports only for this tab
        search_reports = ReportClassifier.filter_searches_only(analysis.reports)
        search_count = len(search_reports)
        folder_count = len(analysis.folders) if analysis.folders else 0
        
        st.toast(f"Search Analysis: {search_count} search{'es' if search_count != 1 else ''} across {folder_count} folder{'s' if folder_count != 1 else ''}", icon="🔍")
        
        # Search-focused metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            complexity_color = {
                'Basic': '🟢',
                'Moderate': '🟡', 
                'Complex': '🟠',
                'Very Complex': '🔴'
            }
            # Safe access to complexity metrics with fallbacks for both orchestrated and legacy analysis
            complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
            complexity_level = complexity_data.get('complexity_level', 
                               complexity_data.get('classification', 'Basic'))
            complexity_score = complexity_data.get('complexity_score', 'N/A')
            
            st.metric(
                "Complexity", 
                f"{complexity_color.get(complexity_level, '⚪')} {complexity_level}",
                help=f"Score: {complexity_score}"
            )
        
        with col2:
            st.metric(
                "🔍 Searches", 
                search_count,
                help="Population-based search criteria that define patient groups"
            )
        
        with col3:
            folder_count = len(analysis.folders) if hasattr(analysis, 'folders') and analysis.folders else 0
            st.metric(
                "📁 Folders", 
                folder_count,
                help="Organizational folder structure"
            )
        
        # Search analysis sub-tabs
        if analysis.folders:
            struct_tab1, struct_tab2, struct_tab3 = st.tabs([
                "📁 Folder Structure", 
                "🔧 Rule Logic Browser",
                "🔗 Dependencies"
            ])
        else:
            struct_tab1, struct_tab2 = st.tabs([
                "🔧 Rule Logic Browser",
                "🔗 Dependencies"
            ])
        
        if analysis.folders:
            with struct_tab1:
                render_folder_structure_tab(analysis)
            
            with struct_tab2:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab3:
                render_dependencies_tab(analysis)
        else:
            with struct_tab1:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab2:
                render_dependencies_tab(analysis)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error analyzing search structure: {str(e)}")
        with st.expander("Debug Information", expanded=False):
            st.code(error_details)


def render_list_reports_tab(xml_content: str, xml_filename: str):
    """Render the List Reports tab with dedicated List Report browser and analysis"""
    if not xml_content:
        st.info("📋 Upload and process an XML file to see List Reports")
        return
    
    try:
        # Use cached analysis from session state if available
        analysis = st.session_state.get('search_analysis')
        
        if analysis is None:
            # Fallback: analyze if not cached (shouldn't happen in normal flow)
            from ..analysis.xml_structure_analyzer import analyze_search_rules
            with st.spinner("Analyzing List Reports..."):
                analysis = analyze_search_rules(xml_content)
                st.session_state.search_analysis = analysis
        
        from ..core.report_classifier import ReportClassifier
        
        # Filter to List Reports only - ensure we only get Report objects, not SearchReport objects
        all_list_reports = ReportClassifier.filter_by_report_type(analysis.reports, "[List Report]")
        list_reports = [r for r in all_list_reports if hasattr(r, 'report_type')]
        list_count = len(list_reports)
        
        st.toast(f"Found {list_count} List Report{'s' if list_count != 1 else ''}", icon="📋")
        
        st.markdown("### 📋 List Reports Analysis")
        st.markdown("List Reports display patient data in column-based tables with specific data extraction rules.")
        
        if not list_reports:
            st.info("📋 No List Reports found in this XML file")
            return
        
        # List Reports metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📋 List Reports", list_count)
        with col2:
            total_columns = sum(len(report.column_groups) if hasattr(report, 'column_groups') and report.column_groups else 0 for report in list_reports)
            st.metric("📊 Total Column Groups", total_columns)
        with col3:
            # For List Reports, criteria are in column groups, not main criteria_groups
            reports_with_criteria = 0
            for report in list_reports:
                has_column_criteria = False
                if hasattr(report, 'column_groups') and report.column_groups:
                    has_column_criteria = any(group.get('has_criteria', False) for group in report.column_groups)
                if report.criteria_groups or has_column_criteria:
                    reports_with_criteria += 1
            st.metric("🔍 Reports with Criteria", reports_with_criteria)
        
        # List Report browser
        render_report_type_browser(list_reports, analysis, "List Report", "📋")
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error analyzing List Reports: {str(e)}")
        with st.expander("Debug Information", expanded=False):
            st.code(error_details)


def render_audit_reports_tab(xml_content: str, xml_filename: str):
    """Render the Audit Reports tab with dedicated Audit Report browser and analysis"""
    if not xml_content:
        st.info("📊 Upload and process an XML file to see Audit Reports")
        return
    
    try:
        # Use cached analysis from session state if available
        analysis = st.session_state.get('search_analysis')
        
        if analysis is None:
            # Fallback: analyze if not cached (shouldn't happen in normal flow)
            from ..analysis.xml_structure_analyzer import analyze_search_rules
            with st.spinner("Analyzing Audit Reports..."):
                analysis = analyze_search_rules(xml_content)
                st.session_state.search_analysis = analysis
        
        from ..core.report_classifier import ReportClassifier
        
        # Get audit reports from report_results (proper Report objects with metadata)
        report_results = st.session_state.get('report_results')
        if report_results and hasattr(report_results, 'report_breakdown') and 'audit' in report_results.report_breakdown:
            audit_reports = report_results.report_breakdown['audit']
        else:
            all_audit_reports = ReportClassifier.filter_by_report_type(analysis.reports, "[Audit Report]")
            audit_reports = [r for r in all_audit_reports if hasattr(r, 'report_type')]
        
        audit_count = len(audit_reports)
        
        st.toast(f"Found {audit_count} Audit Report{'s' if audit_count != 1 else ''}", icon="📊")
        
        st.markdown("### 📊 Audit Reports Analysis")
        st.markdown("Audit Reports provide organizational aggregation for quality monitoring and compliance tracking.")
        
        if not audit_reports:
            st.info("📊 No Audit Reports found in this XML file")
            return
        
        # Audit Reports metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Audit Reports", audit_count)
        with col2:
            # Count unique population references across all audit reports
            all_populations = set()
            for report in audit_reports:
                if hasattr(report, 'population_references') and report.population_references:
                    all_populations.update(report.population_references)
            st.metric("👥 Referenced Populations", len(all_populations), help="Total unique base searches referenced by all Audit Reports")
        with col3:
            # Count reports with additional criteria (non-PATIENTS table reports)
            reports_with_criteria = 0
            for report in audit_reports:
                has_criteria = hasattr(report, 'criteria_groups') and report.criteria_groups
                # Also check if it's not a simple PATIENTS table report
                is_patients_only = (hasattr(report, 'custom_aggregate') and 
                                  report.custom_aggregate and 
                                  report.custom_aggregate.get('logical_table') == 'PATIENTS' and 
                                  not has_criteria)
                if has_criteria or not is_patients_only:
                    reports_with_criteria += 1
            st.metric("🔍 Reports with Additional Criteria", reports_with_criteria, help="Reports that apply additional filtering beyond organizational aggregation")
        
        # Audit Report browser
        render_report_type_browser(audit_reports, analysis, "Audit Report", "📊")
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error analyzing Audit Reports: {str(e)}")
        with st.expander("Debug Information", expanded=False):
            st.code(error_details)


def render_aggregate_reports_tab(xml_content: str, xml_filename: str):
    """Render the Aggregate Reports tab with dedicated Aggregate Report browser and analysis"""
    if not xml_content:
        st.info("📈 Upload and process an XML file to see Aggregate Reports")
        return
    
    try:
        # Use cached analysis from session state if available
        analysis = st.session_state.get('search_analysis')
        
        if analysis is None:
            # Fallback: analyze if not cached (shouldn't happen in normal flow)
            from ..analysis.xml_structure_analyzer import analyze_search_rules
            with st.spinner("Analyzing Aggregate Reports..."):
                analysis = analyze_search_rules(xml_content)
                st.session_state.search_analysis = analysis
        
        from ..core.report_classifier import ReportClassifier
        
        # Filter to Aggregate Reports only
        all_aggregate_reports = ReportClassifier.filter_by_report_type(analysis.reports, "[Aggregate Report]")
        aggregate_reports = [r for r in all_aggregate_reports if hasattr(r, 'report_type')]
        aggregate_count = len(aggregate_reports)
        
        st.toast(f"Found {aggregate_count} Aggregate Report{'s' if aggregate_count != 1 else ''}", icon="📈")
        
        st.markdown("### 📈 Aggregate Reports Analysis")
        st.markdown("Aggregate Reports provide statistical cross-tabulation and analysis with built-in filtering capabilities.")
        
        if not aggregate_reports:
            st.info("📈 No Aggregate Reports found in this XML file")
            return
        
        # Aggregate Reports metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📈 Aggregate Reports", aggregate_count)
        with col2:
            reports_with_stats = sum(1 for report in aggregate_reports if hasattr(report, 'statistical_groups') and report.statistical_groups)
            st.metric("📊 With Statistical Setup", reports_with_stats)
        with col3:
            reports_with_builtin_filters = sum(1 for report in aggregate_reports if hasattr(report, 'aggregate_criteria') and report.aggregate_criteria)
            st.metric("🔍 With Built-in Filters", reports_with_builtin_filters)
        
        # Aggregate Report browser
        render_report_type_browser(aggregate_reports, analysis, "Aggregate Report", "📈")
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error analyzing Aggregate Reports: {str(e)}")
        with st.expander("Debug Information", expanded=False):
            st.code(error_details)


def render_report_type_browser(reports, analysis, report_type_name, icon):
    """Generic report type browser for dedicated report tabs"""
    from ..core.report_classifier import ReportClassifier
    
    if not reports:
        st.info(f"{icon} No {report_type_name}s found in this XML file")
        return
    
    # Efficient side-by-side layout like Search Analysis tab
    st.markdown("---")
    
    # Use columns for folder and report selection side-by-side
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if analysis.folders:
            folder_options = ["All Folders"] + [f.name for f in analysis.folders]
            selected_folder_name = st.selectbox(
                "📁 Select Folder",
                folder_options,
                key=f"{report_type_name.lower().replace(' ', '_')}_folder_browser"
            )
        else:
            # No folders - show message like Rule Logic Browser
            report_type_plural = f"{report_type_name}s"
            st.selectbox(
                "📁 Select Folder",
                [f"All {report_type_plural} (No Folders)"],
                disabled=True,
                key=f"{report_type_name.lower().replace(' ', '_')}_folder_none"
            )
            selected_folder_name = f"All {report_type_plural} (No Folders)"
        
    # Filter reports by folder
    selected_folder = None
    if analysis.folders and selected_folder_name not in ["All Folders", f"All {report_type_name}s (No Folders)"]:
        selected_folder = next((f for f in analysis.folders if f.name == selected_folder_name), None)
    
    if selected_folder:
        folder_reports = [r for r in reports if r.folder_id == selected_folder.id]
    else:
        folder_reports = reports
    
    # Create report selection options
    report_options = []
    for report in folder_reports:
        option_text = report.name
        report_options.append((option_text, report))
    
    # Sort by name
    report_options.sort(key=lambda x: x[1].name)
    
    with col2:
        if report_options:
            selected_report_text = st.selectbox(
                f"📋 Select {report_type_name}",
                [option[0] for option in report_options],
                key=f"{report_type_name.lower().replace(' ', '_')}_selection"
            )
        else:
            st.selectbox(
                f"📋 Select {report_type_name}",
                ["No reports in selected folder"],
                disabled=True,
                key=f"{report_type_name.lower().replace(' ', '_')}_selection_empty"
            )
            selected_report_text = None
    
    # Display analysis status
    if selected_folder:
        st.info(f"📂 Showing {len(folder_reports)} {report_type_name}s from folder: **{selected_folder.name}**")
    elif analysis.folders:
        st.info(f"{icon} Showing all {len(folder_reports)} {report_type_name}s from all folders")
    else:
        st.info(f"{icon} Showing all {len(folder_reports)} {report_type_name}s (no folder organization)")
    
    if not folder_reports:
        st.warning(f"No {report_type_name}s found in the selected scope.")
        return
    
    if selected_report_text:
        # Find the selected report
        selected_report = next((option[1] for option in report_options if option[0] == selected_report_text), None)
        
        if selected_report:
            # Render the selected report visualization
            render_report_visualization(selected_report, analysis)


def render_xml_structure_tabs(xml_content: str, xml_filename: str):
    """Render XML structure analysis with sub-tabs"""
    if not xml_content:
        st.info("📋 Upload and process an XML file to see XML structure analysis")
        return
    
    try:
        # Use cached analysis from session state if available
        analysis = st.session_state.get('search_analysis')
        
        if analysis is None:
            # Fallback: analyze if not cached (shouldn't happen in normal flow)
            from ..analysis.xml_structure_analyzer import analyze_search_rules
            with st.spinner("Analyzing XML structure..."):
                analysis = analyze_search_rules(xml_content)
                st.session_state.search_analysis = analysis
            
            # Notify user of discovered report counts
            folder_count = len(analysis.folders) if analysis.folders else 0
            report_type_counts = ReportClassifier.get_report_type_counts(analysis.reports)
            total_items = report_type_counts['Total Reports']
            
            # Detailed XML structure analysis notification
            search_count = report_type_counts['[Search]']
            list_count = report_type_counts['[List Report]']
            audit_count = report_type_counts['[Audit Report]']
            aggregate_count = report_type_counts['[Aggregate Report]']
            
            # Structure analysis breakdown
            breakdown_parts = []
            if search_count > 0:
                breakdown_parts.append(f"{search_count} search{'es' if search_count != 1 else ''}")
            if list_count > 0:
                breakdown_parts.append(f"{list_count} list report{'s' if list_count != 1 else ''}")
            if audit_count > 0:
                breakdown_parts.append(f"{audit_count} audit report{'s' if audit_count != 1 else ''}")
            if aggregate_count > 0:
                breakdown_parts.append(f"{aggregate_count} aggregate report{'s' if aggregate_count != 1 else ''}")
            
            breakdown_text = ", ".join(breakdown_parts) if breakdown_parts else f"{total_items} items"
            st.toast(f"XML Structure analyzed! {breakdown_text} across {folder_count} folder{'s' if folder_count != 1 else ''}", icon="🔍")
        
        
        # Overview metrics for all report types
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            complexity_color = {
                'Basic': '🟢',
                'Moderate': '🟡', 
                'Complex': '🟠',
                'Very Complex': '🔴'
            }
            # Safe access to complexity metrics with fallbacks for both orchestrated and legacy analysis
            complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
            complexity_level = complexity_data.get('complexity_level', 
                               complexity_data.get('classification', 'Basic'))
            complexity_score = complexity_data.get('complexity_score', 'N/A')
            
            st.metric(
                "Complexity", 
                f"{complexity_color.get(complexity_level, '⚪')} {complexity_level}",
                help=f"Score: {complexity_score}"
            )
        
        with col2:
            st.metric(
                "🔍 Searches", 
                search_count,
                help="Population-based search criteria that define patient groups"
            )
        
        with col3:
            st.metric(
                "📋 List Reports", 
                list_count,
                help="Column-based reports displaying patient data"
            )
        
        with col4:
            st.metric(
                "📊 Audit Reports", 
                audit_count,
                help="Organizational aggregation reports for quality monitoring"
            )
        
        with col5:
            st.metric(
                "📈 Aggregate Reports", 
                aggregate_count,
                help="Statistical cross-tabulation and analysis reports"
            )
        
        with col6:
            # Use overall_complexity for orchestrated analysis, fall back to complexity_metrics for legacy
            complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
            st.metric(
                "📁 Folders", 
                complexity_data.get('total_folders', 0),
                help="Organizational folder structure"
            )
        
        # Create sub-tabs for different XML structure views
        if analysis.folders:
            # Complex structure with folders
            struct_tab1, struct_tab2, struct_tab3, struct_tab4 = st.tabs([
                "📁 Folder Structure", 
                "🔧 Rule Logic Browser",
                "🔗 Dependencies",
                "📊 Reports"
            ])
        else:
            # Simple structure without folders
            struct_tab1, struct_tab2, struct_tab3 = st.tabs([
                "🔧 Rule Logic Browser",
                "🔗 Dependencies",
                "📊 Reports"
            ])
        
        if analysis.folders:
            with struct_tab1:
                render_folder_structure_tab(analysis)
            
            with struct_tab2:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab3:
                render_dependencies_tab(analysis)
            
            with struct_tab4:
                render_reports_tab(analysis)
        else:
            with struct_tab1:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab2:
                render_dependencies_tab(analysis)
            
            with struct_tab3:
                render_reports_tab(analysis)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # Print detailed error to console for debugging
        print(f"ERROR: XML structure analysis failed")
        print(f"Error: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        
        st.error(f"Error analyzing XML structure: {str(e)}")
        with st.expander("Debug Information", expanded=False):
            st.code(error_details)

def render_folder_structure_tab(analysis):
    """Render folder structure sub-tab"""
    from ..analysis.report_structure_visualizer import render_folder_structure
    render_folder_structure(analysis.folder_tree, analysis.folders, analysis.reports)

def render_dependencies_tab(analysis):
    """Render dependencies sub-tab"""
    from ..analysis.report_structure_visualizer import render_dependency_tree
    render_dependency_tree(analysis.dependency_tree, analysis.reports)


def render_detailed_rules_tab(analysis, xml_filename):
    """Render detailed rules and export sub-tab"""
    from ..analysis.search_rule_visualizer import render_detailed_rules, render_complexity_analysis, export_rule_analysis
    from ..export_handlers import UIExportManager
    
    # Detailed rule breakdown
    with st.expander("🔧 Detailed Rule Breakdown", expanded=True):
        # Import at the top of the function scope
        from ..core.report_classifier import ReportClassifier
        
        # Use searches from orchestrated results if available
        if hasattr(analysis, 'orchestrated_results') and analysis.orchestrated_results and hasattr(analysis.orchestrated_results, 'searches'):
            # Use searches from orchestrated results
            search_only_reports = analysis.orchestrated_results.searches
        elif hasattr(analysis, 'searches') and analysis.searches:
            # Direct orchestrated analysis - use searches directly
            search_only_reports = analysis.searches
        else:
            # Legacy analysis - filter reports to get searches only
            search_only_reports = ReportClassifier.filter_searches_only(analysis.reports)
        
        # Debug information (only if debug mode is enabled)
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug: Total reports before filtering: {len(analysis.reports)}")
            st.write(f"Debug: Search reports after filtering: {len(search_only_reports)}")
            
            # Handle duplicate report names
            name_counts = {}
            for r in analysis.reports:
                name = r.name
                if name not in name_counts:
                    name_counts[name] = []
                name_counts[name].append(r)
            
            duplicates = {name: reports for name, reports in name_counts.items() if len(reports) > 1}
            if duplicates:
                st.write("Debug: Found duplicate names:")
                for name, reports in duplicates.items():
                    st.write(f"  '{name}' appears {len(reports)} times:")
                    for r in reports:
                        classification = ReportClassifier.classify_report_type(r)
                        is_list_report = hasattr(r, 'is_list_report') and r.is_list_report
                        is_actual_search = ReportClassifier.is_actual_search(r)
                        parent_guid = getattr(r, 'parent_guid', 'None')
                        st.write(f"    - ID: {r.id}, Classification: {classification}, is_list_report: {is_list_report}, is_actual_search: {is_actual_search}, parent_guid: {parent_guid}")
            
        
        render_detailed_rules(search_only_reports, analysis)
    
    # Complexity analysis
    with st.expander("📈 Complexity Analysis", expanded=False):
        # Use overall_complexity for orchestrated analysis, fall back to complexity_metrics for legacy
        complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
        render_complexity_analysis(complexity_data, analysis)
    
    # Consolidated Export Section
    st.markdown("---")
    st.subheader("📤 Export Options")
    
    # Initialize export manager
    export_manager = UIExportManager(analysis)
    
    # Create organized columns for different export types
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 Analysis Exports**")
        
        # Rule analysis text export
        from ..analysis.search_rule_visualizer import generate_rule_analysis_report
        report_text, filename = generate_rule_analysis_report(analysis, xml_filename)
        st.download_button(
            label="📥 Rule Analysis (TXT)",
            data=report_text,
            file_name=filename,
            mime="text/plain",
            help="Download detailed rule analysis as text file"
        )
        
    
    with col2:
        st.markdown("**💊 Clinical Codes**")
        
        # Clinical codes export
        include_report_codes = st.session_state.get('clinical_include_report_codes', True)
        show_code_sources = st.session_state.get('clinical_show_code_sources', True)
        current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
        
        # In unique codes mode, don't include source tracking as it's misleading
        # (each unique code might appear in multiple sources)
        include_source_tracking = show_code_sources and (current_mode == 'unique_per_entity')
        
        codes_filename, codes_content = export_manager.clinical_export.export_all_codes_as_csv(
            analysis.reports, 
            include_search_context=True,
            include_source_tracking=include_source_tracking,
            include_report_codes=include_report_codes,
            deduplication_mode=current_mode
        )
        st.download_button(
            label="📥 All Clinical Codes (CSV)",
            data=codes_content,
            file_name=codes_filename,
            mime="text/csv",
            help="Download all clinical codes with enhanced metadata"
        )
        
        # Optional statistics
        if st.checkbox("📊 Show Code Statistics", key="show_code_stats"):
            stats = export_manager.clinical_export.get_code_statistics(analysis.reports)
            export_manager._render_code_statistics(stats)
    
    with col3:
        st.markdown("**📁 Bulk Exports**")
        
        # All searches ZIP export
        try:
            zip_buffer = export_manager._create_bulk_search_export(analysis, xml_filename)
            if zip_buffer:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                zip_filename = f"all_searches_{timestamp}.zip"
                st.download_button(
                    label="📦 All Searches (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=zip_filename,
                    mime="application/zip",
                    help="Download comprehensive analysis of all searches"
                )
            else:
                st.warning("Bulk export not available - check console for errors")
        except Exception as e:
            st.error(f"Bulk export error: {str(e)}")

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
        if processing_time > 120:
            st.error(f"**Processing Time:** {processing_time:.2f}s")
        elif processing_time > 60:
            st.warning(f"**Processing Time:** {processing_time:.2f}s")
        else:
            st.success(f"**Processing Time:** {processing_time:.2f}s")
    
    with col3:
        st.info(f"**Processed:** {audit_stats['xml_stats']['processing_timestamp']}")
    
    # XML Structure Analysis
    st.write("### 🏗️ XML Structure Analysis")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
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
    
    with col5:
        # Clinical Searches count
        search_results = st.session_state.get('search_results')
        search_count = len(search_results.searches) if search_results and hasattr(search_results, 'searches') else 0
        if search_count > 0:
            st.success(f"**Clinical Searches:** {search_count}")
        else:
            st.info(f"**Clinical Searches:** {search_count}")
    
    with col6:
        # Reports count with breakdown
        report_results = st.session_state.get('report_results')
        if report_results and hasattr(report_results, 'report_breakdown'):
            total_reports = sum(len(reports) for reports in report_results.report_breakdown.values())
            if total_reports > 0:
                st.success(f"**Reports Found:** {total_reports}")
            else:
                st.info(f"**Reports Found:** {total_reports}")
        else:
            st.info(f"**Reports Found:** 0")
    
    # Show folder count in a second row
    st.write("")  # Add some spacing
    col_folder1, col_folder2, col_folder_spacer = st.columns([1, 1, 4])
    
    with col_folder1:
        # Folders count
        analysis = st.session_state.get('search_analysis')
        folder_count = len(analysis.folders) if analysis and hasattr(analysis, 'folders') else 0
        if folder_count > 0:
            st.success(f"**Folders Found:** {folder_count}")
        else:
            st.info(f"**Folders Found:** {folder_count}")
    
    with col_folder2:
        # Report type breakdown as detailed info
        if report_results and hasattr(report_results, 'report_breakdown'):
            breakdown_parts = []
            for report_type, reports in report_results.report_breakdown.items():
                if reports:
                    count = len(reports)
                    breakdown_parts.append(f"{count} {report_type}")
            
            if breakdown_parts:
                breakdown_text = ", ".join(breakdown_parts)
                st.info(f"**Report Types:** {breakdown_text}")
            else:
                st.info(f"**Report Types:** None")
        else:
            st.info(f"**Report Types:** None")
    
    # Enhanced Translation Accuracy including report data
    st.write("### 🎯 Translation Accuracy")
    trans_accuracy = audit_stats['translation_accuracy']
    
    # Get report data for enhanced metrics
    report_results = st.session_state.get('report_results')
    report_clinical_count = 0
    if report_results and hasattr(report_results, 'clinical_codes'):
        report_clinical_count = len(report_results.clinical_codes)
    
    # Enhanced clinical codes breakdown
    search_found = trans_accuracy['clinical_codes']['found']
    search_total = trans_accuracy['clinical_codes']['total']
    total_clinical = search_total + report_clinical_count
    total_found = search_found + report_clinical_count  # Report codes always found
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Search Codes**")
        
        # Search clinical codes
        render_success_rate_metric(
            "Search Clinical Codes",
            search_found,
            search_total
        )
        
        # Original clinical codes metric (for reference)
        st.caption(f"Parsed from clinical searches")
    
    with col2:
        st.markdown("**Report Codes**") 
        
        # Report clinical codes (always 100% since they use same lookup)
        render_success_rate_metric(
            "Report Clinical Codes",
            report_clinical_count,
            report_clinical_count
        )
        
        if report_clinical_count > 0:
            # Get report type breakdown for accurate captions
            report_type_caption = _build_report_type_caption(report_results)
            st.caption(f"Parsed from {report_type_caption}")
        else:
            st.caption("No reports found in XML")
    
    with col3:
        st.markdown("**Combined Totals**")
        
        # Combined clinical codes
        render_success_rate_metric(
            "All Clinical Codes",
            total_found,
            total_clinical
        )
        
        st.caption(f"Search + Report codes combined")
    
    # Additional metrics section
    st.write("---")
    col_additional1, col_additional2 = st.columns(2)
    
    with col_additional1:
        st.markdown("**Other Standalone Items**")
        
        render_success_rate_metric(
            "Standalone Medications",
            trans_accuracy['medications']['found'],
            trans_accuracy['medications']['total']
        )
    
    with col_additional2:
        st.markdown("**Pseudo-Refset Members**")
        
        # Clinical members
        render_success_rate_metric(
            "Clinical Members",
            trans_accuracy['pseudo_refset_clinical']['found'],
            trans_accuracy['pseudo_refset_clinical']['total']
        )
        
        # Medication members
        render_success_rate_metric(
            "Medication Members",
            trans_accuracy['pseudo_refset_medications']['found'],
            trans_accuracy['pseudo_refset_medications']['total']
        )
    
    # Enhanced overall success rate including report data
    st.write("---")
    
    # Calculate enhanced overall metrics
    original_overall_found = trans_accuracy['overall']['found']
    original_overall_total = trans_accuracy['overall']['total']
    enhanced_overall_found = original_overall_found + report_clinical_count
    enhanced_overall_total = original_overall_total + report_clinical_count
    
    col_overall1, col_overall2 = st.columns(2)
    
    with col_overall1:
        render_success_rate_metric(
            "Original Overall Success",
            original_overall_found,
            original_overall_total
        )
        st.caption("Based on main translation only")
    
    with col_overall2:
        render_success_rate_metric(
            "Enhanced Overall Success",
            enhanced_overall_found,
            enhanced_overall_total
        )
        st.caption("Including search + report codes")
    
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
                st.success(f"**Codes With 'Include Children = True':** {include_children}")
            else:
                st.info(f"**Codes With 'Include Children = True':** {include_children}")
            
            # Display names present
            display_names = quality['has_display_names']
            total_references = audit_stats['xml_structure']['total_guid_occurrences']
            if total_references > 0:
                display_percentage = (display_names / total_references) * 100
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
        # Use export manager for enhanced JSON export
        from ..export_handlers.ui_export_manager import UIExportManager
        export_manager = UIExportManager()
        export_manager.render_enhanced_json_export(audit_stats)
    
    with col2:
        # Export summary report
        from ..utils.audit import create_validation_report
        summary_report = create_validation_report(audit_stats)
        st.download_button(
            label="📋 Download Summary Report",
            data=summary_report,
            file_name=f"processing_report_{audit_stats['xml_stats']['filename']}.txt",
            mime="text/plain"
        )
    
    with col3:
        # Use export manager for proper analytics export
        from ..export_handlers.ui_export_manager import UIExportManager
        export_manager = UIExportManager()
        export_manager.render_analytics_export(audit_stats)


def render_reports_tab(analysis):
    """Render reports sub-tab with folder browser and report visualization"""
    
    if not analysis or not analysis.reports:
        st.info("📋 No reports found in this XML file")
        return
    
    # Import here to avoid circular imports
    from ..core.report_classifier import ReportClassifier
    from ..export_handlers.search_export import SearchExportHandler
    
    st.markdown("**📊 EMIS Report Explorer**")
    st.markdown("Browse and visualize all report types: Search, List, Audit, and Aggregate reports.")
    
    # Get report type counts for overview
    report_type_counts = ReportClassifier.get_report_type_counts(analysis.reports)
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔍 Searches", report_type_counts['[Search]'])
    with col2:
        st.metric("📋 List Reports", report_type_counts['[List Report]'])
    with col3:
        st.metric("📊 Audit Reports", report_type_counts['[Audit Report]'])
    with col4:
        st.metric("📈 Aggregate Reports", report_type_counts['[Aggregate Report]'])
    
    # Folder browser section
    st.markdown("---")
    
    # Folder selection (if folders exist)
    selected_folder = None
    if analysis.folders:
        st.subheader("📁 Browse by Folder")
        
        # Create folder options
        folder_options = ["All Folders"] + [f.name for f in analysis.folders]
        selected_folder_name = st.selectbox(
            "Select folder to view reports:",
            folder_options,
            key="reports_folder_browser"
        )
        
        if selected_folder_name != "All Folders":
            # Find the selected folder
            selected_folder = next((f for f in analysis.folders if f.name == selected_folder_name), None)
    
    # Filter reports based on selected folder
    if selected_folder:
        # Get reports in the selected folder
        folder_reports = [r for r in analysis.reports if r.folder_id == selected_folder.id]
        st.info(f"📂 Showing {len(folder_reports)} reports from folder: **{selected_folder.name}**")
    else:
        folder_reports = analysis.reports
        if analysis.folders:
            st.info(f"📊 Showing all {len(folder_reports)} reports from all folders")
        else:
            st.info(f"📊 Showing all {len(folder_reports)} reports")
    
    if not folder_reports:
        st.warning("No reports found in the selected scope.")
        return
    
    # Report type filter
    st.subheader("🔍 Filter by Report Type")
    
    report_types = ["All Types", "[Search]", "[List Report]", "[Audit Report]", "[Aggregate Report]"]
    selected_type = st.selectbox(
        "Filter by report type:",
        report_types,
        key="reports_type_filter"
    )
    
    # Apply type filter
    if selected_type == "All Types":
        filtered_reports = folder_reports
    else:
        filtered_reports = ReportClassifier.filter_by_report_type(folder_reports, selected_type)
    
    st.info(f"🎯 Found {len(filtered_reports)} reports matching your criteria")
    
    # Report selection and visualization
    if filtered_reports:
        st.subheader("📋 Select Report to Visualize")
        
        # Create report selection options with type and name
        report_options = []
        for report in filtered_reports:
            report_type = ReportClassifier.classify_report_type(report)
            clean_type = report_type.strip('[]')
            option_text = f"{clean_type}: {report.name}"
            report_options.append((option_text, report))
        
        # Sort options by type then name
        report_options.sort(key=lambda x: (x[1].report_type or 'search', x[1].name))
        
        selected_report_text = st.selectbox(
            "Choose a report to view details:",
            [option[0] for option in report_options],
            key="reports_selection"
        )
        
        if selected_report_text:
            # Find the selected report
            selected_report = next((option[1] for option in report_options if option[0] == selected_report_text), None)
            
            if selected_report:
                # Render the selected report visualization
                render_report_visualization(selected_report, analysis)


def render_report_visualization(report, analysis):
    """Render detailed visualization for a specific report based on its type"""
    
    from ..core.report_classifier import ReportClassifier
    
    report_type = ReportClassifier.classify_report_type(report)
    
    st.markdown("---")
    st.subheader(f"📊 {report_type} {report.name}")
    
    # Helper function to resolve parent search name from GUID
    def get_parent_search_name(report, analysis):
        if hasattr(report, 'direct_dependencies') and report.direct_dependencies:
            parent_guid = report.direct_dependencies[0]  # First dependency is usually the parent
            # Find the parent report by GUID
            for parent_report in analysis.reports:
                if parent_report.id == parent_guid:
                    return parent_report.name
            return f"Search {parent_guid[:8]}..."  # Fallback to shortened GUID
        return None
    
    # Report header with useful info
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if report.description:
            st.markdown(f"**Description:** {report.description}")
        
        # Parent relationship context with proper EMIS terminology
        parent_search_name = get_parent_search_name(report, analysis)
        if parent_search_name:
            st.markdown(f"**Parent Search:** {parent_search_name}")
        elif report.parent_type == 'ACTIVE':
            st.markdown(f"**Population:** All currently registered regular patients")
        elif report.parent_type == 'ALL':
            st.markdown(f"**Population:** All patients (including left and deceased)")
        elif report.parent_type == 'POP':
            st.markdown(f"**Population:** Population-based (filtered)")
        elif hasattr(report, 'parent_guid') and report.parent_guid:
            # Custom search parent - resolve the GUID to search name
            parent_name = get_parent_search_name(report, analysis)
            if parent_name:
                st.markdown(f"**Parent Search:** {parent_name}")
            else:
                st.markdown(f"**Parent Search:** Custom search ({report.parent_guid[:8]}...)")
        elif report.parent_type:
            st.markdown(f"**Parent Type:** {report.parent_type}")  # Fallback for unknown types
        
        st.markdown(f"**Search Date:** {report.search_date}")
    
    with col2:
        # Export button using dedicated ReportExportHandler
        export_handler = ReportExportHandler(analysis)
        try:
            filename, content = export_handler.generate_report_export(report)
            st.download_button(
                label=f"📥 Export {report_type.strip('[]')}",
                data=content,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help=f"Download comprehensive {report_type.strip('[]')} export with structure, filters, and clinical codes"
            )
        except Exception as e:
            st.error(f"Export failed: {e}")
            st.error(f"Debug info - Exception type: {type(e).__name__}")
            import traceback
            st.error(f"Full traceback: {traceback.format_exc()}")
    
    # Type-specific visualization with proper type checking
    if hasattr(report, 'report_type'):
        # This is a Report object from report_analyzer
        if report.report_type == 'search':
            render_search_report_details(report)
        elif report.report_type == 'list':
            render_list_report_details(report)
        elif report.report_type == 'audit':
            render_audit_report_details(report)
        elif report.report_type == 'aggregate':
            render_aggregate_report_details(report)
        else:
            st.error(f"Unknown report type: {report.report_type}")
    else:
        # This is a SearchReport object from search_analyzer - shouldn't be in report visualization
        st.error("⚠️ SearchReport object passed to report visualization - this indicates a data flow issue")
        st.write("Object type:", type(report).__name__)
        if hasattr(report, 'name'):
            st.write("Name:", report.name)


def render_search_report_details(report):
    """Render Search Report specific details"""
    st.markdown("### 🔍 Search Criteria")
    
    if report.criteria_groups:
        for i, group in enumerate(report.criteria_groups, 1):
            with st.expander(f"Rule {i}: {group.member_operator} Logic ({len(group.criteria)} criteria)", expanded=False):
                st.markdown(f"**Logic:** {group.member_operator}")
                st.markdown(f"**Action if True:** {group.action_if_true}")
                st.markdown(f"**Action if False:** {group.action_if_false}")
                
                if group.criteria:
                    st.markdown("**Criteria:**")
                    for j, criterion in enumerate(group.criteria, 1):
                        st.markdown(f"  {j}. **{criterion.display_name}** ({criterion.table})")
                        if criterion.description:
                            st.markdown(f"     _{criterion.description}_")
    else:
        st.info("No search criteria found")


def render_list_report_details(report):
    """Render List Report specific details"""
    st.markdown("### 📋 Column Structure")
    
    if report.column_groups:
        for i, group in enumerate(report.column_groups, 1):
            # Combine group info into cleaner header
            group_name = group.get('display_name', 'Unnamed')
            logical_table = group.get('logical_table', 'N/A')
            with st.expander(f"Group {i}: {group_name} (Logical Table: {logical_table})", expanded=False):  # Default closed
                
                # Column structure (user-visible EMIS data)
                columns = group.get('columns', [])
                if columns:
                    st.markdown("**📊 Columns:**")
                    col_data = []
                    for col in columns:
                        # Only show what users see in the EMIS UI - the Display Name
                        col_data.append({
                            'Column': col.get('display_name', col.get('column', ''))  # Fallback to technical name if no display name
                        })
                    
                    if col_data:
                        import pandas as pd
                        df = pd.DataFrame(col_data)
                        st.dataframe(df, width='stretch', hide_index=True)
                else:
                    st.info("No columns defined")
                
                # Filtering criteria
                st.markdown(f"**Has Criteria:** {'Yes' if group.get('has_criteria', False) else 'No'}")
                
                # Criteria implementation details
                if group.get('has_criteria', False) and group.get('criteria_details'):
                    criteria_details = group['criteria_details']
                    st.markdown("**🔍 Column Group Criteria:**")
                    
                    criteria_count = criteria_details.get('criteria_count', 0)
                    st.info(f"This column group has {criteria_count} filtering criterion that determines which records appear in this column section.")
                    
                    # Criteria display using standard format
                    criteria_list = criteria_details.get('criteria', [])
                    for j, criterion in enumerate(criteria_list, 1):
                        
                        # Table and action information
                        table_name = criterion.get('table', 'UNKNOWN')
                        negation = criterion.get('negation', False)
                        
                        st.markdown(f"**Table:** {table_name}")
                        
                        if negation:
                            st.markdown("**Action:** ❌ **Exclude**")
                        else:
                            st.markdown("**Action:** ✅ **Include**")
                        
                        # Value sets section
                        value_sets = criterion.get('value_sets', [])
                        total_codes = sum(len(vs.get('values', [])) for vs in value_sets) if value_sets else 0
                        if value_sets:
                            with st.expander(f"🏥 Value Set {j} ({total_codes} codes)", expanded=False):
                                for i, value_set in enumerate(value_sets, 1):
                                    code_system = value_set.get('code_system', 'Unknown')
                                    
                                    # Transform internal code system names to user-friendly labels
                                    if 'SNOMED_CONCEPT' in code_system:
                                        system_display = "SNOMED CT"
                                    elif 'SCT_DRGGRP' in code_system:
                                        system_display = "Drug Group Classification"
                                    elif 'EMISINTERNAL' in code_system:
                                        system_display = "EMIS Internal Classifications"
                                    else:
                                        system_display = code_system
                                    
                                    st.markdown(f"**System:** {system_display}")
                                    
                                    # Display codes as scrollable dataframe with icons
                                    codes = value_set.get('values', [])
                                    if codes:
                                        import pandas as pd
                                        
                                        # Prepare data for dataframe display
                                        code_data = []
                                        for code in codes:
                                            emis_guid = code.get('value', 'N/A')
                                            code_name = code.get('display_name', 'N/A')
                                            include_children = code.get('include_children', False)
                                            
                                            # Check if this is a refset
                                            is_refset = code.get('is_refset', False)
                                            
                                            # Handle refsets differently - they are direct SNOMED codes
                                            if is_refset:
                                                snomed_code = emis_guid  # Refset codes are direct SNOMED codes
                                                # Clean up the description for refsets
                                                if code_name.startswith('Refset: ') and '[' in code_name and ']' in code_name:
                                                    # Extract just the name part before the bracket
                                                    clean_name = code_name.replace('Refset: ', '').split('[')[0]
                                                    code_name = clean_name
                                                scope = '🎯 Refset'
                                            else:
                                                snomed_code = _lookup_snomed_for_ui(emis_guid)
                                                # Determine scope indicator for regular codes
                                                if include_children:
                                                    scope = '👥 + Children'
                                                else:
                                                    scope = '🎯 Exact'
                                            
                                            code_data.append({
                                                'EMIS Code': emis_guid,
                                                'SNOMED Code': snomed_code,
                                                'Description': code_name,
                                                'Scope': scope,
                                                'Is Refset': 'Yes' if is_refset else 'No'
                                            })
                                        
                                        # Create dataframe with custom styling
                                        codes_df = pd.DataFrame(code_data)
                                        
                                        # Display as scrollable table like Clinical Codes tab
                                        st.dataframe(
                                            codes_df,
                                            width='stretch',
                                            hide_index=True,
                                            column_config={
                                                "EMIS Code": st.column_config.TextColumn(
                                                    "🔍 EMIS Code",
                                                    width="medium"
                                                ),
                                                "SNOMED Code": st.column_config.TextColumn(
                                                    "🩺 SNOMED Code", 
                                                    width="medium"
                                                ),
                                                "Description": st.column_config.TextColumn(
                                                    "📝 Description",
                                                    width="large"
                                                ),
                                                "Scope": st.column_config.TextColumn(
                                                    "🔗 Scope",
                                                    width="small"
                                                ),
                                                "Is Refset": st.column_config.TextColumn(
                                                    "🎯 Refset",
                                                    width="small"
                                                )
                                            }
                                        )
                        
                        # Filter criteria section
                        st.markdown("**⚙️ Filters:**")
                        column_filters = criterion.get('column_filters', [])
                        if column_filters:
                            for filter_item in column_filters:
                                # Handle column being either string or list
                                column_value = filter_item.get('column', '')
                                if isinstance(column_value, list):
                                    filter_column = str(column_value[0]).upper() if column_value else ''
                                else:
                                    filter_column = str(column_value).upper()
                                filter_name = filter_item.get('display_name', 'Filter')
                                
                                if 'DATE' in filter_column:
                                    # Parse date range from XML structure: rangeValue/rangeFrom
                                    range_info = filter_item.get('range', {})
                                    if range_info:
                                        # Handle different XML parsing structures for range data
                                        range_from = range_info.get('from', {}) or range_info.get('range_from', {})
                                        if range_from:
                                            operator = range_from.get('operator', 'GT')
                                            value = range_from.get('value', '-1')
                                            unit = range_from.get('unit', 'YEAR')
                                            
                                            if value and unit and operator == 'GT':
                                                # Convert negative relative values to positive for display
                                                display_value = value.replace('-', '') if value.startswith('-') else value
                                                unit_display = unit.lower() if unit else 'year'
                                                st.caption(f"• Date is after {display_value} {unit_display} before the search date")
                                            else:
                                                st.caption(f"• Date is after 1 year before the search date")
                                        else:
                                            # Default fallback for standard EMIS date filtering
                                            st.caption(f"• Date is after 1 year before the search date")
                                else:
                                    # Standard clinical code filter with count
                                    if total_codes > 0:
                                        st.caption(f"• Include {total_codes} specified clinical codes")
                                    else:
                                        st.caption(f"• Include specified clinical codes")
                        
                        # Record ordering and restrictions
                        restrictions = criterion.get('restrictions', [])
                        if restrictions:
                            for restriction in restrictions:
                                if restriction.get('record_count'):
                                    count = restriction.get('record_count')
                                    direction = restriction.get('direction', 'DESC').upper()
                                    column = restriction.get('ordering_column')
                                    
                                    if column and column != 'None':
                                        st.caption(f"• Ordering by: {column}, select the latest {count}")
                                    else:
                                        st.caption(f"• Ordering by: Date, select the latest {count}")
                                else:
                                    restriction_desc = restriction.get('description', 'Record restriction applied')
                                    st.caption(f"• Restriction: {restriction_desc}")
                        
                        if j < len(criteria_list):  # Add separator if not last criterion
                            st.markdown("---")
    else:
        st.info("No column groups found")
    
    # Dependencies are now shown in the header as "Parent Search" - no need for separate section


def render_audit_report_details(report):
    """Render Audit Report specific details following the exact List Report format"""
    
    # Helper function to resolve population GUIDs to search names
    def get_member_search_names(report, analysis):
        """Resolve population GUIDs to meaningful search names"""
        if not hasattr(report, 'population_references') or not report.population_references:
            return []
        
        member_searches = []
        for pop_guid in report.population_references:
            # Find the search by GUID
            search_report = next((r for r in analysis.reports if r.id == pop_guid), None)
            if search_report:
                member_searches.append(search_report.name)
            else:
                member_searches.append(f"Search {pop_guid[:8]}...")  # Fallback to shortened GUID
        
        return member_searches
    
    # Get analysis from session state for resolving names
    analysis = st.session_state.get('search_analysis')
    
    # Aggregation Configuration Section
    st.markdown("### 📊 Aggregation Configuration")
    
    if hasattr(report, 'custom_aggregate') and report.custom_aggregate:
        agg = report.custom_aggregate
        
        col1, col2 = st.columns(2)
        with col1:
            logical_table = agg.get('logical_table', 'N/A')
            st.markdown(f"**Logical Table:** {logical_table}")
            result = agg.get('result', {})
            st.markdown(f"**Result Source:** {result.get('source', 'N/A')}")
            st.markdown(f"**Calculation Type:** {result.get('calculation_type', 'N/A')}")
        
        with col2:
            # Show member search count
            pop_count = len(report.population_references) if hasattr(report, 'population_references') else 0
            st.markdown(f"**Member Searches:** {pop_count}")
            
            # Show if it has additional criteria
            has_criteria = hasattr(report, 'criteria_groups') and report.criteria_groups
            criteria_type = "Complex (with additional criteria)" if has_criteria else "Simple (organizational only)"
            st.markdown(f"**Type:** {criteria_type}")
        
        # Dynamic Grouping Section
        groups = agg.get('groups', [])
        if groups:
            group_columns = []
            for group in groups:
                group_name = group.get('display_name', 'Unnamed')
                # Use display name if available, otherwise fall back to column name
                if group_name and group_name != 'Unnamed':
                    group_columns.append(group_name)
                else:
                    grouping_cols = group.get('grouping_column', [])
                    if isinstance(grouping_cols, str):
                        grouping_cols = [grouping_cols]
                    group_columns.extend(grouping_cols)
            
            # Determine grouping type for dynamic title
            grouping_type = "Data Grouping"  # Default fallback
            if group_columns:
                # Check for common patterns to determine grouping type
                columns_str = ' '.join(group_columns).lower()
                if any(term in columns_str for term in ['practice', 'organization', 'organisation', 'ccg', 'gp']):
                    grouping_type = "Organizational Grouping"
                elif any(term in columns_str for term in ['age', 'birth', 'dob']):
                    grouping_type = "Age Group Analysis"
                elif any(term in columns_str for term in ['medication', 'drug', 'prescription']):
                    grouping_type = "Medication Grouping"
                elif any(term in columns_str for term in ['clinical', 'diagnosis', 'condition', 'snomed']):
                    grouping_type = "Clinical Code Grouping"
                elif any(term in columns_str for term in ['gender', 'sex']):
                    grouping_type = "Demographic Grouping"
                elif any(term in columns_str for term in ['date', 'time', 'year', 'month']):
                    grouping_type = "Temporal Grouping"
            
            st.markdown(f"### 📋 {grouping_type}")
            st.info(f"Results grouped by: {', '.join(group_columns)}")
    else:
        st.info("No aggregation configuration found")
    
    # Member Searches Section (NEW - key feature for Audit Reports)
    if analysis:
        member_searches = get_member_search_names(report, analysis)
        if member_searches:
            st.markdown(f"### 👥 Member Searches ({len(member_searches)} searches)")
            st.info("This Audit Report combines results from the following base searches:")
            
            with st.expander("📋 View All Member Searches", expanded=False):
                for i, search_name in enumerate(member_searches, 1):
                    st.markdown(f"{i}. **{search_name}**")
            
            st.caption("Each base search defines a patient population. The Audit Report shows aggregated results across all these populations.")
    
    # Additional Criteria Section (for non-PATIENTS table reports)
    if hasattr(report, 'criteria_groups') and report.criteria_groups:
        st.markdown("### 🔍 Additional Report Criteria")
        st.info(f"This Audit Report applies {len(report.criteria_groups)} additional filtering rule(s) across all member searches.")
        
        # Use the same detailed criteria rendering as List Reports
        for i, group in enumerate(report.criteria_groups, 1):
            rule_name = f"Additional Filter {i}"
            
            with st.expander(f"🔍 {rule_name} ({group.member_operator} Logic, {len(group.criteria)} criteria)", expanded=False):
                st.markdown(f"**Logic:** {group.member_operator}")
                st.markdown(f"**Action if True:** {group.action_if_true}")
                st.markdown(f"**Action if False:** {group.action_if_false}")
                
                if group.criteria:
                    st.markdown("**Criteria Details:**")
                    for j, criterion in enumerate(group.criteria, 1):
                        st.markdown(f"**Criterion {j}: {criterion.display_name}** ({criterion.table})")
                        if criterion.description:
                            st.markdown(f"_{criterion.description}_")
                        
                        # Value sets section (same format as List Reports)
                        value_sets = criterion.value_sets or []
                        total_codes = sum(len(vs.get('values', [])) for vs in value_sets) if value_sets else 0
                        if value_sets:
                            with st.expander(f"🏥 Value Set {j} ({total_codes} codes)", expanded=False):
                                for vs_idx, value_set in enumerate(value_sets, 1):
                                    code_system = value_set.get('code_system', 'Unknown')
                                    
                                    # Transform internal code system names to user-friendly labels
                                    if 'SNOMED_CONCEPT' in code_system:
                                        system_display = "SNOMED Clinical Terminology"
                                    elif 'SCT_DRGGRP' in code_system:
                                        system_display = "Drug Group Classification"
                                    elif 'EMISINTERNAL' in code_system:
                                        system_display = "EMIS Internal Classifications"
                                    else:
                                        system_display = code_system
                                    
                                    st.markdown(f"**System:** {system_display}")
                                    
                                    # Display codes using same format as List Reports
                                    codes = value_set.get('values', [])
                                    if codes:
                                        import pandas as pd
                                        
                                        # Prepare data for dataframe display
                                        code_data = []
                                        for code in codes:
                                            emis_guid = code.get('value', 'N/A')
                                            code_name = code.get('display_name', 'N/A')
                                            include_children = code.get('include_children', False)
                                            
                                            # Check if this is a refset
                                            is_refset = code.get('is_refset', False)
                                            
                                            # Handle refsets differently - they are direct SNOMED codes
                                            if is_refset:
                                                snomed_code = emis_guid  # Refset codes are direct SNOMED codes
                                                # Clean up the description for refsets
                                                if code_name.startswith('Refset: ') and '[' in code_name and ']' in code_name:
                                                    # Extract just the name part before the bracket
                                                    clean_name = code_name.replace('Refset: ', '').split('[')[0]
                                                    code_name = clean_name
                                                scope = '🎯 Refset'
                                            else:
                                                snomed_code = _lookup_snomed_for_ui(emis_guid)
                                                # Determine scope indicator for regular codes
                                                if include_children:
                                                    scope = '👥 + Children'
                                                else:
                                                    scope = '🎯 Exact'
                                            
                                            code_data.append({
                                                'EMIS Code': emis_guid,
                                                'SNOMED Code': snomed_code,
                                                'Description': code_name,
                                                'Scope': scope,
                                                'Is Refset': 'Yes' if is_refset else 'No'
                                            })
                                        
                                        # Create dataframe with same styling as List Reports
                                        codes_df = pd.DataFrame(code_data)
                                        
                                        # Display as scrollable table
                                        st.dataframe(
                                            codes_df,
                                            width='stretch',
                                            hide_index=True,
                                            column_config={
                                                "EMIS Code": st.column_config.TextColumn(
                                                    "🔍 EMIS Code",
                                                    width="medium"
                                                ),
                                                "SNOMED Code": st.column_config.TextColumn(
                                                    "🩺 SNOMED Code", 
                                                    width="medium"
                                                ),
                                                "Description": st.column_config.TextColumn(
                                                    "📝 Description",
                                                    width="large"
                                                ),
                                                "Scope": st.column_config.TextColumn(
                                                    "🔗 Scope",
                                                    width="small"
                                                ),
                                                "Is Refset": st.column_config.TextColumn(
                                                    "🎯 Refset",
                                                    width="small"
                                                )
                                            }
                                        )
                        
                        # Filter criteria section (same format as List Reports)
                        st.markdown("**⚙️ Filters:**")
                        column_filters = criterion.column_filters or []
                        if column_filters:
                            for filter_item in column_filters:
                                # Handle column being either string or list
                                column_value = filter_item.get('column', '')
                                if isinstance(column_value, list):
                                    filter_column = str(column_value[0]).upper() if column_value else ''
                                else:
                                    filter_column = str(column_value).upper()
                                filter_name = filter_item.get('display_name', 'Filter')
                                
                                if 'DATE' in filter_column:
                                    # Parse date range from XML structure
                                    range_info = filter_item.get('range', {})
                                    if range_info:
                                        range_from = range_info.get('from', {}) or range_info.get('range_from', {})
                                        if range_from:
                                            operator = range_from.get('operator', 'GT')
                                            value = range_from.get('value', '-1')
                                            unit = range_from.get('unit', 'YEAR')
                                            
                                            if value and unit and operator == 'GT':
                                                display_value = value.replace('-', '') if value.startswith('-') else value
                                                unit_display = unit.lower() if unit else 'year'
                                                st.caption(f"• Date is after {display_value} {unit_display} before the search date")
                                            else:
                                                st.caption(f"• Date is after 1 year before the search date")
                                        else:
                                            st.caption(f"• Date is after 1 year before the search date")
                                elif 'AUTHOR' in filter_column or 'USER' in filter_column:
                                    st.caption(f"• User authorization: Active users only")
                                else:
                                    # Standard clinical code filter with count
                                    if total_codes > 0:
                                        st.caption(f"• Include {total_codes} specified clinical codes")
                                    else:
                                        st.caption(f"• Include specified clinical codes")
                        
                        # Record ordering and restrictions
                        restrictions = criterion.restrictions or []
                        if restrictions:
                            for restriction in restrictions:
                                if restriction.get('record_count'):
                                    count = restriction.get('record_count')
                                    direction = restriction.get('direction', 'DESC').upper()
                                    column = restriction.get('ordering_column')
                                    
                                    if column and column != 'None':
                                        st.caption(f"• Ordering by: {column}, select the latest {count}")
                                    else:
                                        st.caption(f"• Ordering by: Date, select the latest {count}")
                                else:
                                    restriction_desc = restriction.get('description', 'Record restriction applied')
                                    st.caption(f"• Restriction: {restriction_desc}")
                        
                        if j < len(group.criteria):  # Add separator if not last criterion
                            st.markdown("---")
    
    elif hasattr(report, 'custom_aggregate') and report.custom_aggregate:
        logical_table = report.custom_aggregate.get('logical_table', '')
        if logical_table == 'PATIENTS':
            st.markdown("### ℹ️ Simple Organizational Report")
            st.info("This Audit Report performs pure organizational aggregation without additional clinical criteria.")
        else:
            st.markdown("### ℹ️ No Additional Criteria")
            st.info(f"This Audit Report uses the {logical_table} table but does not apply additional filtering criteria.")


def render_aggregate_report_details(report):
    """Render Aggregate Report specific details"""
    st.markdown("### 📈 Statistical Configuration")
    
    # Aggregate groups
    if report.aggregate_groups:
        st.markdown("#### 📊 Aggregate Groups")
        for i, group in enumerate(report.aggregate_groups, 1):
            with st.expander(f"Group {i}: {group.get('display_name', 'Unnamed')}", expanded=False):
                st.markdown(f"**Grouping Columns:** {', '.join(group.get('grouping_columns', []))}")
                st.markdown(f"**Sub Totals:** {'Yes' if group.get('sub_totals', False) else 'No'}")
                st.markdown(f"**Repeat Header:** {'Yes' if group.get('repeat_header', False) else 'No'}")
    
    # Statistical setup with resolved names (enhanced 2025-09-18)
    if report.statistical_groups:
        st.markdown("#### 📈 Statistical Setup")
        
        # Display statistical setup with resolved names
        rows_group = next((g for g in report.statistical_groups if g.get('type') == 'rows'), None)
        cols_group = next((g for g in report.statistical_groups if g.get('type') == 'columns'), None)
        result_group = next((g for g in report.statistical_groups if g.get('type') == 'result'), None)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if rows_group:
                group_name = rows_group.get('group_name', f"Group {rows_group.get('group_id', 'Unknown')}")
                st.info(f"**Rows:** {group_name}")
            else:
                st.warning("**Rows:** Not configured")
        
        with col2:
            if cols_group:
                group_name = cols_group.get('group_name', f"Group {cols_group.get('group_id', 'Unknown')}")
                st.info(f"**Columns:** {group_name}")
            else:
                st.warning("**Columns:** Not configured")
        
        with col3:
            if result_group:
                calc_type = result_group.get('calculation_type', 'count')
                source = result_group.get('source', 'record')
                
                # Determine what we're counting based on logical table and criteria
                count_of_what = "Records"  # Default
                
                if hasattr(report, 'logical_table'):
                    logical_table = getattr(report, 'logical_table', '')
                    if logical_table == 'EVENTS':
                        count_of_what = "Clinical Codes"
                    elif logical_table == 'MEDICATION_ISSUES':
                        count_of_what = "Medication Issues"
                    elif logical_table == 'MEDICATION_COURSES':
                        count_of_what = "Medication Courses"
                    elif logical_table == 'PATIENTS':
                        count_of_what = "Patients"
                    elif logical_table:
                        count_of_what = logical_table.replace('_', ' ').title()
                
                # Check if we can get more specific from criteria
                if hasattr(report, 'aggregate_criteria') and report.aggregate_criteria:
                    criteria_groups = report.aggregate_criteria.get('criteria_groups', [])
                    for group in criteria_groups:
                        for criterion in group.get('criteria', []):
                            display_name = criterion.get('display_name', '')
                            if 'Clinical Codes' in display_name:
                                count_of_what = "Clinical Codes"
                            elif 'Medication' in display_name:
                                count_of_what = "Medications"
                            break
                
                result_text = f"{calc_type.title()} of {count_of_what}"
                st.success(f"**Result:** {result_text}")
            else:
                st.error("**Result:** Not configured")
    
    # Display built-in criteria if present (enhanced 2025-09-18)
    if hasattr(report, 'aggregate_criteria') and report.aggregate_criteria:
        st.markdown("### 🔍 Built-in Report Filters")
        st.info("This aggregate report has its own built-in criteria that filters the data before aggregation.")
        
        # Use the same sophisticated rendering as regular searches
        from ..analysis.search_rule_visualizer import render_criteria_group
        from ..analysis.common_structures import CriteriaGroup
        from ..xml_parsers.criterion_parser import SearchCriterion
        
        criteria_data = report.aggregate_criteria
        for i, criteria_group_data in enumerate(criteria_data.get('criteria_groups', [])):
            # Convert the parsed criteria to CriteriaGroup format for rendering
            criteria_objects = []
            for criterion_data in criteria_group_data.get('criteria', []):
                # Create SearchCriterion object with full data
                search_criterion = SearchCriterion(
                    id=criterion_data.get('id', ''),
                    table=criterion_data.get('table', ''),
                    display_name=criterion_data.get('display_name', ''),
                    description=criterion_data.get('description', ''),
                    negation=criterion_data.get('negation', False),
                    column_filters=criterion_data.get('column_filters', []),
                    value_sets=criterion_data.get('value_sets', []),
                    restrictions=criterion_data.get('restrictions', []),
                    linked_criteria=criterion_data.get('linked_criteria', [])
                )
                criteria_objects.append(search_criterion)
            
            # Create CriteriaGroup object
            criteria_group = CriteriaGroup(
                id=criteria_group_data.get('id', ''),
                member_operator=criteria_group_data.get('member_operator', 'AND'),
                action_if_true=criteria_group_data.get('action_if_true', 'SELECT'),
                action_if_false=criteria_group_data.get('action_if_false', 'REJECT'),
                criteria=criteria_objects,
                population_criteria=criteria_group_data.get('population_criteria', [])
            )
            
            # Use the same detailed rendering as searches
            rule_name = f"Built-in Filter {i+1}"
            render_criteria_group(criteria_group, rule_name)
    
    # Include legacy criteria if present  
    elif report.criteria_groups:
        st.markdown("### 🔍 Own Criteria")
        st.info("This aggregate report defines its own search criteria (independent of other searches)")
        render_search_report_details(report)
    
    if not report.aggregate_groups and not report.statistical_groups:
        st.info("No statistical configuration found")