# 🔧 The Unofficial EMIS XML Toolkit

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

## 🚀 Quick Start

### **Option 1: Use Live App (Recommended)**
**[🌐 Access Live Application](https://emis-xml-toolkit.streamlit.app/)** - No installation required

1. Upload your EMIS XML file
2. View comprehensive analysis across 5 specialized tabs
3. Export detailed reports in multiple formats
4. Navigate folder structures and analyze dependencies

### **Option 2: Run Locally**

#### Prerequisites
- Python 3.8+
- MKB lookup table with EMIS GUID to SNOMED mappings

#### Installation
```bash
git clone https://github.com/triplebob/emis-xml-convertor.git
cd emis-xml-convertor
pip install -r requirements.txt
```

#### Run Application
```bash
streamlit run streamlit_app.py
```

---

## 📁 Project Structure

```
emis-xml-convertor/
├── streamlit_app.py           # Main application entry point
├── xml_utils.py               # Core XML parsing and GUID extraction
├── requirements.txt           # Python dependencies
├── util_modules/              # Modular application architecture
│   ├── analysis/              # Analysis engines and orchestration
│   │   ├── xml_element_classifier.py    # Element type classification
│   │   ├── analysis_orchestrator.py     # Central analysis coordination
│   │   ├── search_analyzer.py           # Search logic analysis
│   │   ├── report_analyzer.py           # Report structure analysis
│   │   └── search_rule_visualizer.py    # Interactive rule displays
│   ├── xml_parsers/           # Modular XML parsing system
│   │   ├── namespace_handler.py         # Universal namespace handling
│   │   ├── base_parser.py               # Base parsing utilities
│   │   ├── criterion_parser.py          # Search criteria parsing
│   │   ├── report_parser.py             # Report structure parsing
│   │   └── value_set_parser.py          # Clinical code value sets
│   ├── core/                  # Business logic and classification
│   │   ├── translator.py                # GUID to SNOMED translation
│   │   ├── report_classifier.py         # EMIS report type classification
│   │   └── search_manager.py            # Search data management
│   ├── ui/                    # User interface components
│   │   ├── ui_tabs.py                   # 5-tab results interface
│   │   ├── status_bar.py                # Application status display
│   │   └── rendering_utils.py           # Standardized UI components
│   ├── export_handlers/       # Comprehensive export system
│   │   ├── search_export.py             # Search-specific exports
│   │   ├── report_export.py             # Report export handler
│   │   └── clinical_code_export.py      # Clinical code exports
│   ├── utils/                 # General utilities
│   │   ├── lookup.py                    # Lookup table management
│   │   └── audit.py                     # Processing statistics
│   └── common/                # Shared utilities and error handling
├── docs/                      # Technical documentation
│   ├── modules.md                       # Module architecture guide
│   ├── emis-xml-patterns.md             # EMIS XML pattern reference
│   └── namespace-handling.md            # Namespace handling guide
└── tests/                     # Test suite
```

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

## 📊 Use Cases

### **Clinical Governance**
- **QOF Indicator Analysis**: Quality and Outcomes Framework reporting
- **Clinical Pathway Review**: Analyze complex care pathways and protocols
- **Code Set Validation**: Verify SNOMED code usage and mapping accuracy
- **Search Logic Auditing**: Review and optimize clinical search criteria

### **System Administration**
- **EMIS Configuration Review**: Analyze search and report configurations
- **Folder Organization**: Review hierarchical folder structures
- **Dependency Mapping**: Understand search and report relationships
- **Performance Analysis**: Identify complex searches and optimization opportunities

### **Healthcare Analytics**
- **Population Analysis**: Understand search population logic and criteria
- **Report Structure Review**: Analyze List/Audit/Aggregate report configurations
- **Clinical Code Translation**: Convert EMIS codes to SNOMED for external systems
- **Quality Measurement**: Export data for external quality measurement tools

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

## 🤝 Contributing

### **Bug Reports**
Please report issues with detailed XML examples (anonymized) and steps to reproduce.

### **Feature Requests**
Enhancement suggestions welcome, particularly for new EMIS XML patterns or export formats.

### **Technical Documentation**
Contributions to technical documentation and pattern identification appreciated.

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