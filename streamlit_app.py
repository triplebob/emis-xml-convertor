import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
from datetime import datetime
from github_loader import GitHubLookupLoader

# Page configuration
st.set_page_config(
    page_title="EMIS XML to SNOMED Translator",
    page_icon="🏥",
    layout="wide"
)

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
    
    # First check explicit medication code systems
    if code_system_upper in ['SCT_CONST', 'SCT_DRGGRP', 'SCT_PREP']:
        return True
    
    # Check for medication context even if codeSystem is SNOMED_CONCEPT
    if (table_context and column_context and 
        table_context.upper() in ['MEDICATION_ISSUES', 'MEDICATION_COURSES'] and 
        column_context.upper() == 'DRUGCODE'):
        return True
        
    return False

def is_clinical_code_system(code_system, table_context=None, column_context=None):
    """Check if the code system indicates this is a clinical code, considering XML context."""
    code_system_upper = code_system.upper() if code_system else ""
    
    # If it's a medication context, it's not clinical
    if (table_context and column_context and 
        table_context.upper() in ['MEDICATION_ISSUES', 'MEDICATION_COURSES'] and 
        column_context.upper() == 'DRUGCODE'):
        return False
    
    # Otherwise, SNOMED_CONCEPT is clinical
    return code_system_upper == 'SNOMED_CONCEPT'

def translate_emis_guids_to_snomed(emis_guids, lookup_df, emis_guid_col, snomed_code_col):
    """Translate EMIS GUIDs to SNOMED codes using lookup DataFrame."""
    # Convert lookup_df to dict for faster lookups
    # GUID -> SNOMED mapping for clinical codes and medications
    guid_to_snomed_dict = {}
    # SNOMED -> SNOMED mapping for refsets (to get descriptions)
    snomed_to_info_dict = {}
    
    if lookup_df is not None and not lookup_df.empty:
        for _, row in lookup_df.iterrows():
            code_id = str(row.get(emis_guid_col, '')).strip()  # This is the EMIS GUID
            concept_id = str(row.get(snomed_code_col, '')).strip()  # This is the SNOMED code
            source_type = str(row.get('Source_Type', 'Unknown')).strip()
            
            if code_id and code_id != 'nan' and concept_id and concept_id != 'nan':
                # For GUID lookup (clinical codes and medications)
                guid_to_snomed_dict[code_id] = {
                    'snomed_code': concept_id,
                    'source_type': source_type
                }
                
                # For SNOMED lookup (refsets) - map SNOMED code back to itself with source info
                snomed_to_info_dict[concept_id] = {
                    'snomed_code': concept_id,
                    'source_type': source_type
                }
    
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
                mapping_found = True
            else:
                snomed_code = 'Not Found'
                source_type = 'Unknown'
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
                # Add to unique clinical pseudo dict (deduplicate by emis_guid)
                unique_clinical_pseudo[emis_guid] = member_record
            else:
                # Fall back to lookup table source type for unknown code systems
                if source_type in ['Medication', 'Constituent', 'DM+D']:
                    member_record['Medication Type'] = 'Standard Medication'
                    unique_medication_pseudo[emis_guid] = member_record
                else:
                    member_record['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
                    unique_clinical_pseudo[emis_guid] = member_record
            
            continue  # Don't add to standalone codes
        
        # For standalone codes (not in pseudo-refsets)
        else:
            if emis_guid in guid_to_snomed_dict:
                mapping = guid_to_snomed_dict[emis_guid]
                snomed_code = mapping['snomed_code']
                source_type = mapping['source_type']
                mapping_found = True
            else:
                snomed_code = 'Not Found'
                source_type = 'Unknown'
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
                'Pseudo-Refset Member': 'No'
            }
            
            # Classify as clinical or medication based on XML codeSystem and context
            code_system = guid_info['code_system']
            table_context = guid_info.get('table_context')
            column_context = guid_info.get('column_context')
            
            # Use XML codeSystem and context as primary indicator of type
            if is_medication_code_system(code_system, table_context, column_context):
                result['Medication Type'] = get_medication_type_flag(code_system)
                # Add to unique medications dict (deduplicate by emis_guid)
                unique_medications[emis_guid] = result
            elif is_clinical_code_system(code_system, table_context, column_context):
                result['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
                # Add to unique clinical codes dict (deduplicate by emis_guid)
                unique_clinical_codes[emis_guid] = result
            else:
                # Fall back to lookup table source type for unknown code systems
                if source_type in ['Medication', 'Constituent', 'DM+D']:
                    result['Medication Type'] = 'Standard Medication'
                    unique_medications[emis_guid] = result
                else:
                    result['Include Children'] = 'Yes' if guid_info['include_children'] else 'No'
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

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_lookup_table():
    """Load the lookup table using the GitHubLookupLoader class."""
    try:
        # Get secrets from Streamlit configuration
        url = st.secrets["LOOKUP_TABLE_URL"]
        token = st.secrets["GITHUB_TOKEN"]
        expiry_date = st.secrets.get("TOKEN_EXPIRY", "2025-12-31")  # Default expiry if not set
        
        # Create loader instance
        loader = GitHubLookupLoader(token=token, lookup_url=url, expiry_date=expiry_date)
        
        # Check token health and show warnings if needed
        is_healthy, status = loader.get_token_health_status()
        if not is_healthy:
            st.warning(f"⚠️ Token Issue: {status}")
        elif "expires soon" in status.lower():
            st.info(f"📅 Token Status: {status}")
        
        # Load the lookup table
        return loader.load_lookup_table()
        
    except KeyError as e:
        raise Exception(f"Required secret not found: {e}. Please configure in Streamlit Cloud settings.")
    except Exception as e:
        raise Exception(f"Error loading lookup table: {str(e)}")


# Main app
def main():
    st.title("🏥 EMIS XML to SNOMED Code Translator")
    st.markdown("Upload EMIS XML files and translate internal GUIDs to SNOMED codes using the latest MKB lookup table.")
    
    # Load lookup table automatically
    with st.sidebar:
        st.header("📋 Lookup Table Status")
        st.markdown("Using the latest MKB EMIS GUID to SNOMED mapping table.")
        
        with st.spinner("Loading lookup table..."):
            try:
                lookup_df, emis_guid_col, snomed_code_col = load_lookup_table()
                
                # Calculate clinical vs medication breakdown
                if 'Source_Type' in lookup_df.columns:
                    clinical_count = len(lookup_df[lookup_df['Source_Type'] == 'Clinical'])
                    medication_count = len(lookup_df[lookup_df['Source_Type'].isin(['Medication', 'Constituent', 'DM+D'])])
                    other_count = len(lookup_df) - clinical_count - medication_count
                    
                    st.success(f"✅ Lookup table loaded: {len(lookup_df):,} total mappings")
                    st.info(f"🏥 Clinical: {clinical_count:,} | 💊 Medications: {medication_count:,}")
                    
                    if other_count > 0:
                        st.info(f"📊 Other types: {other_count:,}")
                else:
                    st.success(f"✅ Lookup table loaded: {len(lookup_df):,} mappings")
                    
                # Store in session state for later use
                st.session_state.lookup_df = lookup_df
                st.session_state.emis_guid_col = emis_guid_col
                st.session_state.snomed_code_col = snomed_code_col
                
            except Exception as e:
                st.error(f"❌ Error loading lookup table: {str(e)}")
                st.stop()
    
    # Get lookup table from session state
    lookup_df = st.session_state.get('lookup_df')
    emis_guid_col = st.session_state.get('emis_guid_col')
    snomed_code_col = st.session_state.get('snomed_code_col')
    
    # Main content area
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📁 Upload XML File")
        uploaded_xml = st.file_uploader(
            "Choose EMIS XML file",
            type=['xml'],
            help="Select an EMIS clinical search XML file"
        )
        
        if uploaded_xml is not None:
            if st.button("🔄 Process XML File", type="primary"):
                with st.spinner("Processing XML and translating GUIDs..."):
                    try:
                        # Read and parse XML
                        xml_content = uploaded_xml.read().decode('utf-8')
                        emis_guids = parse_xml_for_emis_guids(xml_content)
                        
                        if not emis_guids:
                            st.error("No EMIS GUIDs found in the XML file")
                            st.stop()
                        
                        # Translate to SNOMED codes
                        translated_codes = translate_emis_guids_to_snomed(
                            emis_guids, 
                            lookup_df, 
                            emis_guid_col, 
                            snomed_code_col
                        )
                        
                        # Store results in session state
                        st.session_state.results = translated_codes
                        st.session_state.xml_filename = uploaded_xml.name
                        
                        # Count all items
                        standalone_clinical = len(translated_codes['clinical'])
                        standalone_medications = len(translated_codes['medications'])
                        clinical_pseudo = len(translated_codes['clinical_pseudo_members'])
                        medication_pseudo = len(translated_codes['medication_pseudo_members'])
                        refsets = len(translated_codes['refsets'])
                        pseudo_refsets = len(translated_codes['pseudo_refsets'])
                        
                        total_items = standalone_clinical + standalone_medications + clinical_pseudo + medication_pseudo + refsets + pseudo_refsets
                        st.success(f"✅ Processed {total_items} items: {standalone_clinical} standalone clinical, {standalone_medications} standalone medications, {clinical_pseudo} clinical in pseudo-refsets, {medication_pseudo} medications in pseudo-refsets, {refsets} refsets, {pseudo_refsets} pseudo-refsets")
                        
                    except Exception as e:
                        st.error(f"Error processing XML: {str(e)}")
        
        else:
            st.info("📤 Upload an XML file to begin processing")
    
    with col2:
        st.header("📊 Results")
        
        if 'results' in st.session_state:
            results = st.session_state.results
            
            # Create tabs for different types
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Summary", "🏥 Clinical Codes", "💊 Medications", "📊 Refsets", "⚠️ Pseudo-Refsets", "📝 Pseudo-Refset Members"])
            
            with tab1:
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
            
            with tab2:
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
                    st.dataframe(styled_clinical, width='stretch')
                    
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
                    st.dataframe(styled_pseudo_clinical, width='stretch')
                else:
                    st.success("✅ No clinical codes found in pseudo-refsets")
            
            with tab3:
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
                    st.dataframe(styled_medications, width='stretch')
                    
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
                    st.dataframe(styled_pseudo_medications, width='stretch')
                else:
                    st.success("✅ No medications found in pseudo-refsets")
            
            with tab4:
                st.subheader("Refsets")
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
            
            with tab5:
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
            
            with tab6:
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
            
        else:
            st.info("Results will appear here after processing an XML file")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
        <p>EMIS XML to SNOMED Code Translator | Upload XML files to translate into SNOMED clinical codes</p>
        <p style='font-size: 0.8em; margin-top: 10px;'>
        EMIS and EMIS Web are trademarks of Optum Inc. This application is not affiliated with, 
        endorsed by, or sponsored by Optum Inc or any of its subsidiaries.
        </p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()