"""
XML utilities for EMIS XML to SNOMED Translator
Handles XML parsing, GUID extraction, and code system classification
"""

import xml.etree.ElementTree as ET

def parse_xml_for_emis_guids(xml_content):
    """Parse XML content and extract EMIS GUIDs from value elements."""
    try:
        root = ET.fromstring(xml_content)
        
        # Define namespaces
        namespaces = {
            'emis': 'http://www.e-mis.com/emisopen'
        }
        
        emis_guids = []
        
        # Find all valueSet elements
        for valueset in root.findall('.//emis:valueSet', namespaces):
            valueset_id = valueset.find('emis:id', namespaces)
            valueset_description = valueset.find('emis:description', namespaces)
            code_system = valueset.find('emis:codeSystem', namespaces)
            
            # Get valueSet metadata
            vs_id = valueset_id.text if valueset_id is not None else "N/A"
            vs_desc = valueset_description.text if valueset_description is not None else "N/A"
            vs_system = code_system.text if code_system is not None else "N/A"
            
            # Look for context information (table and column) - first try within valueSet
            table_elem = valueset.find('.//emis:table', namespaces)
            column_elem = valueset.find('.//emis:column', namespaces)
            
            # If not found within valueSet, look in parent elements (for pseudo-refsets)
            if table_elem is None or column_elem is None:
                # Find the parent criterion that contains this valueSet
                parent_criterion = None
                for criterion in root.findall('.//emis:criterion', namespaces):
                    if valueset in criterion.iter():
                        parent_criterion = criterion
                        break
                
                if parent_criterion is not None:
                    if table_elem is None:
                        table_elem = parent_criterion.find('emis:table', namespaces)
                    if column_elem is None:
                        column_elem = parent_criterion.find('.//emis:column', namespaces)
            
            table_context = table_elem.text if table_elem is not None else None
            column_context = column_elem.text if column_elem is not None else None
            
            # Find all values elements within this valueSet
            for values in valueset.findall('.//emis:values', namespaces):
                # Get metadata that applies to all values in this set
                include_children_elem = values.find('emis:includeChildren', namespaces)
                include_children = include_children_elem.text if include_children_elem is not None else "false"
                
                is_refset_elem = values.find('emis:isRefset', namespaces)
                is_refset = is_refset_elem.text if is_refset_elem is not None else "false"
                
                # Check if this is a refset - if so, there's usually only one value
                is_refset_bool = is_refset.lower() == 'true'
                
                for value in values.findall('emis:value', namespaces):
                    emis_guid = value.text if value.text else "N/A"
                    
                    # For refsets, there's no displayName, use the valueSet description
                    if is_refset_bool:
                        xml_display_name = vs_desc  # Use valueSet description for refsets
                    else:
                        # Get displayName - could be child of value or sibling
                        display_name_elem = value.find('emis:displayName', namespaces)
                        if display_name_elem is None:
                            # Try finding displayName as sibling of value
                            display_name_elem = values.find('emis:displayName', namespaces)
                        
                        xml_display_name = display_name_elem.text if display_name_elem is not None else "N/A"
                    
                    emis_guids.append({
                        'valueSet_guid': vs_id,
                        'valueSet_description': vs_desc,
                        'code_system': vs_system,
                        'emis_guid': emis_guid,
                        'xml_display_name': xml_display_name,
                        'include_children': include_children.lower() == 'true',
                        'is_refset': is_refset_bool,
                        'table_context': table_context,
                        'column_context': column_context
                    })
        
        return emis_guids
        
    except ET.ParseError as e:
        raise Exception(f"XML parsing error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing XML: {str(e)}")

def is_pseudo_refset(identifier, valueset_description):
    """Detect if a valueSet is a pseudo-refset based on its description/identifier patterns."""
    # Check the identifier (could be GUID or description) for specific pseudo-refset patterns
    identifier_upper = identifier.upper() if identifier else ""
    
    # Known pseudo-refset patterns - these are identifiers for pseudo-refsets
    pseudo_refset_patterns = [
        'ASTTRT_COD',    # Asthma treatment codes
        'ASTRES_COD',    # Asthma register codes
        'AST_COD',       # Asthma codes
        # Add other known pseudo-refset identifiers here as needed
    ]
    
    # Check for exact matches with known pseudo-refset identifiers
    for pattern in pseudo_refset_patterns:
        if pattern in identifier_upper:
            return True
    
    # Check for general pattern: ends with _COD and looks like a refset identifier (not numeric)
    if identifier_upper.endswith('_COD') and not identifier_upper.replace('_', '').replace('COD', '').isdigit():
        return True
    
    return False

def get_medication_type_flag(code_system):
    """Determine medication type flag based on code system from XML."""
    code_system_upper = code_system.upper() if code_system else ""
    
    # Check for specific medication type flags in the code system
    if code_system_upper == 'SCT_CONST':
        return 'SCT_CONST (Constituent)'
    elif code_system_upper == 'SCT_DRGGRP':
        return 'SCT_DRGGRP (Drug Group)'
    elif code_system_upper == 'SCT_PREP':
        return 'SCT_PREP (Preparation)'
    else:
        return 'Standard Medication'

def is_medication_code_system(code_system, table_context=None, column_context=None):
    """Check if the code system indicates this is a medication, considering XML context."""
    code_system_upper = code_system.upper() if code_system else ""
    
    # Exclude internal EMIS system codes - these are never medications
    if code_system_upper == 'EMISINTERNAL':
        return False
    
    # First check explicit medication code systems
    if code_system_upper in ['SCT_CONST', 'SCT_DRGGRP', 'SCT_PREP']:
        return True
    
    # Check for medication context even if codeSystem is SNOMED_CONCEPT
    # Must be both medication table AND drug column (not status, date, etc.)
    if (table_context and column_context and 
        table_context.upper() in ['MEDICATION_ISSUES', 'MEDICATION_COURSES'] and 
        column_context.upper() == 'DRUGCODE'):
        return True
        
    return False

def is_clinical_code_system(code_system, table_context=None, column_context=None):
    """Check if the code system indicates this is a clinical code, considering XML context."""
    code_system_upper = code_system.upper() if code_system else ""
    
    # Exclude internal EMIS system codes - these are never clinical codes
    if code_system_upper == 'EMISINTERNAL':
        return False
    
    # If it's a medication context, it's not clinical
    if (table_context and column_context and 
        table_context.upper() in ['MEDICATION_ISSUES', 'MEDICATION_COURSES'] and 
        column_context.upper() == 'DRUGCODE'):
        return False
    
    # Otherwise, SNOMED_CONCEPT is clinical
    return code_system_upper == 'SNOMED_CONCEPT'