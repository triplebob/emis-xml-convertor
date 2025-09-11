# 🏥 EMIS XML to SNOMED Code Translator

A comprehensive web application that translates EMIS XML files (which use an EMIS specific GUID placeholder) to their native SNOMED codes!
With advanced categorization of clinical codes, medications, refsets, and pseudo-refsets.

## ✨ Key Features

- **🧠 Advanced Classification**: Automatically categorizes codes as clinical, medications, refsets, or pseudo-refsets
- **💊 Medication Type Detection**: Identifies SCT_CONST (Constituent), SCT_DRGGRP (Drug Group), SCT_PREP (Preparation)
- **⚠️ Pseudo-Refset Handling**: Properly handles pseudo-refsets like ASTTRT_COD with context-aware medication classification
- **📊 Multi-Tab Interface**: Organized tabs for different code types with appropriate export options
- **🔍 Context-Aware Processing**: Considers XML table/column context (e.g., MEDICATION_ISSUES + DRUGCODE)
- **📈 Comprehensive Statistics**: Detailed counts and success rates for all categories
- **🎨 Color-Coded Results**: Visual indicators for mapping success and code types

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- CSV lookup table with EMIS GUID to SNOMED mappings

### Installation
```bash
git clone <repository-url>
cd emis-xml-translator
pip install -r requirements.txt
```

### Running Locally
```bash
streamlit run streamlit_app.py
```
Open browser to: `http://localhost:8501`


## 📊 Lookup Table

The application uses a fork of the EMIS internal GUID to SNOMED mapping database, automatically loaded from a private repository. This ensures:

- **Always up-to-date**: Latest mappings are loaded automatically
- **No manual uploads**: Ready to use immediately  
- **Comprehensive coverage**: Thousands of pre-mapped clinical codes and medications

The lookup table contains:
- **Clinical codes**: General SNOMED clinical concepts
- **Medication codes**: Drug preparations, constituents, and groups
- **Source classifications**: Automatic categorization by type

## 📖 How to Use

### 1. Automatic Setup
- The app automatically loads the latest EMIS GUID to SNOMED lookup table
- No manual uploads required - everything is ready to use
- View lookup table status and preview key stats in the sidebar

### 2. Upload & Process XML
- Upload your EMIS XML search definition file
- Click "Process XML File" to begin translation
- View real-time processing statistics

### 3. Explore Results by Category

#### 📋 Summary Tab
- Overview statistics for all categories
- Success rates and mapping counts
- Pseudo-refset detection alerts

#### 🏥 Clinical Codes Tab
- **Standalone Clinical**: Direct SNOMED clinical codes (exportable)
- **Clinical in Pseudo-Refsets**: Display only, not directly usable

#### 💊 Medications Tab  
- **Standalone Medications**: Direct medication codes (exportable)
- **Medications in Pseudo-Refsets**: Display only, use members instead
- **Type Flags**: SCT_CONST, SCT_DRGGRP, SCT_PREP identification

#### 📊 Refsets Tab
- True SNOMED refsets that can be referenced directly

#### ⚠️ Pseudo-Refsets Tab
- Containers like ASTTRT_COD that cannot be used directly
- Must use individual member codes instead

#### 📝 Pseudo-Refset Members Tab
- Individual codes from pseudo-refsets (exportable)
- The actual usable codes from pseudo-refsets

## 🧠 Advanced Classification Logic

### Code System Detection
- **SCT_CONST**: SNOMED Constituent substances
- **SCT_DRGGRP**: SNOMED Drug Groups  
- **SCT_PREP**: SNOMED Preparations
- **SNOMED_CONCEPT**: SNOMED clinical code concepts

### Context-Aware Processing
The app considers XML structure context:
```xml
<table>MEDICATION_ISSUES</table>
<column>DRUGCODE</column>
<codeSystem>SNOMED_CONCEPT</codeSystem>
```
Even with `SNOMED_CONCEPT`, codes are classified as medications when in medication context.

## 📁 File Structure

```
emis-xml-translator/
├── streamlit_app.py           # Main Streamlit application
├── requirements.txt           # Python dependencies
├── README.md                 # This documentation
└── README_STREAMLIT.md       # Streamlit-specific guide
```

## 🔧 Troubleshooting

### Lookup Table Issues
- **Loading Errors**: Check internet connection for automatic table loading
- **Outdated Data**: App automatically loads latest version with 1-hour cache

### Classification Issues
- **Missing Medications**: Check if pseudo-refset members are in the Members tab
- **Wrong Categories**: Verify XML structure and context elements
- **Empty Results**: Ensure EMIS GUIDs in XML match lookup table format

### Performance
- **Large Files**: Processing 1000+ codes may take 10-30 seconds
- **Memory**: Very large XML files (>1k codes) may impact performance

## 🔒 Security & Privacy

- **No Data Storage**: All processing happens in memory
- **Session-Based**: Results cleared when browser closed  
- **Local Processing**: No external API calls or data transmission
- **Enterprise-Friendly**: No executables, runs in standard browser
- **GDPR Compliant**: No persistent storage of clinical data

## 📊 Use Cases

### Clinical Quality Improvement
- Extract codes from EMIS search definitions
- Map to SNOMED for standardized reporting
- Identify pseudo-refsets requiring member code lists

### Data Migration
- Translate legacy EMIS searches to SNOMED
- Generate code lists for new systems
- Validate mapping completeness

### Audit & Compliance  
- Document search criteria with SNOMED codes
- Create audit trails for clinical searches
- Ensure terminology standards compliance

---

**Built for healthcare teams who need reliable, secure EMIS to SNOMED translation** 🏥