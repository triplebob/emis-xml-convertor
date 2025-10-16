"""
Debug Logging Utility
Provides optional debug logging for audit trails and troubleshooting.
"""

import logging
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import unittest
import sys
import io
from contextlib import redirect_stdout, redirect_stderr


class EMISDebugLogger:
    """
    Debug logger for EMIS XML to SNOMED translation process.
    Provides structured logging for audit trails and troubleshooting.
    """
    
    def __init__(self, enable_debug: bool = False):
        """
        Initialize the debug logger.
        
        Args:
            enable_debug: Whether to enable debug logging
        """
        self.enable_debug = enable_debug
        self.logger = logging.getLogger('emis_translator')
        
        if self.enable_debug and not self.logger.handlers:
            # Configure logger
            self.logger.setLevel(logging.DEBUG)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
    
    def log_xml_processing_start(self, filename: str, file_size: int) -> None:
        """Log the start of XML processing."""
        if not self.enable_debug:
            return
            
        self.logger.info(f"Starting XML processing for file: {filename} (size: {file_size} bytes)")
    
    def log_xml_parsing_result(self, emis_guids: List[Dict]) -> None:
        """Log XML parsing results."""
        if not self.enable_debug:
            return
            
        unique_guids = set(guid['emis_guid'] for guid in emis_guids)
        unique_valuesets = set(guid['valueSet_guid'] for guid in emis_guids)
        
        self.logger.info(f"XML parsing completed: {len(emis_guids)} total entries, "
                        f"{len(unique_guids)} unique GUIDs, {len(unique_valuesets)} unique valueSets")
        
        # Log code system distribution
        code_systems = {}
        for guid in emis_guids:
            system = guid['code_system']
            code_systems[system] = code_systems.get(system, 0) + 1
        
        self.logger.debug(f"Code system distribution: {json.dumps(code_systems, indent=2)}")
    
    def log_pseudo_refset_detection(self, pseudo_refsets: List[str]) -> None:
        """Log pseudo-refset detection results."""
        if not self.enable_debug:
            return
            
        self.logger.info(f"Pseudo-refset detection: {len(pseudo_refsets)} pseudo-refsets found")
        for refset_id in pseudo_refsets:
            self.logger.debug(f"Detected pseudo-refset: {refset_id}")
    
    def log_classification_results(self, results: Dict[str, List]) -> None:
        """Log classification results summary."""
        if not self.enable_debug:
            return
            
        clinical_count = len(results.get('clinical', []))
        medication_count = len(results.get('medications', []))
        refset_count = len(results.get('refsets', []))
        pseudo_refset_count = len(results.get('pseudo_refsets', []))
        
        self.logger.info(f"Classification results: {clinical_count} clinical, "
                        f"{medication_count} medications, {refset_count} refsets, "
                        f"{pseudo_refset_count} pseudo-refsets")
    
    def log_lookup_performance(self, lookup_stats: Dict[str, Any]) -> None:
        """Log lookup table performance metrics."""
        if not self.enable_debug:
            return
            
        self.logger.info(f"Lookup performance: {lookup_stats.get('total_lookups', 0)} lookups, "
                        f"{lookup_stats.get('successful_lookups', 0)} successful, "
                        f"{lookup_stats.get('lookup_time_ms', 0):.2f}ms average")
    
    def log_error(self, error: Exception, context: str = "") -> None:
        """Log errors with context."""
        if not self.enable_debug:
            return
            
        context_msg = f" in {context}" if context else ""
        self.logger.error(f"Error{context_msg}: {str(error)}", exc_info=True)
    
    def log_user_action(self, action: str, details: Optional[Dict] = None) -> None:
        """Log user actions for audit trail."""
        if not self.enable_debug:
            return
            
        details_str = f" - Details: {json.dumps(details)}" if details else ""
        self.logger.info(f"User action: {action}{details_str}")
    
    def log_processing_complete(self, total_time: float, success_rate: float) -> None:
        """Log processing completion summary."""
        if not self.enable_debug:
            return
            
        self.logger.info(f"Processing completed in {total_time:.2f}s with "
                        f"{success_rate:.1f}% success rate")


def get_debug_logger() -> EMISDebugLogger:
    """
    Get a debug logger instance based on Streamlit settings.
    
    Returns:
        EMISDebugLogger instance
    """
    # Check if debug mode is enabled via Streamlit session state or environment
    enable_debug = st.session_state.get('debug_mode', False)
    
    return EMISDebugLogger(enable_debug)


def run_test_suite(test_module: str) -> tuple[bool, str]:
    """
    Run a specific test module and return results.
    
    Args:
        test_module: Name of the test module (e.g., 'test_performance')
        
    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        import sys
        import os
        
        # Add the project root to Python path if not already there
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Import the test module
        if test_module == 'test_performance':
            import tests.test_performance as test_perf
            suite = unittest.TestLoader().loadTestsFromModule(test_perf)
        else:
            return False, f"Unknown test module: {test_module}"
        
        # Capture output
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        
        with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
            runner = unittest.TextTestRunner(
                stream=output_buffer,
                verbosity=2,
                buffer=True
            )
            result = runner.run(suite)
        
        # Combine stdout and stderr
        output = output_buffer.getvalue()
        errors = error_buffer.getvalue()
        if errors:
            output += "\n" + errors
        
        # Add detailed failure information
        if not result.wasSuccessful():
            output += f"\n\n=== TEST SUMMARY ===\n"
            output += f"Tests run: {result.testsRun}\n"
            output += f"Failures: {len(result.failures)}\n"
            output += f"Errors: {len(result.errors)}\n"
            
            if result.failures:
                output += "\n=== FAILURES ===\n"
                for test, traceback in result.failures:
                    output += f"\nFAILED: {test}\n{traceback}\n"
            
            if result.errors:
                output += "\n=== ERRORS ===\n"
                for test, traceback in result.errors:
                    output += f"\nERROR: {test}\n{traceback}\n"
            
        success = result.wasSuccessful()
        return success, output
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return False, f"Error running tests: {str(e)}\n\nFull traceback:\n{error_details}"


def render_debug_controls() -> None:
    """
    Render debug controls in Streamlit sidebar as a collapsible section.
    Only shows in local development environment.
    """
    import os
    
    # Detect if running in Streamlit Cloud environment
    is_cloud = (os.getenv('STREAMLIT_SHARING_MODE') or 
                os.getenv('HOSTNAME', '').startswith('streamlit') or
                'streamlit.app' in os.getenv('STREAMLIT_SERVER_HEADLESS', '') or
                os.path.exists('/.streamlit'))
    
    # Only show debug options in local environment
    if not is_cloud:
        with st.sidebar.expander("🐛 Debug Options", expanded=False):
            # Debug mode toggle
            debug_mode = st.checkbox(
                "Enable Debug Logging",
                value=st.session_state.get('debug_mode', False),
                help="Enable detailed logging for troubleshooting and audit trails"
            )
            
            st.session_state['debug_mode'] = debug_mode
            
            if debug_mode:
                st.info("Debug logging is enabled. Check console output for detailed logs.")
                
                # Option to download debug logs
                if st.button("📁 Export Debug Session"):
                    debug_info = {
                        'session_id': st.session_state.get('session_id', 'unknown'),
                        'timestamp': datetime.now().isoformat(),
                        'debug_enabled': True,
                        'processed_files': st.session_state.get('processed_files', []),
                        'lookup_table_info': {
                            'loaded': st.session_state.get('lookup_df') is not None,
                            'rows': len(st.session_state.get('lookup_df', [])),
                            'columns': list(st.session_state.get('lookup_df', {}).columns) if st.session_state.get('lookup_df') is not None else []
                        }
                    }
                    
                    debug_json = json.dumps(debug_info, indent=2, default=str)
                    
                    st.download_button(
                        label="💾 Download Debug Info",
                        data=debug_json,
                        file_name=f"emis_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            # Cache Generation Section
            st.markdown("---")
            st.markdown("**⚡ Cache Generation**")
            
            # Generate GitHub cache button
            if st.button("🔨 Generate Cache"):
                st.info("🔐 Cache will be encrypted using GZIP_TOKEN from secrets")
                try:
                    # Import required modules
                    from .caching.lookup_cache import generate_cache_for_github
                    import os
                    
                    # Get lookup table data
                    lookup_df = st.session_state.get('lookup_df')
                    snomed_code_col = st.session_state.get('snomed_code_col', 'SNOMED Code')
                    emis_guid_col = st.session_state.get('emis_guid_col', 'EMIS GUID')
                    version_info = st.session_state.get('lookup_version_info')
                    
                    if lookup_df is None or lookup_df.empty:
                        st.error("❌ No lookup table loaded. Please check that the app has loaded the lookup table.")
                    else:
                        with st.spinner("Generating EMIS lookup cache for GitHub..."):
                            # Create .cache directory if it doesn't exist
                            cache_dir = ".cache"
                            os.makedirs(cache_dir, exist_ok=True)
                            
                            # Generate the cache
                            success = generate_cache_for_github(
                                lookup_df=lookup_df,
                                snomed_code_col=snomed_code_col,
                                emis_guid_col=emis_guid_col,
                                output_dir=cache_dir,
                                version_info=version_info
                            )
                            
                            if success:
                                st.success("✅ Encrypted GitHub cache generated successfully!")
                                st.info("💡 Check the `.cache/` directory for the generated encrypted file. Commit and push it to make it available to all users.")
                            else:
                                st.error("❌ Failed to generate GitHub cache")
                
                except Exception as e:
                    st.error(f"❌ Cache generation failed: {str(e)}")
            
            st.caption("💡 Generates pre-built cache for GitHub deployment - saves build time for all users")
            
            # Test Runner Section
            st.markdown("---")
            st.markdown("**🧪 Test Runner**")
            
            # Performance tests
            if st.button("⚡ Performance Tests"):
                with st.spinner("Running performance tests..."):
                    success, output = run_test_suite('test_performance')
                
                if success:
                    st.success("✅ Performance tests passed!")
                else:
                    st.error("❌ Performance tests failed!")
                
                with st.expander("📄 Performance Test Output"):
                    st.code(output)
            
            st.caption("💡 Verify memory tracking, cloud environment detection, and performance optimization features")


def add_performance_logging(func):
    """
    Decorator to add performance logging to functions.
    
    Args:
        func: Function to wrap with performance logging
        
    Returns:
        Wrapped function with performance logging
    """
    def wrapper(*args, **kwargs):
        logger = get_debug_logger()
        
        start_time = datetime.now()
        logger.logger.debug(f"Starting {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.logger.debug(f"Completed {func.__name__} in {duration:.3f}s")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.log_error(e, f"{func.__name__} after {duration:.3f}s")
            raise
    
    return wrapper