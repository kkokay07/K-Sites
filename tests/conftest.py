"""
Shared test fixtures for K-Sites unit tests.
"""

import pytest
from unittest.mock import MagicMock, patch
import json


@pytest.fixture
def mock_ncbi_esearch_response():
    """Mock NCBI esearch response for organism resolution."""
    def _mock_response(id_list):
        mock_result = MagicMock()
        mock_result.json.return_value = {
            "esearchresult": {
                "idlist": id_list,
                "count": len(id_list),
                "retmax": len(id_list),
                "retstart": 0
            }
        }
        return mock_result
    return _mock_response


@pytest.fixture
def mock_ncbi_efetch_response():
    """Mock NCBI efetch response for organism details."""
    def _mock_response(taxid, scientific_name, common_name=""):
        mock_result = MagicMock()
        mock_result.json.return_value = {
            "taxonomy": [{
                "TaxId": taxid,
                "ScientificName": scientific_name,
                "OtherNames": {
                    "GenbankCommonName": common_name
                }
            }]
        }
        return mock_result
    return _mock_response


@pytest.fixture
def mock_quickgo_response():
    """Mock QuickGO API response for GO term annotations."""
    def _mock_response(results):
        mock_result = {
            "results": results
        }
        return mock_result
    return _mock_response


@pytest.fixture
def mock_uniprot_response():
    """Mock UniProt API response."""
    def _mock_response(entry_data):
        mock_result = {
            "results": [entry_data] if entry_data else []
        }
        return mock_result
    return _mock_response


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver and session."""
    with patch('k_sites.neo4j.graph_client.GraphDatabase') as mock_driver_class:
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_transaction = MagicMock()
        
        # Configure the mock chain: driver -> session -> transaction -> result
        mock_driver_class.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        yield {
            'driver_class': mock_driver_class,
            'driver': mock_driver,
            'session': mock_session,
            'transaction': mock_transaction
        }


@pytest.fixture
def sample_gene_data():
    """Sample gene data for testing."""
    return {
        "BRCA1": {
            "symbol": "BRCA1",
            "entrez_id": "672",
            "description": "BRCA1 DNA repair associated"
        },
        "TP53": {
            "symbol": "TP53", 
            "entrez_id": "7157",
            "description": "tumor protein p53"
        }
    }


@pytest.fixture
def sample_go_annotation():
    """Sample GO annotation data."""
    return [
        {
            "goId": "GO:0006281",
            "goName": "DNA repair",
            "aspect": "biological_process",
            "evidenceCode": ["EXP", "IDA"],
            "geneProduct": {
                "id": "UniProtKB:P38398",
                "symbol": "BRCA1"
            }
        },
        {
            "goId": "GO:0006974", 
            "goName": "cellular response to DNA damage stimulus",
            "aspect": "biological_process", 
            "evidenceCode": ["EXP"],
            "geneProduct": {
                "id": "UniProtKB:P38398",
                "symbol": "BRCA1"
            }
        }
    ]