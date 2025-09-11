# EMIS XML to SNOMED Translator - Streamlit Version

A web application that translates EMIS XML files to SNOMED codes using CSV lookup tables. Perfect for enterprise environments where executables cannot be run.

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

### 1. Prepare Your Lookup Table
Create a CSV file with your EMIS GUID to SNOMED mappings:

```csv
EMIS_GUID,SNOMED_Code,SNOMED_Description
999010611000230105,49436004,Atrial fibrillation
999007971000230109,195080001,Atrial fibrillation resolved
```

**Required columns:**
- `EMIS_GUID`: The EMIS internal GUID (from XML `<value>` elements)
- `SNOMED_Code`: The actual SNOMED CT code
- `SNOMED_Description`: Human-readable SNOMED description

### 2. Use the Application

1. **Upload Lookup Table**: 
   - Use the sidebar to upload your CSV mapping file
   - Download the sample CSV template if needed

2. **Upload XML File**:
   - Upload your EMIS XML search definition file
   - Click "Process XML File"

3. **View Results**:
   - See translation statistics and success rate
   - Browse the results table (color-coded: green = found, red = not found)
   - Download results as CSV

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
- **No external calls**: All processing happens locally/in the app

### Enterprise Considerations
- No executable files to worry about
- Runs in standard web browser
- Can be deployed on internal networks
- CSV lookup tables can be version controlled

## 🎯 Features

- **📁 Dual File Upload**: XML files + CSV lookup tables
- **🔄 Real-time Processing**: Instant translation results
- **📊 Statistics Dashboard**: Success rates and counts
- **🎨 Color-coded Results**: Visual indication of mapping success
- **📥 CSV Export**: Download results with timestamps
- **📋 Sample Templates**: Download example CSV format
- **🔍 Data Preview**: View lookup table before processing

## 📈 Workflow

```mermaid
graph LR
    A[Upload CSV Lookup] --> B[Upload EMIS XML]
    B --> C[Extract EMIS GUIDs]
    C --> D[Lookup SNOMED Codes]
    D --> E[Display Results]
    E --> F[Export CSV]
```

## 🛠️ Technical Details

- **Framework**: Streamlit (pure Python web apps)
- **Dependencies**: Only `streamlit` and `pandas`
- **File Processing**: XML parsing with `xml.etree.ElementTree`
- **Data Handling**: Pandas DataFrames for efficient lookup
- **Deployment**: Cloud-ready, no database required

## 📝 Example Usage

1. Export your EMIS GUID → SNOMED mappings from Power BI to CSV
2. Upload the CSV to the Streamlit app
3. Upload any EMIS XML search file
4. Get instant translation results
5. Download as CSV for further analysis

Perfect for clinical teams who need a simple, secure, web-based solution!