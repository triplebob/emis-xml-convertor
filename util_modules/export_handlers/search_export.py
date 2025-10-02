"""
Search Export Handler
Handles detailed per-search export functionality with comprehensive breakdowns
"""

import io
import zipfile
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any, Optional
from ..utils.text_utils import pluralize_unit, format_operator_text
from ..core import ReportClassifier, SearchManager
from ..common.export_utils import sanitize_dataframe_for_excel


class SearchExportHandler:
    """Handles comprehensive export of individual search details"""
    
    def __init__(self, analysis):
        self.analysis = analysis
        
    def generate_search_export(self, search_report, include_parent_info=True):
        """
        Generate comprehensive export for any report type (Search, List, Audit, Aggregate)
        
        Args:
            search_report: The SearchReport to export
            include_parent_info: Whether to include parent search reference info
            
        Returns:
            tuple: (filename, file_content) ready for download
        """
        # Route to appropriate export method based on report type
        if hasattr(search_report, 'report_type'):
            if search_report.report_type == 'list':
                return self._generate_list_report_export(search_report, include_parent_info)
            elif search_report.report_type == 'audit':
                return self._generate_audit_report_export(search_report, include_parent_info)
            elif search_report.report_type == 'aggregate':
                return self._generate_aggregate_report_export(search_report, include_parent_info)
        
        # Default to search export for backward compatibility
        export_data = self._build_search_export_data(search_report, include_parent_info)
        
        # Create Excel file in memory
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Overview sheet
            overview_df = self._create_overview_sheet(search_report, include_parent_info)
            overview_df_safe = sanitize_dataframe_for_excel(overview_df)
            overview_df_safe.to_excel(writer, sheet_name='Overview', index=False)
            
            # Rules and criteria sheets
            for i, group in enumerate(search_report.criteria_groups, 1):
                rule_df = self._create_rule_sheet(group, i)
                rule_df_safe = sanitize_dataframe_for_excel(rule_df)
                rule_df_safe.to_excel(writer, sheet_name=f'Rule_{i}', index=False)
                
                # Clinical codes sheet for each rule
                codes_df = self._create_clinical_codes_sheet(group, i)
                if not codes_df.empty:
                    sheet_name = f'Rule_{i}_Codes'[:31]  # Excel sheet name limit
                    codes_df_safe = sanitize_dataframe_for_excel(codes_df)
                    codes_df_safe.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # All clinical codes summary
            all_codes_df = self._create_all_codes_summary(search_report)
            if not all_codes_df.empty:
                all_codes_df_safe = sanitize_dataframe_for_excel(all_codes_df)
                all_codes_df_safe.to_excel(writer, sheet_name='All_Clinical_Codes', index=False)
        
        output.seek(0)
        
        # Generate filename
        clean_name = SearchManager.clean_search_name(search_report.name)
        safe_name = "".join(c for c in clean_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{safe_name}_{timestamp}.xlsx"
        
        return filename, output.getvalue()
    
    def _build_search_export_data(self, search_report, include_parent_info):
        """Build comprehensive data structure for export"""
        export_data = {
            'search_info': {
                'id': search_report.id,
                'name': search_report.name,
                'description': search_report.description,
                'folder': search_report.folder_id,
                'search_date': search_report.search_date,
                'creation_time': search_report.creation_time or '',
                'author': search_report.author or '',
                'population_type': search_report.population_type
            },
            'rules': [],
            'all_clinical_codes': []
        }
        
        if include_parent_info and search_report.parent_guid:
            export_data['parent_info'] = {
                'type': search_report.parent_type or '',
                'reference': search_report.parent_guid or 'Unknown parent search'
            }
        
        # Process each rule/criteria group
        for i, group in enumerate(search_report.criteria_groups, 1):
            rule_data = self._process_rule_for_export(group, i)
            export_data['rules'].append(rule_data)
            
            # Collect all clinical codes
            for criterion in group.criteria:
                self._collect_clinical_codes(criterion, export_data['all_clinical_codes'], i)
        
        return export_data
    
    def _process_rule_for_export(self, group, rule_number):
        """Process a rule/criteria group for export"""
        rule_data = {
            'rule_number': rule_number,
            'logic': group.member_operator,
            'action_if_true': group.action_if_true,
            'action_if_false': group.action_if_false,
            'criteria_count': len(group.criteria),
            'uses_another_search': bool(hasattr(group, 'population_criteria') and group.population_criteria),
            'criteria': [self._process_criterion_for_export(crit, i+1) for i, crit in enumerate(group.criteria)]
        }
        
        # Add population criteria details if present
        if hasattr(group, 'population_criteria') and group.population_criteria:
            rule_data['referenced_searches'] = []
            for pop_crit in group.population_criteria:
                ref_search_name = "Unknown Search"
                if hasattr(self.analysis, 'reports') and self.analysis.reports:
                    ref_report = next((r for r in self.analysis.reports if r.id == pop_crit.report_guid), None)
                    if ref_report:
                        from ..core import SearchManager
                        ref_search_name = SearchManager.clean_search_name(ref_report.name)
                
                rule_data['referenced_searches'].append({
                    'search_id': pop_crit.report_guid,
                    'search_name': ref_search_name
                })
        
        return rule_data
    
    def _process_criterion_for_export(self, criterion, criterion_number):
        """Process individual criterion for export"""
        criterion_data = {
            'criterion_number': criterion_number,
            'id': criterion.id,
            'table': criterion.table,
            'display_name': criterion.display_name,
            'description': criterion.description,
            'negation': criterion.negation,
            'exception_code': criterion.exception_code,
            'value_sets_count': len(criterion.value_sets) if criterion.value_sets else 0,
            'column_filters_count': len(criterion.column_filters) if criterion.column_filters else 0,
            'linked_criteria_count': len(criterion.linked_criteria) if criterion.linked_criteria else 0
        }
        
        # Add value sets details
        if criterion.value_sets:
            criterion_data['value_sets'] = [
                {
                    'id': vs.get('id', ''),
                    'code_system': vs.get('code_system', ''),
                    'description': vs.get('description', ''),
                    'values_count': len(vs.get('values', []))
                }
                for vs in criterion.value_sets
            ]
        
        # Add column filters details
        if criterion.column_filters:
            criterion_data['column_filters'] = [
                self._process_column_filter_for_export(cf)
                for cf in criterion.column_filters
            ]
        
        # Add linked criteria details
        if criterion.linked_criteria:
            criterion_data['linked_criteria'] = [
                self._process_criterion_for_export(linked, i+1)
                for i, linked in enumerate(criterion.linked_criteria)
            ]
        
        return criterion_data
    
    def _process_column_filter_for_export(self, column_filter):
        """Process column filter for export"""
        return {
            'column': column_filter.get('column', ''),
            'display_name': column_filter.get('display_name', ''),
            'type': column_filter.get('type', ''),
            'in_not_in': column_filter.get('in_not_in', ''),
            'operator': column_filter.get('operator', ''),
            'values': column_filter.get('values', []),
            'range_description': column_filter.get('range_description', ''),
            'restriction_type': column_filter.get('restriction_type', '')
        }
    
    def _collect_clinical_codes(self, criterion, codes_list, rule_number):
        """Collect all clinical codes from a criterion"""
        if not criterion.value_sets:
            return
            
        for vs in criterion.value_sets:
            if not vs.get('values'):
                continue
                
            for value in vs['values']:
                codes_list.append({
                    'rule_number': rule_number,
                    'criterion_description': criterion.description,
                    'value_set_id': vs.get('id', ''),
                    'value_set_description': vs.get('description', ''),
                    'code_system': vs.get('code_system', ''),
                    'code_value': value.get('value', ''),
                    'display_name': value.get('display_name', ''),
                    'include_children': value.get('include_children', False),
                    'is_refset': value.get('is_refset', False)
                })
    
    def _create_overview_sheet(self, search_report, include_parent_info):
        """Create overview sheet for the search"""
        data = [
            ['Search Name', search_report.name],
            ['Description', search_report.description or 'N/A'],
            ['Creation Time', search_report.creation_time or 'N/A'],
            ['Author', search_report.author or 'N/A'],
            ['Population Type', search_report.population_type or ''],
            ['Search Date', search_report.search_date or ''],
            ['Number of Rules', len(search_report.criteria_groups)]
        ]
        
        if include_parent_info and search_report.parent_guid:
            data.extend([
                ['Parent Search Type', search_report.parent_type or ''],
                ['Parent Reference', search_report.parent_guid or '']
            ])
        
        data.extend([
            ['Export Generated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ['Export Tool', 'EMIS XML Toolkit']
        ])
        
        return pd.DataFrame(data, columns=['Property', 'Value'])
    
    def _create_rule_sheet(self, group, rule_number):
        """Create detailed rule sheet"""
        data = []
        
        # Count only main criteria (not linked ones that appear as separate criteria)
        main_criteria = [c for c in group.criteria if not self._is_linked_criterion(c, group.criteria)]
        main_criteria_count = len(main_criteria)
        
        # Rule header info
        data.extend([
            ['Rule Number', rule_number],
            ['Logic', group.member_operator],
            ['Action if True', group.action_if_true],
            ['Action if False', group.action_if_false],
            ['Number of Main Criteria', main_criteria_count],
            ['', '']  # Spacer
        ])
        
        # Check for population criteria (references to other searches)
        if hasattr(group, 'population_criteria') and group.population_criteria:
            data.extend([
                ['Uses Another Search', 'YES'],
                ['', '']  # Spacer
            ])
            
            for i, pop_crit in enumerate(group.population_criteria, 1):
                # Try to find the referenced search name - use fresh analysis from session state if available
                ref_search_name = "Unknown Search"
                analysis_to_use = self.analysis
                
                # Try to get fresh analysis from session state
                try:
                    import streamlit as st
                    fresh_analysis = st.session_state.get('search_analysis')
                    if fresh_analysis and hasattr(fresh_analysis, 'reports') and fresh_analysis.reports:
                        analysis_to_use = fresh_analysis
                except:
                    pass  # Fallback to self.analysis if streamlit not available
                
                if hasattr(analysis_to_use, 'reports') and analysis_to_use.reports:
                    ref_report = next((r for r in analysis_to_use.reports if r.id == pop_crit.report_guid), None)
                    if ref_report:
                        from ..core import SearchManager
                        ref_search_name = SearchManager.clean_search_name(ref_report.name)
                    else:
                        # Try to find in all reports (including member searches)
                        all_reports = []
                        def collect_all_reports(reports):
                            for report in reports:
                                all_reports.append(report)
                                if hasattr(report, 'member_searches') and report.member_searches:
                                    collect_all_reports(report.member_searches)
                        
                        collect_all_reports(analysis_to_use.reports)
                        ref_report = next((r for r in all_reports if r.id == pop_crit.report_guid), None)
                        
                        if ref_report:
                            from ..core import SearchManager
                            ref_search_name = SearchManager.clean_search_name(ref_report.name)
                
                data.extend([
                    [f'Referenced Search {i}', ref_search_name],
                    [f'  Search ID', pop_crit.report_guid[:8] + '...'],
                    ['', '']  # Spacer
                ])
        else:
            data.extend([
                ['Uses Another Search', 'NO'],
                ['', '']  # Spacer
            ])
        
        # Criteria details - show only main criteria (skip those that are linked to others)
        main_criteria = [c for c in group.criteria if not self._is_linked_criterion(c, group.criteria)]
        
        for i, criterion in enumerate(main_criteria, 1):
            criterion_label = f'Main Criterion {i}'
            
            # Use the same filtering logic as the UI to avoid showing all filters from baseCriteriaGroup
            try:
                from ..analysis.linked_criteria_handler import filter_linked_column_filters_from_main, filter_linked_value_sets_from_main
                main_column_filters = filter_linked_column_filters_from_main(criterion)
                main_value_sets = filter_linked_value_sets_from_main(criterion)
                additional_filters_count = len(main_column_filters)
                clinical_code_sets_count = len(main_value_sets)
            except ImportError:
                # Fallback to original logic if import fails
                additional_filters_count = len(criterion.column_filters) if criterion.column_filters else 0
                clinical_code_sets_count = len(criterion.value_sets) if criterion.value_sets else 0
            
            data.extend([
                [criterion_label, criterion.display_name or ''],
                ['  Table', criterion.table],
                ['  Action', 'Exclude' if criterion.negation else 'Include'],
                ['  Clinical Code Sets', clinical_code_sets_count],
                ['  Additional Filters', additional_filters_count],
                ['  Linked Criteria', 'Yes' if criterion.linked_criteria else 'No'],
                ['', '']  # Spacer
            ])
            
            # Add restriction details (like "Latest 1") 
            if criterion.restrictions:
                for j, restriction in enumerate(criterion.restrictions, 1):
                    restriction_details = self._format_restriction_simple(restriction)
                    data.extend([
                        ['  Record Limit', restriction_details],
                    ])
            
            # Add main criterion filters (excluding those that belong to linked criteria)
            if criterion.column_filters:
                # Get filters that belong to linked criteria
                linked_filters = []
                for linked_crit in criterion.linked_criteria:
                    if hasattr(linked_crit, 'column_filters'):
                        linked_filters.extend(linked_crit.column_filters)
                
                # Filter out linked criterion filters from main criterion
                main_filters = []
                for col_filter in criterion.column_filters:
                    # Simple comparison - if filter doesn't match any linked filter exactly, include it
                    is_linked_filter = False
                    for linked_filter in linked_filters:
                        if (col_filter.get('column') == linked_filter.get('column') and 
                            col_filter.get('id') == linked_filter.get('id')):
                            is_linked_filter = True
                            break
                    
                    if not is_linked_filter:
                        main_filters.append(col_filter)
                
                # Show main criterion filters only
                for j, col_filter in enumerate(main_filters, 1):
                    filter_summary = self._format_filter_summary(col_filter)
                    data.extend([
                        [f'  Filter {j}', filter_summary],
                    ])
                    
                if main_filters:
                    data.append(['', ''])  # Spacer
            
            # Add simplified linked criteria details
            if criterion.linked_criteria:
                for j, linked_crit in enumerate(criterion.linked_criteria, 1):
                    data.extend([
                        [f'  Linked Criterion {j}', linked_crit.display_name or 'Clinical Codes'],
                        [f'    Table', linked_crit.table],
                        [f'    Action', 'Exclude' if linked_crit.negation else 'Include'],
                    ])
                    
                    # Add linked criterion's restrictions
                    if linked_crit.restrictions:
                        for k, restriction in enumerate(linked_crit.restrictions, 1):
                            restriction_details = self._format_restriction_simple(restriction)
                            data.extend([
                                [f'    Record Limit', restriction_details],
                            ])
                    
                    # Add linked criterion's column filters
                    if linked_crit.column_filters:
                        for k, col_filter in enumerate(linked_crit.column_filters, 1):
                            filter_summary = self._format_filter_summary(col_filter)
                            data.extend([
                                [f'    Filter {k}', filter_summary],
                            ])
                    
                    data.append(['', ''])  # Spacer after each linked criterion
        
        
        return pd.DataFrame(data, columns=['Property', 'Value'])
    
    def _create_clinical_codes_sheet(self, group, rule_number):
        """Create clinical codes sheet for a rule"""
        codes_data = []
        
        # Only process main criteria (not those that are linked to others)
        main_criteria = [c for c in group.criteria if not self._is_linked_criterion(c, group.criteria)]
        
        for i, criterion in enumerate(main_criteria, 1):
            # This is a main criterion
            if not criterion.value_sets:
                continue
                
            for vs in criterion.value_sets:
                if not vs.get('values'):
                    continue
                    
                for value in vs['values']:
                    codes_data.append({
                        'Rule Number': rule_number,
                        'Criterion Number': i,
                        'Criterion Type': "MAIN CRITERION",
                        'Criterion Description': criterion.description,
                        'Exception Code': criterion.exception_code or '',
                        'Value Set ID': vs.get('id', ''),
                        'Value Set Description': vs.get('description', ''),
                        'Code System': vs.get('code_system', ''),
                        'Code Value': value.get('value', ''),
                        'Display Name': value.get('display_name', ''),
                        'Include Children': value.get('include_children', False),
                        'Is Refset': value.get('is_refset', False)
                    })
            
            # Include codes from linked criteria within this criterion
            if criterion.linked_criteria:
                for j, linked_crit in enumerate(criterion.linked_criteria, 1):
                    if linked_crit.value_sets:
                        for vs in linked_crit.value_sets:
                            if not vs.get('values'):
                                continue
                                
                            for value in vs['values']:
                                codes_data.append({
                                    'Rule Number': rule_number,
                                    'Criterion Number': f"{i}.{j}",
                                    'Criterion Type': f"LINKED TO CRITERION {i}",
                                    'Criterion Description': linked_crit.description,
                                    'Exception Code': linked_crit.exception_code or '',
                                    'Value Set ID': vs.get('id', ''),
                                    'Value Set Description': vs.get('description', ''),
                                    'Code System': vs.get('code_system', ''),
                                    'Code Value': value.get('value', ''),
                                    'Display Name': value.get('display_name', ''),
                                    'Include Children': value.get('include_children', False),
                                    'Is Refset': value.get('is_refset', False)
                                })
        
        return pd.DataFrame(codes_data) if codes_data else pd.DataFrame()
    
    def _create_all_codes_summary(self, search_report):
        """Create summary of all clinical codes across all rules"""
        all_codes = []
        
        for rule_num, group in enumerate(search_report.criteria_groups, 1):
            # Only process main criteria (not those that are linked to others)
            main_criteria = [c for c in group.criteria if not self._is_linked_criterion(c, group.criteria)]
            
            for crit_num, criterion in enumerate(main_criteria, 1):
                # This is a main criterion
                if not criterion.value_sets:
                    continue
                    
                for vs in criterion.value_sets:
                    if not vs.get('values'):
                        continue
                        
                    for value in vs['values']:
                        all_codes.append({
                            'Rule': rule_num,
                            'Criterion': crit_num,
                            'Criterion Type': "MAIN CRITERION",
                            'Criterion Description': criterion.description,
                            'Exception Code': criterion.exception_code or '',
                            'Value Set': vs.get('description', vs.get('id', 'Unknown')),
                            'Code System': vs.get('code_system', ''),
                            'Code Value': value.get('value', ''),
                            'Display Name': value.get('display_name', ''),
                            'Include Children': value.get('include_children', False),
                            'Is Refset': value.get('is_refset', False)
                        })
                
                # Include codes from linked criteria within this criterion
                if criterion.linked_criteria:
                    for j, linked_crit in enumerate(criterion.linked_criteria, 1):
                        if linked_crit.value_sets:
                            for vs in linked_crit.value_sets:
                                if not vs.get('values'):
                                    continue
                                    
                                for value in vs['values']:
                                    all_codes.append({
                                        'Rule': rule_num,
                                        'Criterion': f"{crit_num}.{j}",
                                        'Criterion Type': f"LINKED TO CRITERION {crit_num}",
                                        'Criterion Description': linked_crit.description,
                                        'Exception Code': linked_crit.exception_code or '',
                                        'Value Set': vs.get('description', vs.get('id', 'Unknown')),
                                        'Code System': vs.get('code_system', ''),
                                        'Code Value': value.get('value', ''),
                                        'Display Name': value.get('display_name', ''),
                                        'Include Children': value.get('include_children', False),
                                        'Is Refset': value.get('is_refset', False)
                                    })
        
        return pd.DataFrame(all_codes) if all_codes else pd.DataFrame()
    
    def _is_linked_criterion(self, criterion, all_criteria):
        """Check if a criterion appears as a linked criterion in another criterion within the same rule"""
        for other_criterion in all_criteria:
            if other_criterion.id != criterion.id and other_criterion.linked_criteria:
                for linked in other_criterion.linked_criteria:
                    if linked.id == criterion.id:
                        return True
        return False
    
    def _format_column_filter_details(self, col_filter):
        """Format column filter details into a comprehensive, rebuild-ready description"""
        details = []
        
        # Basic filter info - essential for rebuilding
        column = col_filter.get('column', 'Unknown')
        display_name = col_filter.get('display_name', column)
        details.append(f"Column: {display_name} ({column})")
        
        # In/Not In - critical for rebuild
        in_not_in = col_filter.get('in_not_in', '')
        if in_not_in:
            action = "Include" if in_not_in.upper() == "IN" else "Exclude" if in_not_in.upper() == "NOTIN" else in_not_in
            details.append(f"Action: {action} ({in_not_in})")
        
        # Enhanced range information with specific values for rebuild
        if 'range' in col_filter and col_filter['range']:
            range_description = self._format_range_description_from_parsed(col_filter['range'])
            if range_description:
                details.append(f"Range: {range_description}")
        
        # Relationship information for linked criteria - essential for rebuild
        if 'relationship' in col_filter:
            relationship_desc = self._format_relationship_description(col_filter['relationship'])
            if relationship_desc:
                details.append(f"Relationship: {relationship_desc}")
        
        # Values list with complete details for rebuild
        if 'values' in col_filter and col_filter['values']:
            values = col_filter['values']
            details.append(f"Values Count: {len(values)}")
            if len(values) <= 10:  # Show more values for rebuild purposes
                values_str = ', '.join(str(v) for v in values)
                details.append(f"Values: {values_str}")
            else:
                values_str = f"{', '.join(str(v) for v in values[:5])}... (showing 5 of {len(values)})"
                details.append(f"Values (partial): {values_str}")
        
        # Context-specific rebuild instructions based on column type
        column_name = col_filter.get('column', '').upper()
        
        # Clinical coding - specific instructions for rebuild
        if column_name in ['READCODE', 'SNOMEDCODE']:
            details.append("Filter Type: Clinical codes - Use Clinical Code column in EMIS search builder")
            details.append("Rebuild: Select 'Clinical Codes' table, choose appropriate value sets")
        elif column_name in ['DRUGCODE']:
            details.append("Filter Type: Medication codes - Use Drug column in EMIS search builder")
            details.append("Rebuild: Select 'Medication Issues' table, choose drug codes/groups")
        elif column_name in ['DISPLAYTERM', 'NAME']:
            details.append("Filter Type: Medication names - Use drug name/description filtering")
        
        # Date/time columns with specific rebuild instructions
        elif column_name in ['DATE']:
            details.append("Filter Type: General date - Use Date column with range settings")
            details.append("Rebuild: Set date range relative to search date or absolute dates")
        elif column_name in ['ISSUE_DATE', 'PRESCRIPTION_DATE']:
            details.append("Filter Type: Medication dates - Use Issue Date in medication table")
        elif column_name in ['CONSULTATION_DATE', 'EPISODE_DATE']:
            details.append("Filter Type: Episode dates - Use consultation/episode date filtering")
        elif column_name in ['DATE_OF_BIRTH', 'DOB']:
            details.append("Filter Type: Birth date - Use Date of Birth in patient demographics")
        elif column_name == 'GMS_DATE_OF_REGISTRATION':
            details.append("Filter Type: Registration date - Use GMS registration date from patient table")
        
        # Demographics and age with rebuild guidance
        elif column_name in ['AGE']:
            details.append("Filter Type: Patient age - Use Age column in patient demographics")
            details.append("Rebuild: Set age range (years) with >= or <= operators")
        elif column_name == 'AGE_AT_EVENT':
            details.append("Filter Type: Age at event - Use Age at Event for vaccination/procedure timing")
            details.append("Rebuild: Specify age at time of specific clinical event")
        
        # Clinical values and measurements
        elif column_name == 'NUMERIC_VALUE':
            details.append("Filter Type: Numeric values - Use Value column for test results")
            details.append("Rebuild: Set numeric range for lab results, spirometry, BMI, etc.")
        
        # Episode and workflow states
        elif column_name in ['EPISODE']:
            details.append("Filter Type: Episode states - Use Episode column for workflow status")
            details.append("Rebuild: Select episode types (FIRST, NEW, REVIEW, ENDED, NONE)")
        
        # Record count and sorting - critical for rebuild
        if 'record_count' in col_filter:
            count = col_filter['record_count']
            details.append(f"Record Limit: Latest {count} records")
            details.append(f"Rebuild: Set restriction to 'Latest {count}' in search builder")
        
        # Sort direction - essential for rebuild
        if 'direction' in col_filter:
            direction = col_filter['direction']
            direction_text = "Most recent first (DESC)" if direction == "DESC" else "Earliest first (ASC)" if direction == "ASC" else direction
            details.append(f"Sort Direction: {direction_text}")
            details.append(f"Rebuild: Set sort order to {direction}")
        
        # Test attributes and complex conditions
        if 'test_attribute' in col_filter:
            details.append("Complex Conditions: Test attributes applied")
            details.append("Rebuild: Use advanced restrictions with conditional logic")
        
        # Enhanced restriction type descriptions with rebuild instructions
        if 'restriction_type' in col_filter:
            restriction = col_filter['restriction_type']
            details.append(f"Restriction Type: {restriction}")
            if restriction.lower() in ['current', 'is_current']:
                details.append("Rebuild: Add restriction for 'Current/Active records only'")
            elif restriction.lower() in ['latest', 'most_recent']:
                details.append("Rebuild: Add restriction for 'Latest records only'")
            elif restriction.lower() in ['earliest', 'first']:
                details.append("Rebuild: Add restriction for 'Earliest records only'")
        
        # Current status indicators
        if col_filter.get('column', '').upper() in ['CURRENT', 'IS_CURRENT', 'STATUS']:
            details.append("Status Filter: Current/Active records only")
            details.append("Rebuild: Enable 'Current records only' checkbox")
        elif column_name == 'EPISODE':
            details.append("Episode type filtering (FIRST, NEW, REVIEW, ENDED, NONE)")
        
        # NHS/system identifiers
        elif column_name in ['NHS_NO', 'NHS_NUMBER']:
            details.append("NHS number filtering")
        elif column_name in ['ORGANISATION_NPC', 'ORGANISATION_CODE']:
            details.append("Organisation code filtering")
        
        # Value set and code system context
        if 'code_system' in col_filter:
            code_system = col_filter.get('code_system', '').upper()
            if 'SCT_DRGGRP' in code_system:
                details.append("Drug group classification")
            elif 'EMISINTERNAL' in code_system:
                details.append("EMIS internal classification")
            elif 'SNOMED_CONCEPT' in code_system:
                details.append("SNOMED clinical terminology")
        
        return ' | '.join(details) if details else 'No filter details available'
    
    def _format_range_description(self, col_filter):
        """Format range information into human-readable descriptions"""
        range_parts = []
        
        
        # Helper function to format relative dates
        def format_relative_date(value_dict):
            val = value_dict.get('value', '')
            unit = value_dict.get('unit', '').lower()
            
            # Handle negative values (past dates)
            if val.startswith('-'):
                val_num = val[1:]  # Remove minus sign
                if unit == 'month':
                    unit_str = 'months' if val_num != '1' else 'month'
                    return f"{val_num} {unit_str} before the search date"
                elif unit == 'day':
                    unit_str = 'days' if val_num != '1' else 'day'
                    return f"{val_num} {unit_str} before the search date"
                elif unit == 'year':
                    unit_str = 'years' if val_num != '1' else 'year'
                    return f"{val_num} {unit_str} before the search date"
            else:
                if unit == 'day':
                    unit_str = 'days' if val != '1' else 'day'
                    return f"{val} {unit_str}"
                elif unit == 'month':
                    unit_str = 'months' if val != '1' else 'month'
                    return f"{val} {unit_str}"
                elif unit == 'year':
                    unit_str = 'years' if val != '1' else 'year'
                    return f"{val} {unit_str}"
            
            return f"{val} {unit}"
        
        # Process range_from
        if 'range_from' in col_filter:
            from_val = col_filter['range_from']
            operator = from_val.get('operator', 'GTEQ')
            op_text = translate_operator(operator, is_numeric=False)  # Default to date format
            value = from_val.get('value', {})
            
            if isinstance(value, dict) and value.get('relation') == 'RELATIVE':
                date_desc = format_relative_date(value)
                range_parts.append(f"{op_text} {date_desc}")
            else:
                range_parts.append(f"{op_text} {value}")
        
        # Process range_to  
        if 'range_to' in col_filter:
            to_val = col_filter['range_to']
            operator = to_val.get('operator', 'LTEQ')
            op_text = translate_operator(operator, is_numeric=False)  # Default to date format
            value = to_val.get('value', {})
            
            if isinstance(value, dict) and value.get('relation') == 'RELATIVE':
                date_desc = format_relative_date(value)
                range_parts.append(f"{op_text} {date_desc}")
            elif not value:  # Empty value for "up to baseline"
                range_parts.append(f"{op_text} the search date")
            else:
                range_parts.append(f"{op_text} {value}")
        
        return f"Range: {' AND '.join(range_parts)}" if range_parts else None
    
    def _format_range_description_from_parsed(self, range_data):
        """Format range information from the parsed data structure"""
        if not range_data:
            return None
        
        range_parts = []
        
        # Use shared operator formatting function
        def translate_operator(op, is_numeric=False):
            return format_operator_text(op, is_numeric)
        
        # Helper function to format relative dates and age values  
        def format_relative_date(value, unit, relation=None, operator=None):
            unit = unit.lower()
            
            # Handle absolute dates (like 01/04/2023)
            if relation == 'ABSOLUTE' or unit == 'date':
                return f"the absolute date {value}"
            
            # Handle age values (for demographics)
            if unit in ['year', 'years'] and relation == 'RELATIVE':
                unit_str = 'years old' if value != '1' else 'year old'
                return f"{value} {unit_str}"
            
            # Handle negative values (past dates) with EMIS-style operator interpretation
            if value.startswith('-'):
                val_num = value[1:]  # Remove minus sign
                
                # Format according to EMIS conventions
                if unit in ['month', 'months']:
                    unit_str = 'months' if val_num != '1' else 'month'
                    return f"{val_num} {unit_str} before the search date"
                elif unit in ['day', 'days']:
                    unit_str = 'days' if val_num != '1' else 'day'
                    return f"{val_num} {unit_str} before the search date"
                elif unit in ['year', 'years']:
                    unit_str = 'years' if val_num != '1' else 'year'
                    return f"{val_num} {unit_str} before the search date"
                elif unit in ['week', 'weeks']:
                    unit_str = 'weeks' if val_num != '1' else 'week'
                    return f"{val_num} {unit_str} before the search date"
                
                # Default interpretation for other operators
                if unit in ['month', 'months']:
                    unit_str = 'months' if val_num != '1' else 'month'
                    return f"{val_num} {unit_str} before the search date"
                elif unit in ['day', 'days']:
                    unit_str = 'days' if val_num != '1' else 'day'
                    return f"{val_num} {unit_str} before the search date"
                elif unit in ['year', 'years']:
                    unit_str = 'years' if val_num != '1' else 'year'
                    return f"{val_num} {unit_str} before the search date"
                elif unit in ['week', 'weeks']:
                    unit_str = 'weeks' if val_num != '1' else 'week'
                    return f"{val_num} {unit_str} before the search date"
            # Handle positive values (future dates or age)
            elif value and not value.startswith('0'):
                if unit in ['month', 'months']:
                    unit_str = 'months' if value != '1' else 'month'
                    return f"{value} {unit_str} after the search date"
                elif unit in ['day', 'days']:
                    unit_str = 'days' if value != '1' else 'day' 
                    # Special case for vaccination schedules
                    if value == '248':
                        return f"{value} days (8 months)"
                    return f"{value} {unit_str} after the search date"
                elif unit in ['year', 'years']:
                    unit_str = 'years' if value != '1' else 'year'
                    return f"{value} {unit_str} after the search date"
                elif unit in ['week', 'weeks']:
                    unit_str = 'weeks' if value != '1' else 'week'
                    return f"{value} {unit_str} after the search date"
            
            # Handle current/baseline (value is 0 or empty)
            return "the search date"
        
        # Process range from
        if range_data.get('from'):
            from_data = range_data['from']
            operator = from_data.get('operator', 'GTEQ')
            value = from_data.get('value', '')
            unit = from_data.get('unit', '')
            relation = from_data.get('relation', '')
            
            if value and unit:
                date_desc = format_relative_date(value, unit, relation, operator)
                op_text = translate_operator(operator, is_numeric=False)
                range_parts.append(f"{op_text} {date_desc}")
            elif value:
                # Handle numeric values (like spirometry results, BMI scores)
                op_text = translate_operator(operator, is_numeric=True)
                if value.replace('.', '').replace('-', '').isdigit():
                    range_parts.append(f"{op_text} {value}")
                else:
                    range_parts.append(f"{op_text} {value}")
        
        # Process range to  
        if range_data.get('to'):
            to_data = range_data['to']
            operator = to_data.get('operator', 'LTEQ')
            value = to_data.get('value', '')
            unit = to_data.get('unit', '')
            relation = to_data.get('relation', '')
            
            # Always define op_text first
            op_text = translate_operator(operator, is_numeric=False)
            
            if value and unit:
                date_desc = format_relative_date(value, unit, relation, operator)
                range_parts.append(f"{op_text} {date_desc}")
            elif value:
                # Handle numeric values (like spirometry results, BMI scores)
                op_text = translate_operator(operator, is_numeric=True)
                if value.replace('.', '').isdigit():
                    range_parts.append(f"{op_text} {value}")
                else:
                    range_parts.append(f"{op_text} {value}")
            elif range_data.get('relative_to') == 'BASELINE':
                range_parts.append(f"{op_text} the search date")
            else:
                range_parts.append(f"{op_text}")
        
        return f"Range: {' AND '.join(range_parts)}" if range_parts else None
    
    def _format_relationship_description(self, relationship):
        """Format relationship information for linked criteria"""
        if not relationship:
            return None
        
        parent_col = relationship.get('parent_column', 'Unknown')
        child_col = relationship.get('child_column', 'Unknown')
        
        # Check for range relationship
        if 'range_from' in relationship:
            from_val = relationship['range_from']
            operator = from_val.get('operator', 'GT')
            value = from_val.get('value', {})
            
            if isinstance(value, dict):
                val_str = value.get('value', '0')
                unit = value.get('unit', 'DAY').lower()
                
                if operator == 'GT' and val_str == '0' and unit == 'day':
                    return f"Relationship: The {child_col} is more than 0 days after the {parent_col} from the above feature"
        
        return f"Relationship: {child_col} relates to {parent_col}"
    
    def _format_restriction_details(self, restriction):
        """Format comprehensive restriction details including latest/earliest, current status, etc."""
        if not restriction:
            return "Unknown restriction"
        
        # Handle SearchRestriction objects
        if hasattr(restriction, 'type'):
            restriction_type = restriction.type
            if restriction_type == "latest_records":
                # Enhanced description for record restrictions
                if hasattr(restriction, 'record_count') and hasattr(restriction, 'direction'):
                    count = restriction.record_count
                    direction = restriction.direction
                    
                    details = []
                    if direction == "DESC":
                        if count == 1:
                            details.append("Latest 1 record only")
                        else:
                            details.append(f"Latest {count} records only")
                        details.append("Ordered by: most recent first")
                    elif direction == "ASC":
                        if count == 1:
                            details.append("Earliest 1 record only")
                        else:
                            details.append(f"Earliest {count} records only")
                        details.append("Ordered by: earliest first")
                    else:
                        details.append(f"{count} records with {direction} ordering")
                        
                    return " | ".join(details)
                elif hasattr(restriction, 'description'):
                    return restriction.description
                else:
                    return "Record count restriction applied"
                    
            elif restriction_type == "conditional_latest":
                # Complex restriction with conditional logic (like AST005)
                if hasattr(restriction, 'description') and restriction.description:
                    details = [restriction.description]
                    if hasattr(restriction, 'record_count') and hasattr(restriction, 'direction'):
                        direction_text = "most recent first" if restriction.direction == "DESC" else "earliest first"
                        details.append(f"Ordered by: {direction_text}")
                    return " | ".join(details)
                else:
                    return "Conditional record filtering applied"
                    
            elif restriction_type == "test_condition":
                # Test condition descriptions
                if hasattr(restriction, 'description') and restriction.description:
                    return restriction.description
                else:
                    details = ["Additional filtering condition"]
                    if hasattr(restriction, 'conditions') and restriction.conditions:
                        details.append("Complex test criteria applied")
                    return " | ".join(details)
                
            elif restriction_type == "current_status":
                return "Only current/active records included"
                
            elif restriction_type == "date_range":
                return "Date range filtering applied"
                
            elif restriction_type == "medication_current":
                return "Only current medications included"
                
            elif restriction_type == "latest_issue":
                if hasattr(restriction, 'issue_count'):
                    count = restriction.issue_count
                    return f"Latest issue is {count}"
                return "Latest issue restriction"
                
            elif restriction_type == "episode_based":
                return "Episode-based filtering (FIRST, NEW, REVIEW, etc.)"
                
            elif restriction_type == "age_range":
                return "Age range restriction applied"
                
            elif restriction_type == "demographic":
                return "Patient demographic filtering"
                
            else:
                # Fallback to description if available
                if hasattr(restriction, 'description') and restriction.description:
                    return restriction.description
                return f"Restriction type: {restriction_type}"
        
        # Handle dictionary format (legacy support)
        if isinstance(restriction, dict):
            if 'record_count' in restriction:
                count = restriction['record_count']
                direction = restriction.get('direction', 'DESC')
                order_text = "latest" if direction == "DESC" else "earliest"
                return f"{order_text.title()} {count} records only"
            elif 'type' in restriction:
                return f"Restriction: {restriction['type']}"
        
        return str(restriction)
    
    def _format_restriction_simple(self, restriction):
        """Format restriction details in a simple, user-friendly way"""
        if not restriction:
            return "No limit"
        
        # Handle SearchRestriction objects
        if hasattr(restriction, 'type'):
            restriction_type = restriction.type
            if restriction_type == "latest_records":
                if hasattr(restriction, 'record_count') and hasattr(restriction, 'direction'):
                    count = restriction.record_count
                    direction = restriction.direction
                    
                    if direction == "DESC":
                        return f"Latest {count}" if count != 1 else "Latest 1"
                    elif direction == "ASC":
                        return f"Earliest {count}" if count != 1 else "Earliest 1"
                    else:
                        return f"{count} records"
                else:
                    return "Record limit applied"
            elif restriction_type == "current_status":
                return "Current records only"
            elif restriction_type == "medication_current":
                return "Current medications only"
            elif hasattr(restriction, 'description') and restriction.description:
                return restriction.description
        
        # Handle dictionary format
        if isinstance(restriction, dict):
            if 'record_count' in restriction:
                count = restriction['record_count']
                direction = restriction.get('direction', 'DESC')
                order_text = "Latest" if direction == "DESC" else "Earliest"
                return f"{order_text} {count}"
        
        return "Record limit applied"
    
    def _format_filter_summary(self, col_filter):
        """Format column filter in EMIS clinical style"""
        if not col_filter:
            return "No filter"
        
        column = col_filter.get('column', 'Unknown')
        display_name = col_filter.get('display_name', column)
        
        # EMIS-style clinical filter descriptions
        if column.upper() in ['READCODE', 'SNOMEDCODE']:
            # Count value sets to show how many codes
            value_count = 0
            if 'value_sets' in col_filter:
                value_sets = col_filter.get('value_sets', [])
                for vs in value_sets:
                    if 'values' in vs:
                        value_count += len(vs['values'])
            
            in_not_in = col_filter.get('in_not_in', 'IN')
            action = "Include" if in_not_in.upper() == "IN" else "Exclude"
            
            if value_count > 0:
                return f"{action} {value_count} specified clinical codes"
            else:
                return f"{action} specified clinical codes"
                
        elif column.upper() == 'DATE':
            # Check for range information
            if 'range' in col_filter and col_filter['range']:
                range_desc = self._format_range_emis_style(col_filter['range'])
                return range_desc if range_desc else "Date is after/before search date"
            return "Date filter applied"
            
        elif column.upper() == 'AGE':
            # Age range information
            if 'range' in col_filter and col_filter['range']:
                range_desc = self._format_range_emis_style(col_filter['range'], is_age=True)
                return range_desc if range_desc else "Age filter applied"
            return "Age filter applied"
            
        elif column.upper() == 'CONSULTATION_HEADING':
            # Check for specific consultation types
            in_not_in = col_filter.get('in_not_in', 'IN')
            heading_types = []
            
            # Extract values from value_sets
            if 'value_sets' in col_filter:
                value_sets = col_filter.get('value_sets', [])
                for vs in value_sets:
                    if 'values' in vs:
                        for v in vs['values']:
                            if isinstance(v, dict):
                                # Handle dict format with displayName
                                heading_types.append(v.get('displayName', v.get('value', str(v))))
                            else:
                                # Handle simple string format
                                heading_types.append(str(v))
            
            action = "Include" if in_not_in.upper() == "IN" else "Exclude"
            
            if heading_types:
                if len(heading_types) == 1:
                    return f"{action} consultations where the consultation heading is: {heading_types[0]}"
                else:
                    return f"{action} consultations with heading types: {', '.join(heading_types)}"
            else:
                return f"{action} consultations with specified heading types"
                
        elif column.upper() == 'NUMERIC_VALUE':
            # Numeric value ranges
            if 'range' in col_filter and col_filter['range']:
                range_desc = self._format_range_emis_style(col_filter['range'], is_numeric=True)
                return range_desc if range_desc else "Numeric value filter applied"
            return "Numeric value filter applied"
            
        elif column.upper() == 'EPISODE':
            # Episode type filtering
            values = col_filter.get('values', [])
            in_not_in = col_filter.get('in_not_in', 'IN')
            
            if values:
                episode_types = [str(v) for v in values]
                action = "Include" if in_not_in.upper() == "IN" else "Exclude"
                return f"{action} episodes of type: {', '.join(episode_types)}"
            else:
                return "Episode type filter applied"
                
        elif 'DRUG' in column.upper():
            # Drug/medication codes
            value_count = len(col_filter.get('values', []))
            if value_count > 0:
                return f"Include {value_count} specified medication codes"
            else:
                return "Include specified medication codes"
        else:
            return f"{display_name} filter applied"
    
    def _format_range_simple(self, range_data):
        """Format range information in a simple way"""
        if not range_data:
            return None
        
        parts = []
        
        # Process range from
        if range_data.get('from'):
            from_data = range_data['from']
            value = from_data.get('value', '')
            unit = from_data.get('unit', '')
            
            if value and unit:
                if value.startswith('-'):
                    val_num = value[1:]
                    parts.append(f"{val_num} {unit}s ago")
                else:
                    parts.append(f"{value} {unit}s")
        
        # Process range to
        if range_data.get('to'):
            to_data = range_data['to']
            value = to_data.get('value', '')
            unit = to_data.get('unit', '')
            
            if value and unit:
                if value.startswith('-'):
                    val_num = value[1:]
                    parts.append(f"to {val_num} {unit}s ago")
                else:
                    parts.append(f"to {value} {unit}s")
            else:
                parts.append("to search date")
        
        return " ".join(parts) if parts else "Date range"
    
    def _format_range_emis_style(self, range_data, is_age=False, is_numeric=False):
        """Format range information in EMIS clinical style"""
        if not range_data:
            return None
        
        # Process range from
        if range_data.get('from'):
            from_data = range_data['from']
            operator = from_data.get('operator', 'GTEQ')
            value = from_data.get('value', '')
            unit = from_data.get('unit', '')
            
            if value and unit:
                if value.startswith('-'):
                    # Past dates/ages
                    val_num = value[1:]
                    if is_age:
                        return f"Age is more than {val_num} {unit.lower()}s old"
                    elif unit.upper() == 'YEAR':
                        return f"Date is after {val_num} year{'s' if val_num != '1' else ''} before the search date"
                    elif unit.upper() == 'MONTH':
                        return f"Date is after {val_num} month{'s' if val_num != '1' else ''} before the search date"
                    elif unit.upper() == 'DAY':
                        return f"Date is after {val_num} day{'s' if val_num != '1' else ''} before the search date"
                else:
                    # Future dates or positive values
                    if is_numeric:
                        op_text = "greater than" if operator == "GT" else "greater than or equal to" if operator == "GTEQ" else "equal to"
                        return f"Numeric value is {op_text} {value}"
                    elif is_age:
                        return f"Age is more than {value} {unit.lower()}s"
                    else:
                        return f"Date is after {value} {unit.lower()}s from the search date"
        
        # Process range to
        if range_data.get('to'):
            to_data = range_data['to']
            operator = to_data.get('operator', 'LTEQ')
            value = to_data.get('value', '')
            unit = to_data.get('unit', '')
            
            if value and unit:
                if value.startswith('-'):
                    val_num = value[1:]
                    if is_age:
                        return f"Age is less than {val_num} {unit.lower()}s old"
                    elif unit.upper() == 'YEAR':
                        return f"Date is before {val_num} year{'s' if val_num != '1' else ''} before the search date"
                    else:
                        return f"Date is before {val_num} {unit.lower()}{'s' if val_num != '1' else ''} before the search date"
                else:
                    if is_numeric:
                        op_text = "less than" if operator == "LT" else "less than or equal to" if operator == "LTEQ" else "equal to"
                        return f"Numeric value is {op_text} {value}"
                    elif is_age:
                        return f"Age is less than {value} {unit.lower()}s"
                    else:
                        return f"Date is before {value} {unit.lower()}s from the search date"
            else:
                # Empty value for "up to baseline"
                return "Date is before the search date"
        
        return "Date/value range filter applied"
    
    def _generate_list_report_export(self, list_report, include_parent_info=True):
        """Generate export for List Report type"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Overview sheet
            overview_data = [
                ['Report Type', 'List Report'],
                ['Report Name', list_report.name],
                ['Description', list_report.description or 'N/A'],
                ['Parent Type', list_report.parent_type or 'N/A'],
                ['Search Date', list_report.search_date],
                ['Export Date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            ]
            
            if include_parent_info and list_report.direct_dependencies:
                overview_data.extend([
                    ['', ''],
                    ['Parent Dependencies', ''],
                    ['Referenced Search IDs', ', '.join(list_report.direct_dependencies)]
                ])
            
            overview_df = pd.DataFrame(overview_data, columns=['Property', 'Value'])
            overview_df_safe = sanitize_dataframe_for_excel(overview_df)
            overview_df_safe.to_excel(writer, sheet_name='Overview', index=False)
            
            # Column groups sheet
            if list_report.column_groups:
                columns_data = []
                for group in list_report.column_groups:
                    group_info = {
                        'Group ID': group.get('id', ''),
                        'Logical Table': group.get('logical_table', ''),
                        'Display Name': group.get('display_name', ''),
                        'Has Criteria': group.get('has_criteria', False),
                        'Column Count': len(group.get('columns', []))
                    }
                    columns_data.append(group_info)
                    
                    # Add individual columns
                    for col in group.get('columns', []):
                        col_info = {
                            'Group ID': f"  └─ {col.get('id', '')}",
                            'Logical Table': col.get('column', ''),
                            'Display Name': col.get('display_name', ''),
                            'Has Criteria': '',
                            'Column Count': ''
                        }
                        columns_data.append(col_info)
                
                columns_df = pd.DataFrame(columns_data)
                columns_df_safe = sanitize_dataframe_for_excel(columns_df)
                columns_df_safe.to_excel(writer, sheet_name='Column_Structure', index=False)
        
        output.seek(0)
        
        # Generate filename
        clean_name = SearchManager.clean_search_name(list_report.name)
        safe_name = "".join(c for c in clean_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"ListReport_{safe_name}_{timestamp}.xlsx"
        
        return filename, output.getvalue()
    
    def _generate_audit_report_export(self, audit_report, include_parent_info=True):
        """Generate export for Audit Report type"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Overview sheet
            overview_data = [
                ['Report Type', 'Audit Report'],
                ['Report Name', audit_report.name],
                ['Description', audit_report.description or 'N/A'],
                ['Parent Type', audit_report.parent_type or 'N/A'],
                ['Search Date', audit_report.search_date],
                ['Export Date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            ]
            
            if include_parent_info and audit_report.direct_dependencies:
                overview_data.extend([
                    ['', ''],
                    ['Population References', ''],
                    ['Referenced Population IDs', ', '.join(audit_report.direct_dependencies)]
                ])
            
            overview_df = pd.DataFrame(overview_data, columns=['Property', 'Value'])
            overview_df_safe = sanitize_dataframe_for_excel(overview_df)
            overview_df_safe.to_excel(writer, sheet_name='Overview', index=False)
            
            # Aggregation logic sheet
            if audit_report.custom_aggregate:
                agg = audit_report.custom_aggregate
                agg_data = [
                    ['Logical Table', agg.get('logical_table', '')],
                    ['Result Source', agg.get('result', {}).get('source', '')],
                    ['Calculation Type', agg.get('result', {}).get('calculation_type', '')],
                    ['Population Reference', agg.get('population_reference', '')]
                ]
                
                # Add grouping information
                groups = agg.get('groups', [])
                if groups:
                    agg_data.extend([['', ''], ['Grouping Configuration', '']])
                    for i, group in enumerate(groups, 1):
                        agg_data.extend([
                            [f'Group {i} ID', group.get('id', '')],
                            [f'Group {i} Display Name', group.get('display_name', '')],
                            [f'Group {i} Grouping Column', group.get('grouping_column', '')],
                            [f'Group {i} Sub Totals', str(group.get('sub_totals', False))],
                            [f'Group {i} Repeat Header', str(group.get('repeat_header', False))]
                        ])
                
                agg_df = pd.DataFrame(agg_data, columns=['Property', 'Value'])
                agg_df_safe = sanitize_dataframe_for_excel(agg_df)
                agg_df_safe.to_excel(writer, sheet_name='Aggregation_Logic', index=False)
        
        output.seek(0)
        
        # Generate filename
        clean_name = SearchManager.clean_search_name(audit_report.name)
        safe_name = "".join(c for c in clean_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"AuditReport_{safe_name}_{timestamp}.xlsx"
        
        return filename, output.getvalue()
    
    def _generate_aggregate_report_export(self, aggregate_report, include_parent_info=True):
        """Generate export for Aggregate Report type"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Overview sheet
            overview_data = [
                ['Report Type', 'Aggregate Report'],
                ['Report Name', aggregate_report.name],
                ['Description', aggregate_report.description or 'N/A'],
                ['Parent Type', aggregate_report.parent_type or 'N/A'],
                ['Search Date', aggregate_report.search_date],
                ['Export Date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            ]
            
            overview_df = pd.DataFrame(overview_data, columns=['Property', 'Value'])
            overview_df_safe = sanitize_dataframe_for_excel(overview_df)
            overview_df_safe.to_excel(writer, sheet_name='Overview', index=False)
            
            # Aggregate groups sheet
            if aggregate_report.aggregate_groups:
                groups_data = []
                for group in aggregate_report.aggregate_groups:
                    group_info = {
                        'Group ID': group.get('id', ''),
                        'Display Name': group.get('display_name', ''),
                        'Grouping Columns': ', '.join(group.get('grouping_columns', [])),
                        'Sub Totals': str(group.get('sub_totals', False)),
                        'Repeat Header': str(group.get('repeat_header', False))
                    }
                    groups_data.append(group_info)
                
                groups_df = pd.DataFrame(groups_data)
                groups_df_safe = sanitize_dataframe_for_excel(groups_df)
                groups_df_safe.to_excel(writer, sheet_name='Aggregate_Groups', index=False)
            
            # Statistical configuration sheet
            if aggregate_report.statistical_groups:
                stats_data = []
                for stat in aggregate_report.statistical_groups:
                    stat_info = {
                        'Type': stat.get('type', ''),
                        'Group ID': stat.get('group_id', ''),
                        'Source': stat.get('source', ''),
                        'Calculation Type': stat.get('calculation_type', '')
                    }
                    stats_data.append(stat_info)
                
                stats_df = pd.DataFrame(stats_data)
                stats_df_safe = sanitize_dataframe_for_excel(stats_df)
                stats_df_safe.to_excel(writer, sheet_name='Statistical_Config', index=False)
            
            # Include criteria if present (aggregate reports can have their own criteria)
            if aggregate_report.criteria_groups:
                for i, group in enumerate(aggregate_report.criteria_groups, 1):
                    rule_df = self._create_rule_sheet(group, i)
                    rule_df_safe = sanitize_dataframe_for_excel(rule_df)
                    rule_df_safe.to_excel(writer, sheet_name=f'Criteria_Rule_{i}', index=False)
        
        output.seek(0)
        
        # Generate filename
        clean_name = SearchManager.clean_search_name(aggregate_report.name)
        safe_name = "".join(c for c in clean_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"AggregateReport_{safe_name}_{timestamp}.xlsx"
        
        return filename, output.getvalue()