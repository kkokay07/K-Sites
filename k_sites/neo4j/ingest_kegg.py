"""
Production-hardened KEGG to Neo4j ingestion module for K-Sites.

This module ingests KEGG pathway data into Neo4j for pathway-aware pleiotropy scoring.
Follows production hardening practices as per OpenClaw conventions.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KeggIngestionError(Exception):
    """Raised when KEGG ingestion fails."""
    pass


def _get_cache_dir() -> Path:
    """Get the cache directory path."""
    return Path.home() / ".openclaw" / "workspace" / "k-sites" / ".cache"


def _get_checkpoint_file(taxid: str) -> Path:
    """Get the checkpoint file path for a specific organism."""
    cache_dir = _get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"kegg_ingest_checkpoint_{taxid}.json"


def _save_checkpoint(taxid: str, progress_data: Dict) -> None:
    """Save ingestion progress to checkpoint file."""
    checkpoint_file = _get_checkpoint_file(taxid)
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
        logger.debug(f"Saved checkpoint for taxid {taxid}")
    except Exception as e:
        logger.warning(f"Could not save checkpoint: {e}")


def _load_checkpoint(taxid: str) -> Optional[Dict]:
    """Load ingestion progress from checkpoint file."""
    checkpoint_file = _get_checkpoint_file(taxid)
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded checkpoint for taxid {taxid}, resuming from pathway: {data.get('last_pathway', 'None')}")
            return data
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")
    return None


def _make_kegg_request(url: str, params: Dict = None, max_retries: int = 3) -> requests.Response:
    """
    Make a request to KEGG API with rate limiting and retry logic.
    
    Args:
        url: KEGG API URL
        params: Request parameters
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response object
    """
    # Rate limiting: max 2 requests per second
    time.sleep(0.5)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            # Check for rate limiting or server errors
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) + (attempt * 0.5)
                    logger.warning(f"Received {response.status_code} from KEGG, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()
            else:
                response.raise_for_status()
                
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + (attempt * 0.5)
                logger.warning(f"Request failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(wait_time)
            else:
                raise KeggIngestionError(f"Failed to make request after {max_retries} attempts: {e}")


def _taxid_to_kegg_code(taxid: str) -> Optional[str]:
    """
    Map NCBI TaxID to KEGG organism code.
    
    Args:
        taxid: NCBI Taxonomy ID
        
    Returns:
        KEGG organism code if found, None otherwise
    """
    taxid_to_kegg = {
        "9606": "hsa",      # Homo sapiens
        "10090": "mmu",     # Mus musculus
        "10116": "rno",     # Rattus norvegicus
        "7227": "dme",      # Drosophila melanogaster
        "6239": "cel",      # Caenorhabditis elegans
        "7955": "dre",      # Danio rerio
        "4932": "sce",      # Saccharomyces cerevisiae
        "3702": "ath",      # Arabidopsis thaliana
        "9913": "bta",      # Bos taurus
        "9031": "gga",      # Gallus gallus
    }
    
    return taxid_to_kegg.get(taxid)


def _create_neo4j_constraints(driver) -> None:
    """
    Create Neo4j constraints for KEGG data.
    
    Args:
        driver: Neo4j driver instance
    """
    constraints = [
        "CREATE CONSTRAINT organism_id IF NOT EXISTS FOR (o:Organism) REQUIRE o.id IS UNIQUE",
        "CREATE CONSTRAINT pathway_id IF NOT EXISTS FOR (p:Pathway) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT gene_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE",
        "CREATE CONSTRAINT gene_entrez_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.entrez_id IS UNIQUE"
    ]
    
    with driver.session() as session:
        for constraint in constraints:
            session.run(constraint)
            logger.debug(f"Applied constraint: {constraint}")


def _fetch_kegg_pathways(kegg_code: str) -> List[Dict[str, str]]:
    """
    Fetch all pathways for an organism from KEGG.
    
    Args:
        kegg_code: KEGG organism code (e.g., 'hsa')
        
    Returns:
        List of pathway dictionaries with 'id' and 'name'
    """
    url = f"https://rest.kegg.jp/list/pathway/{kegg_code}"
    response = _make_kegg_request(url)
    
    pathways = []
    for line in response.text.strip().split('\n'):
        if line:
            parts = line.split('\t')
            if len(parts) >= 2:
                pathway_id = parts[0].replace("path:", "")
                pathway_name = parts[1]
                pathways.append({"id": pathway_id, "name": pathway_name})
    
    logger.info(f"Fetched {len(pathways)} pathways for organism {kegg_code}")
    return pathways


def _fetch_pathway_genes(kegg_code: str, pathway_id: str) -> List[Dict[str, str]]:
    """
    Fetch genes in a specific pathway from KEGG.
    
    Args:
        kegg_code: KEGG organism code
        pathway_id: KEGG pathway ID
        
    Returns:
        List of gene dictionaries with 'kegg_id' and 'symbol'
    """
    # First get genes linked to this pathway
    url = f"https://rest.kegg.jp/link/genes/{pathway_id}"
    response = _make_kegg_request(url)
    
    kegg_gene_ids = []
    for line in response.text.strip().split('\n'):
        if line:
            parts = line.split('\t')
            if len(parts) >= 2:
                pathway_entry, gene_entry = parts[0], parts[1]
                # Only take genes from the target organism
                if gene_entry.startswith(f"{kegg_code}:"):
                    kegg_gene_ids.append(gene_entry)
    
    if not kegg_gene_ids:
        return []
    
    # Convert KEGG gene IDs to Entrez IDs
    # Join the gene IDs with '+' for the conv API call
    gene_ids_str = '+'.join(kegg_gene_ids)
    url = f"https://rest.kegg.jp/conv/ncbi-geneid/{gene_ids_str}"
    response = _make_kegg_request(url)
    
    genes = []
    for line in response.text.strip().split('\n'):
        if line:
            parts = line.split('\t')
            if len(parts) >= 2:
                kegg_gene_id = parts[0]  # e.g., hsa:1234
                entrez_id = parts[1].replace("ncbi-geneid:", "")  # e.g., 1234
                
                # Extract symbol from KEGG ID (part after ':')
                symbol = kegg_gene_id.split(':')[-1]
                
                genes.append({
                    "kegg_id": kegg_gene_id,
                    "entrez_id": entrez_id,
                    "symbol": symbol
                })
    
    logger.debug(f"Found {len(genes)} genes for pathway {pathway_id}")
    return genes


def _ingest_pathway_to_neo4j(driver, kegg_code: str, pathway: Dict[str, str], genes: List[Dict[str, str]]) -> None:
    """
    Ingest a single pathway and its genes into Neo4j.
    
    Args:
        driver: Neo4j driver instance
        kegg_code: KEGG organism code
        pathway: Pathway dictionary with 'id' and 'name'
        genes: List of gene dictionaries
    """
    with driver.session() as session:
        # Create pathway node
        session.run("""
            MERGE (p:Pathway {id: $pathway_id})
            SET p.name = $pathway_name,
                p.kegg_code = $kegg_code
        """, {
            "pathway_id": pathway["id"],
            "pathway_name": pathway["name"],
            "kegg_code": kegg_code
        })
        
        # Create organism node and relationship
        session.run("""
            MERGE (o:Organism {id: $organism_id})
            WITH o
            MATCH (p:Pathway {id: $pathway_id})
            MERGE (o)-[:HAS_PATHWAY]->(p)
        """, {
            "organism_id": kegg_code,
            "pathway_id": pathway["id"]
        })
        
        # Create gene nodes and relationships
        for gene in genes:
            session.run("""
                MERGE (g:Gene {id: $gene_id})
                SET g.entrez_id = $entrez_id,
                    g.symbol = $symbol
                WITH g
                MATCH (p:Pathway {id: $pathway_id})
                MERGE (g)-[:PARTICIPATES_IN]->(p)
            """, {
                "gene_id": gene["kegg_id"],
                "entrez_id": gene["entrez_id"],
                "symbol": gene["symbol"],
                "pathway_id": pathway["id"]
            })


def _validate_ingestion(driver, kegg_code: str) -> Dict[str, int]:
    """
    Validate the ingestion by checking connectivity.
    
    Args:
        driver: Neo4j driver instance
        kegg_code: KEGG organism code
        
    Returns:
        Dictionary with validation metrics
    """
    with driver.session() as session:
        # Count genes for this organism
        gene_count_result = session.run("""
            MATCH (o:Organism {id: $organism_id})-[:HAS_PATHWAY]->()-[:PARTICIPATES_IN]-(g:Gene)
            RETURN count(DISTINCT g) AS gene_count
        """, {"organism_id": kegg_code})
        
        gene_count = gene_count_result.single()["gene_count"]
        
        # Count pathways for this organism
        pathway_count_result = session.run("""
            MATCH (o:Organism {id: $organism_id})-[:HAS_PATHWAY]->(p:Pathway)
            RETURN count(p) AS pathway_count
        """, {"organism_id": kegg_code})
        
        pathway_count = pathway_count_result.single()["pathway_count"]
        
        # Count gene-pathway relationships for this organism
        relationship_count_result = session.run("""
            MATCH (o:Organism {id: $organism_id})-[:HAS_PATHWAY]->()-[:PARTICIPATES_IN]-(g:Gene)
            RETURN count(*) AS relationship_count
        """, {"organism_id": kegg_code})
        
        relationship_count = relationship_count_result.single()["relationship_count"]
        
        logger.info(f"Validation for {kegg_code}: {gene_count} genes, {pathway_count} pathways, {relationship_count} relationships")
        
        return {
            "genes": gene_count,
            "pathways": pathway_count,
            "relationships": relationship_count
        }


def _clear_existing_data(driver, kegg_code: str) -> None:
    """
    Clear existing KEGG data for an organism.
    
    Args:
        driver: Neo4j driver instance
        kegg_code: KEGG organism code
    """
    logger.info(f"Clearing existing KEGG data for organism {kegg_code}")
    
    with driver.session() as session:
        # Delete relationships and genes for this organism's pathways
        session.run("""
            MATCH (o:Organism {id: $organism_id})-[:HAS_PATHWAY]->(p:Pathway)<-[:PARTICIPATES_IN]-(g:Gene)
            DETACH DELETE g, p
        """, {"organism_id": kegg_code})
        
        # Delete the organism itself
        session.run("""
            MATCH (o:Organism {id: $organism_id})
            DETACH DELETE o
        """, {"organism_id": kegg_code})


def ingest_kegg_organism(taxid: str, organism_name: str, force: bool = False, show_progress: bool = True) -> Dict:
    """
    Ingest KEGG pathway data for a specific organism into Neo4j.
    
    Args:
        taxid: NCBI Taxonomy ID
        organism_name: Organism scientific name
        force: Whether to re-ingest and clear existing data
        show_progress: Whether to show progress updates
        
    Returns:
        Dictionary with ingestion statistics
    """
    logger.info(f"Starting KEGG ingestion for organism: {organism_name} (TaxID: {taxid})")
    
    # Map TaxID to KEGG code
    kegg_code = _taxid_to_kegg_code(taxid)
    if not kegg_code:
        raise KeggIngestionError(f"Cannot map TaxID {taxid} to KEGG organism code")
    
    logger.info(f"Mapped TaxID {taxid} to KEGG code {kegg_code}")
    
    # Connect to Neo4j
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'kkokay07')
    
    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password),
        max_connection_lifetime=3600,
        max_connection_pool_size=10
    )
    
    try:
        # Test connection
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info("Connected to Neo4j successfully")
        
        # Create constraints
        _create_neo4j_constraints(driver)
        
        # Clear existing data if force is True
        if force:
            _clear_existing_data(driver, kegg_code)
        
        # Load checkpoint if available
        checkpoint = _load_checkpoint(taxid)
        start_pathway_idx = 0
        processed_pathways = set()
        
        if checkpoint and not force:
            processed_pathways = set(checkpoint.get('processed_pathways', []))
            logger.info(f"Resuming from checkpoint - already processed {len(processed_pathways)} pathways")
        
        # Fetch pathways
        pathways = _fetch_kegg_pathways(kegg_code)
        total_pathways = len(pathways)
        
        if show_progress:
            logger.info(f"Processing {total_pathways} pathways for {organism_name}")
        
        # Process each pathway
        successful_ingests = 0
        failed_ingests = 0
        
        for idx, pathway in enumerate(pathways):
            pathway_id = pathway["id"]
            
            # Skip if already processed
            if pathway_id in processed_pathways:
                if show_progress and idx % 50 == 0:
                    logger.info(f"Progress: {idx}/{total_pathways} pathways (skipping already processed)")
                continue
            
            try:
                if show_progress and idx % 10 == 0:
                    logger.info(f"Processing pathway {idx+1}/{total_pathways}: {pathway_id}")
                
                # Fetch genes for this pathway
                genes = _fetch_pathway_genes(kegg_code, pathway_id)
                
                # Ingest pathway and genes
                _ingest_pathway_to_neo4j(driver, kegg_code, pathway, genes)
                
                # Mark as processed
                processed_pathways.add(pathway_id)
                successful_ingests += 1
                
                # Save checkpoint periodically
                if successful_ingests % 10 == 0:
                    checkpoint_data = {
                        "taxid": taxid,
                        "organism_name": organism_name,
                        "kegg_code": kegg_code,
                        "processed_pathways": list(processed_pathways),
                        "last_pathway": pathway_id,
                        "successful_ingests": successful_ingests,
                        "failed_ingests": failed_ingests
                    }
                    _save_checkpoint(taxid, checkpoint_data)
                
            except Exception as e:
                logger.warning(f"Failed to process pathway {pathway_id}: {str(e)}")
                failed_ingests += 1
                continue  # Continue with next pathway
        
        # Final checkpoint
        checkpoint_data = {
            "taxid": taxid,
            "organism_name": organism_name,
            "kegg_code": kegg_code,
            "processed_pathways": list(processed_pathways),
            "last_pathway": pathways[-1]["id"] if pathways else "none",
            "successful_ingests": successful_ingests,
            "failed_ingests": failed_ingests,
            "completed": True
        }
        _save_checkpoint(taxid, checkpoint_data)
        
        # Validate the ingestion
        validation_results = _validate_ingestion(driver, kegg_code)
        
        results = {
            "taxid": taxid,
            "organism_name": organism_name,
            "kegg_code": kegg_code,
            "total_pathways": total_pathways,
            "successful_pathways": successful_ingests,
            "failed_pathways": failed_ingests,
            "validation": validation_results
        }
        
        logger.info(f"Ingestion completed for {organism_name}: {successful_ingests}/{total_pathways} pathways processed")
        
        return results
        
    except Exception as e:
        logger.error(f"KEGG ingestion failed: {str(e)}")
        raise
    finally:
        driver.close()
        logger.info("Neo4j connection closed")


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="KEGG to Neo4j ingestion for K-Sites")
    parser.add_argument("--taxid", required=True, help="NCBI Taxonomy ID (e.g., 9606)")
    parser.add_argument("--organism", required=True, help="Organism name (e.g., 'Homo sapiens')")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion (clear existing data)")
    
    args = parser.parse_args()
    
    try:
        results = ingest_kegg_organism(
            taxid=args.taxid,
            organism_name=args.organism,
            force=args.force
        )
        
        print(f"\nIngestion completed successfully!")
        print(f"Organism: {results['organism_name']} (TaxID: {results['taxid']})")
        print(f"KEGG Code: {results['kegg_code']}")
        print(f"Pathways processed: {results['successful_pathways']}/{results['total_pathways']}")
        print(f"Genes ingested: {results['validation']['genes']}")
        print(f"Pathways in DB: {results['validation']['pathways']}")
        print(f"Gene-pathway relationships: {results['validation']['relationships']}")
        
        if results['failed_pathways'] > 0:
            print(f"Warning: {results['failed_pathways']} pathways failed to process")
        
    except KeggIngestionError as e:
        logger.error(f"Ingestion error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()