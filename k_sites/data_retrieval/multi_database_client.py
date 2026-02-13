"""
Multi-Database Integration Client for K-Sites

Queries GO.org, UniProt, and KEGG SIMULTANEOUSLY for comprehensive gene data.
This is a CRITICAL component for non-pleiotropic gene identification.
"""

import logging
import requests
import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Set up logging
logger = logging.getLogger(__name__)

# API Rate limiting
RATE_LIMIT_DELAY = 0.34  # ~3 requests per second


class MultiDatabaseClient:
    """
    Client for querying GO.org, UniProt, and KEGG simultaneously.
    """
    
    # Evidence code classifications - EXPLICIT as per requirements
    EXPERIMENTAL_EVIDENCE_CODES = {
        "IDA",  # Inferred from Direct Assay
        "IMP",  # Inferred from Mutant Phenotype
        "IGI",  # Inferred from Genetic Interaction
        "IPI",  # Inferred from Physical Interaction
        "IEP",  # Inferred from Expression Pattern
        "HTP",  # High Throughput experimental
        "HDA",  # High Throughput Direct Assay
        "HMP",  # High Throughput Mutant Phenotype
        "HGI",  # High Throughput Genetic Interaction
        "HEP",  # High Throughput Expression Pattern
    }
    
    COMPUTATIONAL_EVIDENCE_CODES = {
        "ISS",  # Inferred from Sequence or Structural Similarity
        "ISO",  # Inferred from Sequence Orthology
        "ISA",  # Inferred from Sequence Alignment
        "ISM",  # Inferred from Sequence Model
        "IGC",  # Inferred from Genomic Context
        "IBA",  # Inferred from Biological aspect of Ancestor
        "IBD",  # Inferred from Biological aspect of Descendant
        "IKR",  # Inferred from Key Residues
        "IRD",  # Inferred from Rapid Divergence
        "RCA",  # Reviewed Computational Analysis
    }
    
    # IEA is specifically called out as computational PREDICTION (not evidence)
    IEA_CODE = {"IEA"}  # Inferred from Electronic Annotation
    
    CURATORIAL_CODES = {
        "TAS",  # Traceable Author Statement
        "NAS",  # Non-traceable Author Statement
        "IC",   # Inferred by Curator
        "ND",   # No biological Data available
    }
    
    # Model organisms for cross-species validation (human, mouse, fly, worm)
    MODEL_ORGANISMS = {
        "9606": "Homo sapiens",      # Human
        "10090": "Mus musculus",     # Mouse
        "7227": "Drosophila melanogaster",  # Fly
        "6239": "Caenorhabditis elegans",   # Worm
    }
    
    # KEGG organism codes
    KEGG_ORGANISM_CODES = {
        "9606": "hsa",
        "10090": "mmu",
        "7227": "dme",
        "6239": "cel",
        "10116": "rno",
        "7955": "dre",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "K-Sites/1.0 (CRISPR Guide Design Platform)",
            "Accept": "application/json"
        })
    
    def query_all_databases_simultaneously(
        self, 
        gene_symbol: str, 
        taxid: str
    ) -> Dict[str, any]:
        """
        Query GO.org, UniProt, and KEGG simultaneously for a gene.
        
        Args:
            gene_symbol: Gene symbol (e.g., "BRCA1")
            taxid: NCBI Taxonomy ID
            
        Returns:
            Comprehensive gene data from all three databases
        """
        logger.info(f"Querying all databases simultaneously for {gene_symbol} in {taxid}")
        
        results = {
            "gene_symbol": gene_symbol,
            "taxid": taxid,
            "go_data": {},
            "uniprot_data": {},
            "kegg_data": {},
            "combined_bp_terms": [],
            "combined_evidence": [],
            "query_status": {}
        }
        
        # Execute queries in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._query_quickgo, gene_symbol, taxid): "go",
                executor.submit(self._query_uniprot, gene_symbol, taxid): "uniprot",
                executor.submit(self._query_kegg, gene_symbol, taxid): "kegg",
            }
            
            for future in as_completed(futures):
                db_name = futures[future]
                try:
                    data = future.result(timeout=30)
                    results[f"{db_name}_data"] = data
                    results["query_status"][db_name] = "success"
                except Exception as e:
                    logger.warning(f"Failed to query {db_name}: {e}")
                    results["query_status"][db_name] = f"failed: {str(e)}"
        
        # Combine and deduplicate BP terms from all sources
        results["combined_bp_terms"] = self._combine_bp_terms(results)
        results["combined_evidence"] = self._combine_evidence(results)
        
        return results
    
    def _query_quickgo(self, gene_symbol: str, taxid: str) -> Dict:
        """Query QuickGO (GO.org) for gene annotations."""
        logger.debug(f"Querying QuickGO for {gene_symbol}")
        
        try:
            # First resolve to UniProt ID
            uniprot_id = self._resolve_gene_to_uniprot(gene_symbol, taxid)
            if not uniprot_id:
                return {"error": "Could not resolve gene to UniProt ID", "annotations": []}
            
            base_url = "https://www.ebi.ac.uk/QuickGO/services/annotation/search"
            params = {
                "geneProductId": uniprot_id,
                "limit": 1000,
                "includeFields": "goId,evidenceCode,goAspect,qualifier,goName"
            }
            
            time.sleep(RATE_LIMIT_DELAY)
            response = self.session.get(base_url, params=params, timeout=30)
            
            if response.status_code == 400:
                logger.warning(f"QuickGO returned 400 for {gene_symbol}")
                return {"error": "Bad request", "annotations": []}
            
            response.raise_for_status()
            data = response.json()
            
            annotations = []
            bp_terms = []
            
            for result in data.get("results", []):
                go_id = result.get("goId", "")
                aspect = result.get("goAspect", "")
                evidence_codes = result.get("evidenceCode", [])
                go_name = result.get("goName", "")
                
                # Classify evidence
                evidence_type = self._classify_evidence(evidence_codes)
                
                annotation = {
                    "go_id": go_id,
                    "go_name": go_name,
                    "aspect": aspect,
                    "evidence_codes": evidence_codes,
                    "evidence_type": evidence_type,
                    "source": "QuickGO"
                }
                annotations.append(annotation)
                
                # Track BP terms specifically
                if aspect == "biological_process" or aspect == "P":
                    bp_terms.append(annotation)
            
            return {
                "uniprot_id": uniprot_id,
                "total_annotations": len(annotations),
                "bp_term_count": len(bp_terms),
                "annotations": annotations,
                "bp_terms": bp_terms
            }
            
        except Exception as e:
            logger.error(f"QuickGO query failed: {e}")
            return {"error": str(e), "annotations": []}
    
    def _query_uniprot(self, gene_symbol: str, taxid: str) -> Dict:
        """Query UniProt for gene/protein data."""
        logger.debug(f"Querying UniProt for {gene_symbol}")
        
        try:
            # UniProt REST API
            base_url = "https://rest.uniprot.org/uniprotkb/search"
            
            # Build query
            query = f"gene:{gene_symbol} AND organism_id:{taxid}"
            params = {
                "query": query,
                "format": "json",
                "fields": "accession,id,gene_names,protein_name,go_p,go_f,go_c,organism_name",
                "size": 10
            }
            
            time.sleep(RATE_LIMIT_DELAY)
            response = self.session.get(base_url, params=params, timeout=30)
            
            if response.status_code == 400:
                logger.warning(f"UniProt returned 400 for {gene_symbol}")
                return {"error": "Bad request", "entries": []}
            
            response.raise_for_status()
            data = response.json()
            
            entries = []
            bp_terms = []
            
            for result in data.get("results", []):
                accession = result.get("primaryAccession", "")
                
                # Extract GO terms from UniProt response
                go_annotations = []
                
                # Biological Process GO terms
                for go in result.get("uniProtKBCrossReferences", []):
                    if go.get("database") == "GO":
                        go_id = go.get("id", "")
                        properties = {p["key"]: p["value"] for p in go.get("properties", [])}
                        go_term = properties.get("GoTerm", "")
                        evidence = properties.get("GoEvidenceType", "")
                        
                        # Determine aspect from GO term prefix
                        aspect = "unknown"
                        if go_term.startswith("P:"):
                            aspect = "P"
                            bp_terms.append({
                                "go_id": go_id,
                                "go_name": go_term[2:],
                                "evidence_type": self._classify_evidence([evidence]),
                                "source": "UniProt"
                            })
                        elif go_term.startswith("F:"):
                            aspect = "F"
                        elif go_term.startswith("C:"):
                            aspect = "C"
                        
                        go_annotations.append({
                            "go_id": go_id,
                            "go_term": go_term,
                            "aspect": aspect,
                            "evidence": evidence
                        })
                
                entries.append({
                    "accession": accession,
                    "go_annotations": go_annotations
                })
            
            return {
                "total_entries": len(entries),
                "bp_term_count": len(bp_terms),
                "entries": entries,
                "bp_terms": bp_terms
            }
            
        except Exception as e:
            logger.error(f"UniProt query failed: {e}")
            return {"error": str(e), "entries": []}
    
    def _query_kegg(self, gene_symbol: str, taxid: str) -> Dict:
        """Query KEGG for pathway data."""
        logger.debug(f"Querying KEGG for {gene_symbol}")
        
        try:
            org_code = self.KEGG_ORGANISM_CODES.get(taxid)
            if not org_code:
                return {"error": f"No KEGG org code for taxid {taxid}", "pathways": []}
            
            # KEGG API: Find gene
            find_url = f"https://rest.kegg.jp/find/{org_code}/{gene_symbol}"
            
            time.sleep(RATE_LIMIT_DELAY)
            response = self.session.get(find_url, timeout=30)
            
            if response.status_code != 200:
                return {"error": "Gene not found in KEGG", "pathways": []}
            
            # Parse gene IDs from response
            gene_ids = []
            for line in response.text.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if parts:
                        gene_ids.append(parts[0])
            
            if not gene_ids:
                return {"error": "No gene IDs found", "pathways": []}
            
            # Get pathway information for first gene ID
            kegg_gene_id = gene_ids[0]
            link_url = f"https://rest.kegg.jp/link/pathway/{kegg_gene_id}"
            
            time.sleep(RATE_LIMIT_DELAY)
            response = self.session.get(link_url, timeout=30)
            
            pathways = []
            if response.status_code == 200:
                for line in response.text.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            pathway_id = parts[1].replace("path:", "")
                            pathways.append({
                                "pathway_id": pathway_id,
                                "gene_id": kegg_gene_id
                            })
            
            return {
                "kegg_gene_id": kegg_gene_id,
                "pathway_count": len(pathways),
                "pathways": pathways
            }
            
        except Exception as e:
            logger.error(f"KEGG query failed: {e}")
            return {"error": str(e), "pathways": []}
    
    def _resolve_gene_to_uniprot(self, gene_symbol: str, taxid: str) -> Optional[str]:
        """Resolve gene symbol to UniProt ID."""
        try:
            base_url = "https://rest.uniprot.org/uniprotkb/search"
            query = f"gene:{gene_symbol} AND organism_id:{taxid} AND reviewed:true"
            params = {
                "query": query,
                "format": "json",
                "fields": "accession",
                "size": 1
            }
            
            time.sleep(RATE_LIMIT_DELAY)
            response = self.session.get(base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    return results[0].get("primaryAccession")
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to resolve {gene_symbol} to UniProt: {e}")
            return None
    
    def _classify_evidence(self, evidence_codes: List[str]) -> str:
        """
        Classify evidence codes into experimental, computational, or IEA.
        
        CRITICAL: IDA, IMP, IGI must be classified as EXPERIMENTAL.
        IEA must be classified as computational PREDICTION.
        """
        if not evidence_codes:
            return "unknown"
        
        # Check for experimental evidence FIRST (highest priority)
        if any(code in self.EXPERIMENTAL_EVIDENCE_CODES for code in evidence_codes):
            return "experimental"
        
        # Check for computational analysis (not IEA)
        if any(code in self.COMPUTATIONAL_EVIDENCE_CODES for code in evidence_codes):
            return "computational"
        
        # Check for IEA (electronic annotation - lowest quality)
        if any(code in self.IEA_CODE for code in evidence_codes):
            return "IEA"
        
        # Check for curatorial evidence
        if any(code in self.CURATORIAL_CODES for code in evidence_codes):
            return "curatorial"
        
        return "unknown"
    
    def _combine_bp_terms(self, results: Dict) -> List[Dict]:
        """Combine and deduplicate BP terms from all sources."""
        all_bp_terms = {}
        
        # From QuickGO
        go_data = results.get("go_data", {})
        for term in go_data.get("bp_terms", []):
            go_id = term.get("go_id", "")
            if go_id and go_id not in all_bp_terms:
                all_bp_terms[go_id] = term
        
        # From UniProt
        uniprot_data = results.get("uniprot_data", {})
        for term in uniprot_data.get("bp_terms", []):
            go_id = term.get("go_id", "")
            if go_id and go_id not in all_bp_terms:
                all_bp_terms[go_id] = term
        
        return list(all_bp_terms.values())
    
    def _combine_evidence(self, results: Dict) -> Dict:
        """Combine evidence statistics from all sources."""
        evidence_counts = {
            "experimental": 0,
            "computational": 0,
            "IEA": 0,
            "curatorial": 0,
            "unknown": 0
        }
        
        # From QuickGO
        go_data = results.get("go_data", {})
        for annotation in go_data.get("annotations", []):
            evidence_type = annotation.get("evidence_type", "unknown")
            evidence_counts[evidence_type] = evidence_counts.get(evidence_type, 0) + 1
        
        # From UniProt (already classified in bp_terms)
        uniprot_data = results.get("uniprot_data", {})
        for term in uniprot_data.get("bp_terms", []):
            evidence_type = term.get("evidence_type", "unknown")
            evidence_counts[evidence_type] = evidence_counts.get(evidence_type, 0) + 1
        
        return evidence_counts


# Singleton instance
_multi_db_client = None


def get_multi_database_client() -> MultiDatabaseClient:
    """Get the singleton multi-database client."""
    global _multi_db_client
    if _multi_db_client is None:
        _multi_db_client = MultiDatabaseClient()
    return _multi_db_client


def query_gene_from_all_databases(gene_symbol: str, taxid: str) -> Dict:
    """
    Query GO.org, UniProt, and KEGG simultaneously for a gene.
    
    This is the main entry point for multi-database integration.
    """
    client = get_multi_database_client()
    return client.query_all_databases_simultaneously(gene_symbol, taxid)
