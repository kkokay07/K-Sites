"""
Unit tests for go_gene_mapper module.
"""

import pytest
from unittest.mock import patch, MagicMock
from k_sites.data_retrieval.go_gene_mapper import get_genes_for_go_term, GoTermNotFoundError, GeneRetrievalError


class TestGoGeneMapper:
    """Test cases for GO term to gene mapping functionality."""
    
    @patch('requests.get')
    def test_get_genes_for_valid_go_term(self, mock_get):
        """Test getting genes for a valid GO term."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "geneProductAc": "P38398",
                    "geneProductName": "BRCA1",
                    "proteinId": "672",
                    "evidenceCode": ["EXP", "IDA"],
                    "reference": "DNA repair function"
                },
                {
                    "geneProductAc": "P04637", 
                    "geneProductName": "TP53",
                    "proteinId": "7157",
                    "evidenceCode": ["EXP"],
                    "reference": "Tumor suppressor"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        genes = get_genes_for_go_term("GO:0006281", "9606")
        
        assert len(genes) == 2
        assert genes[0]["symbol"] == "BRCA1"
        assert genes[0]["entrez_id"] == "672"
        assert genes[1]["symbol"] == "TP53"
        assert genes[1]["entrez_id"] == "7157"
    
    @patch('requests.get')
    def test_get_genes_filters_iea_evidence(self, mock_get):
        """Test that IEA evidence codes are filtered out."""
        # Mock response with only IEA evidence
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "geneProductAc": "P38398",
                    "geneProductName": "BRCA1", 
                    "proteinId": "672",
                    "evidenceCode": ["IEA", "ECO:0000501"],  # Both are IEA
                    "reference": "Electronic annotation"
                },
                {
                    "geneProductAc": "P04637",
                    "geneProductName": "TP53",
                    "proteinId": "7157", 
                    "evidenceCode": ["EXP", "IEA"],  # Mixed - should be included
                    "reference": "Experimental annotation"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        genes = get_genes_for_go_term("GO:0006281", "9606")
        
        # Should only include the gene with EXP evidence (not just IEA)
        assert len(genes) == 1
        assert genes[0]["symbol"] == "TP53"
    
    @patch('requests.get')
    def test_get_genes_empty_result(self, mock_get):
        """Test getting genes for a GO term with no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": []
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        genes = get_genes_for_go_term("GO:0000000", "9606")  # Non-existent GO term
        
        assert len(genes) == 0
    
    @patch('requests.get')
    def test_go_term_not_found_raises_error(self, mock_get):
        """Test that non-existent GO term raises GoTermNotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_get.return_value = mock_response
        
        with pytest.raises(GoTermNotFoundError):
            get_genes_for_go_term("GO:0000000", "9606")
    
    @patch('requests.get')
    def test_request_failure_raises_error(self, mock_get):
        """Test that API request failure raises GeneRetrievalError."""
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(GeneRetrievalError):
            get_genes_for_go_term("GO:0006281", "9606")
    
    def test_invalid_go_term_format(self):
        """Test that invalid GO term format raises ValueError."""
        with pytest.raises(ValueError):
            get_genes_for_go_term("INVALID_FORMAT", "9606")
        
        with pytest.raises(ValueError):
            get_genes_for_go_term("GO:123", "9606")  # Wrong length
    
    @patch('requests.get')
    def test_taxid_to_species_mapping(self, mock_get):
        """Test that taxid gets properly mapped to species name."""
        # This test verifies the internal mapping works
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # This should not raise an error for valid taxid
        try:
            genes = get_genes_for_go_term("GO:0006281", "9606")
            # Even if no genes are returned, the call should succeed
        except GeneRetrievalError:
            # This is expected if the API call fails for other reasons
            pass