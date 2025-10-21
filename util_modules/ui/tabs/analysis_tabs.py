"""
Analysis-related tab rendering functions.

This module handles rendering of all analysis-related tabs:
- Search analysis tab with rule logic browser and dependencies  
- XML structure analysis with folder navigation
- Complex rule visualization and export functionality
- Folder structure and dependency tree rendering
- Detailed rules tab with complexity analysis and exports

All functions preserve:
- Bulk export disabled functionality (to prevent hangs)
- Debug logging and performance optimizations
- UI styling and export features
- Session state management
"""

from .common_imports import *
from .base_tab import BaseTab, TabRenderer
from .tab_helpers import (
    _reprocess_with_new_mode,
    _lookup_snomed_for_ui,
    _deduplicate_clinical_data_by_emis_guid,
    _add_source_info_to_clinical_data,
    ensure_analysis_cached
)


def render_search_analysis_tab(xml_content: str, xml_filename: str):
    """
    Render the Search Analysis tab focused on search logic only.
    
    This tab provides a focused view of search reports with:
    - Complexity metrics and analysis
    - Folder structure browser (if folders exist)
    - Rule logic browser with detailed breakdown
    - Dependencies visualization
    
    Args:
        xml_content (str): The XML content to analyze
        xml_filename (str): Name of the XML file for exports
    """
    if not xml_content:
        st.info("📋 Upload and process an XML file to see search analysis")
        return
    
    try:
        # EMERGENCY BYPASS: Report tabs should NOT trigger expensive analysis
        # If analysis isn't already cached, show error instead of hanging for 10 minutes
        analysis = st.session_state.get('search_analysis') or st.session_state.get('xml_structure_analysis')
        if analysis is None:
            st.error("⚠️ Analysis not available. Please ensure XML processing completed successfully and try refreshing the page.")
            st.info("💡 Try switching to the 'Clinical Codes' tab first, then return to this tab.")
            return
        
        # Use the same complexity data source as the detailed complexity breakdown for consistency
        complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
        search_count = complexity_data.get('total_searches', 0)
        
        # Get the actual search reports for detailed rule content
        from ...core.report_classifier import ReportClassifier
        search_reports = ReportClassifier.filter_searches_only(analysis.reports)
        
        # If complexity data doesn't have search count, use the actual count
        if search_count == 0:
            search_count = len(search_reports)
        folder_count = len(analysis.folders) if analysis.folders else 0
        
        st.toast(f"Search Analysis: {search_count} search{'es' if search_count != 1 else ''} across {folder_count} folder{'s' if folder_count != 1 else ''}", icon="🔍")
        
        # Search-focused metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            complexity_color = {
                'Basic': '🟢',
                'Moderate': '🟡', 
                'Complex': '🟠',
                'Very Complex': '🔴'
            }
            # Safe access to complexity metrics with fallbacks for both orchestrated and legacy analysis
            complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
            complexity_level = complexity_data.get('complexity_level', 
                               complexity_data.get('classification', 'Basic'))
            complexity_score = complexity_data.get('complexity_score', 'N/A')
            
            st.metric(
                "Complexity", 
                f"{complexity_color.get(complexity_level, '⚪')} {complexity_level}",
                help=f"Score: {complexity_score}"
            )
        
        with col2:
            st.metric(
                "🔍 Searches", 
                search_count,
                help="Population-based search criteria that define patient groups"
            )
        
        with col3:
            folder_count = len(analysis.folders) if hasattr(analysis, 'folders') and analysis.folders else 0
            st.metric(
                "📁 Folders", 
                folder_count,
                help="Organizational folder structure"
            )
        
        # Search analysis sub-tabs
        if analysis.folders:
            struct_tab1, struct_tab2, struct_tab3 = st.tabs([
                "📁 Folder Structure", 
                "🔧 Rule Logic Browser",
                "🔗 Dependencies"
            ])
        else:
            struct_tab1, struct_tab2 = st.tabs([
                "🔧 Rule Logic Browser",
                "🔗 Dependencies"
            ])
        
        if analysis.folders:
            with struct_tab1:
                render_folder_structure_tab(analysis)
            
            with struct_tab2:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab3:
                render_dependencies_tab(analysis)
        else:
            with struct_tab1:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab2:
                render_dependencies_tab(analysis)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Error analyzing search structure: {str(e)}")
        with st.expander("Debug Information", expanded=False):
            st.code(error_details)


def render_xml_structure_tabs(xml_content: str, xml_filename: str):
    """
    Render XML structure analysis with sub-tabs.
    
    This comprehensive analysis view provides:
    - Overall complexity and report count metrics
    - Folder structure visualization (if folders exist) 
    - Rule logic browser with detailed breakdown
    - Dependencies tree visualization
    - Reports overview tab
    
    Args:
        xml_content (str): The XML content to analyze
        xml_filename (str): Name of the XML file for exports
    """
    if not xml_content:
        st.info("📋 Upload and process an XML file to see XML structure analysis")
        return
    
    try:
        # EMERGENCY BYPASS: Report tabs should NOT trigger expensive analysis
        # If analysis isn't already cached, show error instead of hanging for 10 minutes
        analysis = st.session_state.get('search_analysis') or st.session_state.get('xml_structure_analysis')
        if analysis is None:
            st.error("⚠️ Analysis not available. Please ensure XML processing completed successfully and try refreshing the page.")
            st.info("💡 Try switching to the 'Clinical Codes' tab first, then return to this tab.")
            return
        
        if analysis:
            # Notify user of discovered report counts (SKIP expensive type counting to prevent hang)
            folder_count = len(analysis.folders) if analysis.folders else 0
            # PERFORMANCE FIX: Skip expensive get_report_type_counts() that causes hang
            total_items = len(analysis.reports) if analysis.reports else 0
            
            # PERFORMANCE FIX: Simple notification without expensive type classification
            st.toast(f"XML Structure analyzed! {total_items} items across {folder_count} folder{'s' if folder_count != 1 else ''}", icon="🔍")
            st.info("📊 Individual report type counts available in each dedicated tab to avoid performance issues.")
        
        # Calculate report type counts efficiently using pre-processed data
        report_results = st.session_state.get('report_results')
        if report_results and hasattr(report_results, 'report_breakdown'):
            search_count = len(report_results.report_breakdown.get('search', []))
            list_count = len(report_results.report_breakdown.get('list', []))
            audit_count = len(report_results.report_breakdown.get('audit', []))
            aggregate_count = len(report_results.report_breakdown.get('aggregate', []))
        else:
            # Fallback to basic counts if pre-processed data not available
            search_count = 0
            list_count = 0
            audit_count = 0 
            aggregate_count = 0
        
        # Overview metrics for all report types
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            complexity_color = {
                'Basic': '🟢',
                'Moderate': '🟡', 
                'Complex': '🟠',
                'Very Complex': '🔴'
            }
            # Safe access to complexity metrics with fallbacks for both orchestrated and legacy analysis
            complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
            complexity_level = complexity_data.get('complexity_level', 
                               complexity_data.get('classification', 'Basic'))
            complexity_score = complexity_data.get('complexity_score', 'N/A')
            
            st.metric(
                "Complexity", 
                f"{complexity_color.get(complexity_level, '⚪')} {complexity_level}",
                help=f"Score: {complexity_score}"
            )
        
        with col2:
            st.metric(
                "🔍 Searches", 
                search_count,
                help="Population-based search criteria that define patient groups"
            )
        
        with col3:
            st.metric(
                "📋 List Reports", 
                list_count,
                help="Column-based reports displaying patient data"
            )
        
        with col4:
            st.metric(
                "📊 Audit Reports", 
                audit_count,
                help="Organizational aggregation reports for quality monitoring"
            )
        
        with col5:
            st.metric(
                "📈 Aggregate Reports", 
                aggregate_count,
                help="Statistical cross-tabulation and analysis reports"
            )
        
        with col6:
            # Use overall_complexity for orchestrated analysis, fall back to complexity_metrics for legacy
            complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
            st.metric(
                "📁 Folders", 
                complexity_data.get('total_folders', folder_count),
                help="Organizational folder structure"
            )
        
        # Create sub-tabs for different XML structure views
        if analysis.folders:
            # Complex structure with folders
            struct_tab1, struct_tab2, struct_tab3, struct_tab4 = st.tabs([
                "📁 Folder Structure", 
                "🔧 Rule Logic Browser",
                "🔗 Dependencies",
                "📊 Reports"
            ])
        else:
            # Simple structure without folders
            struct_tab1, struct_tab2, struct_tab3 = st.tabs([
                "🔧 Rule Logic Browser",
                "🔗 Dependencies",
                "📊 Reports"
            ])
        
        if analysis.folders:
            with struct_tab1:
                render_folder_structure_tab(analysis)
            
            with struct_tab2:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab3:
                render_dependencies_tab(analysis)
            
            with struct_tab4:
                render_reports_tab(analysis)
        else:
            with struct_tab1:
                render_detailed_rules_tab(analysis, xml_filename)
            
            with struct_tab2:
                render_dependencies_tab(analysis)
            
            with struct_tab3:
                render_reports_tab(analysis)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # Print detailed error to console for debugging
        print(f"ERROR: XML structure analysis failed")
        print(f"Error: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        
        st.error(f"Error analyzing XML structure: {str(e)}")
        with st.expander("Debug Information", expanded=False):
            st.code(error_details)


def render_folder_structure_tab(analysis):
    """
    Render folder structure sub-tab with memory safety for large datasets.
    
    This tab provides:
    - Visual folder hierarchy representation
    - Report distribution across folders
    - Navigation capabilities for large folder structures
    
    Args:
        analysis: The analysis object containing folder and report data
    """
    from ...analysis.report_structure_visualizer import render_folder_structure
    
    # Process all reports - no artificial limits
    reports_to_process = analysis.reports
    
    render_folder_structure(analysis.folder_tree, analysis.folders, reports_to_process)


def render_dependencies_tab(analysis):
    """
    Render dependencies sub-tab with memory safety for large datasets.
    
    This tab provides:
    - Dependency tree visualization showing report relationships
    - Cross-references between searches and other report types
    - Impact analysis for understanding report dependencies
    
    Args:
        analysis: The analysis object containing dependency tree data
    """
    # Dependencies tab fully enabled
    
    from ...analysis.report_structure_visualizer import render_dependency_tree
    
    # Process all reports - no artificial limits
    reports_to_process = analysis.reports
    
    render_dependency_tree(analysis.dependency_tree, reports_to_process)



def render_detailed_rules_tab(analysis, xml_filename):
    """
    Render detailed rules and export sub-tab.
    
    This is the most comprehensive analysis tab providing:
    - Detailed rule breakdown with search criteria visualization
    - Complexity analysis with scoring and classification
    - Multiple export options including:
      - Rule analysis text reports
      - Clinical codes CSV exports with metadata
      - Bulk ZIP exports (temporarily disabled due to performance)
    - Advanced filtering and deduplication options
    - Debug information and performance monitoring
    
    Args:
        analysis: The analysis object containing all report and rule data
        xml_filename (str): Name of the XML file for export naming
    """
    from ...analysis.search_rule_visualizer import render_detailed_rules, render_complexity_analysis, export_rule_analysis
    from ...export_handlers import UIExportManager
    
    
    # Detailed rule breakdown
    with st.expander("🔧 Detailed Rule Breakdown", expanded=True):
        # Import at the top of the function scope
        from ...core.report_classifier import ReportClassifier
        
        
        # Use searches from orchestrated results for the detailed rules (they need proper structure)
        if hasattr(analysis, 'orchestrated_results') and analysis.orchestrated_results and hasattr(analysis.orchestrated_results, 'searches'):
            # Use searches from orchestrated results
            search_only_reports = analysis.orchestrated_results.searches
        elif hasattr(analysis, 'searches') and analysis.searches:
            # Direct orchestrated analysis - use searches directly
            search_only_reports = analysis.searches
        else:
            # Legacy analysis - filter reports to get searches only
            search_only_reports = ReportClassifier.filter_searches_only(analysis.reports)
        
        # Debug information (only if debug mode is enabled)
        if st.session_state.get('debug_mode', False):
            st.write(f"Debug: Total reports before filtering: {len(analysis.reports)}")
            st.write(f"Debug: Search reports after filtering: {len(search_only_reports)}")
            
            # Handle duplicate report names
            name_counts = {}
            for r in analysis.reports:
                name = r.name
                if name not in name_counts:
                    name_counts[name] = []
                name_counts[name].append(r)
            
            duplicates = {name: reports for name, reports in name_counts.items() if len(reports) > 1}
            if duplicates:
                st.write("Debug: Found duplicate names:")
                for name, reports in duplicates.items():
                    st.write(f"  '{name}' appears {len(reports)} times:")
                    for r in reports:
                        classification = ReportClassifier.classify_report_type(r)
                        is_list_report = hasattr(r, 'is_list_report') and r.is_list_report
                        is_actual_search = ReportClassifier.is_actual_search(r)
                        parent_guid = getattr(r, 'parent_guid', 'None')
                        st.write(f"    - ID: {r.id}, Classification: {classification}, is_list_report: {is_list_report}, is_actual_search: {is_actual_search}, parent_guid: {parent_guid}")
            
        
        render_detailed_rules(search_only_reports, analysis)
    
    
    # Complexity analysis
    with st.expander("📈 Complexity Analysis", expanded=False):
        # Use overall_complexity for orchestrated analysis, fall back to complexity_metrics for legacy
        complexity_data = getattr(analysis, 'overall_complexity', getattr(analysis, 'complexity_metrics', {}))
        render_complexity_analysis(complexity_data, analysis)
        
        # Add rule analysis text export inside the complexity analysis
        st.markdown("---")
        st.markdown("**📊 Export Analysis**")
        
        # LAZY export generation - only when button is clicked
        if st.button("📥 Rule Analysis (TXT)", help="Generate detailed rule analysis as text file", key="rule_analysis_export"):
            try:
                with st.spinner("Generating rule analysis report..."):
                    from ...analysis.search_rule_visualizer import generate_rule_analysis_report
                    report_text, filename = generate_rule_analysis_report(analysis, xml_filename)
                    
                    st.download_button(
                        label="⬇️ Download Rule Analysis",
                        data=report_text,
                        file_name=filename,
                        mime="text/plain",
                        key="rule_analysis_download"
                    )
                    # Clear large content from memory immediately after download
                    del report_text
                    import gc
                    gc.collect()
                    st.success("✅ Rule analysis report generated successfully")
            except Exception as e:
                st.error(f"Rule analysis export failed: {e}")
    


# Import render_reports_tab from the main ui_tabs module since it's not extracted yet
try:
    from .report_tabs import render_reports_tab
except ImportError:
    def render_reports_tab(analysis):
        st.info("🔄 Reports tab under refactoring - functionality will be restored shortly")