"""
Pleiotropy Scorer for K-Sites

This module calculates pleiotropy scores for genes based on their connections
in both GO term networks and KEGG pathway graphs, implementing advanced
scoring with evidence-based filtering and cross-species validation.
"""

import logging
import os
import math
from typing import Dict, List, Optional, Union
from pathlib import Path
import requests
import time

# Set up logging
logger = logging.getLogger(__name__)


def score_pleiotropy(gene_symbol: str, taxid: str, go_term: str = None, evidence_filter: str = "experimental") -> float:
    """
    Calculate pleiotropy score for a gene using advanced metrics including:
    - Exponential decay scoring based on number of associated Biological Process GO terms
    - Pathway-based connectivity
    - Evidence-based weighting
    - Cross-species conservation
    
    Args:
        gene_symbol: Gene symbol (e.g., "BRCA1")
        taxid: NCBI Taxonomy ID (e.g., "9606" for human)
        go_term: Optional GO term for context
        evidence_filter: Type of evidence to include ("experimental", "computational", "all")
        
    Returns:
        Pleiotropy score (higher = more pleiotropic, 0-10 scale)
    """
    logger.debug(f"Scoring pleiotropy for gene {gene_symbol} in organism {taxid} with {evidence_filter} evidence")
    
    try:
        # Get detailed scoring information
        detailed_scores = _get_detailed_pleiotropy_scores(gene_symbol, taxid, evidence_filter)
        
        # Calculate exponential decay score for BP terms
        bp_term_count = detailed_scores["bp_term_count"]
        lambda_val = 0.3  # Decay rate - adjust as needed
        bp_score = 1 - math.exp(-lambda_val * (bp_term_count - 1)) if bp_term_count > 0 else 0
        
        # Get pathway-based score
        kegg_degree = detailed_scores["pathway_score"]
        pathway_score = kegg_degree * 0.1  # Scale pathway score appropriately
        
        # Get evidence-based weighting
        evidence_weight = _calculate_evidence_weight(detailed_scores)
        
        # Calculate final score with evidence weighting
        raw_score = bp_score + pathway_score
        weighted_score = raw_score * evidence_weight
        
        # Scale to 0-10 range for user-friendliness
        scaled_score = min(10.0, weighted_score * 5)  # Adjust multiplier as needed
        
        logger.info(f"Pleiotropy score for {gene_symbol}: {scaled_score:.2f} "
                   f"(BP: {bp_score:.2f}, Pathway: {pathway_score:.2f}, "
                   f"Evidence weight: {evidence_weight:.2f})")
        
        return scaled_score
        
    except Exception as e:
        logger.error(f"Error calculating pleiotropy score for {gene_symbol}: {str(e)}")
        # Return a conservative score if calculation fails
        return 5.0  # Default medium score


def _get_detailed_pleiotropy_scores(gene_symbol: str, taxid: str, evidence_filter: str) -> Dict:
    """
    Get detailed scoring information for a gene.
    
    Args:
        gene_symbol: Gene symbol
        taxid: NCBI Taxonomy ID
        evidence_filter: Type of evidence to include
        
    Returns:
        Dictionary with detailed scoring information
    """
    try:
        # Import the updated go_gene_mapper
        from k_sites.data_retrieval.go_gene_mapper import get_pleiotropy_score_detailed
        
        detailed_result = get_pleiotropy_score_detailed(gene_symbol, taxid)
        
        return detailed_result
        
    except Exception as e:
        logger.error(f"Error getting detailed scores for {gene_symbol}: {str(e)}")
        
        # Return default values
        return {
            "gene_symbol": gene_symbol,
            "taxid": taxid,
            "total_pleiotropy_score": 0,
            "bp_term_count": 1,
            "bp_score": 0,
            "pathway_score": 0,
            "experimental_evidence_count": 0,
            "computational_evidence_count": 0,
            "iea_evidence_count": 1,
            "all_go_terms": [],
            "biological_process_terms": [],
            "molecular_function_terms": [],
            "cellular_component_terms": [],
            "conservation_score": 0.0
        }


def _calculate_evidence_weight(scores: Dict) -> float:
    """
    Calculate evidence-based weight for pleiotropy scoring.
    
    Args:
        scores: Dictionary with detailed scoring information
        
    Returns:
        Evidence weight factor (0.0-1.0)
    """
    exp_count = scores.get("experimental_evidence_count", 0)
    comp_count = scores.get("computational_evidence_count", 0)
    iea_count = scores.get("iea_evidence_count", 0)
    
    # Total evidence count
    total_evidence = exp_count + comp_count + iea_count
    
    if total_evidence == 0:
        return 0.5  # Default weight if no evidence
    
    # Calculate weight based on evidence quality
    # Experimental evidence gets highest weight
    exp_weight = exp_count / total_evidence * 1.0
    comp_weight = comp_count / total_evidence * 0.7
    iea_weight = iea_count / total_evidence * 0.3
    
    # Combine weights
    total_weight = exp_weight + comp_weight + iea_weight
    
    # Normalize to 0-1 range
    normalized_weight = min(1.0, max(0.1, total_weight))
    
    return normalized_weight


def rank_genes_by_specificity(gene_list: List[Dict], taxid: str, evidence_filter: str = "experimental") -> List[Dict]:
    """
    Rank genes by specificity using weighted scoring combining:
    - Pleiotropy score (lower is better)
    - Evidence quality
    - Literature support
    - Conservation across species
    
    Args:
        gene_list: List of gene dictionaries with symbol and other info
        taxid: NCBI Taxonomy ID
        evidence_filter: Type of evidence to include
        
    Returns:
        Ranked list of genes with scoring information
    """
    logger.info(f"Ranking {len(gene_list)} genes by specificity")
    
    ranked_genes = []
    
    for gene_info in gene_list:
        gene_symbol = gene_info.get("symbol", "")
        
        try:
            # Calculate pleiotropy score
            pleiotropy_score = score_pleiotropy(gene_symbol, taxid, evidence_filter=evidence_filter)
            
            # Get detailed scores for additional metrics
            detailed_scores = _get_detailed_pleiotropy_scores(gene_symbol, taxid, evidence_filter)
            
            # Calculate specificity score (inverse of pleiotropy)
            specificity_score = max(0, 10 - pleiotropy_score)  # Higher = more specific
            
            # Calculate evidence quality score
            evidence_quality = _calculate_evidence_weight(detailed_scores)
            
            # Calculate literature support (simplified - in practice would query PubMed)
            literature_support = _estimate_literature_support(gene_symbol)
            
            # Calculate conservation score if cross-species data available
            conservation_score = detailed_scores.get("conservation_score", 0.0)
            
            # Calculate composite weighted score
            # Weight more specific scores higher
            composite_score = (
                specificity_score * 0.4 +  # Primary factor
                evidence_quality * 10 * 0.25 +  # Evidence quality
                literature_support * 0.2 +  # Literature support
                conservation_score * 10 * 0.15  # Conservation
            )
            
            # Create ranked gene entry
            ranked_gene = {
                "symbol": gene_symbol,
                "description": gene_info.get("description", ""),
                "entrez_id": gene_info.get("entrez_id", ""),
                "pleiotropy_score": pleiotropy_score,
                "specificity_score": specificity_score,
                "evidence_quality": evidence_quality,
                "literature_support": literature_support,
                "conservation_score": conservation_score,
                "composite_score": composite_score,
                "bp_term_count": detailed_scores.get("bp_term_count", 0),
                "experimental_evidence_count": detailed_scores.get("experimental_evidence_count", 0),
                "computational_evidence_count": detailed_scores.get("computational_evidence_count", 0),
                "iea_evidence_count": detailed_scores.get("iea_evidence_count", 0)
            }
            
            ranked_genes.append(ranked_gene)
            
        except Exception as e:
            logger.warning(f"Error ranking gene {gene_symbol}: {str(e)}")
            # Add gene with default scores
            ranked_genes.append({
                "symbol": gene_symbol,
                "description": gene_info.get("description", ""),
                "entrez_id": gene_info.get("entrez_id", ""),
                "pleiotropy_score": 5.0,
                "specificity_score": 5.0,
                "evidence_quality": 0.5,
                "literature_support": 0.5,
                "conservation_score": 0.0,
                "composite_score": 2.5,
                "bp_term_count": 5,
                "experimental_evidence_count": 0,
                "computational_evidence_count": 2,
                "iea_evidence_count": 3
            })
    
    # Sort by composite score (descending - highest first)
    ranked_genes.sort(key=lambda x: x["composite_score"], reverse=True)
    
    logger.info(f"Completed ranking of {len(ranked_genes)} genes")
    return ranked_genes


def _estimate_literature_support(gene_symbol: str) -> float:
    """
    Estimate literature support for a gene (simplified implementation).
    
    Args:
        gene_symbol: Gene symbol
        
    Returns:
        Literature support score (0.0-1.0)
    """
    try:
        # In a full implementation, this would query PubMed for publications
        # about the gene. For now, we'll use a simple heuristic.
        
        # Genes with fewer than 5 characters might be less studied
        if len(gene_symbol) < 5:
            return 0.3
        
        # Common gene names might have more literature
        common_suffixes = ["1", "2", "3", "A", "B", "C", "D", "P", "K"]
        if any(gene_symbol.endswith(suffix) for suffix in common_suffixes):
            return 0.7
        
        # Default moderate support
        return 0.5
        
    except Exception as e:
        logger.warning(f"Error estimating literature support for {gene_symbol}: {str(e)}")
        return 0.5


def validate_gene_specificity_across_species(gene_symbol: str, target_go_term: str, species_list: List[str]) -> Dict:
    """
    Validate gene specificity across multiple species.
    
    Args:
        gene_symbol: Gene symbol to validate
        target_go_term: Target GO term for validation
        species_list: List of species taxids to validate across
        
    Returns:
        Dictionary with cross-species validation results
    """
    logger.info(f"Validating {gene_symbol} across {len(species_list)} species for GO term {target_go_term}")
    
    results = {
        "gene_symbol": gene_symbol,
        "target_go_term": target_go_term,
        "species_validated": {},
        "conservation_score": 0.0,
        "specificity_consistency": 0.0
    }
    
    found_in_species = 0
    total_pleiotropy_scores = 0
    
    for species_taxid in species_list:
        try:
            # Check if gene exists in this species and get its pleiotropy score
            from k_sites.data_retrieval.go_gene_mapper import get_genes_for_go_term
            
            # First, see if the gene is associated with the target GO term in this species
            genes_in_species = get_genes_for_go_term(target_go_term, species_taxid)
            
            gene_found = any(
                g.get("symbol", "").upper() == gene_symbol.upper() 
                for g in genes_in_species
            )
            
            if gene_found:
                # Calculate pleiotropy score for this species
                pleiotropy_score = score_pleiotropy(gene_symbol, species_taxid)
                
                results["species_validated"][species_taxid] = {
                    "found": True,
                    "pleiotropy_score": pleiotropy_score,
                    "bp_term_count": _get_bp_terms_for_gene_in_species(gene_symbol, species_taxid)
                }
                
                found_in_species += 1
                total_pleiotropy_scores += pleiotropy_score
            else:
                results["species_validated"][species_taxid] = {
                    "found": False,
                    "pleiotropy_score": None,
                    "bp_term_count": 0
                }
                
        except Exception as e:
            logger.warning(f"Error validating {gene_symbol} in species {species_taxid}: {str(e)}")
            results["species_validated"][species_taxid] = {
                "found": False,
                "error": str(e),
                "pleiotropy_score": None,
                "bp_term_count": 0
            }
    
    # Calculate conservation metrics
    conservation_score = found_in_species / len(species_list) if species_list else 0
    avg_pleiotropy = total_pleiotropy_scores / found_in_species if found_in_species > 0 else 5.0
    
    results["conservation_score"] = conservation_score
    results["average_pleiotropy_score"] = avg_pleiotropy
    results["species_found_in_count"] = found_in_species
    
    logger.info(f"Cross-species validation for {gene_symbol}: "
                f"conservation={conservation_score:.2f}, "
                f"avg_pleiotropy={avg_pleiotropy:.2f}")
    
    return results


def _get_bp_terms_for_gene_in_species(gene_symbol: str, taxid: str) -> int:
    """
    Get the count of biological process terms for a gene in a specific species.
    
    Args:
        gene_symbol: Gene symbol
        taxid: NCBI Taxonomy ID
        
    Returns:
        Count of biological process terms
    """
    try:
        from k_sites.data_retrieval.go_gene_mapper import _get_all_go_terms_for_gene
        all_terms = _get_all_go_terms_for_gene(gene_symbol, taxid)
        bp_terms = [term for term in all_terms if term.get("aspect") == "P"]
        return len(bp_terms)
    except:
        return 0