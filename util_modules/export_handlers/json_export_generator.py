"""
JSON Export Generator for Rule Logic Browser
Generates focused JSON exports containing complete search logic for the selected search only.
Provides SNOMED codes (not EMIS codes) and everything needed for programmatic recreation.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..core import SearchManager


class JSONExportGenerator:
    """Generates focused JSON exports for individual search recreation"""
    
    def __init__(self, analysis):
        self.analysis = analysis
    
    def generate_search_json(self, search_report, xml_filename: str) -> tuple[str, str]:
        """
        Generate focused JSON export for a single search
        
        Args:
            search_report: The specific SearchReport to export
            xml_filename: Original XML filename for reference
            
        Returns:
            tuple: (filename, json_string)
        """
        
        # Build focused JSON structure for this search only
        export_data = {
            "search_definition": self._build_search_definition(search_report, xml_filename),
            "rule_logic": self._build_complete_rule_logic(search_report),
            "clinical_terminology": self._build_clinical_terminology(search_report),
            "dependencies": self._build_search_dependencies(search_report)
        }
        
        # Generate focused filename
        clean_name = SearchManager.clean_search_name(search_report.name)
        safe_name = "".join(c for c in clean_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{safe_name}_logic_{timestamp}.json"
        
        # Format JSON with proper indentation
        json_string = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        return filename, json_string
    
    def _build_search_definition(self, search_report, xml_filename: str) -> Dict[str, Any]:
        """Build core search definition with essential metadata only"""
        return {
            "search_name": search_report.name,
            "search_id": search_report.id,
            "description": search_report.description or "",
            "population_type": search_report.population_type,
            "folder_location": search_report.folder_id or "Root",
            "source_xml": xml_filename,
            "export_timestamp": datetime.now().isoformat(),
            "export_version": "1.0"
        }
    
    def _build_complete_rule_logic(self, search_report) -> List[Dict[str, Any]]:
        """Build complete rule structure with all logic components"""
        rules = []
        
        for rule_number, group in enumerate(search_report.criteria_groups, 1):
            rule_data = {
                "rule_number": rule_number,
                "logic_operator": group.member_operator,  # AND/OR
                "if_conditions_met": group.action_if_true,
                "if_conditions_not_met": group.action_if_false,
                "criteria": self._build_complete_criteria(group.criteria),
                "population_references": self._build_population_refs(group)
            }
            rules.append(rule_data)
        
        return rules
    
    def _build_complete_criteria(self, criteria) -> List[Dict[str, Any]]:
        """Build complete criteria with all SNOMED codes and logic"""
        criteria_list = []
        
        for criterion in criteria:
            criterion_data = {
                "criterion_id": criterion.id,
                "table": criterion.table,
                "display_name": criterion.display_name,
                "description": criterion.description or "",
                "negation": criterion.negation,
                "exception_code": criterion.exception_code,
                "clinical_codes": self._extract_clinical_codes_from_criterion(criterion),
                "column_filters": self._build_complete_column_filters(criterion.column_filters),
                "restrictions": self._build_complete_restrictions(criterion.restrictions),
                "linked_criteria": self._build_linked_criteria_details(criterion.linked_criteria)
            }
            criteria_list.append(criterion_data)
        
        return criteria_list
    
    def _extract_clinical_codes_from_criterion(self, criterion) -> List[Dict[str, Any]]:
        """Extract unique clinical codes with SNOMED translations from a criterion"""
        seen_codes = set()
        unique_codes = []
        
        # Extract from value sets
        for vs in criterion.value_sets:
            for value in vs.get('values', []):
                emis_code = value.get('value')
                if emis_code and emis_code not in seen_codes:
                    seen_codes.add(emis_code)
                    snomed_info = self._get_snomed_translation(emis_code)
                    
                    # Use the best available description: SNOMED description > original display_name > fallback
                    description = snomed_info.get('description', '').strip()
                    if not description:
                        description = value.get('display_name', '').strip()
                    if not description:
                        description = 'No description available'
                    
                    code_entry = {
                        "emis_guid": emis_code,
                        "snomed_code": snomed_info.get('snomed_code', 'Not found'),
                        "description": description,
                        "code_system": snomed_info.get('code_system', ''),
                        "is_medication": snomed_info.get('is_medication', False),
                        "is_refset": snomed_info.get('is_refset', False),
                        "include_children": value.get('include_children', False),
                        "source_context": vs.get('description', 'Value Set'),
                        "translation_status": snomed_info.get('status', 'unknown')
                    }
                    unique_codes.append(code_entry)
        
        # Extract from column filter value sets (only if not already seen)
        for col_filter in criterion.column_filters:
            for vs in col_filter.get('value_sets', []):
                for value in vs.get('values', []):
                    emis_code = value.get('value')
                    if emis_code and emis_code not in seen_codes:
                        seen_codes.add(emis_code)
                        snomed_info = self._get_snomed_translation(emis_code)
                        
                        # Use the best available description: SNOMED description > original display_name > fallback
                        description = snomed_info.get('description', '').strip()
                        if not description:
                            description = value.get('display_name', '').strip()
                        if not description:
                            description = 'No description available'
                        
                        code_entry = {
                            "emis_guid": emis_code,
                            "snomed_code": snomed_info.get('snomed_code', 'Not found'),
                            "description": description,
                            "code_system": snomed_info.get('code_system', ''),
                            "is_medication": snomed_info.get('is_medication', False),
                            "is_refset": snomed_info.get('is_refset', False),
                            "include_children": value.get('include_children', False),
                            "source_context": f"{col_filter.get('display_name', 'Column Filter')} ({col_filter.get('in_not_in', 'UNKNOWN')})",
                            "translation_status": snomed_info.get('status', 'unknown')
                        }
                        unique_codes.append(code_entry)
        
        return unique_codes
    
    def _build_complete_column_filters(self, column_filters) -> List[Dict[str, Any]]:
        """Build complete column filter logic"""
        filters = []
        
        for col_filter in column_filters:
            filter_data = {
                "column": col_filter.get('column'),
                "display_name": col_filter.get('display_name'),
                "inclusion_logic": "INCLUDE" if col_filter.get('in_not_in') == "IN" else "EXCLUDE",
                "filter_constraints": self._build_filter_constraints_complete(col_filter)
            }
            filters.append(filter_data)
        
        return filters
    
    def _build_filter_constraints_complete(self, col_filter) -> Dict[str, Any]:
        """Build complete filter constraints with SQL-ready logic"""
        constraints = {}
        column = col_filter.get('column', '').upper()
        
        # Date/range constraints using the same format as search_export.py
        if col_filter.get('range'):
            range_info = col_filter['range']
            
            # Process range_from (typically GTEQ operators like age >=18)
            if range_info.get('from'):
                from_data = range_info['from']
                operator = from_data.get('operator', 'GTEQ')
                value = from_data.get('value', '')
                unit = from_data.get('unit', '')
                
                # Format human-readable constraint
                if column == 'AGE' and value:
                    op_text = "greater than or equal to" if operator == "GTEQ" else "greater than" if operator == "GT" else "equal to"
                    unit_text = "years" if unit.upper() == "YEAR" else unit.lower()
                    human_desc = f"Age {op_text} {value} {unit_text}"
                elif column == 'DATE' and value:
                    op_text = self._format_date_operator(operator, value, unit)
                    human_desc = f"Date {op_text}"
                else:
                    op_text = "greater than or equal to" if operator == "GTEQ" else "greater than" if operator == "GT" else "equal to"
                    human_desc = f"{op_text} {value} {unit}"
                
                constraints["range_filter"] = {
                    "type": "range_from",
                    "operator": operator,
                    "value": value,
                    "unit": unit,
                    "human_readable": human_desc,
                    "sql_ready": bool(operator and value)
                }
            
            # Process range_to (typically LTEQ operators)
            if range_info.get('to'):
                to_data = range_info['to']
                operator = to_data.get('operator', 'LTEQ')
                value = to_data.get('value', '')
                unit = to_data.get('unit', '')
                
                # Format human-readable constraint
                if column == 'AGE' and value:
                    op_text = "less than or equal to" if operator == "LTEQ" else "less than" if operator == "LT" else "equal to"
                    unit_text = "years" if unit.upper() == "YEAR" else unit.lower()
                    human_desc = f"Age {op_text} {value} {unit_text}"
                elif column == 'DATE' and value:
                    op_text = self._format_date_operator(operator, value, unit)
                    human_desc = f"Date {op_text}"
                else:
                    op_text = "less than or equal to" if operator == "LTEQ" else "less than" if operator == "LT" else "equal to"
                    human_desc = f"{op_text} {value} {unit}"
                
                constraints["range_filter_to"] = {
                    "type": "range_to",
                    "operator": operator,
                    "value": value,
                    "unit": unit,
                    "human_readable": human_desc,
                    "sql_ready": bool(operator and value)
                }
        
        # Runtime parameters
        if col_filter.get('parameter'):
            param_info = col_filter['parameter']
            constraints["parameter_filter"] = {
                "parameter_name": param_info.get('name', 'UNKNOWN_PARAMETER'),
                "global_scope": param_info.get('allow_global', False),
                "data_type": self._determine_parameter_type(col_filter.get('column')),
                "requires_user_input": True
            }
        
        # Value set constraints (for completeness, even though handled in clinical_codes)
        if col_filter.get('value_sets'):
            value_count = sum(len(vs.get('values', [])) for vs in col_filter['value_sets'])
            constraints["value_set_filter"] = {
                "total_values": value_count,
                "inclusion_logic": "INCLUDE" if col_filter.get('in_not_in') == "IN" else "EXCLUDE",
                "values_handled_in": "clinical_codes_section"
            }
        
        # Text/string constraints
        if col_filter.get('text_value'):
            constraints["text_filter"] = {
                "value": col_filter['text_value'],
                "comparison": col_filter.get('text_operator', 'EQUALS'),
                "case_sensitive": col_filter.get('case_sensitive', False)
            }
        
        # If no specific constraints found but we have basic column info
        if not constraints and col_filter.get('column'):
            constraints["basic_filter"] = {
                "filter_type": f"{column.lower()}_filter",
                "column": col_filter.get('column'),
                "display_name": col_filter.get('display_name', col_filter.get('column'))
            }
        
        return constraints
    
    def _build_complete_restrictions(self, restrictions) -> List[Dict[str, Any]]:
        """Build complete restriction logic"""
        restriction_list = []
        
        for restriction in restrictions:
            restriction_data = {
                "restriction_type": restriction.restriction_type,
                "count": restriction.count,
                "time_constraint": {
                    "period": getattr(restriction, 'time_period', None),
                    "unit": getattr(restriction, 'time_unit', None)
                },
                "sort_order": getattr(restriction, 'sort_order', 'DESC'),
                "conditional_where": self._build_where_conditions_complete(restriction),
                "sql_pattern": f"{restriction.restriction_type} {restriction.count}"
            }
            restriction_list.append(restriction_data)
        
        return restriction_list
    
    def _build_where_conditions_complete(self, restriction) -> List[Dict[str, Any]]:
        """Build WHERE conditions for restrictions"""
        conditions = []
        
        if hasattr(restriction, 'where_conditions'):
            for condition in restriction.where_conditions:
                condition_data = {
                    "column": condition.get('column'),
                    "operator": condition.get('operator'),
                    "value": condition.get('value'),
                    "negation": condition.get('negation', False),
                    "sql_clause": f"{condition.get('column')} {condition.get('operator')} {condition.get('value')}"
                }
                conditions.append(condition_data)
        
        return conditions
    
    def _build_linked_criteria_details(self, linked_criteria) -> List[Dict[str, Any]]:
        """Build linked criteria relationships"""
        linked_list = []
        
        for linked in linked_criteria:
            linked_data = {
                "relationship_type": getattr(linked, 'relationship_type', 'cross_reference'),
                "target_table": linked.table,
                "target_display_name": linked.display_name,
                "temporal_constraint": getattr(linked, 'temporal_constraint', None)
            }
            linked_list.append(linked_data)
        
        return linked_list
    
    def _build_population_refs(self, group) -> List[Dict[str, Any]]:
        """Build population criteria references"""
        pop_refs = []
        
        if hasattr(group, 'population_criteria') and group.population_criteria:
            for pop_crit in group.population_criteria:
                pop_data = {
                    "referenced_search_id": pop_crit.report_guid,
                    "referenced_search_name": getattr(pop_crit, 'search_name', 'Unknown'),
                    "inclusion_type": getattr(pop_crit, 'inclusion_type', 'INCLUDE'),
                    "description": getattr(pop_crit, 'description', '')
                }
                pop_refs.append(pop_data)
        
        return pop_refs
    
    def _build_clinical_terminology(self, search_report) -> Dict[str, Any]:
        """Build complete clinical terminology with SNOMED focus"""
        # Get all unique codes from this search only
        all_codes = set()
        code_details = []
        
        for group in search_report.criteria_groups:
            for criterion in group.criteria:
                # Extract from value sets
                for vs in criterion.value_sets:
                    for value in vs.get('values', []):
                        emis_code = value.get('value')
                        if emis_code and emis_code not in all_codes:
                            all_codes.add(emis_code)
                            snomed_info = self._get_snomed_translation(emis_code)
                            
                            # Use the best available description: SNOMED description > original display_name > fallback
                            description = snomed_info.get('description', '').strip()
                            if not description:
                                description = value.get('display_name', '').strip()
                            if not description:
                                description = 'No description available'
                            
                            code_details.append({
                                "emis_guid": emis_code,
                                "snomed_code": snomed_info.get('snomed_code', 'Not found'),
                                "preferred_term": description,
                                "code_system": snomed_info.get('code_system', ''),
                                "semantic_type": "medication" if snomed_info.get('is_medication') else "clinical_concept",
                                "is_refset": snomed_info.get('is_refset', False),
                                "include_descendants": value.get('include_children', False),
                                "translation_quality": snomed_info.get('status', 'unknown')
                            })
                
                # Extract from column filters
                for col_filter in criterion.column_filters:
                    for vs in col_filter.get('value_sets', []):
                        for value in vs.get('values', []):
                            emis_code = value.get('value')
                            if emis_code and emis_code not in all_codes:
                                all_codes.add(emis_code)
                                snomed_info = self._get_snomed_translation(emis_code)
                                
                                # Use the best available description: SNOMED description > original display_name > fallback
                                description = snomed_info.get('description', '').strip()
                                if not description:
                                    description = value.get('display_name', '').strip()
                                if not description:
                                    description = 'No description available'
                                
                                code_details.append({
                                    "emis_guid": emis_code,
                                    "snomed_code": snomed_info.get('snomed_code', 'Not found'),
                                    "preferred_term": description,
                                    "code_system": snomed_info.get('code_system', ''),
                                    "semantic_type": "medication" if snomed_info.get('is_medication') else "clinical_concept",
                                    "is_refset": snomed_info.get('is_refset', False),
                                    "filter_context": col_filter.get('display_name', ''),
                                    "translation_quality": snomed_info.get('status', 'unknown')
                                })
        
        return {
            "total_unique_codes": len(all_codes),
            "terminology_focus": "SNOMED_CT",
            "codes": sorted(code_details, key=lambda x: x['snomed_code'])
        }
    
    def _build_search_dependencies(self, search_report) -> Dict[str, Any]:
        """Build dependency information for this search only"""
        dependencies = {
            "parent_search": None,
            "referenced_searches": []
        }
        
        # Parent search
        if hasattr(search_report, 'parent_guid') and search_report.parent_guid:
            dependencies["parent_search"] = {
                "search_id": search_report.parent_guid,
                "search_name": getattr(search_report, 'parent_name', 'Unknown')
            }
        
        # Referenced searches from population criteria
        for group in search_report.criteria_groups:
            if hasattr(group, 'population_criteria') and group.population_criteria:
                for pop_crit in group.population_criteria:
                    dependencies["referenced_searches"].append({
                        "search_id": pop_crit.report_guid,
                        "search_name": getattr(pop_crit, 'search_name', 'Unknown'),
                        "inclusion_type": getattr(pop_crit, 'inclusion_type', 'INCLUDE')
                    })
        
        return dependencies
    
    
    def _get_all_processed_clinical_codes(self) -> List[Dict[str, Any]]:
        """Get all already processed and translated clinical codes from session state"""
        import streamlit as st
        
        # Import the same function used by clinical tabs to get unified data
        try:
            from ..ui.tabs.tab_helpers import get_unified_clinical_data
            unified_results = get_unified_clinical_data()
            
            all_codes = []
            
            # Get clinical codes
            clinical_codes = unified_results.get('clinical_codes', [])
            for code in clinical_codes:
                all_codes.append({
                    'emis_guid': code.get('EMIS GUID', ''),
                    'snomed_code': code.get('SNOMED Code', 'Not found'),
                    'description': code.get('Description', ''),
                    'code_system': code.get('Code System', ''),
                    'semantic_type': 'clinical_concept',
                    'is_medication': False,
                    'is_refset': code.get('Refset', 'No') == 'Yes',
                    'source_entity': code.get('Source Entity', ''),
                    'source_search': code.get('Source Search', ''),
                    'translation_status': 'translated' if code.get('SNOMED Code', 'Not found') != 'Not found' else 'not_found'
                })
            
            # Get medications
            medications = unified_results.get('medications', [])
            for med in medications:
                all_codes.append({
                    'emis_guid': med.get('EMIS GUID', ''),
                    'snomed_code': med.get('SNOMED Code', 'Not found'),
                    'description': med.get('Description', ''),
                    'code_system': med.get('Code System', ''),
                    'semantic_type': 'medication',
                    'is_medication': True,
                    'is_refset': False,
                    'source_entity': med.get('Source Entity', ''),
                    'source_search': med.get('Source Search', ''),
                    'translation_status': 'translated' if med.get('SNOMED Code', 'Not found') != 'Not found' else 'not_found'
                })
            
            # Get refsets
            refsets = unified_results.get('refsets', [])
            for refset in refsets:
                all_codes.append({
                    'emis_guid': refset.get('EMIS GUID', ''),
                    'snomed_code': refset.get('SNOMED Code', 'Not found'),
                    'description': refset.get('Description', ''),
                    'code_system': refset.get('Code System', ''),
                    'semantic_type': 'refset',
                    'is_medication': False,
                    'is_refset': True,
                    'source_entity': refset.get('Source Entity', ''),
                    'source_search': refset.get('Source Search', ''),
                    'translation_status': 'translated' if refset.get('SNOMED Code', 'Not found') != 'Not found' else 'not_found'
                })
            
            return all_codes
            
        except Exception as e:
            # Fallback to empty list if unified data not available
            return []
    
    def _get_snomed_translation(self, emis_code: str) -> Dict[str, Any]:
        """Get SNOMED translation from already processed clinical codes"""
        all_codes = self._get_all_processed_clinical_codes()
        
        # Find this specific EMIS code in the processed data
        for code in all_codes:
            if code['emis_guid'] == emis_code:
                return {
                    'snomed_code': code['snomed_code'],
                    'description': code['description'],
                    'code_system': code['code_system'],
                    'is_medication': code['is_medication'],
                    'is_refset': code['is_refset'],
                    'status': code['translation_status']
                }
        
        # If not found in processed data, return not found
        return {
            'snomed_code': 'Not found',
            'description': '',
            'code_system': '',
            'is_medication': False,
            'is_refset': False,
            'status': 'not_found'
        }
    
    def _format_date_operator(self, operator: str, value: str, unit: str) -> str:
        """Format date operator for human readable descriptions"""
        if value.startswith('-'):
            # Past dates
            val_num = value[1:]
            unit_text = unit.lower() + ('s' if val_num != '1' else '') if unit else 'days'
            if operator == 'GTEQ':
                return f"on or after {val_num} {unit_text} before the search date"
            elif operator == 'GT':
                return f"after {val_num} {unit_text} before the search date"
            elif operator == 'LTEQ':
                return f"on or before {val_num} {unit_text} before the search date"
            elif operator == 'LT':
                return f"before {val_num} {unit_text} before the search date"
        elif value == '0' or not value:
            # Current date/baseline
            if operator == 'GTEQ':
                return "on or after the search date"
            elif operator == 'GT':
                return "after the search date"
            elif operator == 'LTEQ':
                return "on or before the search date"
            elif operator == 'LT':
                return "before the search date"
        else:
            # Future dates or absolute dates
            if '/' in value:  # Absolute date like "23/06/2025"
                if operator == 'GTEQ':
                    return f"on or after {value}"
                elif operator == 'GT':
                    return f"after {value}"
                elif operator == 'LTEQ':
                    return f"on or before {value}"
                elif operator == 'LT':
                    return f"before {value}"
            else:
                # Relative future dates
                unit_text = unit.lower() + ('s' if value != '1' else '') if unit else 'days'
                if operator == 'GTEQ':
                    return f"on or after {value} {unit_text} from the search date"
                elif operator == 'GT':
                    return f"after {value} {unit_text} from the search date"
                elif operator == 'LTEQ':
                    return f"on or before {value} {unit_text} from the search date"
                elif operator == 'LT':
                    return f"before {value} {unit_text} from the search date"
        
        return f"{operator} {value} {unit}"
    
    def _determine_parameter_type(self, column: str) -> str:
        """Determine parameter data type for SQL recreation"""
        if column and ('DATE' in column.upper() or 'DOB' in column.upper()):
            return 'date'
        elif column and ('AGE' in column.upper() or 'YEAR' in column.upper()):
            return 'numeric'
        else:
            return 'text'