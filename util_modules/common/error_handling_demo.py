"""
Demonstration of the standardized error handling system
Shows how to use the new error handling utilities effectively
"""

import xml.etree.ElementTree as ET
from .error_handling import (
    EMISConverterError, XMLParsingError, DataValidationError,
    ErrorSeverity, ErrorCategory, safe_execute, create_error_context
)
from .ui_error_handling import streamlit_safe_execute


def demo_xml_parsing_with_error_handling():
    """Demonstrate XML parsing with proper error handling"""
    
    def parse_xml_safely(xml_content: str):
        """Example of safe XML parsing"""
        context = create_error_context(
            operation="parse_xml_demo",
            user_data={"content_length": len(xml_content)}
        )
        
        try:
            root = ET.fromstring(xml_content)
            return root
        except ET.ParseError as e:
            raise XMLParsingError(
                message=f"Invalid XML format: {str(e)}",
                context=context,
                original_exception=e,
                severity=ErrorSeverity.HIGH
            )
    
    # Example usage
    valid_xml = "<root><item>test</item></root>"
    invalid_xml = "<root><item>test</item>"  # Missing closing tag
    
    print("=== XML Parsing Demo ===")
    
    # Test with valid XML
    try:
        result = parse_xml_safely(valid_xml)
        print("✅ Valid XML parsed successfully")
    except EMISConverterError as e:
        print(f"❌ Error: {e.get_user_friendly_message()}")
    
    # Test with invalid XML
    try:
        result = parse_xml_safely(invalid_xml)
        print("✅ Invalid XML parsed successfully (unexpected)")
    except EMISConverterError as e:
        print(f"❌ Error caught: {e.get_user_friendly_message()}")
        if e.severity == ErrorSeverity.HIGH:
            print("   → High severity error - appropriate handling required")


def demo_safe_execute():
    """Demonstrate safe_execute utility"""
    
    def risky_operation(value: int, should_fail: bool = False):
        """Simulated risky operation"""
        if should_fail:
            raise ValueError(f"Simulated failure with value: {value}")
        return value * 2
    
    print("\n=== Safe Execute Demo ===")
    
    # Test successful operation
    result = safe_execute(
        "risky_operation_success",
        risky_operation,
        5,
        should_fail=False,
        default_return=0
    )
    print(f"✅ Success: result = {result}")
    
    # Test failed operation
    result = safe_execute(
        "risky_operation_failure", 
        risky_operation,
        5,
        should_fail=True,
        default_return=0
    )
    print(f"❌ Failed: returned default = {result}")


def demo_data_validation():
    """Demonstrate data validation with error handling"""
    
    def validate_age(age: int):
        """Example validation function"""
        if not isinstance(age, int):
            raise DataValidationError(
                message="Age must be an integer",
                field_name="age",
                value=age,
                severity=ErrorSeverity.MEDIUM
            )
        
        if age < 0 or age > 150:
            raise DataValidationError(
                message="Age must be between 0 and 150",
                field_name="age", 
                value=age,
                severity=ErrorSeverity.MEDIUM
            )
        
        return True
    
    print("\n=== Data Validation Demo ===")
    
    test_cases = [25, "not_a_number", -5, 200]
    
    for test_age in test_cases:
        try:
            validate_age(test_age)
            print(f"✅ Age {test_age} is valid")
        except DataValidationError as e:
            print(f"❌ Age {test_age}: {e.get_user_friendly_message()}")


def demo_error_categories():
    """Demonstrate different error categories"""
    
    print("\n=== Error Categories Demo ===")
    
    errors = [
        XMLParsingError("XML malformed", element_name="criterion"),
        DataValidationError("Invalid email format", field_name="email", value="invalid-email"),
        EMISConverterError("File not found", category=ErrorCategory.FILE_OPERATION),
        EMISConverterError("Export failed", category=ErrorCategory.EXPORT_OPERATION),
        EMISConverterError("Unknown system error", category=ErrorCategory.SYSTEM)
    ]
    
    for error in errors:
        print(f"[{error.category.value}]: {error.get_user_friendly_message()}")


if __name__ == "__main__":
    """Run all demonstrations"""
    demo_xml_parsing_with_error_handling()
    demo_safe_execute()
    demo_data_validation()
    demo_error_categories()
    
    print("\n🎉 Error handling demonstration completed!")
    print("💡 These patterns can be used throughout the EMIS XML Converter application.")