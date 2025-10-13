"""
Shared utility functions for tab rendering.

This module contains helper functions that are used across multiple
tab rendering modules but are specific to tab functionality.
"""

from .common_imports import *


def _is_medication_from_context(code_system, table_context, column_context):
    """
    Determine if a code is a medication based on code system and table/column context.
    Uses the same logic as xml_utils.is_medication_code_system but as a helper function.
    """
    from ...xml_parsers.xml_utils import is_medication_code_system
    return is_medication_code_system(code_system, table_context, column_context)


def _is_pseudorefset_from_context(emis_guid, valueset_description):
    """
    Determine if a code is a pseudo-refset container based on GUID and description.
    Uses the same logic as xml_utils.is_pseudo_refset.
    """
    from ...xml_parsers.xml_utils import is_pseudo_refset
    return is_pseudo_refset(emis_guid, valueset_description)


def _is_pseudomember_from_context(valueset_guid, valueset_description):
    """
    Determine if a code is a member of a pseudo-refset based on its valueSet information.
    A code is a pseudo-refset member if its valueSet is a pseudo-refset.
    """
    from ...xml_parsers.xml_utils import is_pseudo_refset
    return is_pseudo_refset(valueset_guid, valueset_description)


def _reprocess_with_new_mode(deduplication_mode):
    """Reprocess results with new deduplication mode - isolated update that preserves other session data"""
    try:
        # Clear the unified clinical data cache since deduplication mode affects the results
        if 'unified_clinical_data_cache' in st.session_state:
            del st.session_state['unified_clinical_data_cache']
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
                st.toast(f"Reprocessed with {mode_name} mode", icon="✅")
                
                # Use experimental_rerun to avoid interfering with other tabs
                st.rerun()
    except Exception as e:
        st.error(f"Error reprocessing with new mode: {str(e)}")


def _lookup_snomed_for_ui(emis_guid: str) -> str:
    """
    Look up SNOMED code for display in UI (with caching)
    
    Args:
        emis_guid: EMIS GUID to look up
        
    Returns:
        SNOMED code if found, 'Not found' otherwise
    """
    try:
        lookup_df = st.session_state.get('lookup_df')
        emis_guid_col = st.session_state.get('emis_guid_col')
        snomed_code_col = st.session_state.get('snomed_code_col')
        
        if lookup_df is not None and emis_guid_col and snomed_code_col:
            # Use the optimized lookup function
            cache = get_optimized_lookup_cache(lookup_df, emis_guid_col, snomed_code_col)
            return cache.get(emis_guid, 'Not found')
        else:
            return 'Lookup unavailable'
    except Exception as e:
        return f'Error: {str(e)}'


def _deduplicate_clinical_data_by_emis_guid(clinical_data):
    """
    Remove duplicate clinical codes by EMIS GUID, keeping the best entry for each code.
    
    Args:
        clinical_data: List of clinical code dictionaries
        
    Returns:
        List of deduplicated clinical code dictionaries
    """
    # Group by EMIS GUID
    guid_groups = {}
    for code in clinical_data:
        emis_guid = code.get('EMIS GUID', '')
        if emis_guid not in guid_groups:
            guid_groups[emis_guid] = []
        guid_groups[emis_guid].append(code)
    
    # Select best entry from each group
    deduplicated_codes = []
    for emis_guid, codes_group in guid_groups.items():
        best_code = _select_best_clinical_code_entry(codes_group)
        deduplicated_codes.append(best_code)
    
    return deduplicated_codes


def _select_best_clinical_code_entry(codes_group):
    """
    Select the best clinical code entry from a group of duplicates.
    
    Prioritizes:
    1. Entries with 'Found' mapping status
    2. Entries with complete descriptions
    3. Most recent entries
    
    Args:
        codes_group: List of clinical code dictionaries with same EMIS GUID
        
    Returns:
        Best clinical code dictionary from the group
    """
    if len(codes_group) == 1:
        return codes_group[0]
    
    # Priority 1: Found mappings
    found_codes = [c for c in codes_group if c.get('Mapping Found') == 'Found']
    if found_codes:
        codes_group = found_codes
    
    # Priority 2: Complete descriptions
    complete_codes = [c for c in codes_group if c.get('Description', '').strip()]
    if complete_codes:
        codes_group = complete_codes
    
    # Priority 3: Most complete entry (most non-empty fields)
    def completeness_score(code):
        return sum(1 for v in code.values() if v and str(v).strip())
    
    return max(codes_group, key=completeness_score)


def _filter_report_codes_from_analysis(analysis):
    """Filter out report codes from analysis when configurable integration is disabled"""
    # Create a copy of the analysis with report criteria removed from searches
    filtered_reports = []
    for report in analysis.reports:
        if hasattr(report, 'search_criteria') and report.search_criteria:
            # Create new criteria list without report criteria
            filtered_criteria = []
            for criterion in report.search_criteria:
                if not (hasattr(criterion, 'criterion_type') and 
                       criterion.criterion_type in ['report_codes', 'list_report_codes']):
                    filtered_criteria.append(criterion)
            
            # Only include reports that still have criteria after filtering
            if filtered_criteria:
                # Create a copy of the report with filtered criteria
                import copy
                filtered_report = copy.deepcopy(report)
                filtered_report.search_criteria = filtered_criteria
                filtered_reports.append(filtered_report)
        else:
            # No criteria to filter, include as-is
            filtered_reports.append(report)
    
    # Update the analysis with filtered reports
    analysis.reports = filtered_reports
    return analysis


def _convert_analysis_codes_to_translation_format(analysis_codes):
    """Convert analysis clinical codes to translation format for display with progress tracking"""
    translated_codes = []
    
    
    # Add progress indicator for large code lists
    if len(analysis_codes) > 100:
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(f"Processing {len(analysis_codes)} clinical codes...")
    else:
        progress_bar = None
        status_text = None
    
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
        # Update progress for large datasets
        if progress_bar is not None and i % 50 == 0:  # Update every 50 items
            progress = i / len(analysis_codes)
            progress_bar.progress(progress)
            status_text.text(f"Processing clinical codes: {i}/{len(analysis_codes)} ({progress:.1%})")
        
        # Handle both raw format (code_value) and standardized format (EMIS GUID)
        emis_guid = code.get('EMIS GUID', code.get('code_value', code.get('emis_guid', ''))).strip()
        
        
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
                
                # Get SNOMED description from original XML parsing
                snomed_desc = code.get('display_name', 'N/A')
                
                # Get enriched metadata
                code_type = str(code_type_dict.get(emis_guid, 'Finding')).strip()
                has_qualifier = str(has_qualifier_dict.get(emis_guid, '0')).strip()
                is_parent = str(is_parent_dict.get(emis_guid, '0')).strip()
                descendants = str(descendants_dict.get(emis_guid, '0')).strip()
                
                
                mapping_found = 'Found'
            else:
                mapping_found = 'Not Found'
        
        # Enrich the original code with lookup data instead of creating new structure
        enriched_code = code.copy()  # Start with original structure
        
        # Add/update enriched fields
        enriched_code['SNOMED Code'] = snomed_code
        enriched_code['SNOMED Description'] = snomed_desc  
        enriched_code['Mapping Found'] = mapping_found
        enriched_code['Has Qualifier'] = has_qualifier
        enriched_code['Descendants'] = descendants
        enriched_code['Code Type'] = code_type
        enriched_code['Is Parent'] = is_parent
        
        # Preserve important original fields
        if 'is_refset' in code:
            enriched_code['is_refset'] = code['is_refset']
        if 'is_pseudorefset' in code:
            enriched_code['is_pseudorefset'] = code['is_pseudorefset']
        if 'is_pseudomember' in code:
            enriched_code['is_pseudomember'] = code['is_pseudomember']
        if 'is_pseudo' in code:
            enriched_code['is_pseudo'] = code['is_pseudo']
        if 'is_medication' in code:
            enriched_code['is_medication'] = code['is_medication']
        if 'is_pseudorefset' in code:
            enriched_code['is_pseudorefset'] = code['is_pseudorefset']
        if 'is_pseudomember' in code:
            enriched_code['is_pseudomember'] = code['is_pseudomember']
            
        # Add standard translation fields if missing
        if 'ValueSet GUID' not in enriched_code:
            enriched_code['ValueSet GUID'] = 'N/A'
        # Don't set ValueSet Description to 'N/A' - let standardization handle placeholder text
        if 'Include Children' not in enriched_code:
            enriched_code['Include Children'] = 'Yes' if code.get('include_children', False) else 'No'
        # Pseudo-refset member status is now determined by the is_pseudomember flag from XML structure analysis
        
        translated_codes.append(enriched_code)
    
    # Complete progress and cleanup
    if progress_bar is not None:
        progress_bar.progress(1.0)
        status_text.text(f"✅ Completed processing {len(analysis_codes)} clinical codes")
        # Clear progress indicators after a brief delay
        import time
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
    
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


def _add_source_info_to_clinical_data(clinical_data, guid_to_source_name=None, guid_to_source_container=None, show_sources=True):
    """Add source tracking information to clinical codes data with GUID mapping support"""
    if not show_sources or not clinical_data:
        return clinical_data
    
    # Check current deduplication mode for conditional source column display
    import streamlit as st
    current_mode = st.session_state.get('current_deduplication_mode', 'unique_codes')
    show_source_columns = (current_mode == 'unique_per_entity')
    
    # Build GUID mappings if not provided
    if guid_to_source_name is None:
        guid_to_source_name = {}
        guid_to_source_container = {} if guid_to_source_container is None else guid_to_source_container
        
        # Get search and report results for GUID mapping
        search_results = st.session_state.get('search_results')
        report_results = st.session_state.get('report_results')
        
        
        # Add search GUID mappings - map individual code EMIS GUIDs to search names with detailed container tracking
        if search_results and hasattr(search_results, 'searches'):
            for search in search_results.searches:
                for group in search.criteria_groups:
                    for criterion in group.criteria:
                        # Check if this criterion has restrictions (which contain testAttribute codes)
                        has_restrictions = hasattr(criterion, 'restrictions') and len(getattr(criterion, 'restrictions', [])) > 0
                        
                        # Check for different structural patterns based on EMIS XML patterns
                        
                        # Check if this is a linked criteria (cross-table relationships)
                        is_linked_criteria = (hasattr(criterion, 'linked_criteria') and getattr(criterion, 'linked_criteria', False)) or \
                                           (hasattr(criterion, 'linkedCriterion') and getattr(criterion, 'linkedCriterion', None))
                        
                        # Check if this is from a base criteria group (nested criterion logic)
                        is_base_criteria_group = hasattr(criterion, 'baseCriteriaGroup') and getattr(criterion, 'baseCriteriaGroup', None)
                        
                        # Check if this is a population criteria reference
                        is_population_ref = len(group.population_criteria) > 0
                        
                        # Check if restrictions contain test attributes
                        has_test_attributes = has_restrictions and hasattr(criterion, 'restrictions') and \
                                            any(hasattr(r, 'test_attribute') or hasattr(r, 'testAttribute') for r in criterion.restrictions if r)
                        
                        for value_set in criterion.value_sets:
                            # Map ValueSet GUID for refsets/pseudo-refsets (NOT description - that's different from source name)
                            valueset_guid = value_set.get('id') or value_set.get('guid')
                            if valueset_guid:
                                guid_to_source_name[valueset_guid] = search.name
                                
                                # Determine container type for ValueSet level
                                container_type = "Search Rule Main Criteria"
                                if is_base_criteria_group:
                                    container_type = "Search Rule Base Criteria Group"
                                elif is_linked_criteria:
                                    container_type = "Search Rule Linked Criteria"
                                elif is_population_ref:
                                    container_type = "Search Rule Population Reference"
                                elif has_test_attributes:
                                    container_type = "Search Rule Test Attribute"
                                elif has_restrictions:
                                    container_type = "Search Rule Restriction"
                                
                                guid_to_source_container[valueset_guid] = container_type
                            
                            # Also map individual codes within value sets
                            for value in value_set.get('values', []):
                                # Get the individual code EMIS GUID (not the ValueSet GUID)
                                emis_guid = value.get('value', '')  # This should be the individual code GUID
                                # Skip EMIS internal codes entirely - they shouldn't appear in clinical displays
                                code_system = value.get('code_system', '').upper()
                                if emis_guid and code_system != 'EMISINTERNAL':
                                    guid_to_source_name[emis_guid] = search.name
                                    
                                    # Determine container type based on EMIS XML structural patterns
                                    container_type = "Search Rule Main Criteria"
                                    
                                    # Priority order based on structural complexity
                                    if is_base_criteria_group:
                                        container_type = "Search Rule Base Criteria Group"
                                    elif is_linked_criteria:
                                        container_type = "Search Rule Linked Criteria"
                                    elif is_population_ref:
                                        container_type = "Search Rule Population Reference"
                                    elif has_test_attributes:
                                        container_type = "Search Rule Test Attribute"
                                    elif has_restrictions:
                                        # Basic restrictions without test attributes
                                        container_type = "Search Rule Restriction"
                                    
                                    guid_to_source_container[emis_guid] = container_type
        
        # Add report GUID mappings - map individual code EMIS GUIDs to report names  
        if report_results and hasattr(report_results, 'clinical_codes'):
            for code in report_results.clinical_codes:
                emis_guid = code.get('code_value', '')  # Report analyzer uses 'code_value'
                report_name = code.get('source_report_name', '')
                if emis_guid and report_name:
                    guid_to_source_name[emis_guid] = report_name
                    # Determine container type based on EMIS report structural patterns
                    container_type = "Report Main Criteria"
                    
                    # Priority order based on report structure patterns
                    if code.get('from_column_group'):
                        # List Report column groups - most specific
                        container_type = "List Report Column Group"
                    elif code.get('from_base_criteria_group'):
                        container_type = "Report Base Criteria Group"  
                    elif code.get('from_linked_criteria'):
                        container_type = "Report Linked Criteria"
                    elif code.get('from_population_ref'):
                        container_type = "Report Population Reference"
                    elif code.get('from_test_attribute'):
                        container_type = "Report Test Attribute"
                    elif code.get('from_audit_aggregate'):
                        container_type = "Audit Report Custom Aggregate"
                    elif code.get('from_sub_criteria'):
                        container_type = "Report Sub Criteria"
                    
                    guid_to_source_container[emis_guid] = container_type
        
    enhanced_data = []
    
    for code_entry in clinical_data:
        enhanced_entry = copy.deepcopy(code_entry)  # Proper deep copy
        
        # Get the GUID for mapping (try different key formats for different data types)
        emis_guid = (code_entry.get('code_value', '') or 
                    code_entry.get('EMIS GUID', '') or 
                    code_entry.get('VALUESET GUID', '') or 
                    code_entry.get('ValueSet GUID', '') or 
                    code_entry.get('SNOMED Code', ''))
        
        # Debug: Check if we have mapping data and what keys are available
        import streamlit as st
        
        # Prioritize GUID mapping over inherited source fields (which may be empty for containers)
        if guid_to_source_name and emis_guid in guid_to_source_name:
            source_name = guid_to_source_name[emis_guid]
        else:
            source_name = code_entry.get('source_name', '')  # Actual search/report name - pass through whatever was provided
        
        # Map GUID to source container if available
        if guid_to_source_container and emis_guid in guid_to_source_container:
            source_container = guid_to_source_container[emis_guid]
        else:
            source_container = code_entry.get('source_container', '')  # Container within the source structure
        
        # Extract source information from the original data if available
        source_type = code_entry.get('source_type', '')
        report_type = code_entry.get('report_type', '')
        
        # Determine the main source category 
        if source_type == 'search':
            source_category = 'Search'
        elif source_type == 'report':
            if report_type == 'list':
                source_category = 'List Report'
            elif report_type == 'audit':
                source_category = 'Audit Report'
            else:
                source_category = 'Report'
        else:
            source_category = ''  # No source info available
        
        # Add processed columns with proper data separation and NO emojis (for clean CSV export)
        # Always add source columns - the UI layer will hide them in unique_codes mode
        # Ensure string types for PyArrow compatibility
        enhanced_entry['Source Type'] = str(source_category)  # Category (Search, List Report, etc.)
        enhanced_entry['Source Name'] = str(source_name)  # Actual name of search/report - all must have names
        enhanced_entry['Source Container'] = str(source_container)  # Location within the source structure
        
        # Remove raw tracking fields now that we've processed them into display columns
        enhanced_entry.pop('source_type', None)
        enhanced_entry.pop('report_type', None) 
        enhanced_entry.pop('source_name', None)
        enhanced_entry.pop('source_container', None)
        
        # Remove unwanted columns that shouldn't be displayed
        enhanced_entry.pop('Source GUID', None)  # Remove irrelevant Source GUID
        enhanced_entry.pop('source_guid', None)  # Remove raw source GUID field
        enhanced_entry.pop('Description', None)  # Remove duplicate/unwanted Description column
        enhanced_entry.pop('Display Name', None)  # Remove unwanted Display Name column
        
        # Keep ValueSet GUID for GUID mapping purposes, but it will be hidden from display by UI layer
        
        enhanced_data.append(enhanced_entry)
    
    return enhanced_data


def ensure_analysis_cached(xml_content=None):
    """
    Ensure that analysis data is cached in session state.
    This function only returns existing cached analysis.
    
    Args:
        xml_content: XML content (ignored - kept for compatibility)
    """
    # Only return existing analysis, never trigger expensive recomputation
    analysis = st.session_state.get('search_analysis')
    xml_structure_analysis = st.session_state.get('xml_structure_analysis')
    
    return analysis or xml_structure_analysis


def extract_clinical_codes_from_searches(searches):
    """Extract clinical codes from search criteria in the orchestrated analysis"""
    clinical_codes = []
    
    for search in searches:
        if hasattr(search, 'criteria_groups'):
            for group in search.criteria_groups:
                if hasattr(group, 'criteria'):
                    for criterion in group.criteria:
                        if hasattr(criterion, 'value_sets'):
                            for value_set in criterion.value_sets:
                                # Extract clinical codes from value set
                                if value_set.get('values'):
                                    for value in value_set['values']:
                                        if value.get('code_system') != 'EMISINTERNAL':  # Exclude internal codes
                                            clinical_codes.append({
                                                'EMIS GUID': value.get('value', ''),
                                                'SNOMED Code': value.get('value', ''),
                                                'SNOMED Description': value.get('display_name', ''),
                                                'display_name': value.get('display_name', ''),  # Add for lookup function
                                                'ValueSet GUID': value_set.get('id', ''),
                                                'ValueSet Description': value_set.get('description', ''),
                                                'Code System': value.get('code_system', value_set.get('code_system', 'SNOMED_CONCEPT')),
                                                'Include Children': 'Yes' if value.get('include_children') else 'No',
                                                'is_refset': value.get('is_refset', False),  # Preserve refset flag
                                                'is_pseudorefset': value.get('is_pseudorefset', False),  # Preserve pseudo-refset flag
                                                'is_pseudomember': value.get('is_pseudomember', False),  # Preserve pseudo-member flag
                                                'is_medication': _is_medication_from_context(
                                                    value.get('code_system', value_set.get('code_system', 'SNOMED_CONCEPT')),
                                                    value.get('table_context'),
                                                    value.get('column_context')
                                                ),  # Set medication flag based on code system and context
                                                'is_pseudorefset': value.get('is_pseudorefset', False),  # Preserve pseudo-refset container flag from XML structure analysis
                                                'is_pseudomember': value.get('is_pseudomember', False),  # Preserve pseudo-refset member flag from XML structure analysis
                                                'Source Name': search.name,
                                                'Source Type': 'Search',
                                                'Source Container': determine_container_type(criterion, group),
                                                'Mapping Found': 'Found',  # Assume found for now
                                                'source_type': 'search',
                                                'source_name': search.name,
                                                'source_container': determine_container_type(criterion, group),
                                            })
    
    return clinical_codes


def determine_container_type(criterion, group):
    """Determine the container type based on criterion and group context"""
    # TODO: Implement the container detection logic from EMIS XML patterns
    # For now, return basic container type
    return "Search Rule Main Criteria"


def _determine_proper_container_type(code):
    """
    Determine proper container type based on code source and context.
    Implements EMIS XML patterns from docs/emis-xml-patterns.md
    """
    # Check if this is from a report
    source_type = code.get('source_type') or code.get('_original_fields', {}).get('source_type', '')
    
    if source_type == 'report':
        # Report codes - use column group name or logical table
        column_group = code.get('column_group_name') or code.get('_original_fields', {}).get('column_group_name')
        if column_group:
            return f"Report Column Group: {column_group}"
        
        logical_table = code.get('logical_table') or code.get('_original_fields', {}).get('logical_table')
        if logical_table:
            return f"Report Table: {logical_table}"
        
        # Check if from column group
        if code.get('from_column_group') or code.get('_original_fields', {}).get('from_column_group'):
            return "Report Column Filter"
        
        return "Report Column"
    
    # Search codes - determine container type based on EMIS XML patterns
    existing_container = (code.get('source_container') or 
                         code.get('Source Container') or 
                         code.get('_original_fields', {}).get('source_container'))
    
    if existing_container and existing_container != '':
        return existing_container
    
    # Advanced container detection based on EMIS XML patterns
    # Check for Base Criteria Group patterns
    original_fields = code.get('_original_fields', {})
    
    # Look for nested criteria patterns (Base Criteria Groups)
    if ('baseCriteriaGroup' in str(original_fields) or 
        'nested' in existing_container.lower() if existing_container else False):
        return "Search Rule Base Criteria Group"
    
    # Look for linked criteria patterns  
    if ('linked' in existing_container.lower() if existing_container else False or
        'linkedCriteria' in str(original_fields)):
        return "Search Rule Linked Criteria"
    
    # Look for population reference patterns
    if ('population' in existing_container.lower() if existing_container else False or
        'populationCriterion' in str(original_fields)):
        return "Search Rule Population Reference"
    
    # Look for test attribute patterns
    if ('test' in existing_container.lower() if existing_container else False or
        'testAttribute' in str(original_fields) or
        'NUMERIC_VALUE' in str(original_fields)):
        return "Search Rule Test Attribute"
    
    # Look for restriction patterns  
    if ('restriction' in existing_container.lower() if existing_container else False or
        'dateRestriction' in str(original_fields) or
        'latestRecords' in str(original_fields)):
        return "Search Rule Restriction"
    
    # Check table type for more specific categorization
    table_type = original_fields.get('table') or original_fields.get('logical_table', '')
    if table_type:
        table_containers = {
            'EVENTS': 'Search Rule Clinical Events',
            'MEDICATION_ISSUES': 'Search Rule Medication Issues', 
            'MEDICATION_COURSES': 'Search Rule Medication Courses',
            'PATIENTS': 'Search Rule Patient Demographics',
            'GPES_JOURNALS': 'Search Rule GP Registration'
        }
        if table_type in table_containers:
            return table_containers[table_type]
    
    # Default fallback
    return "Search Rule Main Criteria"




def is_pseudo_refset_valueset(valueset_guid, valueset_description):
    """Check if a valueset is a pseudo-refset based on patterns"""
    # Import the existing logic from xml_utils (in root directory)
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from ...xml_parsers.xml_utils import is_pseudo_refset
    return is_pseudo_refset(valueset_guid, valueset_description)


def get_unified_clinical_data():
    """Get clinical data from orchestrated analysis instead of fragmented translator"""
    import streamlit as st
    
    # Check if we already have cached unified data
    cached_data = st.session_state.get('unified_clinical_data_cache')
    if cached_data is not None:
        return cached_data
    
    # Get comprehensive analysis data
    analysis = st.session_state.get('xml_structure_analysis')
    if not analysis:
        return None
    
    
    # Extract clinical codes from both searches and reports
    all_clinical_codes = []
    
    # Get clinical codes from reports (prefer orchestrated_results, fallback to report_results)
    report_codes_added = False
    if (hasattr(analysis, 'orchestrated_results') and analysis.orchestrated_results and 
        hasattr(analysis.orchestrated_results, 'report_clinical_codes') and 
        analysis.orchestrated_results.report_clinical_codes):
        all_clinical_codes.extend(analysis.orchestrated_results.report_clinical_codes)
        report_codes_added = True
    elif (hasattr(analysis, 'report_results') and analysis.report_results and
          hasattr(analysis.report_results, 'clinical_codes') and
          analysis.report_results.clinical_codes):
        all_clinical_codes.extend(analysis.report_results.clinical_codes)
        report_codes_added = True
        
    # Get clinical codes from searches (prefer orchestrated_results, fallback to search_results)
    search_codes_added = False
    if (hasattr(analysis, 'orchestrated_results') and analysis.orchestrated_results and
        hasattr(analysis.orchestrated_results, 'searches') and analysis.orchestrated_results.searches):
        orchestrated_search_codes = extract_clinical_codes_from_searches(analysis.orchestrated_results.searches)
        all_clinical_codes.extend(orchestrated_search_codes)
        search_codes_added = True
    elif (hasattr(analysis, 'search_results') and analysis.search_results and
          hasattr(analysis.search_results, 'searches') and analysis.search_results.searches):
        search_clinical_codes = extract_clinical_codes_from_searches(analysis.search_results.searches)
        all_clinical_codes.extend(search_clinical_codes)
        search_codes_added = True
    
    # Convert data format using universal field mapping system
    from .field_mapping import standardize_clinical_codes_list, get_field_value, StandardFields
    
    # Apply SNOMED lookup FIRST before filtering to enrich all codes
    translated_clinical_codes = _convert_analysis_codes_to_translation_format(all_clinical_codes)
    all_clinical_codes = translated_clinical_codes  # Use enriched data for filtering
    
    # Apply filtering after enrichment - separate codes for different tabs
    clinical_codes = []  # Standalone clinical codes only  
    medication_codes = []  # Medications
    refset_codes = []  # True refsets
    pseudo_refset_codes = []  # Pseudo-refset containers
    pseudo_member_codes = []  # Pseudo-refset members
    
    # Categorize on enriched data before standardization
    for code in all_clinical_codes:
        # Skip EMISINTERNAL codes entirely (these are internal EMIS filters like gender, age)
        code_system = get_field_value(code, StandardFields.CODE_SYSTEM, '').upper()
        if code_system == 'EMISINTERNAL':
            continue
            
        # Skip patient demographics and non-clinical filters
        table = code.get('table', '').upper()
        column = code.get('column', '').upper()
        if table == 'PATIENTS' or column in ['SEX', 'AGE', 'DOB', 'GENDER']:
            continue
            
        # Skip library item GUIDs (typically have dashes and are not numeric SNOMED codes)
        code_value = get_field_value(code, StandardFields.EMIS_GUID, '')
        if code_value and '-' in code_value and len(code_value) == 36:  # Standard GUID format
            continue
            
        # Separate medications for medications tab - check table info and proper code systems only
        table = code.get('table', '').upper()
        logical_table = code.get('logical_table', '').upper()
        source_name = code.get('source_name', '').lower()
        source_container = code.get('source_container', '').lower()
        original_code_system = code.get('_original_fields', {}).get('code_system', '')
        
        # Use the is_medication flag that was set during extraction based on proper code system/context detection
        is_medication = code.get('is_medication', False)
        if is_medication:
            medication_codes.append(code)
            continue
            
        # Determine code type based on structure and properties
        emis_guid = code.get('EMIS GUID', '')
        snomed_code = code.get('SNOMED Code', '')
        is_refset_flag = code.get('is_refset', False)
        
        # Clean refset descriptions for display
        display_name = get_field_value(code, StandardFields.SNOMED_DESCRIPTION, '')
        if display_name.startswith('Refset: ') and '[' in display_name:
            # Extract "NDAHEIGHT_COD" from "Refset: NDAHEIGHT_COD[999002731000230106]"
            refset_name = display_name.replace('Refset: ', '').split('[')[0]
            code['display_name'] = refset_name
            code['SNOMED Description'] = refset_name

        # Categorize codes based on type using the new flags
        is_pseudorefset = code.get('is_pseudorefset', False)
        is_pseudomember = code.get('is_pseudomember', False)
        
        
        if is_refset_flag and not is_pseudorefset:
            # True refsets only (not pseudo-refset containers)
            refset_codes.append(code)
        elif is_pseudorefset:
            # Pseudo-refset containers go to pseudo_refsets
            code['Source Container'] = _determine_proper_container_type(code)
            pseudo_refset_codes.append(code)
        elif is_pseudomember:
            # Codes that are members of pseudo-refsets go to separate pseudo-member list
            code['Source Container'] = _determine_proper_container_type(code)
            pseudo_member_codes.append(code)
        else:
            # All other codes go to clinical codes
            code['Source Container'] = _determine_proper_container_type(code)
            clinical_codes.append(code)
    
    # Apply standardization to each category separately 
    standardized_clinical_codes = standardize_clinical_codes_list(clinical_codes)
    standardized_medication_codes = standardize_clinical_codes_list(medication_codes)
    standardized_refset_codes = standardize_clinical_codes_list(refset_codes)
    standardized_pseudo_refset_codes = standardize_clinical_codes_list(pseudo_refset_codes)
    standardized_pseudo_member_codes = standardize_clinical_codes_list(pseudo_member_codes)
    
    # Create unified results structure with properly categorized and standardized codes
    unified_results = {
        'clinical_codes': standardized_clinical_codes,  # Standalone clinical codes only
        'medications': standardized_medication_codes,  # Separated medications  
        'refsets': standardized_refset_codes,  # True refsets only
        'pseudo_refsets': standardized_pseudo_refset_codes,  # Pseudo-refset containers only
        'clinical_pseudo_members': standardized_pseudo_member_codes,  # Pseudo-refset member codes
    }
    
    
    # Enhance source tracking with GUID mapping for all clinical data
    # The function should already be available in this module
    
    # Lookup already applied earlier before filtering
    # The unified parsing approach already provides better source tracking than GUID mapping
    # if unified_results.get('clinical_codes'):
    #     unified_results['clinical_codes'] = _add_source_info_to_clinical_data(unified_results['clinical_codes'])
    
    # Apply standardization to pseudo-refset members  
    if unified_results.get('clinical_pseudo_members'):
        # Standardize pseudo-refset members to ensure consistent field formatting including source types
        unified_results['clinical_pseudo_members'] = standardize_clinical_codes_list(unified_results['clinical_pseudo_members'])
    
    
    # Cache the results for subsequent calls
    st.session_state['unified_clinical_data_cache'] = unified_results
    
    return unified_results