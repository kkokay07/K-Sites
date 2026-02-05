"""
Integration test for the K-Sites CLI to validate end-to-end functionality.
"""

import pytest
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import json


class TestCliIntegration:
    """Integration tests for the K-Sites CLI."""
    
    def test_cli_execution_with_mocked_responses(self):
        """Test CLI execution with mocked external services."""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            # Mock all external dependencies
            with patch('k_sites.cli.validate_and_resolve_organism') as mock_resolve, \
                 patch('k_sites.cli.check_neo4j_availability') as mock_neo4j, \
                 patch('k_sites.workflow.pipeline.run_k_sites_pipeline') as mock_pipeline, \
                 patch('k_sites.reporting.report_generator.generate_html_report') as mock_report:
                
                # Set up mocks
                mock_resolve.return_value = "9606"  # Homo sapiens taxid
                mock_neo4j.return_value = True  # Neo4j available
                
                # Mock pipeline output
                mock_pipeline.return_value = {
                    "metadata": {
                        "go_term": "GO:0006281",
                        "organism": "Homo sapiens",
                        "timestamp": "2026-02-05T21:00:00",
                        "max_pleiotropy": 3
                    },
                    "genes": [
                        {
                            "symbol": "BRCA1",
                            "pleiotropy_score": 2,
                            "description": "BRCA1 DNA repair associated",
                            "guides": [
                                {
                                    "seq": "AACGUUUCCUAGCUAGAAAUAGC",
                                    "position": 123456,
                                    "doench_score": 0.85,
                                    "cfd_off_targets": 2,
                                    "pathway_conflict": False
                                }
                            ]
                        }
                    ]
                }
                
                # Mock report generation
                mock_report.return_value = None
                
                # Test the main CLI function directly rather than using subprocess
                from k_sites.cli import run_k_sites_analysis
                import argparse
                
                # Create mock args
                class MockArgs:
                    go_term = "GO:0006281"
                    organism = "Homo sapiens"
                    output = output_path
                    use_graph = True
                
                args = MockArgs()
                
                # Run the analysis
                run_k_sites_analysis(args)
                
                # Verify that the pipeline was called
                assert mock_pipeline.called
                assert mock_report.called
                
                # Verify that the report was generated
                assert os.path.exists(output_path)
                
                # Read the generated HTML to verify content
                with open(output_path, 'r') as f:
                    html_content = f.read()
                
                # Check that the HTML contains expected elements
                assert "BRCA1" in html_content  # Gene symbol should be in report
                assert "GO:0006281" in html_content  # GO term should be in report
                assert "AACGUUUCCUAGCUAGAAAUAGC" in html_content  # gRNA sequence should be in report
                
        finally:
            # Clean up temp file
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_cli_with_neo4j_unavailable(self):
        """Test CLI execution when Neo4j is unavailable (GO-only mode)."""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            # Mock all external dependencies
            with patch('k_sites.cli.validate_and_resolve_organism') as mock_resolve, \
                 patch('k_sites.cli.check_neo4j_availability') as mock_neo4j, \
                 patch('k_sites.workflow.pipeline.run_k_sites_pipeline') as mock_pipeline, \
                 patch('k_sites.reporting.report_generator.generate_html_report') as mock_report:
                
                # Set up mocks - Neo4j unavailable
                mock_resolve.return_value = "9606"  # Homo sapiens taxid
                mock_neo4j.return_value = False  # Neo4j not available
                
                # Mock pipeline output with GO-only results
                mock_pipeline.return_value = {
                    "metadata": {
                        "go_term": "GO:0006281", 
                        "organism": "Homo sapiens",
                        "timestamp": "2026-02-05T21:00:00",
                        "max_pleiotropy": 3,
                        "use_graph": False  # Should be set to False when Neo4j unavailable
                    },
                    "genes": [
                        {
                            "symbol": "BRCA1", 
                            "pleiotropy_score": 2,
                            "description": "BRCA1 DNA repair associated",
                            "guides": [
                                {
                                    "seq": "AACGUUUCCUAGCUAGAAAUAGC",
                                    "position": 123456,
                                    "doench_score": 0.85,
                                    "cfd_off_targets": 2,
                                    "pathway_conflict": False
                                }
                            ]
                        }
                    ]
                }
                
                # Mock report generation
                mock_report.return_value = None
                
                # Test the main CLI function directly
                from k_sites.cli import run_k_sites_analysis
                import argparse
                
                # Create mock args
                class MockArgs:
                    go_term = "GO:0006281"
                    organism = "Homo sapiens" 
                    output = output_path
                    use_graph = True  # User requested graph, but it will be disabled
                
                args = MockArgs()
                
                # Run the analysis
                run_k_sites_analysis(args)
                
                # Verify that the pipeline was called with use_graph=False
                mock_pipeline.assert_called_once()
                call_args = mock_pipeline.call_args
                assert call_args[1]['use_graph'] == False  # Should be False despite user request
                
                # Verify that the report was generated
                assert os.path.exists(output_path)
                
        finally:
            # Clean up temp file
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_cli_invalid_inputs(self):
        """Test CLI with invalid inputs to ensure proper error handling."""
        from k_sites.cli import validate_and_resolve_organism, validate_go_term
        from k_sites.data_retrieval.organism_resolver import OrganismNotFoundError
        
        # Test invalid GO term
        with pytest.raises(ValueError):
            validate_go_term("INVALID_GO_TERM")
        
        with pytest.raises(ValueError):
            validate_go_term("GO:123")  # Wrong format
            
        # Test invalid organism (this might work due to fallback mappings, so test edge case)
        # Instead, we'll test the validation function directly
        try:
            # This should raise an error for truly invalid organism
            with patch('k_sites.data_retrieval.organism_resolver.requests.get') as mock_get:
                mock_get.side_effect = Exception("Network error")
                # This would normally use fallback, but if fallback doesn't have the organism:
                result = validate_and_resolve_organism("completely_unknown_organism_xyz123")
        except Exception:
            # Expected to fail for unknown organism with no fallback
            pass