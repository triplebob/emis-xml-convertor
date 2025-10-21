# Changelog

## v2.1.2 - Memory Optimization and Performance Fixes (October 2025)

### 🧠 **Memory Management Improvements**

**Lazy Export Generation:**
- **Clinical Code Tabs**: Converted all CSV export generation from automatic (on radio button change) to on-demand (button click only)
- **Search Analysis Tab**: Implemented lazy generation for rule analysis text exports to prevent memory consumption during tab rendering
- **Report Tabs**: Converted Excel and JSON export generation from immediate to button-triggered with memory cleanup
- **Immediate Cleanup**: Added garbage collection and object deletion after all export downloads to prevent memory accumulation

**Session-Based Caching:**
- **Sidebar Components**: Implemented `@st.cache_data` decorators for status bar content and version information to prevent re-rendering
- **Report Analysis**: Modified report tabs to use cached analysis data exclusively, eliminating reprocessing on dropdown selections
- **NHS Terminology Results**: Enhanced session-state caching for expansion results to prevent repeated API calls

### ⚡ **Performance Enhancements**

**Dropdown Optimization:**
- **Report Selection**: Eliminated complete file reprocessing when switching between report dropdowns
- **Search Selection**: Removed automatic export generation when selecting different searches in analysis tab
- **Clinical Filters**: Stopped CSV generation on every radio button change, reducing processing overhead by ~90%

**UI Responsiveness:**
- **Toast Message Elimination**: Resolved reprocessing loops that caused repeated toast notifications during dropdown interactions
- **Cached Analysis Usage**: All report and search tabs now use pre-computed analysis data instead of triggering expensive recalculation
- **Progress Indicators**: Added spinner components and success confirmations for export operations

### 🔧 **Bug Fixes**

**Import Resolution:**
- **Search Rule Visualizer**: Fixed missing imports causing application crashes (`filter_top_level_criteria`, `has_linked_criteria`)
- **Module Organization**: Consolidated scattered imports to proper top-level declarations in search analysis components
- **Function Dependencies**: Resolved SearchCriterion and related parser imports for proper rule visualization

**Export System Stability:**
- **Memory Leaks**: Fixed accumulation of large export objects in memory by implementing immediate cleanup after downloads
- **Button Functionality**: Restored proper export button behavior with lazy generation and progress feedback
- **Data Filtering**: Maintained export quality while reducing memory footprint through efficient data processing

### 📊 **Technical Improvements**

**Resource Management:**
- **Memory Cleanup**: Implemented systematic `del` and `gc.collect()` patterns after large data operations
- **Cache Efficiency**: Enhanced session state utilization to reduce redundant processing across UI interactions
- **Export Processing**: Optimized filtering and generation logic to minimize memory usage during CSV/Excel/JSON creation

**Architecture Optimization:**
- **Analysis Caching**: Enforced use of pre-computed analysis data across all tab components
- **State Management**: Improved session state handling to prevent unnecessary data regeneration
- **Component Isolation**: Separated export generation from UI rendering to improve responsiveness

---

### **Performance Impact**

**Memory Usage Reduction:**
- Export generation memory consumption reduced by approximately 80% through lazy loading
- Eliminated automatic generation of large Excel/JSON/CSV files during UI navigation
- Implemented immediate cleanup preventing memory accumulation across multiple operations

**UI Responsiveness:**
- Dropdown selections now execute instantly without reprocessing delays
- Removed toast message loops and unnecessary progress indicators during navigation
- Export operations provide clear feedback with progress spinners and completion confirmations

---

*Version 2.1.2 specifically addresses Streamlit Cloud 2.7GB memory constraints while maintaining full export functionality and improving overall application responsiveness.*

---

## v2.1.1 - Memory & Performance Optimization (October 2025)

### 🚀 **Threading Performance Enhancements**

**Adaptive Worker Scaling:**
- **Dynamic Threading**: Scales from 8-20 concurrent workers based on workload size (≤100: 8 workers, 101-300: 12 workers, 301-500: 16 workers, 501+: 20 workers)
- **Memory Management**: Prevents thread explosion that was creating thousands of workers instead of expected counts
- **Batched Processing**: Implements controlled worker batches to prevent memory overflow in large terminology expansions
- **Resource Optimization**: Balances performance with Streamlit Cloud's 2.7GB memory constraint

**Worker Thread Stabilization:**
- **Credential Passing**: Resolves authentication failures by passing NHS Terminology Server credentials explicitly to worker threads
- **Threading Orchestrator**: Implements pure worker thread pattern with main thread UI updates for Streamlit compatibility
- **Context Management**: Eliminates thousands of ThreadPoolExecutor "missing ScriptRunContext" warnings
- **Performance Monitoring**: Real-time progress tracking with concurrent worker count display

### 🧠 **Memory Management Optimization**

**Session-Based Caching:**
- **Expansion Result Caching**: Implements session-state caching to eliminate repeated NHS Terminology Server API calls
- **Cache Hit Statistics**: Displays cache hit/miss ratios during expansion operations (e.g., "✅ Using 130 cached results, fetching 1 new codes")
- **Immediate Reuse**: Second expansion clicks use cached data instead of re-querying terminology server
- **Memory Efficiency**: Reduces API load and improves response times for repeated operations

**Lookup Table Preservation:**
- **Complete Dataset Retention**: Maintains full 1.5M+ record EMIS lookup table without filtering
- **Cache-First Loading**: Preserves session state → local cache → GitHub cache → API fallback hierarchy
- **Garbage Collection**: Enhanced memory cleanup during large expansion operations
- **Streamlit Cloud Compliance**: Optimized for production deployment memory constraints

### 🔧 **Terminology Server Reliability Fixes**

**Worker Thread Compatibility:**
- **Caching Decorator Resolution**: Fixed conflicts between Streamlit's `@st.cache_data` and worker thread execution
- **Parameter Conflicts**: Resolved `_self` parameter issues that were causing "name '_self' is not defined" errors in worker threads
- **Success Rate Improvement**: Increased expansion success from 0/131 to 131/131 (100% success rate)
- **Error Handling**: Enhanced error reporting and status tracking for failed terminology server connections

**UI Stability:**
- **Loading Loop Elimination**: Resolved infinite "Running NHSTerminologyClient.expand_concept(...)" display loops
- **Progress Tracking**: Accurate real-time progress updates with worker status information
- **Connection Status**: Proper authentication status display and toast notifications
- **State Persistence**: Maintains expansion results across UI interactions and download operations

### 📊 **Enhanced User Experience**

**Performance Feedback:**
- **Cache Statistics**: Shows detailed cache hit/miss information during expansion operations
- **Worker Scaling Display**: Real-time indication of concurrent worker count based on workload size
- **Success Rate Monitoring**: Clear progress indicators with expansion success/failure tracking
- **Connection Notifications**: Toast alerts for successful NHS Terminology Server connections

**Production Readiness:**
- **Cloud Deployment Optimization**: Specifically tuned for Streamlit Cloud memory and threading constraints
- **Stability Improvements**: Comprehensive testing under high-volume terminology expansion scenarios
- **Error Recovery**: Graceful handling of network timeouts and terminology server unavailability
- **Backward Compatibility**: All existing workflows remain unchanged with performance benefits

### 🎯 **Technical Infrastructure**

**Architecture Improvements:**
- **Threading Orchestrator Pattern**: Separates pure API calls in worker threads from UI updates in main thread
- **Memory-Aware Processing**: Dynamic scaling based on available resources and workload characteristics
- **Session State Management**: Intelligent caching with automatic invalidation and memory cleanup
- **Error Boundaries**: Comprehensive exception handling with detailed logging for production debugging

**Performance Monitoring:**
- **Resource Tracking**: Monitor memory usage patterns during large expansion operations
- **Thread Lifecycle Management**: Proper thread cleanup and resource deallocation
- **API Rate Management**: Intelligent request pacing to prevent terminology server overload
- **Cache Efficiency Metrics**: Track cache performance and hit rates for optimization

---

### **Migration Notes**

**Automatic Improvements:**
- All memory and performance optimizations apply automatically to existing workflows
- No configuration changes required - improvements are transparent to users
- Enhanced performance while maintaining complete backward compatibility
- Existing NHS Terminology Server credentials continue to work without modification

**Performance Benefits:**
- Significantly reduced memory usage during large terminology expansions
- Faster response times through session-based result caching
- Improved stability under Streamlit Cloud production constraints
- Better resource utilization with adaptive worker scaling

---

*Version 2.1.1 addresses critical production deployment issues while significantly improving NHS Terminology Server expansion performance and reliability.*

---

## v2.1.0 - NHS Terminology Server Integration & Cache Architecture (October 2025)

### 🌳 **NHS England Terminology Server Integration**

**FHIR R4 API Integration:**
- **System-to-System Authentication**: OAuth2 integration with NHS England Terminology Server
- **SNOMED Code Expansion**: Automatic expansion of codes with `includechildren=True` flags
- **Hierarchical Discovery**: Retrieves all descendant concepts (children, grandchildren, etc.)
- **Individual Code Lookup**: Testing and validation functionality for specific concepts
- **Real-time Status Monitoring**: Connection status tracking with toast notifications

**EMIS Integration & Comparison:**
- **Lookup Table Mapping**: Maps expanded concepts to EMIS GUIDs using cached lookup table
- **Child Count Comparison**: Shows EMIS expected vs NHS Terminology Server actual child counts
- **Discrepancy Analysis**: Identifies differences between EMIS lookup data and current terminology server
- **Source File Tracking**: Links expansion results to original XML files for traceability

**Export Capabilities:**
- **Multiple CSV Formats**: Summary results, SNOMED-only codes, EMIS import-ready data
- **Hierarchical JSON Export**: Parent-child relationships in structured format with metadata
- **XML Output Generation**: Copy-paste ready XML for direct EMIS query implementation
- **Professional Data Cleaning**: Sanitized exports for business and clinical use

### ⚡ **Cache Architecture Overhaul**

**Cache-First Strategy Implementation:**
- **Multi-Tier Caching**: Session state → local cache → GitHub cache → API fallback
- **Lookup Table Optimization**: Comprehensive audit and update of all GitHub API calls
- **Performance Improvements**: Faster startup and reduced API dependencies
- **Session Persistence**: Expansion results maintained across download operations

**Technical Infrastructure:**
- **Local Cache Priority**: Fastest possible access to frequently used data
- **GitHub Cache Distribution**: Pre-built cache files for common lookup tables
- **Fallback Reliability**: Graceful degradation when caches unavailable
- **Cache Health Monitoring**: Automatic validation and regeneration as needed

### 📊 **Enhanced Export System**

**Terminology Server Exports:**
- **Expansion Summary CSV**: Detailed results with success/failure status and timestamps
- **Child Codes Export**: Clean SNOMED codes and descriptions for analysis
- **EMIS Implementation CSV**: Child codes with EMIS GUID mappings for direct implementation
- **Hierarchical JSON**: Parent-child relationships with source file metadata

**Export Improvements:**
- **Data Type Consistency**: Fixed Arrow serialization issues for mixed data types
- **Results Persistence**: Exports remain available during download operations
- **Source Attribution**: Complete traceability to original XML files
- **View Mode Integration**: Export filenames reflect unique vs per-source mode selection

### 🎨 **Interface Enhancements**

**NHS Terminology Server UI:**
- **Dedicated Tab Interface**: Complete terminology expansion interface in Clinical Codes section
- **Progress Tracking**: Real-time feedback during large hierarchy expansions
- **Detailed Results Table**: Comprehensive display with EMIS vs terminology server comparison
- **Status Integration**: Sidebar monitoring with automatic connection updates

**User Experience Improvements:**
- **Streamlined Authentication**: Removed redundant connection testing from main interface
- **Enhanced Status Reporting**: Clear success/failure indicators with detailed error messages
- **Improved Navigation**: Consistent interface patterns across terminology features
- **Results Organization**: Clear categorization of expansion results and export options

### 🔧 **Technical Enhancements**

**System Architecture:**
- **Codebase Audit**: Systematic review and optimization of all GitHub API integrations
- **Error Handling**: Enhanced error reporting and recovery mechanisms
- **Data Validation**: Improved handling of mixed data types and edge cases
- **Memory Management**: Optimized session state usage for large expansion results

**Integration Points:**
- **Cache-First Lookup Access**: All terminology server operations use optimized lookup table access
- **Session State Management**: Persistent results across UI interactions and exports
- **Background Processing**: Non-blocking expansion operations with progress feedback
- **Cross-Component Integration**: Seamless integration with existing clinical codes pipeline

### 💡 **User Benefits**

**Clinical Workflow Support:**
- **Complete Hierarchy Discovery**: Ensures no relevant child concepts are missed in EMIS implementations
- **Implementation Guidance**: Direct XML output for copy-paste into EMIS searches
- **Data Validation**: Compare EMIS expectations with current NHS terminology data
- **Time Savings**: Automated discovery vs manual hierarchy traversal

**Technical Reliability:**
- **Faster Performance**: Cache-first approach reduces loading times significantly
- **Offline Capability**: Local caching enables operation when GitHub API unavailable
- **Data Consistency**: Reliable access to lookup table data across all features
- **Export Integrity**: Professional, clean data exports for clinical and business use

---

### **Migration Notes**

**Full Backward Compatibility:**
- All existing XML processing workflows remain unchanged
- Enhanced functionality available immediately without configuration
- Existing lookup table integrations automatically benefit from cache optimization
- No changes required to existing user workflows

**New Requirements (Optional):**
- NHS England System-to-System credentials required for terminology server features
- Credentials configured in `.streamlit/secrets.toml` for terminology expansion
- Internet connectivity required for terminology server operations

---

*Version 2.1.0 introduces comprehensive NHS terminology integration while significantly improving system performance through cache architecture optimization.*

---

## v2.0.1 - Performance & UI Improvements (October 2025)

### 🚀 **Performance Optimizations**

**Unified Pipeline Caching:**
- **Instant Loading**: Refsets, pseudo-refsets, and pseudo-members tabs now load instantly after initial processing
- **Session State Caching**: Added `get_unified_clinical_data()` caching with automatic invalidation
- **Memory Optimization**: Eliminated redundant processing across clinical code tabs

**Search Count Consistency:**
- **Unified Metrics**: All tabs now show consistent search counts 
- **Pipeline Integration**: Analytics, Dependencies, and Rule Logic Browser use same data source
- **Accurate Reporting**: Fixed discrepancies where tabs showed diferrent counts depending on the parsing logic used

**Streamlit Compatibility:**
- **Deprecation Fixes**: Replaced all `use_container_width=True` with `width='stretch'`
- **Future Proofing**: Eliminated hundreds of console debug messages for cleaner operation

### 🎨 **User Interface Enhancements**

**Filter Logic Improvements:**
- **Include/Exclude Clarity**: Fixed filter parsing to show correct "Include" vs "Exclude" based on XML logic
- **Hierarchy Display**: Enhanced filter layout with indented "Additional Filters" under main "Filters" section
- **EMISINTERNAL Logic**: Proper handling of issue methods and internal classifications

**Dependency Tree Enhancements:**
- **Enhanced Clarity**: Now shows for example "31 root searches, 5 branch searches" instead of just "31 searches"
- **Total Understanding**: Users can clearly see 31+5=36 total searches across dependency relationships
- **Consistent Display**: Applied same logic to both Dependency Tree and Detailed Dependency View

**Export Experience:**
- **One-Click Downloads**: Eliminated page refresh issues - all downloads are now immediate
- **Consistent Behavior**: Rule Logic Browser and Report tabs now have uniform download experience

### 🔧 **Technical Improvements**

**Rule Logic Browser Fixes:**
- **Functionality Restored**: Fixed broken rule display that showed "No detailed rules found" in certain XML logic
- **Data Source Optimization**: Balanced search count accuracy with detailed rule content display
- **Complexity Metrics**: Maintained accurate complexity analysis (36 searches in breakdown)

**Architecture Updates:**
- **Module Documentation**: Completely updated `docs/modules.md` to reflect current unified pipeline structure
- **New Modules Documented**: Added documentation for all recent architectural additions

**Session State Management:**
- **Cache Invalidation**: Automatic cache clearing when XML files change or deduplication modes switch
- **Performance Monitoring**: Better tracking of data pipeline efficiency
- **Error Recovery**: Improved handling of session state inconsistencies

### 🧹 **Code Quality & Maintenance**

**Removed Deprecated Features:**
- **ZIP Export Cleanup**: Completely removed all ZIP export functionality app-wide
- **Memory Safety**: Eliminated memory-intensive ZIP creation that was causing performance issues
- **Clean Codebase**: Removed commented-out ZIP export code and related imports (previously disabled for debugging)

**Consistency Improvements:**
- **Search Counting**: All tabs use unified pipeline for search metrics
- **Error Handling**: Standardized error messages and fallback behaviors

### 💡 **User Experience Impact**

**Immediate Benefits:**
- **Faster Loading**: Clinical code tabs load instantly after first access
- **Clear Numbers**: Dependency tree clearly shows search relationship structure (31+5=36)
- **Reliable Downloads**: No more page refresh delays or broken download states

**Technical Reliability:**
- **Consistent Data**: All tabs show accurate, synchronized search counts
- **Clean Console**: No deprecation warnings or unnecessary debug output
- **Stable Performance**: Optimized caching prevents memory issues

---

### **Migration Notes**

**Full Backward Compatibility:**
- All existing XML files continue to work exactly as before
- No changes to core translation functionality
- Enhanced performance without changing user workflows

**Recommended Action:**
- No action required - improvements are automatic
- Users will notice faster loading and more consistent displays
- All existing bookmarks and workflows remain valid

---

*Version 2.0.1 represents a significant quality-of-life improvement focusing on performance, consistency, and professional polish while maintaining 100% backward compatibility.*

---

## v2.0.0 - Major Release: Complete Application Rebuild (December 2024)

### 🎯 **Application Transformation**

**The Unofficial EMIS XML Toolkit** represents a complete rebuild and expansion from the original SNOMED translation tool. What started as a basic GUID-to-SNOMED translator has evolved into a mucfh more complex EMIS XML analysis platform.

### **🔧 Complete Architecture Rewrite**

**New Modular System:**
- **`util_modules/xml_parsers/`** - Sophisticated XML parsing with namespace handling
- **`util_modules/analysis/`** - Advanced analysis engines for searches and reports
- **`util_modules/ui/`** - Modern 5-tab interface with specialized visualizations
- **`util_modules/export_handlers/`** - Comprehensive export system with multiple formats
- **`util_modules/core/`** - Business logic separation with report classification
- **`util_modules/common/`** - Shared utilities and error handling

**Technical Improvements:**
- Universal namespace handling for mixed format XML documents
- Orchestrated analysis pipeline with single XML parse
- Modular parser system supporting complex EMIS patterns
- Separation of search and report parsing logic

### **📊 New 5-Tab Interface (Complete UI Overhaul)**

#### **1. Clinical Codes Tab (Enhanced)**
- **Dual-mode deduplication**: Unique codes vs per-source tracking
- **Advanced filtering**: Clinical codes vs medications with intelligent classification
- **Refset support**: Direct SNOMED code handling for NHS refsets
- **Export filtering**: All codes, matched only, or unmatched only
- **Live metrics**: Real-time translation success rates

#### **2. Search Analysis Tab (NEW)**
- **Rule Logic Browser**: Detailed analysis of search population logic
- **Folder Structure**: Hierarchical navigation with search organization
- **Dependency Tree**: Visual representation of search relationships
- **Search Flow**: Step-by-step execution order analysis
- **Complexity Metrics**: Comprehensive search complexity scoring

#### **3. List Reports Tab (NEW)**
- **Column Structure Analysis**: Detailed breakdown of List Report columns
- **Healthcare Context**: Classification of clinical data, appointments, demographics
- **Filter Logic**: Analysis of per-column search criteria and restrictions
- **Clinical Code Extraction**: SNOMED translation from report filters
- **Export Integration**: Comprehensive Excel exports with multiple sheets

#### **4. Audit Reports Tab (NEW)**
- **Multi-Population Analysis**: Analysis of member search combinations
- **Organizational Grouping**: Practice codes, user authorization, consultation context
- **Enhanced Metadata**: Creation time, author information, quality indicators
- **Clinical Code Aggregation**: Cross-population code analysis
- **Custom Aggregation**: Support for complex audit report structures

#### **5. Aggregate Reports Tab (NEW)**
- **Statistical Analysis**: Grouping definitions and cross-tabulation support
- **Built-in Filters**: Analysis of aggregate report criteria
- **Healthcare Metrics**: QOF indicators and quality measurement support
- **Enterprise Reporting**: Multi-organization analysis capabilities

### **🔍 Advanced XML Pattern Support**

**Complex Structures:**
- **baseCriteriaGroup**: Nested criterion logic within wrapper criteria
- **Linked Criteria**: Cross-table relationships with temporal constraints
- **Population Criteria**: References between searches and reports
- **EMISINTERNAL Classifications**: Episode types, consultation headings, clinical status
- **Advanced Restrictions**: "Latest N WHERE condition" with test attributes

**Clinical Code Systems:**
- **SNOMED Refsets**: Direct code handling with clean description extraction
- **Legacy Code Mapping**: Backward compatibility with legacy EMIS codes
- **Medication Systems**: SCT_APPNAME, SCT_CONST, SCT_DRGGRP support
- **Exception Codes**: QOF exception patterns and healthcare quality integration

### **📤 Comprehensive Export System (Complete Rebuild)**

**Export Handlers:**
- **Search Export**: Detailed rule analysis with criteria breakdown
- **Report Export**: Type-specific exports for List/Audit/Aggregate reports
- **Clinical Code Export**: Conditional source tracking based on deduplication mode
- **Rule Export**: Individual rule exports with comprehensive analysis

**Export Features:**
- **Multiple Formats**: Excel (multi-sheet), CSV, JSON support
- **Smart Filtering**: Export exactly what users need
- **Source Attribution**: Track codes to their originating searches/reports
- **Healthcare Context**: Include clinical workflow information

### **🏗️ Enterprise Features**

**Folder Management:**
- **Hierarchical Organization**: Supports multi-level folder structures
- **Enterprise Reporting**: Multi-organization (XML exported from EMIS Enterprise) support
- **Version Independence**: Cross-version compatibility
- **Population Control**: Patient-level and organizational-level analysis

### **⚡ Performance Optimizations**

**Processing Speed:**
- **Single XML Parse**: Eliminates redundant parsing with element classification
- **Optimized Lookups**: Dictionary-based SNOMED lookups (O(1) vs O(n))
- **Vectorized Operations**: Pandas-optimized data processing
- **Smart Caching**: Session state management with intelligent invalidation

**User Experience:**
- **Progress Tracking**: Real-time feedback for long operations
- **Toast Notifications**: Non-intrusive status updates
- **Responsive Design**: Maintains UI responsiveness during processing
- **Error Recovery**: Graceful failure handling with detailed error messages

### **🔧 Technical Infrastructure**

**XML Processing:**
- **Universal Namespace Handling**: Supports mixed namespaced/non-namespaced documents
- **Robust Error Handling**: Comprehensive exception management
- **Memory Optimization**: Efficient processing of large XML files
- **Cloud Compatibility**: Optimized for Streamlit Cloud deployment

**Data Management:**
- **Session State Integration**: Persistent analysis results across tab navigation
- **Cache Management**: Intelligent data caching with TTL support
- **Memory Efficiency**: Optimized data structures for large datasets

### **🎨 User Interface Improvements**

**Design System:**
- **Consistent Icons**: Standardized emoji indicators across all tabs
- **Professional Layout**: Clean, healthcare-appropriate design
- **Responsive Navigation**: Seamless tab switching with preserved state
- **Accessibility**: Screen reader friendly with proper heading hierarchy

**User Experience:**
- **Progressive Disclosure**: Show basic info first, details on demand
- **Contextual Help**: Dynamic help text based on user selections
- **Export Preview**: Live count of items selected for export
- **Visual Feedback**: Color-coded status indicators and progress bars

---

## **Migration Notes**

### **From Previous Version:**
- **No Breaking Changes**: Existing XML files continue to work
- **Enhanced Output**: Same clinical codes with additional analysis
- **Preserved Workflows**: Translation functionality remains core feature
- **Extended Capabilities**: All previous features enhanced and expanded

### **New URL:**
- **Live Application**: https://emis-xml-toolkit.streamlit.app/
- **Updated Branding**: Reflects expanded toolkit capabilities

---

## **Previous Versions (Historical Reference)**

### **v1.x Series - Foundation Model**
- Simple EMIS GUID to SNOMED translation
- Basic XML parsing and code extraction  
- Single-tab interface with clinical codes only
- CSV export functionality
- MKB lookup table integration

The v1.x series established the foundation but was limited to basic translation and had multiple shortcomings - I was never really happy with it.
v2.0.0 represents a complete evolution into a comprehensive EMIS XML analysis platform.

---

## **Technical Specifications**

**Supported EMIS XML Types:**
- Search Reports (Population-based)
- List Reports (Multi-column data extraction)
- Audit Reports (Quality monitoring and compliance)
- Aggregate Reports (Statistical analysis and cross-tabulation)

**Clinical Code Systems:**
- SNOMED CT Concepts and Refsets
- Legacy Read Codes (via mapping)
- EMIS Internal Classifications
- Medication Codes (dm+d, brand names, constituents)

**Export Formats:**
- Excel (multi-sheet with formatting)
- CSV (filtered and comprehensive)
- JSON (structured data)
- TXT (human-readable reports)

**Browser Compatibility:**
- Chrome/Edge (Recommended)
- Firefox, Safari (Supported)
- Mobile browsers (Limited support)

---

*Last Updated: October 2025*  
*Application Version: 2.1.2*  
*Live at: https://emis-xml-toolkit.streamlit.app/*