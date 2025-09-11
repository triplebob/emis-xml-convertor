import streamlit as st
from util_modules.github_loader import GitHubLookupLoader

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
        
        # Load the lookup table with version info
        return loader.load_lookup_table()
        
    except KeyError as e:
        raise Exception(f"Required secret not found: {e}. Please configure in Streamlit Cloud settings.")
    except Exception as e:
        raise Exception(f"Error loading lookup table: {str(e)}")

def get_lookup_statistics(lookup_df):
    """Calculate statistics about the lookup table."""
    if lookup_df is None or lookup_df.empty:
        return {
            'total_count': 0,
            'clinical_count': 0,
            'medication_count': 0,
            'other_count': 0
        }
    
    total_count = len(lookup_df)
    
    if 'Source_Type' in lookup_df.columns:
        clinical_count = len(lookup_df[lookup_df['Source_Type'] == 'Clinical'])
        medication_count = len(lookup_df[lookup_df['Source_Type'].isin(['Medication', 'Constituent', 'DM+D'])])
        other_count = total_count - clinical_count - medication_count
    else:
        clinical_count = 0
        medication_count = 0
        other_count = 0
    
    return {
        'total_count': total_count,
        'clinical_count': clinical_count,
        'medication_count': medication_count,
        'other_count': other_count
    }

def create_lookup_dictionaries(lookup_df, emis_guid_col, snomed_code_col):
    """Create lookup dictionaries for faster GUID to SNOMED translation."""
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
                # Extract additional lookup table information
                has_qualifier = str(row.get('HasQualifier', 'Unknown')).strip()
                is_parent = str(row.get('IsParent', 'Unknown')).strip()
                descendants = str(row.get('Descendants', '0')).strip()
                code_type = str(row.get('CodeType', 'Unknown')).strip()
                
                # For GUID lookup (clinical codes and medications)
                guid_to_snomed_dict[code_id] = {
                    'snomed_code': concept_id,
                    'source_type': source_type,
                    'has_qualifier': has_qualifier,
                    'is_parent': is_parent,
                    'descendants': descendants,
                    'code_type': code_type
                }
                
                # For SNOMED lookup (refsets) - map SNOMED code back to itself with source info
                snomed_to_info_dict[concept_id] = {
                    'snomed_code': concept_id,
                    'source_type': source_type,
                    'has_qualifier': has_qualifier,
                    'is_parent': is_parent,
                    'descendants': descendants,
                    'code_type': code_type
                }
    
    return guid_to_snomed_dict, snomed_to_info_dict