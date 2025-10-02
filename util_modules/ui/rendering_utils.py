"""
Reusable UI rendering utilities for Streamlit applications
Provides standardized components and styling patterns
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Union


def render_info_box(message: str, box_type: str = "info", icon: str = None) -> None:
    """
    Render a standardized info box with consistent styling
    
    Args:
        message: The message to display
        box_type: Type of box ('info', 'success', 'warning', 'error')
        icon: Optional icon to display before the message
    """
    if icon:
        message = f"{icon} {message}"
    
    if box_type == "info":
        st.info(message)
    elif box_type == "success":
        st.success(message)
    elif box_type == "warning":
        st.warning(message)
    elif box_type == "error":
        st.error(message)
    else:
        st.info(message)


def render_metric_card(title: str, value: Union[str, int, float], 
                      delta: Optional[str] = None, help_text: Optional[str] = None) -> None:
    """
    Render a metric card with consistent formatting
    
    Args:
        title: The metric title
        value: The metric value
        delta: Optional delta value
        help_text: Optional help text
    """
    st.metric(
        label=title,
        value=value,
        delta=delta,
        help=help_text
    )


def render_expandable_section(title: str, content_func, expanded: bool = False,
                            icon: str = None, help_text: str = None) -> None:
    """
    Render an expandable section with consistent styling
    
    Args:
        title: Section title
        content_func: Function to call to render section content
        expanded: Whether section should be expanded by default
        icon: Optional icon for the title
        help_text: Optional help text
    """
    display_title = f"{icon} {title}" if icon else title
    
    with st.expander(display_title, expanded=expanded, help=help_text):
        content_func()


def create_two_column_layout(left_ratio: float = 1.0, right_ratio: float = 1.0):
    """
    Create a standardized two-column layout
    
    Args:
        left_ratio: Ratio for left column width
        right_ratio: Ratio for right column width
        
    Returns:
        Tuple of (left_column, right_column)
    """
    return st.columns([left_ratio, right_ratio])


def create_three_column_layout(ratios: List[float] = None):
    """
    Create a standardized three-column layout
    
    Args:
        ratios: List of ratios for column widths, defaults to [1, 1, 1]
        
    Returns:
        Tuple of (col1, col2, col3)
    """
    if ratios is None:
        ratios = [1, 1, 1]
    return st.columns(ratios)


def create_tabs_layout(tab_names: List[str]):
    """
    Create a standardized tabs layout
    
    Args:
        tab_names: List of tab names
        
    Returns:
        List of tab objects
    """
    return st.tabs(tab_names)


def apply_custom_styling():
    """Apply consistent custom styling across the application"""
    st.markdown("""
    <style>
    /* Custom styling for better readability */
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    
    .stExpander > div:first-child {
        background-color: #f8f9fa;
    }
    
    /* Consistent spacing for metrics */
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    
    /* Color coding for different message types */
    .success-box {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border-color: #ffeaa7;
        color: #856404;
    }
    
    .error-box {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
    }
    
    /* Table styling improvements */
    .dataframe tbody tr:hover {
        background-color: #f5f5f5;
    }
    
    /* Consistent button styling */
    .stButton > button {
        border-radius: 4px;
        border: 1px solid #ccc;
        background-color: #fff;
        color: #333;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #f8f9fa;
        border-color: #007bff;
    }
    </style>
    """, unsafe_allow_html=True)


def render_data_table(df: pd.DataFrame, key: str = None, 
                     height: int = None, width: str = 'stretch') -> None:
    """
    Render a data table with consistent styling
    
    Args:
        df: DataFrame to display
        key: Unique key for the dataframe
        height: Height of the table
        width: Table width ('stretch' for full container width, 'content' for content width)
    """
    st.dataframe(
        df,
        key=key,
        height=height,
        width=width
    )


def render_progress_indicator(current: int, total: int, message: str = "") -> None:
    """
    Render a progress indicator with consistent styling
    
    Args:
        current: Current progress value
        total: Total progress value
        message: Optional message to display
    """
    progress = current / total if total > 0 else 0
    st.progress(progress)
    
    if message:
        st.caption(f"{message} ({current}/{total})")
    else:
        st.caption(f"Progress: {current}/{total}")


def render_status_badge(status: str, status_type: str = "info") -> str:
    """
    Generate HTML for a status badge
    
    Args:
        status: Status text
        status_type: Type of status ('success', 'warning', 'error', 'info')
        
    Returns:
        HTML string for the badge
    """
    color_map = {
        'success': '#28a745',
        'warning': '#ffc107', 
        'error': '#dc3545',
        'info': '#17a2b8'
    }
    
    color = color_map.get(status_type, '#17a2b8')
    
    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.125rem;
    ">{status}</span>
    """


def render_classification_badge(classification: str) -> str:
    """
    Render a classification badge with appropriate styling
    
    Args:
        classification: The classification text
        
    Returns:
        HTML string for the badge
    """
    if "[Search]" in classification:
        return render_status_badge(classification, "info")
    elif "[Report]" in classification:
        return render_status_badge(classification, "success")
    else:
        return render_status_badge(classification, "warning")


def render_collapsible_content(title: str, content: str, expanded: bool = False) -> None:
    """
    Render collapsible content with standardized styling
    
    Args:
        title: Title for the collapsible section
        content: Content to display when expanded
        expanded: Whether to expand by default
    """
    with st.expander(title, expanded=expanded):
        st.markdown(content)


def render_two_column_metrics(left_metrics: List[Dict], right_metrics: List[Dict]) -> None:
    """
    Render metrics in a two-column layout
    
    Args:
        left_metrics: List of metric dictionaries for left column
        right_metrics: List of metric dictionaries for right column
    """
    col1, col2 = create_two_column_layout()
    
    with col1:
        for metric in left_metrics:
            render_metric_card(**metric)
    
    with col2:
        for metric in right_metrics:
            render_metric_card(**metric)


def create_navigation_selectbox(options: List[str], label: str, key: str = None,
                              default_index: int = 0, help_text: str = None) -> str:
    """
    Create a standardized navigation selectbox
    
    Args:
        options: List of options
        label: Label for the selectbox
        key: Unique key
        default_index: Default selected index
        help_text: Optional help text
        
    Returns:
        Selected option
    """
    return st.selectbox(
        label,
        options=options,
        index=default_index,
        key=key,
        help=help_text
    )


def render_section_header(title: str, description: str = None, divider: bool = True) -> None:
    """
    Render a standardized section header
    
    Args:
        title: Section title
        description: Optional description
        divider: Whether to add a divider after the header
    """
    st.markdown(f"### {title}")
    
    if description:
        st.markdown(description)
    
    if divider:
        st.markdown("---")


def render_debug_section(content_func, title: str = "🔍 Debug Information", 
                        expanded: bool = False) -> None:
    """
    Render a standardized debug section
    
    Args:
        content_func: Function to render debug content
        title: Title for the debug section
        expanded: Whether to expand by default
    """
    render_expandable_section(title, content_func, expanded=expanded)


def create_action_buttons_row(buttons: List[Dict]) -> None:
    """
    Create a row of action buttons with consistent spacing
    
    Args:
        buttons: List of button dictionaries with 'label', 'key', and optional 'help' keys
    """
    if not buttons:
        return
        
    # Create columns for buttons
    cols = st.columns(len(buttons))
    
    for i, button_config in enumerate(buttons):
        with cols[i]:
            st.button(
                button_config['label'],
                key=button_config.get('key'),
                help=button_config.get('help')
            )