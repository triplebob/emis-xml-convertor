"""
UI Helper Functions
Reusable functions to reduce code duplication across Streamlit UI components.
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional


def create_styled_dataframe(df: pd.DataFrame, style_function: Callable) -> Any:
    """
    Create a styled dataframe with consistent formatting.
    
    Args:
        df: The DataFrame to style
        style_function: Function that returns styling for each row
        
    Returns:
        Styled DataFrame
    """
    if df.empty:
        return df
    
    return df.style.apply(style_function, axis=1)


def render_download_button(
    data: pd.DataFrame, 
    label: str, 
    filename_prefix: str,
    xml_filename: Optional[str] = None,
    key: Optional[str] = None
) -> None:
    """
    Render a standardized CSV download button.
    
    Args:
        data: DataFrame to export
        label: Button label text
        filename_prefix: Prefix for the generated filename
        xml_filename: Optional XML filename to include in export name
        key: Optional unique key for the button
    """
    if data.empty:
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if xml_filename:
        filename = f"{filename_prefix}_{xml_filename}_{timestamp}.csv"
    else:
        filename = f"{filename_prefix}_{timestamp}.csv"
    
    csv_buffer = io.StringIO()
    data.to_csv(csv_buffer, index=False)
    
    st.download_button(
        label=label,
        data=csv_buffer.getvalue(),
        file_name=filename,
        mime="text/csv",
        key=key
    )


def get_success_highlighting_function(success_column: str = 'Mapping Found'):
    """
    Get a function for highlighting rows based on mapping success.
    
    Args:
        success_column: Column name that contains success/failure status
        
    Returns:
        Function for styling DataFrame rows
    """
    def highlight_success(row):
        if row[success_column] == 'Found':
            return ['background-color: #d4edda'] * len(row)  # Light green
        else:
            return ['background-color: #f8d7da'] * len(row)  # Light red
    
    return highlight_success


def get_warning_highlighting_function():
    """
    Get a function for highlighting rows with warning colors.
    
    Returns:
        Function for styling DataFrame rows with warning colors
    """
    def highlight_warning(row):
        return ['background-color: #fff3cd'] * len(row)  # Light yellow/orange
    
    return highlight_warning


def render_section_with_data(
    title: str,
    data: List[Dict],
    info_text: str,
    empty_message: str,
    download_label: str,
    filename_prefix: str,
    highlighting_function: Optional[Callable] = None,
    additional_processing: Optional[Callable] = None
) -> None:
    """
    Render a standardized section with data table and download button with export filtering.
    
    Args:
        title: Section title
        data: List of dictionaries containing the data
        info_text: Information text to display
        empty_message: Message to show when no data
        download_label: Label for download button
        filename_prefix: Prefix for download filename
        highlighting_function: Optional function to highlight rows
        additional_processing: Optional function for additional data processing
    """
    st.subheader(title)
    if info_text:
        st.info(info_text)
    
    if data:
        df = pd.DataFrame(data)
        
        # Apply additional processing if provided
        if additional_processing:
            df = additional_processing(df)
        
        # Apply highlighting if provided
        if highlighting_function:
            styled_df = create_styled_dataframe(df, highlighting_function)
            st.dataframe(styled_df, width='stretch')
        else:
            st.dataframe(df, width='stretch')
        
        # Export filtering options and download button
        if 'Mapping Found' in df.columns:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                export_filter = st.radio(
                    "Export Filter:",
                    ["All Codes", "Only Matched", "Only Unmatched"],
                    key=f"export_filter_{filename_prefix}",
                    horizontal=True
                )
            
            with col2:
                # Filter data based on selection
                if export_filter == "Only Matched":
                    filtered_df = df[df['Mapping Found'] == 'Found']
                    export_label = download_label.replace("📥", "📥 ✅")
                    export_suffix = "_matched"
                elif export_filter == "Only Unmatched":
                    filtered_df = df[df['Mapping Found'] != 'Found']
                    export_label = download_label.replace("📥", "📥 ❌")
                    export_suffix = "_unmatched"
                else:  # All Codes
                    filtered_df = df
                    export_label = download_label
                    export_suffix = ""
                
                # Show count of filtered items
                st.caption(f"📊 {len(filtered_df)} of {len(df)} items selected for export")
                
                # Render download button with filtered data
                xml_filename = st.session_state.get('xml_filename')
                render_download_button(
                    data=filtered_df,
                    label=export_label,
                    filename_prefix=filename_prefix + export_suffix,
                    xml_filename=xml_filename,
                    key=f"download_{filename_prefix}_{export_filter.lower().replace(' ', '_')}"
                )
        else:
            # No Mapping Found column, render normal download button
            xml_filename = st.session_state.get('xml_filename')
            render_download_button(
                data=df,
                label=download_label,
                filename_prefix=filename_prefix,
                xml_filename=xml_filename
            )
    else:
        st.info(empty_message)


def render_metrics_row(metrics: List[Dict[str, Any]], columns: int = 4) -> None:
    """
    Render a row of metrics with consistent formatting and color coding.
    
    Args:
        metrics: List of metric dictionaries with 'label', 'value', and optional 'thresholds'
        columns: Number of columns to display metrics in
    """
    cols = st.columns(columns)
    
    for i, metric in enumerate(metrics):
        col_index = i % columns
        label = metric['label']
        value = metric['value']
        thresholds = metric.get('thresholds', {})
        
        with cols[col_index]:
            # Apply color coding based on thresholds
            if thresholds:
                if 'error' in thresholds and value >= thresholds['error']:
                    st.error(f"**{label}:** {value}")
                elif 'warning' in thresholds and value >= thresholds['warning']:
                    st.warning(f"**{label}:** {value}")
                elif 'success' in thresholds and value >= thresholds['success']:
                    st.success(f"**{label}:** {value}")
                else:
                    st.info(f"**{label}:** {value}")
            else:
                st.metric(label, value)


def render_success_rate_metric(
    label: str, 
    found: int, 
    total: int, 
    success_threshold: float = 90.0,
    warning_threshold: float = 70.0
) -> None:
    """
    Render a success rate metric with color coding.
    
    Args:
        label: Label for the metric
        found: Number of successful items
        total: Total number of items
        success_threshold: Threshold for success color (green)
        warning_threshold: Threshold for warning color (yellow)
    """
    if total == 0:
        st.info(f"**{label}:** No items to process")
        return
    
    rate = (found / total) * 100
    text = f"**{label}:** {rate:.0f}% ({found}/{total} found)"
    
    if rate >= success_threshold:
        st.success(text)
    elif rate >= warning_threshold:
        st.warning(text)
    else:
        st.error(text)


def create_expandable_sections(
    data_dict: Dict[str, List[Dict]], 
    section_info: Dict[str, Dict],
    item_processor: Optional[Callable] = None
) -> None:
    """
    Create expandable sections for grouped data.
    
    Args:
        data_dict: Dictionary where keys are section identifiers and values are data lists
        section_info: Dictionary containing section metadata
        item_processor: Optional function to process items before display
    """
    for section_id, items in data_dict.items():
        if not items:
            continue
            
        info = section_info.get(section_id, {})
        section_name = info.get('name', section_id)
        item_count = len(items)
        
        with st.expander(f"🔍 {section_name} ({item_count} items)"):
            if item_processor:
                processed_items = item_processor(items)
            else:
                processed_items = items
                
            df = pd.DataFrame(processed_items)
            
            # Apply standard success highlighting
            highlighting_func = get_success_highlighting_function()
            styled_df = create_styled_dataframe(df, highlighting_func)
            st.dataframe(styled_df, width='stretch')
            
            # Individual download button
            safe_name = section_name.replace(' ', '_').replace('/', '_')
            render_download_button(
                data=df,
                label=f"📥 Download {section_name}",
                filename_prefix=f"items_{safe_name}",
                xml_filename=st.session_state.get('xml_filename'),
                key=f"download_{section_id}"
            )


def add_tooltips_to_columns(df: pd.DataFrame, tooltip_map: Dict[str, str]) -> pd.DataFrame:
    """
    Add tooltips to DataFrame columns by renaming them.
    
    Args:
        df: DataFrame to modify
        tooltip_map: Dictionary mapping original column names to tooltip text
        
    Returns:
        DataFrame with renamed columns including tooltips
    """
    column_mapping = {}
    for col in df.columns:
        if col in tooltip_map:
            column_mapping[col] = f"{col} ℹ️"
            # Note: Streamlit doesn't support true tooltips in dataframes yet
            # This is a placeholder for when that feature becomes available
        else:
            column_mapping[col] = col
    
    return df.rename(columns=column_mapping)


def render_info_section(
    title: str,
    content: str,
    section_type: str = "info"
) -> None:
    """
    Render an informational section with consistent formatting.
    
    Args:
        title: Section title
        content: Section content (supports markdown)
        section_type: Type of section (info, warning, success, error)
    """
    st.subheader(title)
    
    if section_type == "warning":
        st.warning(content)
    elif section_type == "success":
        st.success(content)
    elif section_type == "error":
        st.error(content)
    else:
        st.info(content)