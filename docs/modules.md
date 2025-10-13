# EMIS XML Converter - Module Architecture

## Overview

This application converts EMIS XML search files into SNOMED clinical codes and provides detailed analysis of search logic, rules, and criteria. The codebase uses a unified pipeline architecture with specialized analyzers for efficient processing and consistent data handling across the application.

## Core Application Flow

```
streamlit_app.py (file upload)
    ↓ XML content
extract_codes_with_separate_parsers() (separate search/report parsing)
    ↓ GUID list with source attribution
util_modules.core.translator (GUIDs → SNOMED codes)
    ↓ translated results
util_modules.analysis.analysis_orchestrator (unified analysis coordination)
    ↓ orchestrated results
util_modules.ui.ui_tabs (main interface coordinator)
    ↓ delegates to modular tabs
util_modules.ui.tabs.* (specialized tab rendering)
    ↓ export requests
util_modules.export_handlers (specialized export handling)
```

## Main Application Files

### `streamlit_app.py` - Main Application Entry Point
**Purpose:** Primary Streamlit application that coordinates all processing.

**Responsibilities:**
- File upload interface and user controls
- XML processing orchestration using separate parsers
- Progress tracking and user feedback
- Session state management with caching
- Dual-mode deduplication support (unique codes vs per-source)
- Unified clinical data caching for performance

**Key Functions:**
- `extract_codes_with_separate_parsers()` - Maintains search/report parser separation
- Session state management with cache invalidation

**When to modify:** UI layout changes, main workflow changes, parser coordination updates.

### `xml_utils.py` - Core XML Parsing and GUID Extraction
**Purpose:** Parses EMIS XML files and extracts EMIS GUIDs for translation.

**Responsibilities:**
- GUID extraction from valueSet and libraryItem elements
- Code system classification (clinical vs medication)
- Pseudo-refset detection
- Source attribution for dual-mode deduplication
- Universal namespace handling using NamespaceHandler

**Key Functions:**
- `parse_xml_for_emis_guids()` - Main GUID extraction with source tracking
- Centralized namespace handling for mixed namespaced/non-namespaced XML

**When to modify:** XML parsing logic changes, new EMIS XML formats, GUID extraction issues.

## Core Business Logic (`util_modules/core/`)

### `translator.py` - GUID to SNOMED Translation
**Purpose:** Converts extracted GUIDs to SNOMED codes using lookup table.

**Responsibilities:**
- Fast dictionary-based GUID lookups
- Clinical vs medication classification
- Pseudo-refset handling and success/failure tracking
- Dual-mode deduplication system
- Results organization by category

**Deduplication Modes:**
- `unique_codes`: Deduplicate by SNOMED code only
- `unique_per_entity`: Deduplicate by (source_guid, SNOMED code) combination

**When to modify:** Translation logic changes, new code categories, lookup optimization.

### `report_classifier.py` - EMIS Report Type Classification
**Purpose:** Classifies EMIS reports into 4 types: Search, List Report, Audit Report, Aggregate Report.

**Responsibilities:**
- Report type detection based on XML structure
- Search vs report filtering
- Report counting and grouping functions
- Classification logic based on XML element presence

**Key Methods:**
- `classify_report_type()` - Main classification logic
- `is_actual_search()` - Search identification
- `filter_searches_only()` - Search extraction with deduplication

**When to modify:** New report type patterns, classification logic improvements.

### `folder_manager.py` - Folder Structure Management
**Purpose:** Manages folder hierarchy and navigation for organizing searches.

**When to modify:** Folder navigation issues, hierarchy display problems.

### `search_manager.py` - Search Data Management
**Purpose:** Manages search-related data operations and queries.

**When to modify:** Search data handling, filtering improvements.

### `background_processor.py` - Background Processing
**Purpose:** ProcessPoolExecutor-based background processing for heavy XML analysis tasks.

**Responsibilities:**
- Concurrent processing with ProcessPoolExecutor
- Task status management and progress tracking
- Memory-efficient processing for large XML files
- Thread-safe task execution and result handling

**When to modify:** Heavy processing optimization, concurrency improvements.

### `optimized_processor.py` - Processing Integration
**Purpose:** Integrates background processing, progressive loading, and optimized caching with Streamlit patterns.

**Responsibilities:**
- Background processor and progressive loader integration
- Optimized caching with session state management
- Threading and queue management for UI responsiveness
- Performance monitoring and optimization coordination

**When to modify:** Processing pipeline optimization, UI responsiveness improvements.

## Analysis and Visualization (`util_modules/analysis/`)

### `analysis_orchestrator.py` - Central Analysis Coordination
**Purpose:** Coordinates complete analysis pipeline and unifies results from specialized analyzers.

**Responsibilities:**
- Workflow coordination: XMLElementClassifier → SearchAnalyzer → ReportAnalyzer
- Results unification from specialized analyzers
- Complexity metric integration
- Session state preparation for UI compatibility

**When to modify:** Analysis workflow changes, new analyzer integration.

### `xml_element_classifier.py` - Initial Element Classification
**Purpose:** Single XML parse that classifies all elements by type for efficient processing.

**Responsibilities:**
- Single XML parse to eliminate redundant parsing
- Element type classification (search/audit/list/aggregate)
- Document metadata extraction
- Folder structure extraction
- Pre-filtering for specialized analyzers

**Returns:** `ClassifiedElements` object with grouped elements and shared metadata.

**When to modify:** New element types, XML structure changes, classification logic.

### `xml_structure_analyzer.py` - Compatibility Interface
**Purpose:** Maintains backward compatibility while using orchestrated architecture.

**Responsibilities:**
- Legacy API compliance
- Internal delegation to AnalysisOrchestrator
- Result format conversion to legacy format
- Zero breaking changes for existing interfaces

**When to modify:** Interface compatibility issues or full migration planning.

### `search_rule_analyzer.py` - Legacy Search Analysis
**Purpose:** Legacy search rule analysis engine (pre-orchestrated architecture).

**Responsibilities:**
- Search rule parsing with modular XML parsers
- Criteria relationships and folder structure
- Report classification and dependency mapping
- Backwards compatibility for legacy analysis patterns

**When to modify:** Legacy compatibility issues or migration tasks.

### `performance_optimizer.py` - Performance Monitoring
**Purpose:** Cloud-compatible performance optimization and monitoring controls.

**Responsibilities:**
- Memory usage monitoring and optimization
- Large file processing controls (chunking)
- Performance metrics and feedback
- Streamlit Cloud compatibility optimizations

**When to modify:** Performance issues, cloud deployment optimization.

### `search_analyzer.py` - Search Logic Analysis
**Purpose:** Specialized analyzer for EMIS search population logic.

**Responsibilities:**
- Search rule parsing (population logic, operators, criteria)
- Linked criteria analysis and temporal relationships
- Population criteria (cross-search references)
- Column filters and restriction logic
- Dependency mapping and execution flow
- Search complexity metrics calculation

**Key Classes:**
- `SearchAnalyzer` - Main analysis engine
- `SearchReport` - Individual search structure
- `SearchAnalysisResult` - Container for search results

**When to modify:** Search rule features, population logic changes, search-specific analysis.

### `report_analyzer.py` - Report Structure Analysis
**Purpose:** Specialized analyzer for List, Audit, and Aggregate reports.

**Responsibilities:**
- List Report analysis (column structures, table definitions, sorting)
- Audit Report analysis (custom aggregation, organizational grouping)
- Aggregate Report analysis (statistical grouping, cross-tabulation)
- Clinical code extraction from report filters
- Enhanced metadata parsing (creation_time, author, population_references)
- Report complexity metrics

**Key Classes:**
- `ReportAnalyzer` - Main analysis engine
- `Report` - Individual report structure with metadata
- `ReportAnalysisResult` - Container for report results

**When to modify:** New report structures, report-specific features, enhanced parsing requirements.

### `common_structures.py` - Shared Data Structures
**Purpose:** Common data structures used across analyzers.

**Key Structures:**
- `CriteriaGroup` - Rule groups with AND/OR logic
- `PopulationCriterion` - References to other reports
- `ReportFolder` - Folder structure management
- `CompleteAnalysisResult` - Combined analysis results

**When to modify:** Changes to shared structures, new common patterns.

### Visualization Modules

#### `search_rule_visualizer.py` - Search Rule Display
**Purpose:** Interactive displays for search rules, criteria, and detailed analysis.

**Responsibilities:**
- Detailed rule and criteria displays with proper Include/Exclude logic
- Linked criteria relationships
- Search complexity analysis with unified pipeline integration
- Search-specific export functionality
- Filter hierarchy display (Filters → Additional Filters)

#### `report_structure_visualizer.py` - Report Structure Display
**Purpose:** Interactive displays for report structure and dependencies.

**Responsibilities:**
- Folder structure visualization
- Dependency tree analysis
- Report type composition analysis
- Cross-report relationship displays

#### `shared_render_utils.py` - Common Visualization Utilities
**Purpose:** Shared utility functions for visualization modules.

**When to modify:** Common visualization patterns, shared formatting functions.

## User Interface (`util_modules/ui/`)

### `ui_tabs.py` - Main Results Interface Coordinator
**Purpose:** Coordinates tab rendering and provides main results interface entry point.

**Responsibilities:**
- Tab routing and rendering coordination
- Session state management for tab switching
- Main results interface orchestration

**When to modify:** Overall tab structure changes, main interface routing.

### Modular Tab Structure (`util_modules/ui/tabs/`)

#### `clinical_tabs.py` - Clinical Data Tab Rendering
**Purpose:** Comprehensive clinical data tab rendering with unified pipeline integration.

**Tab Structure:**
- **Clinical Codes** - Standalone clinical codes with dual-mode deduplication
- **Medications** - Medication codes with source tracking
- **Refsets** - True refsets (EMIS-supported)  
- **Pseudo-Refsets** - Pseudo-refsets with member code access
- **Pseudo-Refset Members** - Individual pseudo-refset member codes
- **Clinical Codes Main** - Aggregated clinical codes view

**Key Features:**
- Unified pipeline integration with caching for performance
- Dual-mode deduplication (Unique Codes vs Per Source)
- Source tracking with GUID mapping
- Container information (Search Rule Main Criteria, Report Column Group, etc.)
- Export functionality per section

**When to modify:** Clinical code display, medication handling, refset functionality.

#### `analysis_tabs.py` - Analysis Tab Rendering
**Purpose:** Search analysis and structure visualization with unified pipeline integration.

**Responsibilities:**
- Search logic analysis display with consistent search counts
- Folder structure visualization
- Search dependencies and rule logic browser
- Complexity analysis with unified metrics

**When to modify:** Search analysis features, dependency visualization.

#### `analytics_tab.py` - Analytics Display
**Purpose:** Statistics and analytics visualization using unified pipeline data.

**When to modify:** Statistics display, analytics features.

#### `report_tabs.py` - Report Tab Rendering
**Purpose:** Specialized rendering for List Reports, Audit Reports, and Aggregate Reports.

**Responsibilities:**
- List Report browser with column structure analysis
- Audit Report browser with organizational focus
- Aggregate Report browser with statistical analysis
- Report-type-specific interfaces and metrics
- Immediate download functionality (no page refresh)
- Proper field capitalization (Population, Count, etc.)

**When to modify:** Report-specific enhancements, new report patterns.

#### `tab_helpers.py` - Shared Tab Utilities
**Purpose:** Common functionality shared across all tab modules with unified pipeline support.

**Key Functions:**
- `get_unified_clinical_data()` - Unified pipeline data access with caching
- `_add_source_info_to_clinical_data()` - GUID mapping and source tracking
- `_deduplicate_clinical_data_by_emis_guid()` - Deduplication logic
- `_reprocess_with_new_mode()` - Mode switching logic with cache invalidation
- `_lookup_snomed_for_ui()` - SNOMED lookup integration

**When to modify:** Shared tab functionality, GUID mapping logic, deduplication improvements.

#### `base_tab.py` - Tab Base Classes
**Purpose:** Base classes and common patterns for tab implementations.

**When to modify:** Common tab patterns, base functionality.

#### `common_imports.py` - Shared Imports
**Purpose:** Common imports used across tab modules to reduce duplication.

**When to modify:** Shared dependencies, import organization.

#### `field_mapping.py` - Universal Field Mapping
**Purpose:** Standardized field names and mapping functions for clinical codes.

**Responsibilities:**
- Canonical field name definitions (EMIS GUID, SNOMED Code, etc.)
- Consistent field mapping across all application components
- Translation between different data source formats
- Field validation and standardization

**When to modify:** New data sources, field name changes, standardization requirements.

### Core UI Components

#### `status_bar.py` - Application Status Display
**Purpose:** Shows lookup table status and system health.

**Responsibilities:**
- Lookup table loading and status
- Version information display
- Error state handling

**When to modify:** Status display changes, new health checks.

#### `ui_helpers.py` - Reusable UI Components
**Purpose:** Common UI functions used across the application.

**When to modify:** UI consistency improvements, new display patterns.

#### `rendering_utils.py` - Standard UI Components
**Purpose:** Standardized Streamlit components for consistent UI.

**When to modify:** UI standardization, new component patterns.

#### `layout_utils.py` - Complex Layout Management
**Purpose:** Advanced layout utilities for complex UI arrangements.

**When to modify:** Complex UI layouts, navigation improvements.

#### `progressive_loader.py` - Progressive Loading Components
**Purpose:** Progressive loading and performance optimization for large datasets.

**When to modify:** Loading performance, large dataset handling.

#### `async_components.py` - Asynchronous UI Components
**Purpose:** Asynchronous components for improved responsiveness.

**When to modify:** Async functionality, performance improvements.

## Export Functionality (`util_modules/export_handlers/`)

### `ui_export_manager.py` - Export Coordination
**Purpose:** Manages all export functionality with orchestrated analysis integration.

**Responsibilities:**
- Export routing between search and report handlers
- Bulk export coordination
- Clinical codes unification
- Session state compatibility

**When to modify:** Export UI improvements, new export options.

### `search_export.py` - Search-Specific Export
**Purpose:** Exports search reports with detailed criteria analysis.

**Responsibilities:**
- Search criteria export with rule breakdown
- Clinical code extraction and SNOMED translation
- Comprehensive rule analysis sheets
- Parent/child search relationship handling

**When to modify:** Search-specific export requirements, criteria analysis changes.

### `report_export.py` - Report Export Handler
**Purpose:** Comprehensive export for all 4 EMIS report types.

**Responsibilities:**
- List Reports: Column structure analysis with healthcare context
- Audit Reports: Enhanced metadata, member search names, clinical codes
- Aggregate Reports: Statistical setup, grouping definitions, built-in filters
- Type-specific Excel sheet generation
- Clinical code extraction from report filters

**When to modify:** Healthcare domain expansions, new enterprise patterns.

### `rule_export.py` - Individual Rule Export
**Purpose:** Exports single rules with their criteria.

**When to modify:** Rule export format, individual rule analysis features.

### `clinical_code_export.py` - Clinical Code Export
**Purpose:** Exports translated clinical codes and medications.

**Key Features:**
- Conditional source tracking based on deduplication mode
- Clinical codes table export with proper column headers
- Success/failure status export

**When to modify:** Code export formats, new result categories.

## XML Parsing (`util_modules/xml_parsers/`)

### `namespace_handler.py` - Universal Namespace Handling
**Purpose:** Centralized namespace handler for mixed namespaced/non-namespaced XML.

**Key Features:**
- Smart element finding: tries non-namespaced first, then namespaced
- XPath support with automatic namespace conversion
- Safe text extraction with defaults

**Core Pattern:**
```python
ns = NamespaceHandler()
element = ns.find(parent, 'elementName')  # Handles both <elementName> and <emis:elementName>
```

**When to modify:** Core parsing logic, namespace changes.

### `base_parser.py` - Base Parsing Utilities
**Purpose:** Base class providing common parsing methods with namespace support.

**Key Features:**
- All parsers inheriting from XMLParserBase get automatic NamespaceHandler access
- Common parsing methods with centralized namespace handling
- Consistent error handling patterns

**When to modify:** Core parsing logic, parser optimization.

### Specialized Parsers

#### `criterion_parser.py` - Search Criteria Parsing
**Purpose:** Parses individual search criteria and components.

#### `restriction_parser.py` - Search Restriction Parsing
**Purpose:** Parses search restrictions like 'Latest 1' with conditional logic.

#### `value_set_parser.py` - Value Set Parsing
**Purpose:** Parses clinical code value sets and code systems.

#### `linked_criteria_parser.py` - Linked Criteria Parsing
**Purpose:** Parses complex linked criteria and relationships.

#### `report_parser.py` - EMIS Report Type Parsing
**Purpose:** Comprehensive parser for all 4 EMIS report types.

**Responsibilities:**
- Report type detection
- List Report: Column group structure, table type classification, sort configuration
- Audit Report: Multiple population references, custom aggregation
- Aggregate Report: Statistical grouping and cross-tabulation
- Enterprise reporting elements and healthcare domain integration

**When to modify:** New report structures, enterprise patterns, healthcare workflows.

## Shared Utilities (`util_modules/common/`)

### `error_handling.py` - Standardized Error Management
**Purpose:** Centralized error handling with categorization.

### `ui_error_handling.py` - UI Error Display
**Purpose:** User-friendly error display for Streamlit applications.

### `export_utils.py` - Centralized Export Utilities
**Purpose:** Common export functionality used across export handlers.

### `dataframe_utils.py` - DataFrame Operations
**Purpose:** Standardized pandas DataFrame operations and validation.

## General Utilities (`util_modules/utils/`)

### `lookup.py` - Lookup Table Management
**Purpose:** Loads SNOMED lookup table and creates fast lookup dictionaries.

### `audit.py` - Processing Statistics and Validation
**Purpose:** Creates comprehensive stats about translation success rates and processing time.

### `text_utils.py` - Text Processing Utilities
**Purpose:** Common text processing functions for consistent formatting.

### `debug_logger.py` - Development and Troubleshooting
**Purpose:** Logging and debugging tools for development and troubleshooting.

### `github_loader.py` - External Data Loading
**Purpose:** GitHub API integration for loading lookup tables.

## Architecture Dependencies

### Module Organization:
```
util_modules/
├── analysis/           # Analysis and visualization logic
├── common/             # Shared utilities and infrastructure
├── core/               # Core business logic
├── export_handlers/    # Export functionality
├── ui/                 # User interface components
├── utils/              # General utilities
└── xml_parsers/        # Modular XML parsing
```

### Dependency Rules:
- **UI modules** depend on core, common, and utils modules
- **Analysis modules** use xml_parsers, core, and ui modules
- **Export handlers** use core, common, and utils modules
- **All modules** can use common utilities and error handling

## Key Architectural Features

### Unified Pipeline Architecture
**Purpose:** Consistent data handling across all UI components with performance optimization.

**Implementation:**
- **Analysis Orchestrator**: Central coordination of all analysis components
- **Unified Clinical Data**: Cached pipeline results accessible via `get_unified_clinical_data()`
- **Consistent Search Counts**: All tabs use same data source for accurate metrics
- **Performance Caching**: Session state caching with automatic invalidation

### Dual-Mode Deduplication System
**Purpose:** Allows users to toggle between unique codes vs per-source views.

**Implementation:**
- **Parser Level**: Source GUID attribution in xml_utils.py
- **Translation Level**: Mode-specific deduplication in translator.py
- **UI Level**: Inline toggles on applicable tabs
- **Export Level**: Conditional source tracking in export handlers

### Universal Namespace Handling
**Achievement:** Centralized namespace handling eliminating mixed namespace issues.

**Implementation:**
- **NamespaceHandler**: Universal handler for both namespaced and non-namespaced elements
- **XMLParserBase**: Automatic NamespaceHandler access for all parsers
- **Consistent Patterns**: All XML parsing uses unified `ns.find()` methods

### Orchestrated Analysis Pipeline
**Purpose:** Efficient analysis with single XML parse and specialized analyzers.

**Flow:**
1. **XMLElementClassifier**: Single parse + element classification
2. **SearchAnalyzer**: Search population logic analysis
3. **ReportAnalyzer**: Report structure analysis + clinical codes
4. **AnalysisOrchestrator**: Results unification

## Quick Reference for Common Tasks

**New export format:** `util_modules/export_handlers/`
**UI display issues:** `util_modules/ui/` or visualization modules
**Classification problems:** `util_modules/core/report_classifier.py`
**Search rule logic:** `util_modules/analysis/search_analyzer.py`
**Translation issues:** `util_modules/core/translator.py` or `xml_utils.py`
**Lookup table problems:** `util_modules/utils/lookup.py`
**Performance issues:** Check caching in `tab_helpers.py`
**Main app workflow:** `streamlit_app.py`
**Error handling:** `util_modules/common/error_handling.py`
**XML parsing:** `util_modules/xml_parsers/`
**Namespace issues:** `util_modules/xml_parsers/namespace_handler.py`