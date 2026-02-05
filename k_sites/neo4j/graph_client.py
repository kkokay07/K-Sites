"""
Graph Client for K-Sites Neo4j Integration

This module provides a clean interface to interact with the Neo4j graph database
containing KEGG pathway information, integrating Sandip's KEGG-to-Neo4j logic
into the K-Sites pipeline.
"""

import os
import logging
import time
from typing import List, Dict, Optional
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
import requests
import re

# Set up logging
logger = logging.getLogger(__name__)

class GraphClient:
    """
    Client for interacting with the Neo4j graph database containing KEGG pathway data.
    """
    
    def __init__(self):
        """
        Initialize the GraphClient with connection parameters from environment variables.
        """
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'kkokay07')
        
        # Initialize driver with connection pooling
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_lifetime=3600,
            max_connection_pool_size=10,
            connection_timeout=10,
            max_retry_time=5
        )
        
        logger.info(f"Initialized Neo4j driver for {self.uri}")

    def close(self):
        """
        Close the Neo4j driver connection.
        """
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j driver connection")

    def _run_query_with_retry(self, query: str, parameters: Optional[Dict] = None, max_retries: int = 2) -> List[Dict]:
        """
        Run a Neo4j query with retry logic.
        
        Args:
            query: Cypher query to execute
            parameters: Parameters for the query
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of records from the query
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                with self.driver.session() as session:
                    result = session.run(query, parameters or {})
                    return [record.data() for record in result]
            except (ServiceUnavailable, AuthError) as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (attempt + 1)  # 1s, 2s backoff
                    logger.warning(f"Neo4j query failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Neo4j query failed after {max_retries + 1} attempts: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error running Neo4j query: {str(e)}")
                raise
        
        # If we exhausted retries, raise the last exception
        raise last_exception

    def get_pathway_neighbors(self, gene_symbol: str, organism_taxid: str) -> List[str]:
        """
        Get genes in the same pathways as the given gene symbol for the specified organism.
        
        Args:
            gene_symbol: Gene symbol (will be resolved to Entrez ID if needed)
            organism_taxid: NCBI Taxonomy ID for the organism
            
        Returns:
            List of gene symbols in the same pathways as the input gene
        """
        try:
            # First resolve gene symbol to Entrez ID if needed
            entrez_id = self._resolve_gene_symbol(gene_symbol, organism_taxid)
            
            # Query to find genes in the same pathways as the input gene
            query = """
            MATCH (o:Organism {id: $organism_taxid})-[:HAS_PATHWAY]->(p:Pathway)<-[:HAS_GENE]-(g:Gene)
            WHERE g.id = $gene_id OR g.entrez_id = $gene_id
            WITH p
            MATCH (p)<-[:HAS_GENE]-(neighbor_gene:Gene)
            WHERE neighbor_gene.id <> $gene_id AND neighbor_gene.entrez_id <> $gene_id
            RETURN DISTINCT neighbor_gene.id AS gene_symbol
            """
            
            # Try both the original gene ID and the resolved Entrez ID
            parameters = {"gene_id": entrez_id, "organism_taxid": organism_taxid}
            results = self._run_query_with_retry(query, parameters)
            
            # Extract gene symbols from results
            neighbors = [record["gene_symbol"] for record in results if record["gene_symbol"]]
            
            logger.info(f"Found {len(neighbors)} pathway neighbors for gene {gene_symbol}")
            return neighbors
            
        except Exception as e:
            logger.warning(f"Could not retrieve pathway neighbors for gene {gene_symbol} in organism {organism_taxid}: {str(e)}")
            return []

    def _resolve_gene_symbol(self, gene_symbol: str, organism_taxid: str) -> str:
        """
        Resolve a gene symbol to an Entrez ID using NCBI services.
        
        Args:
            gene_symbol: Gene symbol to resolve
            organism_taxid: NCBI Taxonomy ID for the organism
            
        Returns:
            Resolved gene ID (either Entrez ID or original symbol if not found)
        """
        # First, try to map organism taxid to KEGG organism code
        kegg_org_code = self._map_taxid_to_kegg(organism_taxid)
        
        if kegg_org_code:
            # Try to find the gene in the KEGG database first
            kegg_gene_id = f"{kegg_org_code}:{gene_symbol}"
            
            # Check if this gene exists in our Neo4j database
            check_query = """
            MATCH (g:Gene {id: $gene_id})
            RETURN g
            """
            try:
                result = self._run_query_with_retry(check_query, {"gene_id": kegg_gene_id})
                if result:
                    return kegg_gene_id
            except:
                pass  # Continue to NCBI lookup if Neo4j check fails
        
        # Fall back to NCBI Entrez for gene symbol resolution
        try:
            # Use NCBI E-utilities to resolve gene symbol
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "gene",
                "term": f"{gene_symbol}[Gene Name] AND {organism_taxid}[Organism]",
                "retmax": 1,
                "retmode": "json"
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "esearchresult" in data and "idlist" in data["esearchresult"]:
                id_list = data["esearchresult"]["idlist"]
                if id_list:
                    entrez_id = id_list[0]
                    logger.debug(f"Resolved {gene_symbol} to Entrez ID {entrez_id}")
                    return entrez_id
                    
        except Exception as e:
            logger.debug(f"Could not resolve {gene_symbol} via NCBI: {str(e)}")
        
        # If all else fails, return the original symbol
        logger.debug(f"Returning original gene symbol {gene_symbol} as-is")
        return gene_symbol

    def _map_taxid_to_kegg(self, taxid: str) -> Optional[str]:
        """
        Map NCBI TaxID to KEGG organism code.
        
        Args:
            taxid: NCBI Taxonomy ID
            
        Returns:
            KEGG organism code if found, None otherwise
        """
        # Common mappings from NCBI TaxID to KEGG organism codes
        taxid_to_kegg = {
            "9606": "hsa",  # Homo sapiens
            "10090": "mmu",  # Mus musculus
            "10116": "rno",  # Rattus norvegicus
            "7227": "dme",   # Drosophila melanogaster
            "6239": "cel",   # Caenorhabditis elegans
            "7955": "dre",   # Danio rerio
            "4932": "sce",   # Saccharomyces cerevisiae
            "3702": "ath",   # Arabidopsis thaliana
        }
        
        return taxid_to_kegg.get(taxid)

    def test_connection(self) -> bool:
        """
        Test if the Neo4j connection is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Run a simple test query
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                return record is not None and record["test"] == 1
        except Exception as e:
            logger.warning(f"Neo4j connection test failed: {str(e)}")
            return False


# Global client instance
_graph_client = None


def get_graph_client() -> GraphClient:
    """
    Get the singleton graph client instance.
    
    Returns:
        GraphClient instance
    """
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphClient()
    return _graph_client


def get_pathway_neighbors(gene_symbol: str, organism_taxid: str) -> List[str]:
    """
    Get genes in the same pathways as the given gene symbol for the specified organism.
    
    Args:
        gene_symbol: Gene symbol (will be resolved to Entrez ID if needed)
        organism_taxid: NCBI Taxonomy ID for the organism
        
    Returns:
        List of gene symbols in the same pathways as the input gene
    """
    client = get_graph_client()
    return client.get_pathway_neighbors(gene_symbol, organism_taxid)


def close_graph_client():
    """
    Close the global graph client connection.
    """
    global _graph_client
    if _graph_client:
        _graph_client.close()
        _graph_client = None