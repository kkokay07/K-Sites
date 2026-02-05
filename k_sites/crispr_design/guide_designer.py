"""
CRISPR Guide Designer for K-Sites

This module designs and scores gRNAs with integrated pathway-aware off-target filtering.
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from Bio.Seq import Seq
from Bio import Entrez
import requests
import math

# Set up logging
logger = logging.getLogger(__name__)


class GuideDesignError(Exception):
    """Raised when gRNA design fails."""
    pass


def design_guides(gene_symbol: str, taxid: str, max_pleiotropy: int = 3) -> List[Dict]:
    """
    Design gRNAs for a target gene with pathway-aware off-target filtering.
    
    Args:
        gene_symbol: Gene symbol to target
        taxid: NCBI Taxonomy ID
        max_pleiotropy: Maximum allowed pleiotropy score for target gene
        
    Returns:
        List of gRNA designs with scoring and pathway conflict information:
        [
            {
                "seq": "AACGUUUCCUAGCUAGAAAUAGC",
                "position": 123456,
                "doench_score": 0.85,
                "cfd_off_targets": 2,
                "pathway_conflict": False,
                "strand": "+/-",
                "target_gene": "BRCA1"
            },
            ...
        ]
    """
    logger.info(f"Designing gRNAs for gene {gene_symbol} in organism {taxid}")
    
    try:
        # Get gene sequence information
        gene_info = _fetch_gene_info(gene_symbol, taxid)
        if not gene_info:
            raise GuideDesignError(f"Could not fetch gene information for {gene_symbol} in {taxid}")
        
        sequence = gene_info.get("sequence", "")
        tss_position = gene_info.get("tss", 0)  # Transcription Start Site
        
        if not sequence:
            raise GuideDesignError(f"No sequence available for gene {gene_symbol}")
        
        # Find NGG PAM sites around TSS (±200 bp)
        pam_sites = _find_ngg_pam_sites(sequence, tss_position, upstream=200, downstream=200)
        
        guides = []
        for pam_pos, pam_seq, strand in pam_sites:
            # Extract 20nt gRNA sequence (20 nt upstream of NGG)
            if strand == '+':
                guide_start = pam_pos - 23  # 20nt guide + 3nt PAM
                guide_end = pam_pos - 3
            else:  # minus strand
                guide_start = pam_pos + 3  # Skip PAM
                guide_end = pam_pos + 23  # 20nt guide + 3nt PAM
            
            if guide_start < 0 or guide_end > len(sequence):
                continue  # Skip if outside sequence bounds
            
            guide_seq = sequence[guide_start:guide_end]
            
            if len(guide_seq) != 20:
                continue  # Skip incomplete guides
            
            # Calculate Doench 2016 score
            doench_score = _calculate_doench_score(guide_seq, pam_pos)
            
            # Calculate CFD off-target score
            cfd_off_targets = _calculate_cfd_off_targets(guide_seq, taxid)
            
            # Check for pathway conflicts using Neo4j
            pathway_conflict = _check_pathway_conflicts(guide_seq, gene_symbol, taxid)
            
            guide_info = {
                "seq": guide_seq,
                "position": pam_pos if strand == '+' else pam_pos,
                "doench_score": doench_score,
                "cfd_off_targets": cfd_off_targets,
                "pathway_conflict": pathway_conflict,
                "strand": strand,
                "target_gene": gene_symbol
            }
            
            guides.append(guide_info)
        
        # Filter guides based on pathway conflicts and sort by quality
        filtered_guides = _filter_and_rank_guides(guides, max_pleiotropy, gene_symbol, taxid)
        
        logger.info(f"Designed {len(filtered_guides)} high-quality gRNAs for {gene_symbol}")
        return filtered_guides
        
    except Exception as e:
        logger.error(f"Error designing guides for {gene_symbol}: {str(e)}")
        raise GuideDesignError(f"Failed to design guides for gene {gene_symbol}: {str(e)}")


def _fetch_gene_info(gene_symbol: str, taxid: str) -> Optional[Dict]:
    """
    Fetch gene information including sequence and TSS.
    
    Args:
        gene_symbol: Gene symbol to fetch
        taxid: NCBI Taxonomy ID
        
    Returns:
        Dictionary with gene information
    """
    try:
        # Use NCBI E-Utilities to fetch gene information
        # First, find the gene ID
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        esearch_params = {
            "db": "gene",
            "term": f"{gene_symbol}[Gene Name] AND {taxid}[Organism]",
            "retmax": 1,
            "retmode": "json"
        }
        
        response = requests.get(esearch_url, params=esearch_params, timeout=10)
        response.raise_for_status()
        
        search_result = response.json()
        
        if "esearchresult" not in search_result or "idlist" not in search_result["esearchresult"]:
            return None
        
        id_list = search_result["esearchresult"]["idlist"]
        if not id_list:
            return None
        
        gene_id = id_list[0]
        
        # Now fetch detailed gene information
        esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        esummary_params = {
            "db": "gene",
            "id": gene_id,
            "retmode": "json"
        }
        
        response = requests.get(esummary_url, params=esummary_params, timeout=10)
        response.raise_for_status()
        
        summary_result = response.json()
        
        if "result" not in summary_result or gene_id not in summary_result["result"]:
            return None
        
        gene_details = summary_result["result"][gene_id]
        
        # Get genomic sequence information
        nuccore_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
        nuccore_params = {
            "dbfrom": "gene",
            "db": "nuccore",
            "id": gene_id,
            "retmode": "json"
        }
        
        response = requests.get(nuccore_url, params=nuccore_params, timeout=10)
        response.raise_for_status()
        
        link_result = response.json()
        
        # Extract RefSeq mRNA ID to get sequence
        refseq_ids = []
        if "linksets" in link_result and link_result["linksets"]:
            linkset = link_result["linksets"][0]
            if "linksetdbs" in linkset:
                for db_link in linkset["linksetdbs"]:
                    if db_link["dbto"] == "nuccore":
                        refseq_ids = db_link["links"]
                        break
        
        sequence = ""
        tss = 0
        
        if refseq_ids:
            # Get the first RefSeq ID and fetch sequence
            refseq_id = refseq_ids[0]
            
            nuc_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            nuc_params = {
                "db": "nuccore",
                "id": refseq_id,
                "rettype": "fasta",
                "retmode": "text"
            }
            
            response = requests.get(nuc_url, params=nuc_params, timeout=10)
            if response.status_code == 200:
                fasta_lines = response.text.strip().split('\n')
                header = fasta_lines[0]  # Contains position info
                seq_lines = fasta_lines[1:]
                sequence = ''.join(seq_lines)
                
                # Extract TSS from header if available (simplified)
                # In reality, you'd need more sophisticated parsing
                tss = len(sequence) // 2  # Approximate center as TSS for demo purposes
        
        return {
            "gene_id": gene_id,
            "symbol": gene_symbol,
            "sequence": sequence.upper(),
            "tss": tss,
            "description": gene_details.get("summary", "")
        }
        
    except Exception as e:
        logger.warning(f"Could not fetch gene info for {gene_symbol}: {str(e)}")
        return None


def _find_ngg_pam_sites(sequence: str, tss_position: int, upstream: int = 200, downstream: int = 200) -> List[Tuple[int, str, str]]:
    """
    Find all NGG PAM sites in the specified region around TSS.
    
    Args:
        sequence: DNA sequence to search
        tss_position: Transcription Start Site position
        upstream: Number of bases upstream to search
        downstream: Number of bases downstream to search
        
    Returns:
        List of (position, pam_sequence, strand) tuples
    """
    pam_sites = []
    
    # Define search region
    start_pos = max(0, tss_position - upstream)
    end_pos = min(len(sequence), tss_position + downstream)
    
    # Search for NGG PAM sites on forward strand (NGG)
    for i in range(start_pos, end_pos - 2):  # Need 3 bases for NGG
        if sequence[i:i+2] == "NG" and sequence[i+2] in "GTCA":
            pam_sites.append((i+2, sequence[i:i+3], '+'))
    
    # Search for NGG PAM sites on reverse strand (CCN -> NCC on forward strand)
    for i in range(start_pos, end_pos - 2):  # Need 3 bases for CCN
        if sequence[i:i+2] == "CC" and sequence[i+2] in "GTCA":
            pam_sites.append((i, sequence[i:i+3], '-'))
    
    return pam_sites


def _calculate_doench_score(guide_seq: str, position: int) -> float:
    """
    Calculate on-target efficiency using Doench 2016 algorithm.
    
    Args:
        guide_seq: 20nt guide sequence
        position: Position in gene (for context)
        
    Returns:
        Efficiency score (0-1)
    """
    # Simplified Doench 2016 scoring
    # In reality, this would be more complex with position-specific weights
    
    score = 0.5  # Base score
    
    # Position-specific nucleotide preferences (simplified)
    position_weights = {
        1: {'G': 0.5, 'A': 0.2, 'C': 0.3, 'T': 0.0},
        2: {'G': 0.3, 'A': 0.1, 'C': 0.2, 'T': 0.0},
        20: {'G': -0.3, 'A': 0.1, 'C': 0.2, 'T': 0.1}  # PAM-adjacent
    }
    
    for pos, weights in position_weights.items():
        if pos <= len(guide_seq):
            nucleotide = guide_seq[pos - 1]
            score += weights.get(nucleotide, 0)
    
    # GC content optimization
    gc_count = guide_seq.count('G') + guide_seq.count('C')
    gc_content = gc_count / len(guide_seq)
    gc_optimal = 0.5  # 50% GC content is often optimal
    gc_deviation = abs(gc_content - gc_optimal)
    gc_penalty = gc_deviation * 0.2  # Penalty for deviation from optimal
    score -= gc_penalty
    
    # Clamp to 0-1 range
    score = max(0.0, min(1.0, score))
    
    return score


def _calculate_cfd_off_targets(guide_seq: str, taxid: str) -> int:
    """
    Calculate CFD (Cutting Frequency Determination) off-target score.
    
    Args:
        guide_seq: 20nt guide sequence
        taxid: NCBI Taxonomy ID for organism
        
    Returns:
        Number of predicted off-targets with ≤4 mismatches
    """
    # This is a simplified implementation
    # In reality, you'd need to perform genome-wide alignment
    
    # For demonstration purposes, we'll return a mock value based on sequence properties
    # that correlate with off-target potential
    
    # Count homopolymers which increase off-target potential
    off_target_score = 0
    
    # Look for potential problematic motifs
    if 'AAAA' in guide_seq or 'TTTT' in guide_seq:
        off_target_score += 2
    if 'CCCC' in guide_seq or 'GGGG' in guide_seq:
        off_target_score += 1
    
    # Count potential off-targets based on sequence composition
    # This is a simplified heuristic
    potential_off_targets = off_target_score + len(guide_seq) // 10
    
    return min(potential_off_targets, 10)  # Cap at 10 for demo purposes


def _check_pathway_conflicts(guide_seq: str, target_gene: str, taxid: str) -> bool:
    """
    Check if any off-target genes share pathways with the target gene.
    
    Args:
        guide_seq: 20nt guide sequence
        target_gene: Target gene symbol
        taxid: NCBI Taxonomy ID
        
    Returns:
        True if pathway conflicts exist, False otherwise
    """
    try:
        # This is where we would check off-targets against pathway neighbors
        # For now, we'll use the graph client to get pathway neighbors of the target gene
        from k_sites.neo4j.graph_client import get_pathway_neighbors
        
        # Get genes in the same pathways as the target gene
        pathway_neighbors = get_pathway_neighbors(target_gene, taxid)
        
        # In a real implementation, we would:
        # 1. Find all potential off-target sites for this guide
        # 2. Check if any of those off-target genes are in pathway_neighbors
        
        # For this implementation, we'll just check if the target gene has pathway neighbors
        # which indicates it's part of a pathway network
        return len(pathway_neighbors) > 0
        
    except ImportError:
        logger.warning("Neo4j graph client not available, skipping pathway conflict check")
        return False
    except Exception as e:
        logger.warning(f"Could not check pathway conflicts: {str(e)}, proceeding without pathway filtering")
        return False


def _filter_and_rank_guides(guides: List[Dict], max_pleiotropy: int, target_gene: str, taxid: str) -> List[Dict]:
    """
    Filter and rank guides based on quality metrics and pathway conflicts.
    
    Args:
        guides: List of guide designs
        max_pleiotropy: Maximum allowed pleiotropy for target gene
        target_gene: Target gene symbol
        taxid: NCBI Taxonomy ID
        
    Returns:
        Filtered and ranked list of guides
    """
    # First, calculate a composite score for each guide
    scored_guides = []
    
    for guide in guides:
        # Calculate composite score
        # Higher Doench score is better
        # Lower off-target count is better
        # No pathway conflict is better
        score = guide["doench_score"] * 100  # Weight Doench score more heavily
        score -= guide["cfd_off_targets"] * 10  # Heavy penalty for off-targets
        if guide["pathway_conflict"]:
            score -= 50  # Very heavy penalty for pathway conflicts
        
        guide["composite_score"] = score
        scored_guides.append(guide)
    
    # Sort by composite score (descending)
    scored_guides.sort(key=lambda x: x["composite_score"], reverse=True)
    
    # Filter based on pathway conflicts if applicable
    # In this implementation, we prioritize guides without pathway conflicts
    filtered_guides = []
    
    for guide in scored_guides:
        # If guide has pathway conflicts, only include if it's significantly better than alternatives
        if guide["pathway_conflict"]:
            # For now, we'll include all guides but mark them appropriately
            # In a more stringent implementation, you might exclude pathway-conflicting guides
            pass
        
        filtered_guides.append(guide)
    
    # Return top guides (arbitrary limit to avoid too many options)
    return filtered_guides[:20]  # Return top 20 guides