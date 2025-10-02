"""
Report Analyzer - Focused on EMIS Report Analysis
Handles List Reports, Audit Reports, and Aggregate Reports with their specific structures.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ..xml_parsers.criterion_parser import SearchCriterion, CriterionParser
from ..xml_parsers.report_parser import ReportParser
from ..xml_parsers.namespace_handler import NamespaceHandler
from .common_structures import CriteriaGroup, PopulationCriterion, ReportFolder


@dataclass
class Report:
    """Individual report (List/Audit/Aggregate) with type-specific structures"""
    id: str
    name: str
    description: str
    report_type: str  # 'list', 'audit', 'aggregate'
    parent_type: Optional[str]
    parent_guid: Optional[str]
    folder_id: Optional[str]
    search_date: str
    criteria_groups: List[CriteriaGroup]
    sequence: int = 1
    
    # Enhanced relationship tracking
    direct_dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    folder_path: List[str] = field(default_factory=list)
    population_type: Optional[str] = None
    
    # Report type indicators
    is_list_report: bool = False
    is_audit_report: bool = False
    is_aggregate_report: bool = False
    
    # Report-specific content structures
    column_groups: List[Dict] = field(default_factory=list)  # List report columns
    custom_aggregate: Optional[Dict] = None  # Audit report aggregation logic
    aggregate_groups: List[Dict] = field(default_factory=list)  # Aggregate report groupings
    statistical_groups: List[Dict] = field(default_factory=list)  # Statistical analysis groups
    logical_table: Optional[str] = None  # Logical table for aggregate reports
    aggregate_criteria: Optional[Dict] = None  # Built-in criteria for aggregate reports
    
    # Metadata fields
    creation_time: Optional[str] = None
    author: Optional[str] = None
    
    # Audit report specific fields
    population_references: List[str] = field(default_factory=list)  # Member search GUIDs for audit reports


@dataclass 
class ReportAnalysisResult:
    """Results from report-only analysis"""
    reports: List[Report]
    report_breakdown: Dict[str, List[Report]]  # Reports grouped by type
    report_dependencies: Dict[str, Any]
    clinical_codes: List[Dict]  # Clinical codes extracted from reports
    report_complexity: Dict[str, Any]


def _add_source_tracking_to_value_sets(value_sets: List[Dict], source_type: str, report_type: str, source_name: str = None) -> List[Dict]:
    """Add source tracking information to value sets"""
    if not value_sets:
        return []
    
    tracked_value_sets = []
    for value_set in value_sets:
        tracked_value_set = value_set.copy()
        tracked_values = []
        
        for value in value_set.get('values', []):
            tracked_value = value.copy()
            tracked_value['source_type'] = source_type  # 'search' or 'report'
            tracked_value['report_type'] = report_type  # 'search', 'aggregate', 'list', 'audit'
            tracked_value['source_name'] = source_name or 'Unknown'  # Actual name of search/report
            tracked_values.append(tracked_value)
        
        tracked_value_set['values'] = tracked_values
        tracked_value_sets.append(tracked_value_set)
    
    return tracked_value_sets


class ReportAnalyzer:
    """Analyzes EMIS List, Audit, and Aggregate reports"""
    
    def __init__(self):
        self.criterion_parser = CriterionParser()
        self.report_parser = ReportParser()
        self.ns = NamespaceHandler()
    
    def analyze_reports(self, report_elements: List[ET.Element], namespaces: Dict, folders: List[ReportFolder] = None) -> ReportAnalysisResult:
        """
        Analyze pre-filtered report elements (List/Audit/Aggregate)
        
        Args:
            report_elements: Pre-filtered report elements
            namespaces: XML namespaces
            folders: Parsed folder structure
            
        Returns:
            ReportAnalysisResult containing report-only analysis
        """
        try:
            # Parse report elements
            reports = self._parse_report_elements(report_elements, namespaces, folders)
            
            # Build report relationships
            reports = self._build_report_dependencies(reports)
            
            # Group reports by type
            report_breakdown = self._group_reports_by_type(reports)
            
            # Extract clinical codes from reports
            clinical_codes = self._extract_clinical_codes_from_reports(reports)
            
            # Calculate report complexity
            report_complexity = self._calculate_report_complexity(reports)
            
            # Build report dependency tree
            report_dependencies = self._build_report_dependency_tree(reports)
            
            return ReportAnalysisResult(
                reports=reports,
                report_breakdown=report_breakdown,
                report_dependencies=report_dependencies,
                clinical_codes=clinical_codes,
                report_complexity=report_complexity
            )
            
        except Exception as e:
            raise Exception(f"Error analyzing reports: {str(e)}")
    
    def _parse_report_elements(self, report_elements: List[ET.Element], namespaces: Dict, folders: List[ReportFolder] = None) -> List[Report]:
        """Parse pre-filtered report elements"""
        reports = []
        
        for report_elem in report_elements:
            # Use ReportParser to get report structure
            report_structure = self.report_parser.parse_report_structure(report_elem)
            
            # Parse the report (no need to filter - already pre-filtered)
            report = self._parse_report(report_elem, namespaces, folders, report_structure)
            if report:
                reports.append(report)
        
        return reports
    
    def _parse_report(self, report_elem: ET.Element, namespaces: Dict, folders: List[ReportFolder] = None, report_structure: Dict = None) -> Optional[Report]:
        """Parse individual report (List/Audit/Aggregate)"""
        try:
            # Extract basic elements using namespace handler
            report_id = self.ns.find(report_elem, 'id')
            name_elem = self.ns.find(report_elem, 'name')
            desc_elem = self.ns.find(report_elem, 'description')
            parent_elem = self.ns.find(report_elem, 'parent')
            search_date_elem = self.ns.find(report_elem, 'searchDate')
            sequence_elem = self.ns.find(report_elem, 'sequence')
            folder_elem = self.ns.find(report_elem, 'folder')
            population_type_elem = self.ns.find(report_elem, 'populationType')
            
            # Extract metadata elements using namespace handler
            creation_time_elem = self.ns.find(report_elem, 'creationTime')
            author_elem = self.ns.find(report_elem, 'author')
            
            # Extract parent information
            parent_type = None
            parent_guid = None
            if parent_elem is not None:
                parent_type = parent_elem.get('parentType')
                # Look for SearchIdentifier using namespace handler
                search_id_elem = self.ns.find(parent_elem, 'SearchIdentifier')
                if search_id_elem is not None:
                    parent_guid = search_id_elem.get('reportGuid')
            
            # Override parent_type with parsed value if available
            if report_structure and report_structure.get('parent_type'):
                parent_type = report_structure['parent_type']
            
            # Initialize population_refs for all report types
            population_refs = []
            
            # Extract audit report population references FIRST (needed for parent_guid logic)
            if report_structure['report_type'] == 'audit':
                # Extract population references from audit report using namespace handler
                audit_report_elem = self.ns.find(report_elem, 'auditReport')
                if audit_report_elem is not None:
                    # Look for population elements in any nested structure using namespace handler
                    pop_elems = self.ns.findall_with_path(audit_report_elem, './/population')
                    population_refs = [pop.text.strip() for pop in pop_elems if pop.text and pop.text.strip()]
            
            # Get dependencies
            dependencies = self.report_parser.get_report_dependencies(report_elem)
            
            # Extract author information
            author_name = None
            if author_elem is not None:
                # Check for authorName first (preferred format) using namespace handler
                author_name_elem = self.ns.find(author_elem, 'authorName')
                if author_name_elem is not None:
                    author_name = author_name_elem.text
                else:
                    # Fall back to userInRole GUID if authorName not available
                    user_role_elem = self.ns.find(author_elem, 'userInRole')
                    if user_role_elem is not None:
                        author_name = f"User Role: {user_role_elem.text}"  # Show as role rather than raw GUID
            
            # For audit reports without direct parent, check population references
            if not parent_guid and report_structure['report_type'] == 'audit' and population_refs:
                # Use first population reference as parent (base population for audit)
                parent_guid = population_refs[0]
                parent_type = 'POPULATION'
            
            # Build folder path
            folder_id = folder_elem.text if folder_elem is not None else None
            folder_path = self._build_folder_path(folder_id, folders)
            
            # Parse criteria groups (standard criteria)
            criteria_groups = self._parse_report_criteria_groups(report_elem, namespaces)
            
            # For aggregate and audit reports, also include built-in criteria as criteria groups
            report_criteria_groups = []
            if report_structure and report_structure.get('aggregate_criteria'):
                # Aggregate reports have criteria in aggregate_criteria
                agg_criteria = report_structure['aggregate_criteria']
                report_criteria_groups.extend(agg_criteria.get('criteria_groups', []))
            elif report_structure and report_structure.get('criteria_groups'):
                # Audit reports have criteria directly in criteria_groups
                report_criteria_groups.extend(report_structure['criteria_groups'])
            
            # Process report-specific criteria groups
            for criteria_group_data in report_criteria_groups:
                # Convert the parsed criteria to CriteriaGroup format
                criteria_objects = []
                for criterion_data in criteria_group_data.get('criteria', []):
                    # Create SearchCriterion object with source tracking
                    search_criterion = SearchCriterion(
                        id=criterion_data.get('id', ''),
                        table=criterion_data.get('table', ''),
                        display_name=criterion_data.get('display_name', ''),
                        description=criterion_data.get('description', ''),
                        negation=criterion_data.get('negation', False),
                        column_filters=criterion_data.get('column_filters', []),
                        value_sets=_add_source_tracking_to_value_sets(criterion_data.get('value_sets', []), 'report', report_structure.get('report_type', 'unknown'), name_elem.text if name_elem is not None else 'Unknown Report'),
                        restrictions=criterion_data.get('restrictions', []),
                        linked_criteria=criterion_data.get('linked_criteria', [])
                        # Note: SearchCriterion doesn't have parameters field
                    )
                    criteria_objects.append(search_criterion)
                    
                    # Create CriteriaGroup object
                    criteria_group = CriteriaGroup(
                        id=criteria_group_data.get('id', ''),
                        member_operator=criteria_group_data.get('member_operator', 'AND'),
                        action_if_true=criteria_group_data.get('action_if_true', 'SELECT'),
                        action_if_false=criteria_group_data.get('action_if_false', 'REJECT'),
                        criteria=criteria_objects,
                        population_criteria=[]  # Aggregate reports don't typically have population criteria
                    )
                    criteria_groups.append(criteria_group)
            
            return Report(
                id=report_id.text if report_id is not None else "Unknown",
                name=name_elem.text if name_elem is not None else "Unknown",
                description=desc_elem.text if desc_elem is not None else "",
                report_type=report_structure['report_type'],
                parent_type=parent_type,
                parent_guid=parent_guid,
                folder_id=folder_id,
                search_date=search_date_elem.text if search_date_elem is not None else "BASELINE",
                criteria_groups=criteria_groups,
                sequence=int(sequence_elem.text) if sequence_elem is not None else 1,
                folder_path=folder_path,
                population_type=population_type_elem.text if population_type_elem is not None else None,
                # Report type classification
                is_list_report=report_structure['report_type'] == 'list',
                is_audit_report=report_structure['report_type'] == 'audit',
                is_aggregate_report=report_structure['report_type'] == 'aggregate',
                # Report-specific content structures
                column_groups=report_structure.get('column_groups', []),
                custom_aggregate=report_structure.get('custom_aggregate'),
                aggregate_groups=report_structure.get('aggregate_groups', []),
                statistical_groups=report_structure.get('statistical_groups', []),
                logical_table=report_structure.get('logical_table'),
                aggregate_criteria=report_structure.get('aggregate_criteria'),
                # Add dependencies found by parser
                direct_dependencies=dependencies,
                # Metadata fields
                creation_time=creation_time_elem.text if creation_time_elem is not None else None,
                author=author_name,
                # Audit report specific fields
                population_references=population_refs
            )
            
        except Exception:
            return None
    
    def _parse_report_criteria_groups(self, report_elem: ET.Element, namespaces: Dict) -> List[CriteriaGroup]:
        """Parse criteria groups for reports (may be empty for some report types)"""
        criteria_groups = []
        
        # Most reports don't have standard criteria groups, but parse them if they exist
        for group_elem in self.ns.findall_with_path(report_elem, './/criteriaGroup'):
            group = self._parse_criteria_group(group_elem, namespaces)
            if group:
                criteria_groups.append(group)
        
        return criteria_groups
    
    def _parse_criteria_group(self, group_elem: ET.Element, namespaces: Dict) -> Optional[CriteriaGroup]:
        """Parse individual criteria group"""
        try:
            group_id = self.ns.find(group_elem, 'id')
            definition_elem = self.ns.find(group_elem, 'definition')
            action_true_elem = self.ns.find(group_elem, 'actionIfTrue')
            action_false_elem = self.ns.find(group_elem, 'actionIfFalse')
            
            if definition_elem is None:
                return None
                
            member_op_elem = self.ns.find(definition_elem, 'memberOperator')
            member_operator = member_op_elem.text if member_op_elem is not None else "AND"
            
            # Parse individual criteria
            criteria = []
            for criterion_elem in self.ns.findall_with_path(definition_elem, './/criterion'):
                criterion = self.criterion_parser.parse_criterion(criterion_elem)
                if criterion:
                    criteria.append(criterion)
            
            # Parse population criteria (references to other reports)
            population_criteria = []
            for pop_elem in self.ns.findall_with_path(definition_elem, './/populationCriterion'):
                pop_criterion = self._parse_population_criterion(pop_elem, namespaces)
                if pop_criterion:
                    population_criteria.append(pop_criterion)
            
            return CriteriaGroup(
                id=group_id.text if group_id is not None else "",
                member_operator=member_operator,
                action_if_true=action_true_elem.text if action_true_elem is not None else "SELECT",
                action_if_false=action_false_elem.text if action_false_elem is not None else "REJECT",
                criteria=criteria,
                population_criteria=population_criteria
            )
            
        except Exception:
            return None
    
    def _parse_population_criterion(self, pop_elem: ET.Element, namespaces: Dict) -> Optional[PopulationCriterion]:
        """Parse population criterion (reference to another report)"""
        try:
            pop_id = self.ns.find(pop_elem, 'id')
            search_id = self.ns.find(pop_elem, 'SearchIdentifier')
            
            return PopulationCriterion(
                id=pop_id.text if pop_id is not None else "",
                report_guid=search_id.get('reportGuid') if search_id is not None else ""
            )
        except Exception:
            return None
    
    def _build_folder_path(self, folder_id: str, folders: List[ReportFolder] = None) -> List[str]:
        """Build full folder path for a report"""
        if not folder_id or not folders:
            return []
            
        folder_map = {f.id: f for f in folders}
        folder_path = []
        current_folder = folder_map.get(folder_id)
        
        while current_folder:
            folder_path.insert(0, current_folder.name)
            parent_id = current_folder.parent_folder_id
            current_folder = folder_map.get(parent_id) if parent_id else None
        
        return folder_path
    
    def _build_report_dependencies(self, reports: List[Report]) -> List[Report]:
        """Build dependency relationships between reports"""
        report_map = {r.id: r for r in reports}
        
        for report in reports:
            # Add parent dependencies
            if report.parent_guid and report.parent_guid not in report.direct_dependencies:
                report.direct_dependencies.append(report.parent_guid)
                parent = report_map.get(report.parent_guid)
                if parent:
                    parent.dependents.append(report.id)
            
            # Add population criterion dependencies
            for group in report.criteria_groups:
                for pop_criterion in group.population_criteria:
                    if pop_criterion.report_guid not in report.direct_dependencies:
                        report.direct_dependencies.append(pop_criterion.report_guid)
                        dependency = report_map.get(pop_criterion.report_guid)
                        if dependency:
                            dependency.dependents.append(report.id)
        
        return reports
    
    def _group_reports_by_type(self, reports: List[Report]) -> Dict[str, List[Report]]:
        """Group reports by their type"""
        grouped = {
            'list': [],
            'audit': [],
            'aggregate': []
        }
        
        for report in reports:
            if report.report_type in grouped:
                grouped[report.report_type].append(report)
        
        return grouped
    
    def _extract_clinical_codes_from_reports(self, reports: List[Report]) -> List[Dict]:
        """Extract all clinical codes from reports for analysis"""
        clinical_codes = []
        
        for report in reports:
            # Extract codes from criteria groups
            for group in report.criteria_groups:
                for criterion in group.criteria:
                    for value_set in criterion.value_sets:
                        for value in value_set.get('values', []):
                            clinical_codes.append({
                                'source_report_id': report.id,
                                'source_report_name': report.name,
                                'source_report_type': report.report_type,
                                'code_value': value.get('value', ''),
                                'display_name': value.get('display_name', ''),
                                'code_system': value_set.get('code_system', ''),
                                'include_children': value.get('include_children', False),
                                'is_refset': value.get('is_refset', False),
                                'source_type': value.get('source_type', 'report'),
                                'report_type': value.get('report_type', report.report_type)
                            })
        
        return clinical_codes
    
    def _calculate_report_complexity(self, reports: List[Report]) -> Dict[str, Any]:
        """Calculate complexity metrics for reports"""
        if not reports:
            return {}
        
        report_breakdown = self._group_reports_by_type(reports)
        
        # Calculate type-specific metrics
        metrics = {
            'total_reports': len(reports),
            'list_reports': len(report_breakdown['list']),
            'audit_reports': len(report_breakdown['audit']),
            'aggregate_reports': len(report_breakdown['aggregate']),
        }
        
        # List report complexity
        if report_breakdown['list']:
            total_columns = sum(len(r.column_groups) for r in report_breakdown['list'])
            metrics.update({
                'list_report_columns': total_columns,
                'avg_columns_per_list_report': total_columns / len(report_breakdown['list'])
            })
        
        # Audit report complexity
        if report_breakdown['audit']:
            reports_with_custom_agg = len([r for r in report_breakdown['audit'] if r.custom_aggregate])
            metrics.update({
                'audit_reports_with_aggregation': reports_with_custom_agg
            })
        
        # Aggregate report complexity
        if report_breakdown['aggregate']:
            total_groups = sum(len(r.aggregate_groups) for r in report_breakdown['aggregate'])
            total_statistical = sum(len(r.statistical_groups) for r in report_breakdown['aggregate'])
            reports_with_criteria = len([r for r in report_breakdown['aggregate'] if r.aggregate_criteria])
            
            metrics.update({
                'aggregate_report_groups': total_groups,
                'aggregate_statistical_groups': total_statistical,
                'aggregate_reports_with_criteria': reports_with_criteria,
                'avg_groups_per_aggregate': total_groups / len(report_breakdown['aggregate']) if report_breakdown['aggregate'] else 0
            })
        
        return metrics
    
    def _build_report_dependency_tree(self, reports: List[Report]) -> Dict[str, Any]:
        """Build dependency tree for reports"""
        def build_dependency_node(report: Report, all_reports: List[Report], visited: set = None) -> Dict[str, Any]:
            if visited is None:
                visited = set()
            
            if report.id in visited:
                return {'id': report.id, 'name': report.name, 'circular': True}
            
            visited.add(report.id)
            
            # Build children from both search dependencies and child reports
            children = []
            
            # Add search dependencies for audit reports
            if report.report_type == 'audit' and report.direct_dependencies:
                for dep_id in report.direct_dependencies:
                    # Create a child node representing the search dependency
                    children.append({
                        'id': dep_id,
                        'name': f"Member Search ({dep_id[:8]}...)",  # Shortened GUID
                        'type': 'Search',
                        'children': []
                    })
            
            # Add child reports that have this report's ID as their parent_guid
            child_reports = [r for r in all_reports if r.parent_guid == report.id]
            for child_report in child_reports:
                children.append(build_dependency_node(child_report, all_reports, visited.copy()))
            
            return {
                'id': report.id,
                'name': report.name,
                'type': f'{report.report_type.title()} Report',
                'children': children
            }
        
        # Find true root reports (no parent_guid) and build hierarchy
        root_reports = [r for r in reports if not r.parent_guid]
        
        # If no root reports found, treat all as roots (fallback)
        if not root_reports:
            root_reports = reports
        
        return {
            'roots': [build_dependency_node(report, reports) for report in root_reports],
            'total_reports': len(reports),
            'max_depth': self._calculate_max_report_depth(reports)
        }
    
    def _calculate_max_report_depth(self, reports: List[Report]) -> int:
        """Calculate maximum dependency depth for reports"""
        report_map = {r.id: r for r in reports}
        max_depth = 1
        
        def get_depth(report: Report, visited: set = None) -> int:
            if visited is None:
                visited = set()
            
            if report.id in visited:
                return 0  # Circular reference
            
            visited.add(report.id)
            
            if not report.dependents:
                return 1
            
            max_dependent_depth = 0
            for dep_id in report.dependents:
                dependent = report_map.get(dep_id)
                if dependent:
                    depth = get_depth(dependent, visited.copy())
                    max_dependent_depth = max(max_dependent_depth, depth)
            
            return 1 + max_dependent_depth
        
        for report in reports:
            if not report.direct_dependencies:  # Root report
                depth = get_depth(report)
                max_depth = max(max_depth, depth)
        
        return max_depth