# EMIS XML to SNOMED Translator - Streamlit Version

A web application that translates EMIS XML files (which use an EMIS specific GUID placeholder) to their native SNOMED codes! Perfect for enterprise environments where executables cannot be run.

## 🚀 Live Demo

**Deploy to Streamlit Cloud**: [streamlit.app](https://share.streamlit.io/)

## 🏗️ Local Development

### Prerequisites
- Python 3.8+

### Setup
```bash
pip install -r requirements_streamlit.txt
streamlit run streamlit_app.py
```

## 📋 How to Use

### 1. Automatic Setup
- The app automatically loads a fork of the EMIS internal GUID to SNOMED lookup table
- No manual uploads required - everything is ready to use
- View lookup table status and key statistics in the sidebar

### 2. Upload & Process XML
- Upload your EMIS XML search definition file
- Click "Process XML File" to begin translation
- View real-time processing statistics

### 3. Explore Results by Category
- **📋 Summary Tab**: Overview statistics and success rates
- **🏥 Clinical Codes**: Standalone clinical codes (exportable)
- **💊 Medications**: Standalone medications with type flags (exportable)
- **📊 Refsets**: True SNOMED refsets
- **⚠️ Pseudo-Refsets**: Containers that require member code listings
- **📝 Members**: Individual codes from pseudo-refsets (exportable)

## 🌐 Deployment Options

### Option 1: Streamlit Cloud (Recommended)
1. Push code to GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Connect your GitHub repo
4. Deploy with one click
5. Share the public URL with your team

### Option 2: Streamlit Community Cloud
1. Fork this repository
2. Sign up at [streamlit.app](https://streamlit.app/)
3. Deploy directly from GitHub
4. Free hosting for public apps

### Option 3: Local Network Deployment
```bash
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```
Access via: `http://your-computer-ip:8501`

## 🔒 Security & Privacy

### Data Processing
- **No data stored**: Files are processed in memory only
- **Session-based**: Results cleared when browser closed
- **Local processing**: No external API calls or data transmission
- **Enterprise-friendly**: No executables, runs in standard browser
- **GDPR compliant**: No persistent storage of clinical data

### Lookup Table
- **Secure access**: Fork of EMIS internal mappings via private repository
- **Automatic updates**: Latest mappings loaded with 1-hour cache
- **No manual uploads**: Eliminates data handling concerns

## 🎯 Features

- **🧠 Advanced Classification**: Automatically categorizes codes as clinical, medications, refsets, or pseudo-refsets
- **💊 Medication Type Detection**: Identifies SCT_CONST (Constituent), SCT_DRGGRP (Drug Group), SCT_PREP (Preparation)
- **⚠️ Pseudo-Refset Handling**: Properly handles pseudo-refsets like ASTTRT_COD with context-aware medication classification
- **📊 Multi-Tab Interface**: Organized tabs for different code types with appropriate export options
- **🔍 Context-Aware Processing**: Considers XML table/column context (e.g., MEDICATION_ISSUES + DRUGCODE)
- **📈 Comprehensive Statistics**: Detailed counts and success rates for all categories
- **🎨 Color-Coded Results**: Visual indicators for mapping success and code types

## 🛠️ Technical Details

- **Framework**: Streamlit (pure Python web apps)
- **Dependencies**: `streamlit`, `pandas`, `requests`, `pyarrow`
- **File Processing**: XML parsing with `xml.etree.ElementTree`
- **Data Handling**: Pandas DataFrames with Parquet optimization
- **Authentication**: Secure GitHub API access with token management
- **Deployment**: Cloud-ready, no database required

## 📝 Example Usage

1. Upload your EMIS XML search definition file
2. App automatically loads the latest GUID → SNOMED mappings
3. Get instant categorized translation results
4. Export standalone codes and pseudo-refset members as needed
5. Use appropriate codes based on type (direct codes vs member listings)

Perfect for clinical teams who need a comprehensive, secure, web-based solution!