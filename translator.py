from xml_utils import is_pseudo_refset, get_medication_type_flag, is_medication_code_system, is_clinical_code_system
from lookup import create_lookup_dictionaries

def translate_emis_guids_to_snomed(emis_guids, lookup_df, emis_guid_col, snomed_code_col):
    """Translate EMIS GUIDs to SNOMED codes using lookup DataFrame."""
    # Create lookup dictionaries for faster lookups
    guid_to_snomed_dict, snomed_to_info_dict = create_lookup_dictionaries(lookup_df, emis_guid_col, snomed_code_col)
    
    # First pass: identify pseudo-refset containers and group codes by valueSet
    valueset_groups = {}  # Group codes by valueSet GUID
    pseudo_refset_valuesets = set()  # Track which valueSets are pseudo-refsets
    
    for guid_info in emis_guids:
        valueset_guid = guid_info['valueSet_guid']
        emis_guid = guid_info['emis_guid']
        
        # Group all codes by their valueSet
        if valueset_guid not in valueset_groups:
            valueset_groups[valueset_guid] = {
                'info': guid_info,  # Store valueSet info
                'codes': []
            }
        valueset_groups[valueset_guid]['codes'].append(guid_info)
        
        # Check if the valueSet itself is a pseudo-refset based on its description
        # Look for pseudo-refset patterns in the valueSet description (like "ASTTRT_COD")
        valueset_description = guid_info['valueSet_description']
        if (not guid_info['is_refset'] and 
            valueset_description and
            is_pseudo_refset(valueset_description, valueset_description)):
            pseudo_refset_valuesets.add(valueset_guid)
    
    # Separate results by type
    clinical_codes = []  # Standalone clinical codes
    medications = []     # Standalone medications
    clinical_pseudo_members = []  # Clinical codes that are part of pseudo-refsets
    medication_pseudo_members = []  # Medications that are part of pseudo-refsets
    refsets = []
    pseudo_refsets = []  # Containers for pseudo-refsets
    pseudo_refset_members = {}  # Members of each pseudo-refset (for detailed view)
    
    # Track which refsets we've already added to avoid duplicates
    added_refset_guids = set()
    
    # Track unique codes to avoid duplicates in all categories
    unique_clinical_codes = {}  # key: emis_guid, value: code_info
    unique_medications = {}     # key: emis_guid, value: code_info
    unique_clinical_pseudo = {} # key: emis_guid, value: code_info
    unique_medication_pseudo = {} # key: emis_guid, value: code_info
    
    # Create pseudo-refset containers first
    for valueset_guid in pseudo_refset_valuesets:
        valueset_info = valueset_groups[valueset_guid]['info']
        # Count unique member codes (avoid counting duplicates)
        unique_member_codes = set()
        for code_info in valueset_groups[valueset_guid]['codes']:
            unique_member_codes.add(code_info['emis_guid'])
        
        pseudo_refsets.append({
            'ValueSet GUID': valueset_guid,
            'ValueSet Description': valueset_info['valueSet_description'],
            'Code System': valueset_info['code_system'],
            'Type': 'Pseudo-Refset',
            'Usage': '⚠️ Can only be used by listing member codes, not by SNOMED code reference',
            'Status': 'Not in EMIS database - requires member code listing',
            'Member Count': len(unique_member_codes)
        })
        
        # Initialize member dict for this pseudo-refset (for deduplication)
        pseudo_refset_members[valueset_guid] = {}
    
    # Process all individual codes
    for guid_info in emis_guids:
        emis_guid = guid_info['emis_guid']
        is_refset = guid_info['is_refset']
        valueset_guid = guid_info['valueSet_guid']
        
        # For true refsets, the emis_guid IS the SNOMED code
        if is_refset:
            # Only add this refset if we haven't already added it
            if valueset_guid not in added_refset_guids:
                snomed_code = emis_guid
                
                # Try to get additional info from lookup table
                if snomed_code in snomed_to_info_dict:
                    source_info = snomed_to_info_dict[snomed_code]
                    refset_source_type = source_info['source_type']
                else:
                    refset_source_type = 'Refset'
                
                refsets.append({
                    'ValueSet GUID': valueset_guid,
                    'ValueSet Description': guid_info['valueSet_description'], 
                    'Code System': guid_info['code_system'],
                    'SNOMED Code': snomed_code,
                    'SNOMED Description': guid_info['valueSet_description'],
                    'Type': 'True Refset',
                    'Source Type': refset_source_type,
                    'Usage': 'Can be referenced directly by SNOMED code in EMIS'
                })
                
                # Mark this refset as already added
                added_refset_guids.add(valueset_guid)
            continue
        
        # For regular codes, check if they belong to a pseudo-refset
        if valueset_guid in pseudo_refset_valuesets:
            # This code is a member of a pseudo-refset
            if emis_guid in guid_to_snomed_dict:
                mapping = guid_to_snomed_dict[emis_guid]
                snomed_code = mapping['snomed_code']
                source_type = mapping['source_type']
                has_qualifier = mapping.get('has_qualifier', 'Unknown')
                is_parent = mapping.get('is_parent', 'Unknown')
                descendants = mapping.get('descendants', '0')
                code_type = mapping.get('code_type', 'Unknown')
                mapping_found = True
            else:
                snomed_code = 'Not Found'
                source_type = 'Unknown'
                has_qualifier = 'Unknown'
                is_parent = 'Unknown'
                descendants = '0'
                code_type = 'Unknown'
                mapping_found = False
            
            # Always use XML display name for description (whether found or not)
            description = guid_info['xml_display_name']
            if description == "N/A" or not description:
                description = "No display name in XML"
            
            # Create the base member record
            member_record = {
                'ValueSet GUID': valueset_guid,
                'ValueSet Description': guid_info['valueSet_description'],
                'EMIS GUID': emis_guid,
                'SNOMED Code': snomed_code,
                'SNOMED Description': description,
                'Mapping Found': 'Found' if mapping_found else 'Not Found',
                'Pseudo-Refset Member': 'Yes'
            }
            
            # Add to pseudo-refset members (for detailed view) - deduplicate by emis_guid
            detailed_member = member_record.copy()
            detailed_member['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
            pseudo_refset_members[valueset_guid][emis_guid] = detailed_member
            
            # Also add to appropriate category list for display in main tabs
            code_system = guid_info['code_system']
            table_context = guid_info.get('table_context')
            column_context = guid_info.get('column_context')
            
            # Use XML codeSystem and context as primary indicator of type
            if is_medication_code_system(code_system, table_context, column_context):
                member_record['Medication Type'] = get_medication_type_flag(code_system)
                # Add to unique medications pseudo dict (deduplicate by emis_guid)
                unique_medication_pseudo[emis_guid] = member_record
            elif is_clinical_code_system(code_system, table_context, column_context):
                member_record['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
                member_record['Has Qualifier'] = has_qualifier
                member_record['Is Parent'] = is_parent
                member_record['Descendants'] = descendants
                member_record['Code Type'] = code_type
                # Add to unique clinical pseudo dict (deduplicate by emis_guid)
                unique_clinical_pseudo[emis_guid] = member_record
            else:
                # Skip EMIS internal codes entirely - they're not medical codes
                if code_system.upper() == 'EMISINTERNAL':
                    continue  # Skip this pseudo-refset member entirely
                
                # Fall back to lookup table source type for unknown code systems
                if source_type in ['Medication', 'Constituent', 'DM+D']:
                    member_record['Medication Type'] = 'Standard Medication'
                    unique_medication_pseudo[emis_guid] = member_record
                else:
                    member_record['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
                    member_record['Has Qualifier'] = has_qualifier
                    member_record['Is Parent'] = is_parent
                    member_record['Descendants'] = descendants
                    member_record['Code Type'] = code_type
                    unique_clinical_pseudo[emis_guid] = member_record
            
            continue  # Don't add to standalone codes
        
        # For standalone codes (not in pseudo-refsets)
        else:
            if emis_guid in guid_to_snomed_dict:
                mapping = guid_to_snomed_dict[emis_guid]
                snomed_code = mapping['snomed_code']
                source_type = mapping['source_type']
                has_qualifier = mapping.get('has_qualifier', 'Unknown')
                is_parent = mapping.get('is_parent', 'Unknown')
                descendants = mapping.get('descendants', '0')
                code_type = mapping.get('code_type', 'Unknown')
                mapping_found = True
            else:
                snomed_code = 'Not Found'
                source_type = 'Unknown'
                has_qualifier = 'Unknown'
                is_parent = 'Unknown'
                descendants = '0'
                code_type = 'Unknown'
                mapping_found = False
            
            # Always use XML display name for description (whether found or not)
            description = guid_info['xml_display_name']
            if description == "N/A" or not description:
                description = "No display name in XML"
            
            result = {
                'ValueSet GUID': valueset_guid,
                'ValueSet Description': guid_info['valueSet_description'],
                'Code System': guid_info['code_system'],
                'EMIS GUID': emis_guid,
                'SNOMED Code': snomed_code,
                'SNOMED Description': description,
                'Mapping Found': 'Found' if mapping_found else 'Not Found',
                'Pseudo-Refset Member': 'No',
                'Table Context': guid_info.get('table_context', 'N/A'),
                'Column Context': guid_info.get('column_context', 'N/A')
            }
            
            # Classify as clinical or medication based on XML codeSystem and context
            code_system = guid_info['code_system']
            table_context = guid_info.get('table_context')
            column_context = guid_info.get('column_context')
            
            # Use XML codeSystem and context as primary indicator of type
            if is_medication_code_system(code_system, table_context, column_context):
                result['Medication Type'] = get_medication_type_flag(code_system)
                # Add to unique medications dict (deduplicate by emis_guid)
                # Always prioritize medication context - remove from clinical if it exists there
                if emis_guid in unique_clinical_codes:
                    del unique_clinical_codes[emis_guid]
                unique_medications[emis_guid] = result
            elif is_clinical_code_system(code_system, table_context, column_context):
                result['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
                result['Has Qualifier'] = has_qualifier
                result['Is Parent'] = is_parent
                result['Descendants'] = descendants
                result['Code Type'] = code_type
                # Only add to clinical if it's not already in medications (medication context takes priority)
                if emis_guid not in unique_medications:
                    unique_clinical_codes[emis_guid] = result
            else:
                # Skip EMIS internal codes entirely - they're not medical codes
                if code_system.upper() == 'EMISINTERNAL':
                    continue  # Skip this code entirely
                
                # Fall back to lookup table source type for unknown code systems
                if source_type in ['Medication', 'Constituent', 'DM+D']:
                    result['Medication Type'] = 'Standard Medication'
                    # Remove from clinical if it exists there
                    if emis_guid in unique_clinical_codes:
                        del unique_clinical_codes[emis_guid]
                    unique_medications[emis_guid] = result
                else:
                    result['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
                    result['Has Qualifier'] = has_qualifier
                    result['Is Parent'] = is_parent
                    result['Descendants'] = descendants
                    result['Code Type'] = code_type
                    # Only add to clinical if it's not already in medications
                    if emis_guid not in unique_medications:
                        unique_clinical_codes[emis_guid] = result
    
    # Convert dictionaries back to lists (now deduplicated)
    clinical_codes = list(unique_clinical_codes.values())
    medications = list(unique_medications.values())
    clinical_pseudo_members = list(unique_clinical_pseudo.values())
    medication_pseudo_members = list(unique_medication_pseudo.values())
    
    # Convert pseudo_refset_members dictionaries to lists
    deduplicated_pseudo_refset_members = {}
    for valueset_guid, members_dict in pseudo_refset_members.items():
        deduplicated_pseudo_refset_members[valueset_guid] = list(members_dict.values())
    
    return {
        'clinical': clinical_codes,
        'medications': medications,
        'clinical_pseudo_members': clinical_pseudo_members,
        'medication_pseudo_members': medication_pseudo_members,
        'refsets': refsets,
        'pseudo_refsets': pseudo_refsets,
        'pseudo_refset_members': deduplicated_pseudo_refset_members
    }