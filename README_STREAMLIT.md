# 🔧 The Unofficial EMIS XML Toolkit - Streamlit Version

A comprehensive web application for analyzing EMIS XML files with advanced search logic analysis, report structure visualization, and clinical code translation. 
Transform complex EMIS XML documents into actionable insights for healthcare teams.

## 🚀 **[Live Application](https://emis-xml-toolkit.streamlit.app/)**

**Ready to use immediately - no installation required.** Click the link above to access the live application.

*Comprehensive EMIS XML analysis and clinical code extraction for healthcare teams*

---

## ✨ Key Features

### 📊 **Complete 5-Tab Analysis Interface**
- **🔍 Clinical Codes**: Advanced SNOMED translation with refset support and dual-mode deduplication
- **⚙️ Search Analysis**: Rule Logic Browser with detailed criterion analysis and dependency visualization
- **📋 List Reports**: Column structure analysis with healthcare context and filter logic
- **📊 Audit Reports**: Multi-population analysis with organizational grouping and quality indicators  
- **📈 Aggregate Reports**: Statistical analysis with cross-tabulation

### 🔍 **Advanced XML Pattern Support**
- **baseCriteriaGroup**: Nested criterion logic within wrapper criteria
- **Linked Criteria**: Cross-table relationships with temporal constraints
- **SNOMED Refsets**: Direct code handling with clean description extraction
- **EMISINTERNAL Classifications**: Episode types, consultation headings, clinical status
- **Complex Restrictions**: "Latest N WHERE condition" with test attributes

### 📤 **Comprehensive Export System**
- **Multi-sheet Excel exports** with professional formatting
- **Type-specific report exports** for List/Audit/Aggregate reports
- **Smart filtering**: Export all codes, matched only, or unmatched only
- **Multiple formats**: Excel, CSV, JSON, and TXT reports
- **Source attribution**: Track codes to their originating searches/reports

### 🏗️ **Enterprise Features**
- **Hierarchical folder management** with multi-level navigation
- **Supports EMIS QOF indicators** and custom healthcare quality metrics
- **Multi-organization support** for EMIS Enterprise exports
- **Clinical pathway analysis** with workflow context
- **Version independence** across EMIS system versions

---

## 🏗️ Local Development

### Prerequisites
- Python 3.8+
- MKB lookup table with EMIS GUID to SNOMED mappings

### Setup
```bash
git clone https://github.com/triplebob/emis-xml-convertor.git
cd emis-xml-convertor
pip install -r requirements.txt
streamlit run streamlit_app.py
```

---

## 📋 How to Use

### 1. Automatic Setup
- The app automatically loads the EMIS internal GUID to SNOMED lookup table
- No manual uploads required - everything is ready to use
- View lookup table status and key statistics in the sidebar

### 2. Upload & Process XML
- Upload your EMIS XML search definition file
- Automatic processing begins immediately
- View comprehensive analysis across 5 specialized tabs

### 3. Analyze Results
- **Clinical Codes**: Browse SNOMED translations with advanced filtering
- **Search Analysis**: Navigate folder structures and analyze rule logic
- **List Reports**: Review column structures and filter criteria  
- **Audit Reports**: Examine multi-population analysis and quality indicators
- **Aggregate Reports**: Explore statistical analysis and cross-tabulation

### 4. Export Data
- Use export buttons on each tab for specialized data extraction
- Choose from multiple formats (Excel, CSV, JSON, TXT)
- Apply smart filtering (all codes, matched only, unmatched only)
- Download comprehensive reports with professional formatting

---

## 🎯 Supported EMIS XML Types

### **Search Reports**
- Population-based searches with complex criteria groups
- Rule logic analysis with AND/OR operators
- Population criteria and cross-search references
- Dependency visualization and execution flow

### **List Reports** 
- Multi-column data extraction with column-specific filtering
- Healthcare context classification (clinical data, appointments, demographics)
- Per-column search criteria and restrictions analysis
- Clinical code extraction from report filters

### **Audit Reports**
- Quality monitoring and compliance tracking
- Multi-population analysis with member search combinations
- Organizational grouping (practice codes, user authorization)
- Enhanced metadata with creation time and author information

### **Aggregate Reports**
- Statistical analysis and cross-tabulation
- Built-in filters and criteria analysis
- Healthcare metrics and quality measurement
- Enterprise reporting capabilities

---

## 🔬 Clinical Code Systems

### **SNOMED CT Support**
- **Concepts and Refsets**: Full SNOMED CT concept hierarchy
- **Direct Refset Handling**: NHS refsets processed as direct SNOMED codes
- **Legacy Read Codes**: Backward compatibility via mapping tables
- **Include Children**: Automatic descendant code inclusion

### **Medication Systems**
- **dm+d Codes**: Dictionary of medicines and devices
- **SCT_APPNAME**: Brand-specific medication names (Emerade, EpiPen, etc.)
- **SCT_CONST**: Constituent/generic drug names 
- **SCT_DRGGRP**: Drug group classifications

### **EMIS Internal Classifications**
- **Episode Types**: FIRST, NEW, REVIEW, ENDED, NONE
- **Consultation Headings**: PROBLEM, REVIEW, ISSUE
- **Clinical Status**: COMPLICATION, ONGOING, RESOLVED
- **User Authorization**: Active user and contract status filtering

---

## 🔧 Technical Specifications

### **Performance Optimizations**
- **Single XML Parse**: Eliminates redundant processing with element classification
- **Dictionary-based Lookups**: O(1) SNOMED translation (100x faster than DataFrame searches)
- **Smart Caching**: Session state management with intelligent invalidation
- **Progress Tracking**: Real-time feedback for large file processing

### **XML Processing**
- **Universal Namespace Handling**: Mixed namespaced/non-namespaced document support
- **Robust Error Handling**: Comprehensive exception management with graceful degradation
- **Memory Optimization**: Efficient processing of large XML files (40+ entities)
- **Cloud Compatibility**: Optimized for Streamlit Cloud deployment

### **Data Management**
- **Dual-mode Deduplication**: Unique codes vs per-source tracking
- **Session State Integration**: Persistent analysis across tab navigation
- **Export Filtering**: Conditional data inclusion based on user selection
- **Source Attribution**: Track clinical codes to originating searches/reports

### **Browser Compatibility**
- **Chrome/Edge**: Recommended (full feature support)
- **Firefox/Safari**: Supported (core functionality)
- **Mobile**: Limited support (view-only recommended)

---

## 🛡️ Security & Privacy

### **Data Handling**
- **No Data Storage**: XML files processed in memory only
- **Session-based Processing**: Data cleared when session ends
- **Client-side Processing**: SNOMED translation performed locally
- **No External Transmission**: Lookup tables cached locally

### **Compliance Considerations**
- **IG Toolkit Compatible**: Designed for NHS IG Toolkit compliance
- **GDPR Aligned**: No persistent data storage or tracking
- **Audit Trail**: Processing statistics available for governance
- **Version Transparency**: Lookup table versions clearly displayed

---

## ⚖️ Legal & Compliance

### **Disclaimer**
**EMIS and EMIS Web are trademarks of Optum Inc.** This unofficial toolkit is not affiliated with, endorsed by, or sponsored by Optum Inc, EMIS Health, or any of their subsidiaries. All trademarks are the property of their respective owners.

### **License**
This project is provided as-is for healthcare and research purposes. Users are responsible for ensuring compliance with local data protection and clinical governance requirements.

### **No Warranty**
This toolkit is provided without warranty of any kind. Healthcare professionals should validate all clinical code translations against authoritative sources before clinical use.

---

## 📞 Support

### **Documentation**
- **Technical Patterns**: [EMIS XML Patterns Reference](docs/emis-xml-patterns.md)
- **Architecture Guide**: [Module Architecture](docs/modules.md)
- **Namespace Handling**: [Namespace Documentation](docs/namespace-handling.md)

### **Live Application**
**🌐 [https://emis-xml-toolkit.streamlit.app/](https://emis-xml-toolkit.streamlit.app/)**

---

*Last Updated: October 2025*  
*Application Version: 2.0.0*  
*Live Application: https://emis-xml-toolkit.streamlit.app/*