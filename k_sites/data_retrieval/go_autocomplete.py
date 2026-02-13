"""
GO Term Autocomplete and Statistics Module for K-Sites

Provides real-time GO term autocomplete with gene count statistics.
"""

import logging
import requests
from typing import List, Dict, Optional
from pathlib import Path
import json
import time
import re

# Set up logging
logger = logging.getLogger(__name__)


def get_go_term_suggestions(prefix: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Get GO term suggestions based on a prefix for autocomplete functionality.
    
    Args:
        prefix: Prefix to search for (e.g., "DNA repair" or "GO:00")
        limit: Maximum number of suggestions to return
        
    Returns:
        List of dictionaries with GO term suggestions:
        [
            {
                "id": "GO:0006281",
                "name": "DNA repair",
                "definition": "The process of restoring DNA after damage...",
                "aspect": "P"  # P=Process, F=Function, C=Component
            },
            ...
        ]
    """
    logger.info(f"Getting GO term suggestions for prefix: '{prefix}', limit: {limit}")
    
    try:
        # Use the AmiGO Solr API to search for GO terms
        base_url = "http://golr-aux.geneontology.io/solr/select"
        
        # Construct query to search for GO terms
        query_parts = []
        if prefix.startswith("GO:"):
            # If searching for a specific GO ID
            query_parts.append(f"id:*{prefix}*")
        else:
            # If searching for a term name
            query_parts.append(f"term_name:*{prefix}*")
            query_parts.append(f"exact_synonym:*{prefix}*")
        
        query = "(" + " OR ".join(query_parts) + ") AND id:*GO:*"
        
        params = {
            "q": query,
            "rows": limit,
            "fl": "id,term_name,definition,aspect",
            "wt": "json",
            "fq": "document_category:\"ontology_class\""
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        docs = data.get("response", {}).get("docs", [])
        
        suggestions = []
        for doc in docs:
            suggestion = {
                "id": doc.get("id", ""),
                "name": doc.get("term_name", ""),
                "definition": doc.get("definition", ""),
                "aspect": doc.get("aspect", "")
            }
            suggestions.append(suggestion)
        
        logger.info(f"Found {len(suggestions)} suggestions for prefix '{prefix}'")
        return suggestions
        
    except requests.RequestException as e:
        logger.error(f"Request failed while getting GO term suggestions: {str(e)}")
        # Return some common GO terms as fallback
        return _get_common_go_terms_fallback(prefix, limit)
    except Exception as e:
        logger.error(f"Unexpected error getting GO term suggestions: {str(e)}")
        return _get_common_go_terms_fallback(prefix, limit)


def get_gene_count_for_go_term(go_term: str, taxid: str) -> int:
    """
    Get the number of genes associated with a GO term for a specific organism.
    
    Args:
        go_term: GO term identifier (e.g., "GO:0006281")
        taxid: NCBI Taxonomy ID (e.g., "9606" for human)
        
    Returns:
        Number of genes associated with the GO term in the specified organism
    """
    logger.info(f"Getting gene count for GO term {go_term} in organism {taxid}")
    
    try:
        from k_sites.data_retrieval.go_gene_mapper import get_genes_for_go_term
        
        # Get genes for the GO term with minimal evidence filtering to get full count
        genes = get_genes_for_go_term(go_term, taxid, evidence_filter="all")
        
        count = len(genes)
        logger.info(f"Found {count} genes for GO term {go_term} in organism {taxid}")
        return count
        
    except Exception as e:
        logger.error(f"Error getting gene count for GO term {go_term}: {str(e)}")
        return 0


def get_go_term_statistics(go_term: str, taxid: str) -> Dict[str, any]:
    """
    Get comprehensive statistics for a GO term in a specific organism.
    
    Args:
        go_term: GO term identifier (e.g., "GO:0006281")
        taxid: NCBI Taxonomy ID (e.g., "9606" for human)
        
    Returns:
        Dictionary with comprehensive GO term statistics:
        {
            "gene_count": 45,
            "bp_gene_count": 30,
            "mf_gene_count": 10,
            "cc_gene_count": 5,
            "avg_pleiotropy": 2.3,
            "most_specific_genes": [...],
            "least_specific_genes": [...]
        }
    """
    logger.info(f"Getting statistics for GO term {go_term} in organism {taxid}")
    
    try:
        from k_sites.data_retrieval.go_gene_mapper import get_genes_for_go_term
        from k_sites.gene_analysis.pleiotropy_scorer import score_pleiotropy
        
        # Get all genes associated with the GO term
        genes = get_genes_for_go_term(go_term, taxid, evidence_filter="all")
        
        stats = {
            "gene_count": len(genes),
            "bp_gene_count": 0,  # Will be calculated differently
            "mf_gene_count": 0,  # Will be calculated differently
            "cc_gene_count": 0,  # Will be calculated differently
            "avg_pleiotropy": 0.0,
            "most_specific_genes": [],  # Lowest pleiotropy
            "least_specific_genes": []  # Highest pleiotropy
        }
        
        if not genes:
            return stats
        
        # Calculate pleiotropy for each gene to get average and rankings
        gene_pleiotropy_pairs = []
        total_pleiotropy = 0
        
        for gene in genes:
            gene_symbol = gene.get("symbol", "")
            if gene_symbol:
                try:
                    pleiotropy = score_pleiotropy(gene_symbol, taxid)
                    gene_pleiotropy_pairs.append((gene_symbol, pleiotropy))
                    total_pleiotropy += pleiotropy
                except Exception as e:
                    logger.warning(f"Could not calculate pleiotropy for {gene_symbol}: {str(e)}")
                    gene_pleiotropy_pairs.append((gene_symbol, 5.0))  # Default medium score
                    total_pleiotropy += 5.0
        
        # Calculate average pleiotropy
        if gene_pleiotropy_pairs:
            stats["avg_pleiotropy"] = total_pleiotropy / len(gene_pleiotropy_pairs)
            
            # Sort by pleiotropy score to get most and least specific
            sorted_genes = sorted(gene_pleiotropy_pairs, key=lambda x: x[1])
            stats["most_specific_genes"] = [{"symbol": pair[0], "score": pair[1]} for pair in sorted_genes[:5]]
            stats["least_specific_genes"] = [{"symbol": pair[0], "score": pair[1]} for pair in sorted_genes[-5:]]
        
        logger.info(f"Statistics for GO term {go_term}: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics for GO term {go_term}: {str(e)}")
        return {
            "gene_count": 0,
            "bp_gene_count": 0,
            "mf_gene_count": 0,
            "cc_gene_count": 0,
            "avg_pleiotropy": 0.0,
            "most_specific_genes": [],
            "least_specific_genes": []
        }


def _get_common_go_terms_fallback(prefix: str, limit: int) -> List[Dict[str, str]]:
    """
    Fallback method to return common GO terms when API is unavailable.
    
    Args:
        prefix: Prefix to filter common terms
        limit: Maximum number of terms to return
        
    Returns:
        List of common GO terms matching the prefix
    """
    common_terms = [
        {"id": "GO:0006281", "name": "DNA repair", "definition": "The process of restoring DNA after damage", "aspect": "P"},
        {"id": "GO:0006974", "name": "cellular response to DNA damage stimulus", "definition": "A process that results in a change in state or activity of a cell", "aspect": "P"},
        {"id": "GO:0007165", "name": "signal transduction", "definition": "The cellular process involving the conversion of information", "aspect": "P"},
        {"id": "GO:0006259", "name": "DNA metabolic process", "definition": "Cellular metabolic processes involving DNA", "aspect": "P"},
        {"id": "GO:0006351", "name": "transcription, DNA-templated", "definition": "The cellular synthesis of RNA on a template of DNA", "aspect": "P"},
        {"id": "GO:0006412", "name": "translation", "definition": "The process of forming aminoacyl-tRNA and delivering it to the ribosome", "aspect": "P"},
        {"id": "GO:0006915", "name": "apoptotic process", "definition": "A programmed cell death process", "aspect": "P"},
        {"id": "GO:0007049", "name": "cell cycle", "definition": "The progression of biochemical and morphological phases", "aspect": "P"},
        {"id": "GO:0006629", "name": "lipid metabolic process", "definition": "The chemical reactions and pathways involving lipids", "aspect": "P"},
        {"id": "GO:0006954", "name": "inflammatory response", "definition": "The immediate defensive reaction to tissue injury", "aspect": "P"}
    ]
    
    # Filter by prefix if provided
    if prefix:
        prefix_lower = prefix.lower()
        filtered_terms = [
            term for term in common_terms
            if prefix_lower in term["id"].lower() or prefix_lower in term["name"].lower()
        ]
    else:
        filtered_terms = common_terms
    
    return filtered_terms[:limit]


def validate_go_term(go_term: str) -> bool:
    """
    Validate the format of a GO term.
    
    Args:
        go_term: GO term to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^GO:\d{7}$'
    return bool(re.match(pattern, go_term.upper()))


def get_enriched_go_terms(organism_taxid: str, max_terms: int = 50) -> List[Dict[str, any]]:
    """
    Get a list of enriched GO terms for a specific organism with gene counts.
    
    Args:
        organism_taxid: NCBI Taxonomy ID
        max_terms: Maximum number of terms to return
        
    Returns:
        List of GO terms with enrichment statistics
    """
    logger.info(f"Getting enriched GO terms for organism {organism_taxid}, max {max_terms} terms")
    
    # This would typically connect to a database of precomputed enrichments
    # For now, we'll return commonly studied terms with estimated gene counts
    enriched_terms = []
    
    # Common biologically relevant GO terms
    common_terms = [
        "GO:0006281", "GO:0006974", "GO:0007165", "GO:0006259", "GO:0006351",
        "GO:0006412", "GO:0006915", "GO:0007049", "GO:0006629", "GO:0006954",
        "GO:0008283", "GO:0007155", "GO:0006950", "GO:0006457", "GO:0006914"
    ]
    
    for go_id in common_terms[:max_terms]:
        try:
            gene_count = get_gene_count_for_go_term(go_id, organism_taxid)
            if gene_count > 0:  # Only include terms that have genes in this organism
                stats = get_go_term_statistics(go_id, organism_taxid)
                enriched_terms.append({
                    "id": go_id,
                    "gene_count": gene_count,
                    "avg_pleiotropy": stats["avg_pleiotropy"],
                    "most_specific_gene": stats["most_specific_genes"][0] if stats["most_specific_genes"] else None
                })
        except Exception as e:
            logger.warning(f"Could not get statistics for {go_id}: {str(e)}")
    
    # Sort by gene count (descending) to show most populated terms first
    enriched_terms.sort(key=lambda x: x["gene_count"], reverse=True)
    
    logger.info(f"Found {len(enriched_terms)} enriched GO terms for organism {organism_taxid}")
    return enriched_terms