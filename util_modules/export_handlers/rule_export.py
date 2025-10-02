"""
Rule Export Handler
Handles export of individual rules and criteria groups
"""

import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any
from ..common.export_utils import sanitize_dataframe_for_excel


class RuleExportHandler:
    """Handles export of individual rules and their criteria"""
    
    def __init__(self):
        pass
    
    def export_rule_as_csv(self, group, rule_number, search_name="Unknown Search"):
        """
        Export a single rule as CSV
        
        Args:
            group: CriteriaGroup object
            rule_number: Rule number for identification
            search_name: Name of the parent search
            
        Returns:
            tuple: (filename, csv_content)
        """
        data = []
        
        # Rule metadata
        data.append({
            'Type': 'Rule Info',
            'Rule Number': rule_number,
            'Logic': group.member_operator,
            'Action If True': group.action_if_true,
            'Action If False': group.action_if_false,
            'Criteria Count': len(group.criteria),
            'Uses Another Search': 'YES' if (hasattr(group, 'population_criteria') and group.population_criteria) else 'NO',
            'Search Name': search_name
        })
        
        # Add population criteria details if present
        if hasattr(group, 'population_criteria') and group.population_criteria:
            for i, pop_crit in enumerate(group.population_criteria, 1):
                data.append({
                    'Type': 'Referenced Search',
                    'Rule Number': rule_number,
                    'Reference Number': i,
                    'Search ID': pop_crit.report_guid,
                    'Search ID Short': pop_crit.report_guid[:8] + '...' if pop_crit.report_guid else 'Unknown'
                })
        
        # Add empty row
        data.append({})
        
        # Criteria details
        for i, criterion in enumerate(group.criteria, 1):
            data.append({
                'Type': 'Criterion',
                'Rule Number': rule_number,
                'Criterion Number': i,
                'ID': criterion.id,
                'Table': criterion.table,
                'Display Name': criterion.display_name,
                'Description': criterion.description or '',
                'Negation': str(criterion.negation),
                'Exception Code': criterion.exception_code or '',
                'Value Sets': len(criterion.value_sets) if criterion.value_sets else 0,
                'Column Filters': len(criterion.column_filters) if criterion.column_filters else 0,
                'Linked Criteria': len(criterion.linked_criteria) if criterion.linked_criteria else 0
            })
            
            # Add clinical codes for this criterion
            if criterion.value_sets:
                for vs in criterion.value_sets:
                    for value in vs.get('values', []):
                        data.append({
                            'Type': 'Clinical Code',
                            'Rule Number': rule_number,
                            'Criterion Number': i,
                            'Value Set ID': vs.get('id', ''),
                            'Value Set Description': vs.get('description', ''),
                            'Code System': vs.get('code_system', ''),
                            'Code Value': value.get('value', ''),
                            'Display Name': value.get('display_name', ''),
                            'Include Children': value.get('include_children', False),
                            'Is Refset': value.get('is_refset', False)
                        })
        
        df = pd.DataFrame(data)
        csv_content = df.to_csv(index=False)
        
        # Generate filename
        safe_search_name = "".join(c for c in search_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Rule_{rule_number}_{safe_search_name}_{timestamp}.csv"
        
        return filename, csv_content
    
    def export_rule_as_excel(self, group, rule_number, search_name="Unknown Search"):
        """
        Export a single rule as Excel with multiple sheets
        
        Args:
            group: CriteriaGroup object
            rule_number: Rule number for identification
            search_name: Name of the parent search
            
        Returns:
            tuple: (filename, excel_content)
        """
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Rule overview sheet
            overview_data = [
                ['Rule Number', rule_number],
                ['Logic', group.member_operator],
                ['Action If True', group.action_if_true],
                ['Action If False', group.action_if_false],
                ['Criteria Count', len(group.criteria)],
                ['Uses Another Search', 'YES' if (hasattr(group, 'population_criteria') and group.population_criteria) else 'NO'],
                ['Search Name', search_name],
                ['Export Date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            ]
            
            # Add referenced search details if present
            if hasattr(group, 'population_criteria') and group.population_criteria:
                overview_data.extend([
                    ['', ''],  # Spacer
                    ['Referenced Searches', '']
                ])
                for i, pop_crit in enumerate(group.population_criteria, 1):
                    overview_data.extend([
                        [f'Referenced Search {i} ID', pop_crit.report_guid],
                        [f'Referenced Search {i} (Short)', pop_crit.report_guid[:8] + '...' if pop_crit.report_guid else 'Unknown']
                    ])
            overview_df = pd.DataFrame(overview_data, columns=['Property', 'Value'])
            overview_df_safe = sanitize_dataframe_for_excel(overview_df)
            overview_df_safe.to_excel(writer, sheet_name='Rule_Overview', index=False)
            
            # Criteria details sheet
            criteria_data = []
            for i, criterion in enumerate(group.criteria, 1):
                criteria_data.append({
                    'Criterion Number': i,
                    'ID': criterion.id,
                    'Table': criterion.table,
                    'Display Name': criterion.display_name,
                    'Description': criterion.description or '',
                    'Negation': str(criterion.negation),
                    'Exception Code': criterion.exception_code or '',
                    'Value Sets Count': len(criterion.value_sets) if criterion.value_sets else 0,
                    'Column Filters Count': len(criterion.column_filters) if criterion.column_filters else 0,
                    'Linked Criteria Count': len(criterion.linked_criteria) if criterion.linked_criteria else 0
                })
            
            criteria_df = pd.DataFrame(criteria_data)
            criteria_df_safe = sanitize_dataframe_for_excel(criteria_df)
            criteria_df_safe.to_excel(writer, sheet_name='Criteria', index=False)
            
            # Clinical codes sheet
            codes_data = []
            for i, criterion in enumerate(group.criteria, 1):
                if criterion.value_sets:
                    for vs in criterion.value_sets:
                        for value in vs.get('values', []):
                            codes_data.append({
                                'Criterion Number': i,
                                'Criterion Description': criterion.description,
                                'Value Set ID': vs.get('id', ''),
                                'Value Set Description': vs.get('description', ''),
                                'Code System': vs.get('code_system', ''),
                                'Code Value': value.get('value', ''),
                                'Display Name': value.get('display_name', ''),
                                'Include Children': value.get('include_children', False),
                                'Is Refset': value.get('is_refset', False)
                            })
            
            if codes_data:
                codes_df = pd.DataFrame(codes_data)
                codes_df_safe = sanitize_dataframe_for_excel(codes_df)
                codes_df_safe.to_excel(writer, sheet_name='Clinical_Codes', index=False)
        
        output.seek(0)
        
        # Generate filename
        safe_search_name = "".join(c for c in search_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Rule_{rule_number}_{safe_search_name}_{timestamp}.xlsx"
        
        return filename, output.getvalue()