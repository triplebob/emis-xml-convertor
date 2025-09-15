"""
Unit tests for EMIS XML to SNOMED Translator classification logic
Tests key functions that classify codes and detect pseudo-refsets
"""

import unittest
from xml_utils import (
    is_pseudo_refset,
    get_medication_type_flag,
    is_medication_code_system,
    is_clinical_code_system,
    parse_xml_for_emis_guids
)


class TestClassificationLogic(unittest.TestCase):
    """Test classification functions for accuracy and edge cases."""
    
    def test_is_pseudo_refset_positive_cases(self):
        """Test pseudo-refset detection for known patterns."""
        # Known pseudo-refset patterns
        self.assertTrue(is_pseudo_refset("ASTTRT_COD", "Asthma treatment codes"))
        self.assertTrue(is_pseudo_refset("ASTRES_COD", "Asthma register codes"))
        self.assertTrue(is_pseudo_refset("AST_COD", "Asthma codes"))
        
        # Case insensitive
        self.assertTrue(is_pseudo_refset("asttrt_cod", "Asthma treatment codes"))
        
        # General _COD pattern (non-numeric)
        self.assertTrue(is_pseudo_refset("CUSTOM_COD", "Custom codes"))
        self.assertTrue(is_pseudo_refset("DIABETES_COD", "Diabetes codes"))
    
    def test_is_pseudo_refset_negative_cases(self):
        """Test pseudo-refset detection rejects normal identifiers."""
        # Normal SNOMED codes
        self.assertFalse(is_pseudo_refset("1234567890", "Normal SNOMED code"))
        
        # Normal descriptions without _COD
        self.assertFalse(is_pseudo_refset("Asthma Treatment", "Normal description"))
        
        # Numeric _COD patterns (these should be false positives)
        self.assertFalse(is_pseudo_refset("123_COD", "Numeric code"))
        
        # Empty/None values
        self.assertFalse(is_pseudo_refset("", ""))
        self.assertFalse(is_pseudo_refset(None, None))
        
        # Normal refset IDs
        self.assertFalse(is_pseudo_refset("999002271000000101", "SNOMED CT refset"))
    
    def test_get_medication_type_flag(self):
        """Test medication type flag assignment."""
        # Specific medication types
        self.assertEqual(
            get_medication_type_flag("SCT_CONST"), 
            "SCT_CONST (Constituent)"
        )
        self.assertEqual(
            get_medication_type_flag("SCT_DRGGRP"), 
            "SCT_DRGGRP (Drug Group)"
        )
        self.assertEqual(
            get_medication_type_flag("SCT_PREP"), 
            "SCT_PREP (Preparation)"
        )
        
        # Case insensitive
        self.assertEqual(
            get_medication_type_flag("sct_const"), 
            "SCT_CONST (Constituent)"
        )
        
        # Default case
        self.assertEqual(
            get_medication_type_flag("SNOMED_CONCEPT"), 
            "Standard Medication"
        )
        self.assertEqual(
            get_medication_type_flag(""), 
            "Standard Medication"
        )
        self.assertEqual(
            get_medication_type_flag(None), 
            "Standard Medication"
        )
    
    def test_is_medication_code_system_positive_cases(self):
        """Test medication code system detection."""
        # Explicit medication code systems
        self.assertTrue(is_medication_code_system("SCT_CONST"))
        self.assertTrue(is_medication_code_system("SCT_DRGGRP"))
        self.assertTrue(is_medication_code_system("SCT_PREP"))
        
        # Case insensitive
        self.assertTrue(is_medication_code_system("sct_const"))
        
        # Context-based medication detection
        self.assertTrue(is_medication_code_system(
            "SNOMED_CONCEPT",
            table_context="MEDICATION_ISSUES",
            column_context="DRUGCODE"
        ))
        self.assertTrue(is_medication_code_system(
            "SNOMED_CONCEPT",
            table_context="MEDICATION_COURSES",
            column_context="DRUGCODE"
        ))
        
        # Case insensitive context
        self.assertTrue(is_medication_code_system(
            "SNOMED_CONCEPT",
            table_context="medication_issues",
            column_context="drugcode"
        ))
    
    def test_is_medication_code_system_negative_cases(self):
        """Test medication code system rejection."""
        # EMIS internal codes are never medications
        self.assertFalse(is_medication_code_system("EMISINTERNAL"))
        
        # SNOMED_CONCEPT without medication context
        self.assertFalse(is_medication_code_system("SNOMED_CONCEPT"))
        
        # Wrong table context
        self.assertFalse(is_medication_code_system(
            "SNOMED_CONCEPT",
            table_context="CLINICAL_CODES",
            column_context="DRUGCODE"
        ))
        
        # Wrong column context
        self.assertFalse(is_medication_code_system(
            "SNOMED_CONCEPT",
            table_context="MEDICATION_ISSUES",
            column_context="STATUS"
        ))
        
        # Empty/None values
        self.assertFalse(is_medication_code_system(""))
        self.assertFalse(is_medication_code_system(None))
    
    def test_is_clinical_code_system_positive_cases(self):
        """Test clinical code system detection."""
        # Standard clinical codes
        self.assertTrue(is_clinical_code_system("SNOMED_CONCEPT"))
        
        # Case insensitive
        self.assertTrue(is_clinical_code_system("snomed_concept"))
        
        # Clinical codes in non-medication context
        self.assertTrue(is_clinical_code_system(
            "SNOMED_CONCEPT",
            table_context="OBSERVATIONS",
            column_context="CODEID"
        ))
    
    def test_is_clinical_code_system_negative_cases(self):
        """Test clinical code system rejection."""
        # EMIS internal codes are never clinical
        self.assertFalse(is_clinical_code_system("EMISINTERNAL"))
        
        # Medication context should not be clinical
        self.assertFalse(is_clinical_code_system(
            "SNOMED_CONCEPT",
            table_context="MEDICATION_ISSUES",
            column_context="DRUGCODE"
        ))
        
        # Non-SNOMED systems
        self.assertFalse(is_clinical_code_system("SCT_CONST"))
        self.assertFalse(is_clinical_code_system("UNKNOWN_SYSTEM"))
        
        # Empty/None values
        self.assertFalse(is_clinical_code_system(""))
        self.assertFalse(is_clinical_code_system(None))
    
    def test_code_system_mutual_exclusion(self):
        """Test that medication and clinical detection are mutually exclusive."""
        # Test cases that should be medication, not clinical
        test_cases = [
            ("SCT_CONST", None, None),
            ("SNOMED_CONCEPT", "MEDICATION_ISSUES", "DRUGCODE"),
        ]
        
        for code_system, table, column in test_cases:
            is_med = is_medication_code_system(code_system, table, column)
            is_clin = is_clinical_code_system(code_system, table, column)
            self.assertTrue(is_med, f"Should be medication: {code_system}")
            self.assertFalse(is_clin, f"Should not be clinical: {code_system}")
        
        # Test cases that should be clinical, not medication
        test_cases = [
            ("SNOMED_CONCEPT", None, None),
            ("SNOMED_CONCEPT", "OBSERVATIONS", "CODEID"),
        ]
        
        for code_system, table, column in test_cases:
            is_med = is_medication_code_system(code_system, table, column)
            is_clin = is_clinical_code_system(code_system, table, column)
            self.assertFalse(is_med, f"Should not be medication: {code_system}")
            self.assertTrue(is_clin, f"Should be clinical: {code_system}")
    
    def test_xml_parsing_basic(self):
        """Test basic XML parsing functionality."""
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <emis:search xmlns:emis="http://www.e-mis.com/emisopen">
            <emis:criterion>
                <emis:valueSet>
                    <emis:id>test-guid-1</emis:id>
                    <emis:description>Test Clinical Codes</emis:description>
                    <emis:codeSystem>SNOMED_CONCEPT</emis:codeSystem>
                    <emis:values>
                        <emis:isRefset>false</emis:isRefset>
                        <emis:includeChildren>true</emis:includeChildren>
                        <emis:value>123456789</emis:value>
                        <emis:displayName>Test Code</emis:displayName>
                    </emis:values>
                </emis:valueSet>
            </emis:criterion>
        </emis:search>"""
        
        results = parse_xml_for_emis_guids(sample_xml)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['valueSet_guid'], 'test-guid-1')
        self.assertEqual(results[0]['code_system'], 'SNOMED_CONCEPT')
        self.assertEqual(results[0]['emis_guid'], '123456789')
        self.assertEqual(results[0]['xml_display_name'], 'Test Code')
        self.assertFalse(results[0]['is_refset'])
        self.assertTrue(results[0]['include_children'])
    
    def test_xml_parsing_malformed(self):
        """Test XML parsing handles malformed input gracefully."""
        malformed_xml = "<not-valid-xml>"
        
        with self.assertRaises(Exception) as context:
            parse_xml_for_emis_guids(malformed_xml)
        
        self.assertIn("XML parsing error", str(context.exception))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_unicode_handling(self):
        """Test classification functions handle Unicode characters."""
        # Unicode in pseudo-refset detection
        self.assertTrue(is_pseudo_refset("TËST_COD", "Test with unicode"))
        
        # Unicode in medication type flags
        result = get_medication_type_flag("SNÖMËD_CONCEPT")
        self.assertEqual(result, "Standard Medication")
    
    def test_very_long_strings(self):
        """Test functions handle very long input strings."""
        long_string = "A" * 10000 + "_COD"
        
        # Should still work for pseudo-refset detection
        self.assertTrue(is_pseudo_refset(long_string, "Long description"))
        
        # Should work for medication type flags
        result = get_medication_type_flag(long_string)
        self.assertEqual(result, "Standard Medication")
    
    def test_special_characters(self):
        """Test handling of special characters in identifiers."""
        # Special characters in code systems
        self.assertFalse(is_medication_code_system("SCT@CONST"))
        self.assertFalse(is_clinical_code_system("SNOMED#CONCEPT"))
        
        # Special characters in pseudo-refset patterns
        self.assertFalse(is_pseudo_refset("TEST@COD", "Special chars"))


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)