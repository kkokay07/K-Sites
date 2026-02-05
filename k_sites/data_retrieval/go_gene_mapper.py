"""
GO-Gene Mapper for K-Sites

This module retrieves genes associated with a specific GO term for a given organism
using the QuickGO API with evidence-based filtering.
"""

import logging
import requests
import os
import math
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json
import time
import urllib.parse
from collections import defaultdict

# Set up logging
logger = logging.getLogger(__name__)


class GoTermNotFoundError(Exception):
    """Raised when a GO term is not found."""
    pass


class GeneRetrievalError(Exception):
    """Raised when gene retrieval fails."""
    pass


def get_genes_for_go_term(go_term: str, taxid: str, evidence_filter: str = "experimental") -> List[Dict[str, str]]:
    """
    Retrieve genes associated with a specific GO term for a given organism
    with evidence-based filtering.
    
    Args:
        go_term: GO term identifier (e.g., "GO:0006281")
        taxid: NCBI Taxonomy ID (e.g., "9606" for human)
        evidence_filter: Type of evidence to include ("experimental", "computational", "all")
        
    Returns:
        List of dictionaries containing gene information:
        [
            {
                "symbol": "BRCA1", 
                "entrez_id": "672", 
                "description": "BRCA1 DNA repair associated",
                "evidence_codes": ["IDA", "IMP"],
                "go_evidence_type": "experimental",  # "experimental", "computational", or "other"
                "qualifier": ["NOT"] if negative regulation, else []
            },
            ...
        ]
        
    Raises:
        GoTermNotFoundError: If the GO term is not found
        GeneRetrievalError: If gene retrieval fails
    """
    logger.info(f"Fetching genes for GO term {go_term} in organism {taxid} with {evidence_filter} evidence")
    
    # Validate GO term format
    if not _validate_go_term(go_term):
        raise ValueError(f"Invalid GO term format: {go_term}. Expected format: GO:0000000")
    
    try:
        # Build the QuickGO API query with evidence filtering
        base_url = "https://www.ebi.ac.uk/QuickGO/services/annotation/search"
        
        # Parameters for the query with evidence filtering
        params = {
            "goId": go_term,
            "taxonId": taxid,
            "limit": 10000,  # Large limit to get all annotations
            "includeFields": "geneProductSymbol,geneProductId,geneProductType,goQualifier,evidenceCode,reference,taxonId"
        }
        
        # Set headers for JSON response
        headers = {
            "Accept": "application/json"
        }
        
        # Make the request
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 404:
            raise GoTermNotFoundError(f"GO term {go_term} not found in QuickGO for organism {taxid}")
        
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        if "results" not in data:
            logger.warning(f"No results found for GO term {go_term} in organism {taxid}")
            return []
        
        # Process the results and extract gene information with evidence filtering
        genes = {}
        
        # Define evidence code categories
        experimental_codes = {"IDA", "IPI", "IMP", "IGI", "IEP", "HTP", "HDA", "HMP", "HGI", "HEP"}  # Experimental
        computational_codes = {"ISS", "ISO", "ISA", "ISM", "IGC", "IBA", "IBD", "IKR", "IRD", "RCA"}  # Computational
        curatorial_codes = {"TAS", "NAS", "IC", "ND", "IEA"}  # Curatorial
        
        for result in data["results"]:
            # Extract evidence codes
            evidence_codes = result.get("evidenceCode", [])
            qualifier = result.get("goQualifier", [])
            
            # Determine evidence type based on evidence codes
            go_evidence_type = "other"
            has_experimental = any(code in experimental_codes for code in evidence_codes)
            has_computational = any(code in computational_codes for code in evidence_codes)
            has_IEA = any(code == "IEA" for code in evidence_codes)
            
            if has_experimental:
                go_evidence_type = "experimental"
            elif has_computational:
                go_evidence_type = "computational"
            elif has_IEA:
                go_evidence_type = "curatorial"
            
            # Apply evidence filter
            if evidence_filter == "experimental" and go_evidence_type != "experimental":
                continue
            elif evidence_filter == "computational" and go_evidence_type not in ["computational", "curatorial"]:
                continue
            
            # Extract gene information
            gene_symbol = result.get("geneProductSymbol", "")
            gene_product_id = result.get("geneProductId", "")
            gene_id = result.get("geneProductId", "")  # This is usually the UniProt ID
            reference = result.get("reference", "")
            
            # Skip if we don't have essential information
            if not gene_symbol or not gene_id:
                continue
            
            # If this gene is already recorded, add additional evidence
            if gene_id in genes:
                # Append evidence codes and update evidence type if needed
                existing_codes = set(genes[gene_id]["evidence_codes"])
                existing_codes.update(evidence_codes)
                genes[gene_id]["evidence_codes"] = list(existing_codes)
                
                # Update evidence type to the most significant one
                if go_evidence_type == "experimental" and genes[gene_id]["go_evidence_type"] != "experimental":
                    genes[gene_id]["go_evidence_type"] = "experimental"
                elif go_evidence_type == "computational" and genes[gene_id]["go_evidence_type"] == "other":
                    genes[gene_id]["go_evidence_type"] = "computational"
            else:
                # Add new gene
                genes[gene_id] = {
                    "symbol": gene_symbol,
                    "entrez_id": gene_id,  # Note: QuickGO returns UniProt IDs, we might need to convert to Entrez
                    "description": reference,
                    "evidence_codes": evidence_codes,
                    "go_evidence_type": go_evidence_type,
                    "qualifier": qualifier
                }
        
        # Convert to list
        gene_list = list(genes.values())
        logger.info(f"Retrieved {len(gene_list)} genes for GO term {go_term} in organism {taxid} with {evidence_filter} evidence")
        
        # If we got no results with strict evidence filtering, try with less strict filtering
        if not gene_list and evidence_filter == "experimental":
            logger.info("No experimental evidence results found, trying computational evidence...")
            return get_genes_for_go_term(go_term, taxid, "computational")
        
        return gene_list
        
    except requests.RequestException as e:
        logger.error(f"Request failed for GO term {go_term} in organism {taxid}: {str(e)}")
        raise GeneRetrievalError(f"Failed to retrieve genes for GO term {go_term} in organism {taxid}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving genes for GO term {go_term} in organism {taxid}: {str(e)}")
        raise GeneRetrievalError(f"Unexpected error retrieving genes for GO term {go_term} in organism {taxid}: {str(e)}")


def get_genes_with_cross_species_validation(go_term: str, taxids: List[str], evidence_filter: str = "experimental") -> List[Dict]:
    """
    Retrieve genes with cross-species validation across multiple organisms.
    
    Args:
        go_term: GO term identifier
        taxids: List of NCBI Taxonomy IDs to validate across
        evidence_filter: Type of evidence to include
        
    Returns:
        List of genes with cross-species conservation scores
    """
    logger.info(f"Performing cross-species validation for {go_term} across {len(taxids)} species")
    
    # Get genes for each species
    all_genes = {}
    species_counts = defaultdict(int)
    
    for taxid in taxids:
        try:
            genes = get_genes_for_go_term(go_term, taxid, evidence_filter)
            for gene in genes:
                gene_key = gene["symbol"].upper()  # Normalize gene symbol
                if gene_key not in all_genes:
                    all_genes[gene_key] = {
                        "symbol": gene["symbol"],
                        "entrez_id": gene["entrez_id"],
                        "description": gene["description"],
                        "species_found": [],
                        "evidence_types": set(),
                        "conservation_score": 0.0
                    }
                
                all_genes[gene_key]["species_found"].append(taxid)
                all_genes[gene_key]["evidence_types"].add(gene["go_evidence_type"])
                species_counts[gene_key] += 1
        except Exception as e:
            logger.warning(f"Could not retrieve genes for {go_term} in species {taxid}: {e}")
            continue
    
    # Calculate conservation scores and compile results
    results = []
    for gene_key, gene_data in all_genes.items():
        conservation_score = len(gene_data["species_found"]) / len(taxids)
        gene_data["conservation_score"] = conservation_score
        
        # Add weighted score based on evidence type and conservation
        evidence_weight = 1.0  # Experimental evidence
        if "computational" in gene_data["evidence_types"]:
            evidence_weight *= 0.7  # Reduce weight for computational
        if "curatorial" in gene_data["evidence_types"]:
            evidence_weight *= 0.5  # Further reduce for IEA only
        
        gene_data["weighted_score"] = conservation_score * evidence_weight
        
        # Convert evidence_types set to list for JSON serialization
        gene_data["evidence_types"] = list(gene_data["evidence_types"])
        
        results.append(gene_data)
    
    # Sort by weighted score (descending)
    results.sort(key=lambda x: x["weighted_score"], reverse=True)
    
    logger.info(f"Found {len(results)} genes with cross-species validation")
    return results


def get_pleiotropy_score_detailed(gene_symbol: str, taxid: str, go_term: str = None) -> Dict:
    """
    Calculate detailed pleiotropy score with multiple factors.
    
    Args:
        gene_symbol: Gene symbol to score
        taxid: NCBI Taxonomy ID
        go_term: Optional GO term for context
        
    Returns:
        Dictionary with detailed pleiotropy scoring information
    """
    logger.info(f"Calculating detailed pleiotropy score for {gene_symbol} in {taxid}")
    
    try:
        # Get all GO terms for this gene
        all_go_terms = _get_all_go_terms_for_gene(gene_symbol, taxid)
        
        # Count Biological Process terms specifically
        bp_terms = [term for term in all_go_terms if term.get("category") == "P"]  # P = Biological Process
        molecular_function_terms = [term for term in all_go_terms if term.get("category") == "F"]  # F = Molecular Function
        cellular_component_terms = [term for term in all_go_terms if term.get("category") == "C"]  # C = Cellular Component
        
        # Calculate exponential decay scoring for BP terms
        # Formula: 1 - exp(-lambda * n) where lambda adjusts the decay rate and n is the number of BP terms
        lambda_val = 0.3  # Decay rate - adjust as needed
        bp_score = 1 - math.exp(-lambda_val * (len(bp_terms) - 1)) if len(bp_terms) > 0 else 0
        
        # Get pathway degree from Neo4j if available
        try:
            from k_sites.neo4j.graph_client import get_pathway_neighbors
            pathway_neighbors = get_pathway_neighbors(gene_symbol, taxid)
            pathway_score = len(pathway_neighbors)  # Number of connected genes in pathways
        except ImportError:
            logger.warning("Neo4j not available, using 0 for pathway score")
            pathway_score = 0
        except Exception as e:
            logger.warning(f"Could not get pathway neighbors: {e}")
            pathway_score = 0
        
        # Calculate evidence-based score
        experimental_evidence_count = sum(1 for term in all_go_terms if term.get("evidence_type") == "experimental")
        computational_evidence_count = sum(1 for term in all_go_terms if term.get("evidence_type") == "computational")
        iea_evidence_count = sum(1 for term in all_go_terms if term.get("evidence_type") == "IEA")
        
        # Combine scores
        total_score = bp_score + (pathway_score * 0.1)  # Scale pathway score appropriately
        
        result = {
            "gene_symbol": gene_symbol,
            "taxid": taxid,
            "total_pleiotropy_score": total_score,
            "bp_term_count": len(bp_terms),
            "bp_score": bp_score,
            "pathway_score": pathway_score,
            "experimental_evidence_count": experimental_evidence_count,
            "computational_evidence_count": computational_evidence_count,
            "iea_evidence_count": iea_evidence_count,
            "all_go_terms": all_go_terms,
            "biological_process_terms": bp_terms,
            "molecular_function_terms": molecular_function_terms,
            "cellular_component_terms": cellular_component_terms
        }
        
        logger.info(f"Pleiotropy score for {gene_symbol}: {total_score}")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating pleiotropy score for {gene_symbol}: {str(e)}")
        raise


def _get_all_go_terms_for_gene(gene_symbol: str, taxid: str) -> List[Dict]:
    """
    Get all GO terms associated with a gene.
    
    Args:
        gene_symbol: Gene symbol
        taxid: NCBI Taxonomy ID
        
    Returns:
        List of GO terms with details
    """
    try:
        # Use QuickGO to get all annotations for this gene
        base_url = "https://www.ebi.ac.uk/QuickGO/services/annotation/search"
        
        # First, we need to get the gene's UniProt ID
        gene_id = _resolve_gene_to_uniprot(gene_symbol, taxid)
        if not gene_id:
            logger.warning(f"Could not resolve {gene_symbol} to UniProt ID")
            return []
        
        params = {
            "geneProductId": gene_id,
            "limit": 10000,
            "includeFields": "goId,evidenceCode,goAspect,qualifier"
        }
        
        headers = {
            "Accept": "application/json"
        }
        
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if "results" not in data:
            return []
        
        go_terms = []
        for result in data["results"]:
            go_id = result.get("goId", "")
            evidence_codes = result.get("evidenceCode", [])
            aspect = result.get("goAspect", "")
            qualifiers = result.get("qualifier", [])
            
            # Determine evidence type
            evidence_type = "other"
            if any(code in {"IDA", "IPI", "IMP", "IGI", "IEP", "HTP", "HDA", "HMP", "HGI", "HEP"} for code in evidence_codes):
                evidence_type = "experimental"
            elif any(code in {"ISS", "ISO", "ISA", "ISM", "IGC", "IBA", "IBD", "IKR", "IRD", "RCA"} for code in evidence_codes):
                evidence_type = "computational"
            elif any(code == "IEA" for code in evidence_codes):
                evidence_type = "IEA"  # Computational prediction
            
            go_terms.append({
                "go_id": go_id,
                "aspect": aspect,  # P, F, or C for Process, Function, Component
                "evidence_codes": evidence_codes,
                "evidence_type": evidence_type,
                "qualifiers": qualifiers
            })
        
        return go_terms
        
    except Exception as e:
        logger.error(f"Error getting GO terms for {gene_symbol}: {str(e)}")
        return []


def _resolve_gene_to_uniprot(gene_symbol: str, taxid: str) -> Optional[str]:
    """
    Resolve a gene symbol to UniProt ID.
    
    Args:
        gene_symbol: Gene symbol
        taxid: NCBI Taxonomy ID
        
    Returns:
        UniProt ID or None if not found
    """
    try:
        # Use UniProt API to resolve gene symbol to UniProt ID
        base_url = "https://www.uniprot.org/uniprot/"
        
        # Map taxid to common names for UniProt search
        taxid_to_name = {
            "9606": "HUMAN",  # Homo sapiens
            "10090": "MOUSE",  # Mus musculus
            "10116": "RAT",    # Rattus norvegicus
            "7227": "DROME",   # Drosophila melanogaster
            "6239": "CAEEL",   # Caenorhabditis elegans
            "7955": "DANRE",   # Danio rerio
            "4932": "YEAST",   # Saccharomyces cerevisiae
        }
        
        organism_name = taxid_to_name.get(taxid, "")
        if not organism_name:
            logger.warning(f"TaxID {taxid} not mapped to organism name for UniProt search")
            return None
        
        params = {
            "query": f"{gene_symbol}[gene] AND {organism_name}[organism]",
            "format": "tab",
            "columns": "id,database(PDB)"
        }
        
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        
        lines = response.text.strip().split('\n')[1:]  # Skip header
        
        if lines and len(lines[0]) > 0:
            uniprot_id = lines[0].split('\t')[0]  # First column is UniProt ID
            return uniprot_id
            
        return None
        
    except Exception as e:
        logger.warning(f"Could not resolve {gene_symbol} to UniProt ID: {e}")
        return None


def _validate_go_term(go_term: str) -> bool:
    """
    Validate the format of a GO term.
    
    Args:
        go_term: GO term to validate
        
    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^GO:\d{7}$'
    return bool(re.match(pattern, go_term.upper()))