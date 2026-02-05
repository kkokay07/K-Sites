"""
Unit tests for organism_resolver module.
"""

import pytest
from unittest.mock import patch, MagicMock
from k_sites.data_retrieval.organism_resolver import resolve_organism, OrganismNotFoundError


class TestOrganismResolver:
    """Test cases for organism resolution functionality."""
    
    def test_resolve_organism_by_taxid(self):
        """Test resolving organism by TaxID."""
        result = resolve_organism("9606")
        assert result["taxid"] == "9606"
        assert result["scientific_name"] == "Homo sapiens"
        assert result["common_name"] == "human"
    
    def test_resolve_organism_by_scientific_name(self):
        """Test resolving organism by scientific name."""
        result = resolve_organism("Homo sapiens")
        assert result["taxid"] == "9606"
        assert result["scientific_name"] == "Homo sapiens"
        assert result["common_name"] == "human"
    
    def test_resolve_organism_by_common_name(self):
        """Test resolving organism by common name."""
        result = resolve_organism("human")
        assert result["taxid"] == "9606"
        assert result["scientific_name"] == "Homo sapiens"
        assert result["common_name"] == "human"
    
    def test_resolve_organism_by_kegg_code(self):
        """Test resolving organism by KEGG code."""
        result = resolve_organism("hsa")
        assert result["taxid"] == "9606"
        assert result["scientific_name"] == "Homo sapiens"
        assert result["common_name"] == "human"
    
    def test_invalid_organism_raises_error(self, mock_ncbi_esearch_response):
        """Test that invalid organism raises OrganismNotFoundError."""
        # Mock NCBI esearch to return empty result
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "esearchresult": {
                    "idlist": [],
                    "count": 0
                }
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with pytest.raises(OrganismNotFoundError):
                resolve_organism("invalid_organism_name_that_does_not_exist")
    
    @patch('requests.get')
    def test_ncbi_lookup_success(self, mock_get, mock_ncbi_efetch_response):
        """Test successful NCBI lookup for an organism."""
        # Mock the esearch call
        esearch_response = MagicMock()
        esearch_response.json.return_value = {
            "esearchresult": {
                "idlist": ["10090"],
                "count": 1
            }
        }
        esearch_response.raise_for_status.return_value = None
        
        # Mock the efetch call
        efetch_response = mock_ncbi_efetch_response("10090", "Mus musculus", "mouse")
        
        def get_side_effect(*args, **kwargs):
            if 'esearch.fcgi' in args[0]:
                return esearch_response
            else:
                mock_efetch_resp = MagicMock()
                mock_efetch_resp.json.return_value = efetch_response
                mock_efetch_resp.raise_for_status.return_value = None
                return mock_efetch_resp
        
        mock_get.side_effect = get_side_effect
        
        result = resolve_organism("Mus musculus")
        assert result["taxid"] == "10090"
        assert result["scientific_name"] == "Mus musculus"
        assert result["common_name"] == "mouse"
    
    @patch('requests.get')
    def test_ncbi_lookup_failure_falls_back_to_mapping(self, mock_get):
        """Test that NCBI lookup failure falls back to built-in mapping."""
        # Make NCBI calls fail
        mock_get.side_effect = Exception("Network error")
        
        # Should still work with built-in mapping
        result = resolve_organism("mouse")
        assert result["taxid"] == "10090"
        assert result["scientific_name"] == "Mus musculus"
        assert result["common_name"] == "mouse"