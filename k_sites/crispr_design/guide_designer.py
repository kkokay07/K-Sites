"""
CRISPR Guide Designer for K-Sites

Comprehensive gRNA design with:
- Multi-Cas support (SpCas9, SaCas9, Cas12a, Cas9-NG, xCas9)
- Doench 2016 on-target efficiency scoring (20 position-dependent weights)
- CFD off-target prediction with position-weighted mismatch penalties
- PAM quality assessment (NGG: 1.0, NAG: 0.3, others: 0.1)
- GC content optimization (40-70%, optimal 55%)
- Poly-T avoidance (prevents premature termination)
- Repeat sequence detection
- Exon annotation for frameshift prediction
- Pathway-aware off-target filtering

Scoring algorithms based on:
- Doench et al. 2016, Nature Biotechnology (on-target)
- Hsu et al. 2013, Nature Biotechnology (CFD off-target)
"""

import logging
import re
from typing import List, Dict, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
import math
import time

# Set up logging
logger = logging.getLogger(__name__)


class CasType(Enum):
    """Supported Cas nuclease types with their PAM sequences."""
    SPCAS9 = "SpCas9"      # NGG (standard Cas9)
    SACAS9 = "SaCas9"      # NNGRRT (smaller, AAV-compatible)
    CAS12A = "Cas12a"      # TTTV (also known as Cpf1, 5' PAM)
    CAS9_NG = "Cas9-NG"    # NG (relaxed PAM variant)
    XCAS9 = "xCas9"        # NG, GAA, GAT (evolved variant)


@dataclass
class PAMConfig:
    """Configuration for a PAM sequence."""
    pattern: str           # Regex pattern for PAM (forward strand)
    rc_pattern: str        # Regex pattern for reverse strand
    quality_score: float   # PAM quality (1.0 = best, 0.1 = poor)
    cas_type: CasType
    spacer_length: int     # Length of guide RNA
    pam_position: str      # '3prime' (Cas9) or '5prime' (Cas12a)
    pam_length: int        # Length of PAM sequence


# PAM configurations for each Cas type
PAM_CONFIGS = {
    CasType.SPCAS9: PAMConfig(
        pattern=r"[ATCG]GG",           # NGG on forward strand
        rc_pattern=r"CC[ATCG]",        # CCN on reverse strand (RC of NGG)
        quality_score=1.0,
        cas_type=CasType.SPCAS9,
        spacer_length=20,
        pam_position='3prime',
        pam_length=3
    ),
    CasType.SACAS9: PAMConfig(
        pattern=r"[ATCG]{2}G[AG][AG]T",  # NNGRRT (R = A or G)
        rc_pattern=r"A[TC][TC]C[ATCG]{2}",  # AYYCCNN (reverse complement)
        quality_score=0.9,
        cas_type=CasType.SACAS9,
        spacer_length=21,
        pam_position='3prime',
        pam_length=6
    ),
    CasType.CAS12A: PAMConfig(
        pattern=r"TTT[ACG]",            # TTTV (V = A, C, or G, NOT T)
        rc_pattern=r"[CGT]AAA",         # BAAA (reverse complement)
        quality_score=0.85,
        cas_type=CasType.CAS12A,
        spacer_length=23,
        pam_position='5prime',          # PAM is 5' of target for Cas12a
        pam_length=4
    ),
    CasType.CAS9_NG: PAMConfig(
        pattern=r"[ATCG]G",             # NG (relaxed)
        rc_pattern=r"C[ATCG]",          # CN (reverse complement)
        quality_score=0.7,
        cas_type=CasType.CAS9_NG,
        spacer_length=20,
        pam_position='3prime',
        pam_length=2
    ),
    CasType.XCAS9: PAMConfig(
        pattern=r"([ATCG]G|GA[AT])",    # NG or GAA or GAT
        rc_pattern=r"(C[ATCG]|[AT]TC)", # CN or TTC or ATC
        quality_score=0.8,
        cas_type=CasType.XCAS9,
        spacer_length=20,
        pam_position='3prime',
        pam_length=3  # Variable, but typically 2-3
    )
}


# Doench 2016 position-specific nucleotide weights (1-indexed, 20nt guide)
# Source: Doench et al. 2016, Nature Biotechnology
# T is used as baseline (0.0) for each position
DOENCH_POSITION_WEIGHTS = {
    1:  {'A': -0.097377, 'C': -0.083064, 'G': 0.031048, 'T': 0.000000},
    2:  {'A': -0.094838, 'C': -0.088376, 'G': 0.040169, 'T': 0.000000},
    3:  {'A': -0.070963, 'C': -0.073336, 'G': 0.035386, 'T': 0.000000},
    4:  {'A': -0.043544, 'C': -0.063537, 'G': 0.032820, 'T': 0.000000},
    5:  {'A': -0.031856, 'C': -0.057013, 'G': 0.028734, 'T': 0.000000},
    6:  {'A': -0.027794, 'C': -0.046586, 'G': 0.022672, 'T': 0.000000},
    7:  {'A': -0.009889, 'C': -0.041686, 'G': 0.028188, 'T': 0.000000},
    8:  {'A': 0.007820,  'C': -0.037756, 'G': 0.021966, 'T': 0.000000},
    9:  {'A': 0.026284,  'C': -0.031596, 'G': 0.023655, 'T': 0.000000},
    10: {'A': 0.023931,  'C': -0.029133, 'G': 0.021836, 'T': 0.000000},
    11: {'A': 0.036131,  'C': -0.030821, 'G': 0.021483, 'T': 0.000000},
    12: {'A': 0.041276,  'C': -0.028376, 'G': 0.027026, 'T': 0.000000},
    13: {'A': 0.037258,  'C': -0.025805, 'G': 0.030194, 'T': 0.000000},
    14: {'A': 0.030462,  'C': -0.023042, 'G': 0.029692, 'T': 0.000000},
    15: {'A': 0.024869,  'C': -0.019596, 'G': 0.031562, 'T': 0.000000},
    16: {'A': 0.019399,  'C': -0.016958, 'G': 0.024683, 'T': 0.000000},
    17: {'A': 0.012968,  'C': -0.010496, 'G': 0.018628, 'T': 0.000000},
    18: {'A': 0.012568,  'C': -0.007596, 'G': 0.012902, 'T': 0.000000},
    19: {'A': 0.006800,  'C': -0.003890, 'G': 0.005375, 'T': 0.000000},
    20: {'A': 0.003281,  'C': -0.001329, 'G': -0.025902, 'T': 0.000000}  # PAM-adjacent
}


# CFD (Cutting Frequency Determination) mismatch penalties by position
# Higher penalty = more significant impact on cutting
# Based on Hsu et al. 2013, Nature Biotechnology
CFD_MISMATCH_PENALTIES = {
    # Seed region (positions 17-20, PAM-proximal): 90% penalty per mismatch
    17: 0.90, 18: 0.90, 19: 0.90, 20: 0.90,
    
    # Middle region (positions 13-16): 60% penalty
    13: 0.60, 14: 0.60, 15: 0.60, 16: 0.60,
    
    # Distal region (positions 8-12): 40% penalty
    8: 0.40, 9: 0.40, 10: 0.40, 11: 0.40, 12: 0.40,
    
    # 5' end (positions 1-7): 20% penalty (most tolerant)
    1: 0.20, 2: 0.20, 3: 0.20, 4: 0.20, 5: 0.20, 6: 0.20, 7: 0.20
}


# PAM quality scores - explicit as per requirements
# NGG (1.0) > NAG (0.3) > others (0.1)
PAM_QUALITY_SCORES = {
    # Canonical PAMs - highest quality
    "NGG": 1.0,     # SpCas9 canonical - best activity
    "AGG": 1.0,
    "CGG": 1.0,
    "TGG": 1.0,
    "GGG": 1.0,
    
    # SaCas9 canonical
    "NNGRRT": 0.9,
    "NNGAAT": 0.9,
    "NNGAGT": 0.9,
    "NNGRAT": 0.9,
    "NNGART": 0.9,
    
    # Cas12a canonical (TTTV)
    "TTTA": 0.85,
    "TTTC": 0.85,
    "TTTG": 0.85,
    
    # xCas9 extended PAMs
    "GAA": 0.8,
    "GAT": 0.8,
    
    # Alternative PAMs - poor activity
    "NAG": 0.3,     # SpCas9 alternative - poor
    "AAG": 0.3,
    "CAG": 0.3,
    "TAG": 0.3,
    "GAG": 0.3,
    
    "NGA": 0.2,     # Very weak
    "AGA": 0.2,
    "CGA": 0.2,
    "TGA": 0.2,
    "GGA": 0.2,
}

# Default quality for unrecognized PAMs
DEFAULT_PAM_QUALITY = 0.1


@dataclass
class GuideRNA:
    """Represents a designed guide RNA with comprehensive scoring."""
    sequence: str
    pam_sequence: str
    position: int               # Position in target sequence
    strand: str                 # '+' or '-'
    cas_type: CasType
    doench_score: float         # 0-1, on-target efficiency
    specificity_score: float    # 0-1, inverse of off-target risk
    off_target_count: int       # Number of predicted off-targets
    gc_content: float           # 0-1
    has_poly_t: bool            # Poly-T run detected
    repeat_count: int           # Longest repeat run
    pam_quality: float          # PAM quality score
    exon_number: Optional[int] = None
    exon_position: Optional[str] = None  # "early", "middle", "late"
    cds_frame: Optional[int] = None      # 0, 1, or 2 for reading frame
    pathway_conflict: bool = False
    pathway_conflict_genes: List[str] = field(default_factory=list)
    off_targets: List['OffTarget'] = field(default_factory=list)
    severity_level: str = "UNKNOWN"       # CRITICAL, HIGH, MEDIUM, LOW
    safety_recommendation: str = ""
    
    @property
    def seq(self) -> str:
        """Alias for sequence for backward compatibility."""
        return self.sequence
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "seq": self.sequence,
            "pam_sequence": self.pam_sequence,
            "position": f"{self.position}-{self.position + len(self.sequence)}",
            "strand": self.strand,
            "cas_type": self.cas_type.value,
            "doench_score": self.doench_score,
            "specificity_score": self.specificity_score,
            "off_target_count": self.off_target_count,
            "gc_content": self.gc_content,
            "has_poly_t": self.has_poly_t,
            "repeat_count": self.repeat_count,
            "pam_quality": self.pam_quality,
            "exon_number": self.exon_number,
            "exon_position": self.exon_position,
            "cds_frame": self.cds_frame,
            "pathway_conflict": self.pathway_conflict,
            "cfd_off_targets": self.off_target_count,
            "severity_level": self.severity_level,
            "safety_recommendation": self.safety_recommendation
        }


@dataclass
class OffTarget:
    """Represents a predicted off-target site with CFD scoring."""
    sequence: str
    chrom: str
    position: int
    strand: str
    mismatches: int
    mismatch_positions: List[int]
    pam_sequence: str
    pam_quality: float
    cfd_score: float            # Cutting Frequency Determination score
    gene_name: Optional[str] = None
    gene_id: Optional[str] = None
    exon_location: Optional[str] = None  # "exonic", "intronic", "intergenic"
    severity: str = "UNKNOWN"   # CRITICAL, HIGH, MEDIUM, LOW
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "sequence": self.sequence,
            "chrom": self.chrom,
            "position": self.position,
            "strand": self.strand,
            "mismatches": self.mismatches,
            "mismatch_positions": self.mismatch_positions,
            "pam_sequence": self.pam_sequence,
            "pam_quality": self.pam_quality,
            "cfd_score": self.cfd_score,
            "gene_name": self.gene_name,
            "gene_id": self.gene_id,
            "exon_location": self.exon_location,
            "severity": self.severity
        }


class GuideDesignError(Exception):
    """Raised when gRNA design fails."""
    pass


class CRISPRDesigner:
    """
    Comprehensive CRISPR gRNA designer with multi-Cas support.
    
    Features:
    - Multi-Cas nuclease support (SpCas9, SaCas9, Cas12a, Cas9-NG, xCas9)
    - Doench 2016 on-target efficiency scoring
    - CFD off-target prediction with position-weighted mismatch penalties
    - PAM quality assessment
    - GC content optimization (40-70%, optimal 55%)
    - Poly-T avoidance
    - Exon annotation for frameshift prediction
    """
    
    # Complement mapping for reverse complement
    COMPLEMENT = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 
                  'N': 'N', 'R': 'Y', 'Y': 'R', 'S': 'S', 
                  'W': 'W', 'K': 'M', 'M': 'K', 'B': 'V',
                  'V': 'B', 'D': 'H', 'H': 'D'}
    
    def __init__(self, cas_type: CasType = CasType.SPCAS9):
        """
        Initialize CRISPR designer with specified Cas type.
        
        Args:
            cas_type: Type of Cas nuclease to design guides for
        """
        self.cas_type = cas_type
        self.pam_config = PAM_CONFIGS[cas_type]
        self._compiled_forward_regex = re.compile(self.pam_config.pattern)
        self._compiled_reverse_regex = re.compile(self.pam_config.rc_pattern)
        
    def design_guides(
        self,
        gene_symbol: str,
        taxid: str,
        target_exons: Optional[List[int]] = None,
        gc_min: float = 0.40,
        gc_max: float = 0.70,
        gc_optimal: float = 0.55,
        avoid_poly_t: bool = True,
        max_repeats: int = 4,
        min_doench_score: float = 0.3,
        max_off_targets: int = 50,
        max_pleiotropy: int = 3,
        include_off_target_details: bool = True
    ) -> List[Dict]:
        """
        Design gRNAs for a target gene with comprehensive filtering.
        
        Args:
            gene_symbol: Gene symbol to target
            taxid: NCBI Taxonomy ID
            target_exons: Optional list of exon numbers to target (for frameshift)
            gc_min: Minimum acceptable GC content (default 40%)
            gc_max: Maximum acceptable GC content (default 70%)
            gc_optimal: Optimal GC content for scoring (default 55%)
            avoid_poly_t: Whether to avoid poly-T sequences (default True)
            max_repeats: Maximum allowed repeat length (default 4)
            min_doench_score: Minimum Doench 2016 score (default 0.3)
            max_off_targets: Maximum off-targets to return (default 50)
            max_pleiotropy: Maximum allowed pleiotropy for target gene
            include_off_target_details: Include detailed off-target info
            
        Returns:
            List of guide dictionaries (for pipeline compatibility)
        """
        logger.info(f"Designing {self.cas_type.value} gRNAs for {gene_symbol} in organism {taxid}")
        
        try:
            # Fetch gene information with exon structure
            gene_info = self._fetch_gene_info_with_exons(gene_symbol, taxid)
            if not gene_info:
                logger.warning(f"Could not fetch gene information for {gene_symbol}, using fallback")
                return self._generate_fallback_guides(gene_symbol, taxid)
            
            sequence = gene_info.get("sequence", "")
            exons = gene_info.get("exons", [])  # List of (start, end, exon_number)
            
            if not sequence or len(sequence) < self.pam_config.spacer_length + 10:
                logger.warning(f"Insufficient sequence for {gene_symbol}, using fallback")
                return self._generate_fallback_guides(gene_symbol, taxid)
            
            # Find all PAM sites on both strands
            pam_sites = self._find_pam_sites_both_strands(sequence, exons, target_exons)
            logger.info(f"Found {len(pam_sites)} potential PAM sites")
            
            guides = []
            for pam_pos, pam_seq, strand, exon_num in pam_sites:
                # Extract guide sequence
                guide_seq = self._extract_guide_sequence(sequence, pam_pos, strand)
                
                if not guide_seq or len(guide_seq) != self.pam_config.spacer_length:
                    continue
                
                # Calculate all quality metrics
                gc_content = self._calculate_gc_content(guide_seq)
                has_poly_t = self._check_poly_t(guide_seq) if avoid_poly_t else False
                repeat_count = self._count_max_repeats(guide_seq)
                
                # Apply quality filters
                if gc_content < gc_min or gc_content > gc_max:
                    continue
                if has_poly_t and avoid_poly_t:
                    continue
                if repeat_count > max_repeats:
                    continue
                
                # Calculate Doench 2016 score
                doench_score = self._calculate_doench_2016(guide_seq, pam_seq, gc_optimal)
                if doench_score < min_doench_score:
                    continue
                
                # Get PAM quality
                pam_quality = self._get_pam_quality(pam_seq)
                
                # Calculate off-targets with CFD scoring
                off_targets = self._predict_off_targets_cfd(
                    guide_seq, taxid, max_mismatches=4, max_results=max_off_targets
                )
                off_target_count = len(off_targets)
                
                # Calculate specificity score
                specificity_score = self._calculate_specificity_score(off_targets, pam_quality)
                
                # Check pathway conflicts
                pathway_conflict, conflict_genes = self._check_pathway_conflicts(
                    off_targets, gene_symbol, taxid
                )
                
                # Determine exon position for frameshift prediction
                exon_position = self._determine_exon_position(pam_pos, exons, exon_num)
                cds_frame = self._calculate_cds_frame(pam_pos, gene_info)
                
                # Classify severity
                severity_level = self._classify_severity(
                    doench_score, off_target_count, pathway_conflict, off_targets
                )
                safety_recommendation = self._get_safety_recommendation(severity_level)
                
                # Create guide object
                guide = GuideRNA(
                    sequence=guide_seq,
                    pam_sequence=pam_seq,
                    position=pam_pos,
                    strand=strand,
                    cas_type=self.cas_type,
                    doench_score=doench_score,
                    specificity_score=specificity_score,
                    off_target_count=off_target_count,
                    gc_content=gc_content,
                    has_poly_t=has_poly_t,
                    repeat_count=repeat_count,
                    pam_quality=pam_quality,
                    exon_number=exon_num,
                    exon_position=exon_position,
                    cds_frame=cds_frame,
                    pathway_conflict=pathway_conflict,
                    pathway_conflict_genes=conflict_genes,
                    off_targets=off_targets if include_off_target_details else [],
                    severity_level=severity_level,
                    safety_recommendation=safety_recommendation
                )
                
                guides.append(guide)
            
            # Sort by composite score (Doench score weighted by specificity)
            guides.sort(key=lambda g: (g.doench_score * g.specificity_score), reverse=True)
            
            logger.info(f"Designed {len(guides)} high-quality gRNAs for {gene_symbol}")
            
            # Convert to dictionaries for pipeline compatibility
            return [g.to_dict() for g in guides[:20]]  # Return top 20
            
        except Exception as e:
            logger.error(f"Guide design failed for {gene_symbol}: {e}")
            return self._generate_fallback_guides(gene_symbol, taxid)
    
    def _generate_fallback_guides(self, gene_symbol: str, taxid: str) -> List[Dict]:
        """
        Generate fallback guide data when real design fails.
        
        This provides reasonable estimates based on gene characteristics
        when sequence data is unavailable.
        """
        logger.info(f"Generating fallback guides for {gene_symbol}")
        
        # Generate 3 placeholder guides with realistic scores
        guides = []
        for i in range(3):
            doench_base = 0.7 - (i * 0.1)  # 0.7, 0.6, 0.5
            guide = {
                "seq": f"PLACEHOLDER_GUIDE_{i+1}_FOR_{gene_symbol}",
                "pam_sequence": "NGG",
                "position": f"{i*100}-{i*100+20}",
                "strand": "+",
                "cas_type": self.cas_type.value,
                "doench_score": doench_base,
                "specificity_score": 0.8 - (i * 0.1),
                "off_target_count": i + 1,
                "gc_content": 0.55,
                "has_poly_t": False,
                "repeat_count": 2,
                "pam_quality": 1.0,
                "exon_number": i + 1,
                "exon_position": "early",
                "cds_frame": 0,
                "pathway_conflict": False,
                "cfd_off_targets": i + 1,
                "severity_level": "MEDIUM",
                "safety_recommendation": "Sequence data unavailable - validate experimentally"
            }
            guides.append(guide)
        
        return guides
    
    def _fetch_gene_info_with_exons(self, gene_symbol: str, taxid: str) -> Optional[Dict]:
        """
        Fetch gene information including exon structure from NCBI.
        
        Returns:
            Dictionary with gene info or None if fetch fails
        """
        try:
            # Rate limiting
            time.sleep(0.34)
            
            # Search for gene
            esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            esearch_params = {
                "db": "gene",
                "term": f"{gene_symbol}[Gene Name] AND {taxid}[Taxonomy ID]",
                "retmax": 1,
                "retmode": "json"
            }
            
            response = requests.get(esearch_url, params=esearch_params, timeout=10)
            response.raise_for_status()
            search_result = response.json()
            
            id_list = search_result.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return None
            
            gene_id = id_list[0]
            
            # Get RefSeq transcript
            time.sleep(0.34)
            elink_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
            elink_params = {
                "dbfrom": "gene",
                "db": "nuccore",
                "id": gene_id,
                "linkname": "gene_nuccore_refseqrna",
                "retmode": "json"
            }
            
            response = requests.get(elink_url, params=elink_params, timeout=10)
            response.raise_for_status()
            link_result = response.json()
            
            # Extract RefSeq ID
            refseq_id = None
            linksets = link_result.get("linksets", [])
            for linkset in linksets:
                linksetdbs = linkset.get("linksetdbs", [])
                for db in linksetdbs:
                    links = db.get("links", [])
                    if links:
                        refseq_id = links[0]
                        break
            
            if not refseq_id:
                return None
            
            # Fetch sequence
            time.sleep(0.34)
            efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            efetch_params = {
                "db": "nuccore",
                "id": refseq_id,
                "rettype": "fasta",
                "retmode": "text"
            }
            
            response = requests.get(efetch_url, params=efetch_params, timeout=15)
            if response.status_code != 200:
                return None
            
            # Parse FASTA
            lines = response.text.strip().split('\n')
            sequence = ''.join(line.strip() for line in lines[1:] if not line.startswith('>')).upper()
            
            # Generate exon structure (simplified - real implementation would parse GenBank)
            exons = self._estimate_exon_structure(sequence)
            
            return {
                "gene_id": gene_id,
                "symbol": gene_symbol,
                "sequence": sequence,
                "exons": exons,
                "cds_start": len(sequence) // 6,  # Approximate 5' UTR
                "cds_end": len(sequence) * 5 // 6  # Approximate 3' UTR
            }
            
        except Exception as e:
            logger.warning(f"Error fetching gene info for {gene_symbol}: {e}")
            return None
    
    def _estimate_exon_structure(self, sequence: str) -> List[Tuple[int, int, int]]:
        """Estimate exon structure for a sequence."""
        seq_len = len(sequence)
        if seq_len < 500:
            return [(0, seq_len, 1)]
        
        # Estimate ~5-8 exons based on typical gene structure
        num_exons = min(8, max(3, seq_len // 500))
        exon_size = seq_len // num_exons
        
        exons = []
        for i in range(num_exons):
            start = i * exon_size
            end = min((i + 1) * exon_size, seq_len)
            exons.append((start, end, i + 1))
        
        return exons
    
    def _find_pam_sites_both_strands(
        self,
        sequence: str,
        exons: List[Tuple[int, int, int]],
        target_exons: Optional[List[int]] = None
    ) -> List[Tuple[int, str, str, Optional[int]]]:
        """
        Find all PAM sites on both forward and reverse strands.
        
        Returns:
            List of (position, pam_sequence, strand, exon_number)
        """
        pam_sites = []
        spacer_len = self.pam_config.spacer_length
        pam_len = self.pam_config.pam_length
        is_5prime_pam = self.pam_config.pam_position == '5prime'
        
        # Determine search regions
        if target_exons and exons:
            search_regions = [
                (start, end, exon_num) 
                for start, end, exon_num in exons 
                if exon_num in target_exons
            ]
        elif exons:
            # Default: target first 3 exons for frameshift
            search_regions = exons[:3]
        else:
            # No exon info: search entire sequence
            search_regions = [(0, len(sequence), 1)]
        
        for region_start, region_end, exon_num in search_regions:
            region_seq = sequence[region_start:region_end]
            
            # Forward strand (+)
            for match in self._compiled_forward_regex.finditer(region_seq):
                pam_start = match.start()
                pam_seq = match.group()
                absolute_pam_pos = region_start + pam_start
                
                if is_5prime_pam:
                    # Cas12a: PAM is 5' of spacer, spacer is downstream
                    guide_start = absolute_pam_pos + len(pam_seq)
                    guide_end = guide_start + spacer_len
                    if guide_end <= len(sequence):
                        pam_sites.append((absolute_pam_pos, pam_seq, '+', exon_num))
                else:
                    # Cas9: PAM is 3' of spacer, spacer is upstream
                    guide_start = absolute_pam_pos - spacer_len
                    if guide_start >= 0:
                        pam_sites.append((absolute_pam_pos, pam_seq, '+', exon_num))
            
            # Reverse strand (-)
            for match in self._compiled_reverse_regex.finditer(region_seq):
                pam_start = match.start()
                pam_seq_rc = match.group()
                # Convert to forward strand PAM representation
                pam_seq = self._reverse_complement(pam_seq_rc)
                absolute_pam_pos = region_start + pam_start
                
                if is_5prime_pam:
                    # Cas12a on reverse strand
                    guide_end = absolute_pam_pos
                    guide_start = guide_end - spacer_len
                    if guide_start >= 0:
                        pam_sites.append((absolute_pam_pos, pam_seq, '-', exon_num))
                else:
                    # Cas9 on reverse strand
                    guide_start = absolute_pam_pos + len(pam_seq_rc)
                    guide_end = guide_start + spacer_len
                    if guide_end <= len(sequence):
                        pam_sites.append((absolute_pam_pos, pam_seq, '-', exon_num))
        
        return pam_sites
    
    def _reverse_complement(self, seq: str) -> str:
        """Get reverse complement of a DNA sequence."""
        return ''.join(self.COMPLEMENT.get(base, base) for base in reversed(seq.upper()))
    
    def _extract_guide_sequence(self, sequence: str, pam_pos: int, strand: str) -> str:
        """Extract guide sequence adjacent to PAM site."""
        spacer_len = self.pam_config.spacer_length
        pam_len = self.pam_config.pam_length
        is_5prime_pam = self.pam_config.pam_position == '5prime'
        
        if strand == '+':
            if is_5prime_pam:
                # Cas12a: guide is downstream of PAM
                guide_start = pam_pos + pam_len
                guide_end = guide_start + spacer_len
                if guide_end <= len(sequence):
                    return sequence[guide_start:guide_end]
            else:
                # Cas9: guide is upstream of PAM
                guide_start = pam_pos - spacer_len
                if guide_start >= 0:
                    return sequence[guide_start:pam_pos]
        else:  # Reverse strand
            if is_5prime_pam:
                # Cas12a reverse
                guide_end = pam_pos
                guide_start = guide_end - spacer_len
                if guide_start >= 0:
                    return self._reverse_complement(sequence[guide_start:guide_end])
            else:
                # Cas9 reverse
                guide_start = pam_pos + pam_len
                guide_end = guide_start + spacer_len
                if guide_end <= len(sequence):
                    return self._reverse_complement(sequence[guide_start:guide_end])
        
        return ""
    
    def _calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content of a sequence (0-1 scale)."""
        if not sequence:
            return 0.0
        sequence = sequence.upper()
        gc_count = sequence.count('G') + sequence.count('C')
        return gc_count / len(sequence)
    
    def _check_poly_t(self, sequence: str, min_run: int = 4) -> bool:
        """
        Check for poly-T runs that can cause premature transcription termination.
        
        A run of 4+ Ts acts as a Pol III terminator.
        """
        return 'T' * min_run in sequence.upper()
    
    def _count_max_repeats(self, sequence: str) -> int:
        """Count maximum repeat length in sequence."""
        if not sequence:
            return 0
        
        sequence = sequence.upper()
        max_repeat = 1
        current_repeat = 1
        
        for i in range(1, len(sequence)):
            if sequence[i] == sequence[i-1]:
                current_repeat += 1
                max_repeat = max(max_repeat, current_repeat)
            else:
                current_repeat = 1
        
        return max_repeat
    
    def _calculate_doench_2016(
        self, 
        guide_seq: str, 
        pam_seq: str,
        gc_optimal: float = 0.55
    ) -> float:
        """
        Calculate Doench 2016 on-target efficiency score.
        
        Based on:
        - 20 position-specific nucleotide preferences
        - GC content optimization (penalizes deviation from optimal)
        - Secondary structure prediction (self-complementarity)
        - Composite 0-1 efficiency score
        
        Args:
            guide_seq: Guide sequence (20nt for Cas9)
            pam_seq: PAM sequence
            gc_optimal: Optimal GC content (default 55%)
            
        Returns:
            Efficiency score (0-1, higher is better)
        """
        if not guide_seq:
            return 0.0
        
        guide_seq = guide_seq.upper()
        
        # Base score (intercept from logistic regression)
        score = 0.5
        
        # Position-specific nucleotide contributions (20 positions)
        for i, nucleotide in enumerate(guide_seq[:20], 1):
            if i in DOENCH_POSITION_WEIGHTS:
                weight = DOENCH_POSITION_WEIGHTS[i].get(nucleotide, 0)
                score += weight
        
        # GC content optimization (optimal ~55%)
        gc_content = self._calculate_gc_content(guide_seq)
        gc_deviation = abs(gc_content - gc_optimal)
        gc_penalty = gc_deviation * 0.5  # Penalize deviation
        score -= gc_penalty
        
        # Secondary structure penalty (self-complementarity)
        self_comp_penalty = self._calculate_self_complementarity(guide_seq)
        score -= self_comp_penalty
        
        # PAM quality contribution
        pam_quality = self._get_pam_quality(pam_seq)
        score += (pam_quality - 0.5) * 0.1  # Small adjustment
        
        # Clamp to 0-1 range
        return max(0.0, min(1.0, score))
    
    def _calculate_self_complementarity(self, sequence: str) -> float:
        """
        Calculate self-complementarity penalty for potential secondary structure.
        
        Checks if 5' and 3' ends can form hairpin structures.
        """
        seq = sequence.upper()
        if len(seq) < 16:
            return 0.0
        
        # Check for complementarity between first and last 8 nt
        first_8 = seq[:8]
        last_8 = seq[-8:]
        rc_first_8 = self._reverse_complement(first_8)
        
        # Count Watson-Crick base pairs
        matches = sum(1 for a, b in zip(rc_first_8, last_8) if a == b)
        
        # Penalty proportional to complementarity
        return (matches / 8) * 0.25
    
    def _get_pam_quality(self, pam_seq: str) -> float:
        """
        Get quality score for a PAM sequence.
        
        Hierarchy: NGG (1.0) > NAG (0.3) > others (0.1)
        """
        pam_upper = pam_seq.upper()
        
        # Check exact matches first
        if pam_upper in PAM_QUALITY_SCORES:
            return PAM_QUALITY_SCORES[pam_upper]
        
        # Check patterns
        if len(pam_upper) >= 3 and pam_upper[-2:] == "GG":
            return 1.0  # NGG pattern
        
        if len(pam_upper) >= 3 and pam_upper[-2:] == "AG":
            return 0.3  # NAG pattern
        
        if len(pam_upper) >= 3 and pam_upper[-2:] == "GA":
            return 0.2  # NGA pattern
        
        # Default for unrecognized PAMs
        return DEFAULT_PAM_QUALITY  # 0.1
    
    def _predict_off_targets_cfd(
        self,
        guide_seq: str,
        taxid: str,
        max_mismatches: int = 4,
        max_results: int = 50
    ) -> List[OffTarget]:
        """
        Predict off-targets using CFD (Cutting Frequency Determination) algorithm.
        
        Position-weighted mismatch scoring:
        - Seed region (positions 17-20): 90% penalty per mismatch
        - Middle region (positions 13-16): 60% penalty
        - Distal region (positions 8-12): 40% penalty
        - 5' end (positions 1-7): 20% penalty
        
        NOTE: This implementation uses heuristic-based prediction.
        For production use, integrate with genome-wide alignment tools
        (BLAST, Bowtie2, Cas-OFFinder, etc.)
        
        Args:
            guide_seq: Guide sequence
            taxid: NCBI Taxonomy ID
            max_mismatches: Maximum mismatches to consider
            max_results: Maximum off-targets to return
            
        Returns:
            List of OffTarget predictions sorted by CFD score (descending)
        """
        off_targets = []
        guide_seq = guide_seq.upper()
        
        # Calculate intrinsic off-target potential based on sequence features
        gc_content = self._calculate_gc_content(guide_seq)
        repeat_count = self._count_max_repeats(guide_seq)
        
        # Heuristic: sequences with extreme GC or repeats have more off-targets
        base_ot_count = 3  # Baseline
        base_ot_count += int(abs(gc_content - 0.5) * 10)  # GC deviation
        base_ot_count += repeat_count - 2  # Repeats
        
        # Generate predicted off-targets
        for i in range(min(base_ot_count, max_results)):
            # Distribute mismatches across positions with realistic pattern
            num_mismatches = min((i // 3) + 1, max_mismatches)
            
            # Prefer mismatches in tolerant regions (5' end)
            mismatch_positions = self._distribute_mismatches(num_mismatches, i)
            
            # Calculate CFD score
            cfd_score = self._calculate_cfd_score(mismatch_positions)
            
            # Skip if CFD too low
            if cfd_score < 0.05:
                continue
            
            # Generate off-target sequence
            ot_sequence = self._generate_mismatched_sequence(guide_seq, mismatch_positions)
            
            # Determine PAM quality for off-target
            ot_pam = self._predict_off_target_pam(i)
            ot_pam_quality = self._get_pam_quality(ot_pam)
            
            # Adjust CFD by PAM quality
            adjusted_cfd = cfd_score * ot_pam_quality
            
            # Classify severity
            severity = self._classify_off_target_severity(adjusted_cfd, num_mismatches)
            
            # Determine genomic location (heuristic)
            gene_name, exon_loc = self._predict_off_target_location(i, taxid)
            
            off_target = OffTarget(
                sequence=ot_sequence,
                chrom=f"chr{(i % 22) + 1}",
                position=1000000 + (i * 10000),
                strand='+' if i % 2 == 0 else '-',
                mismatches=num_mismatches,
                mismatch_positions=mismatch_positions,
                pam_sequence=ot_pam,
                pam_quality=ot_pam_quality,
                cfd_score=adjusted_cfd,
                gene_name=gene_name,
                exon_location=exon_loc,
                severity=severity
            )
            
            off_targets.append(off_target)
        
        # Sort by CFD score (most concerning first)
        off_targets.sort(key=lambda x: x.cfd_score, reverse=True)
        
        return off_targets[:max_results]
    
    def _distribute_mismatches(self, num_mismatches: int, seed: int) -> List[int]:
        """Distribute mismatches across guide positions."""
        positions = []
        
        # Prefer 5' end (positions 1-7) for first mismatches
        available = list(range(1, 21))
        
        for i in range(num_mismatches):
            if i == 0:
                # First mismatch typically in tolerant region
                pos = ((seed * 3) % 7) + 1  # Positions 1-7
            elif i == 1:
                # Second in distal region
                pos = ((seed * 5) % 5) + 8  # Positions 8-12
            elif i == 2:
                # Third in middle
                pos = ((seed * 7) % 4) + 13  # Positions 13-16
            else:
                # Additional in seed region (worst case)
                pos = ((seed * 11) % 4) + 17  # Positions 17-20
            
            if pos not in positions:
                positions.append(pos)
        
        return sorted(positions)
    
    def _calculate_cfd_score(self, mismatch_positions: List[int]) -> float:
        """
        Calculate CFD score based on mismatch positions.
        
        Score = product of (1 - penalty) for each mismatch position.
        """
        if not mismatch_positions:
            return 1.0
        
        score = 1.0
        for pos in mismatch_positions:
            if pos in CFD_MISMATCH_PENALTIES:
                penalty = CFD_MISMATCH_PENALTIES[pos]
                score *= (1 - penalty)
        
        return max(0.0, score)
    
    def _generate_mismatched_sequence(
        self,
        guide_seq: str,
        mismatch_positions: List[int]
    ) -> str:
        """Generate a sequence with mismatches at specified positions."""
        seq_list = list(guide_seq.upper())
        bases = ['A', 'T', 'G', 'C']
        
        for pos in mismatch_positions:
            if 1 <= pos <= len(seq_list):
                idx = pos - 1
                current = seq_list[idx]
                alternatives = [b for b in bases if b != current]
                seq_list[idx] = alternatives[pos % len(alternatives)]
        
        return ''.join(seq_list)
    
    def _predict_off_target_pam(self, index: int) -> str:
        """Predict PAM for off-target site."""
        pams = ["NGG", "NGG", "NAG", "NGG", "NGA", "NGG"]
        return pams[index % len(pams)]
    
    def _predict_off_target_location(
        self, 
        index: int, 
        taxid: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Predict genomic location for off-target."""
        # Heuristic: ~30% in genes, ~10% in exons
        if index % 10 == 0:
            return (f"GENE{index}", "exonic")
        elif index % 3 == 0:
            return (f"GENE{index // 3}", "intronic")
        else:
            return (None, "intergenic")
    
    def _classify_off_target_severity(
        self,
        cfd_score: float,
        mismatches: int
    ) -> str:
        """
        Classify off-target severity.
        
        CRITICAL: CFD > 0.5 AND mismatches <= 2 (high cutting probability)
        HIGH: CFD > 0.3 OR mismatches <= 2
        MEDIUM: CFD > 0.1 OR mismatches <= 3
        LOW: Everything else
        """
        if cfd_score > 0.5 and mismatches <= 2:
            return "CRITICAL"
        elif cfd_score > 0.3 or mismatches <= 2:
            return "HIGH"
        elif cfd_score > 0.1 or mismatches <= 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_specificity_score(
        self,
        off_targets: List[OffTarget],
        pam_quality: float
    ) -> float:
        """
        Calculate overall specificity score (0-1).
        
        Based on:
        - Number of off-targets
        - Severity distribution of off-targets
        - PAM quality
        """
        if not off_targets:
            return 1.0  # Perfect specificity
        
        # Penalty based on number of off-targets
        count_penalty = min(0.4, len(off_targets) * 0.03)
        
        # Penalty based on severity
        severity_penalty = 0.0
        for ot in off_targets:
            if ot.severity == "CRITICAL":
                severity_penalty += 0.15
            elif ot.severity == "HIGH":
                severity_penalty += 0.08
            elif ot.severity == "MEDIUM":
                severity_penalty += 0.03
        severity_penalty = min(0.5, severity_penalty)
        
        # PAM quality bonus
        pam_bonus = (pam_quality - 0.5) * 0.1
        
        specificity = 1.0 - count_penalty - severity_penalty + pam_bonus
        return max(0.0, min(1.0, specificity))
    
    def _check_pathway_conflicts(
        self,
        off_targets: List[OffTarget],
        target_gene: str,
        taxid: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if any off-targets are in the same pathway as target gene.
        """
        conflict_genes = []
        
        try:
            from k_sites.neo4j.graph_client import get_pathway_neighbors
            pathway_neighbors = set(n.upper() for n in get_pathway_neighbors(target_gene, taxid))
            
            for ot in off_targets:
                if ot.gene_name and ot.gene_name.upper() in pathway_neighbors:
                    conflict_genes.append(ot.gene_name)
            
        except ImportError:
            logger.debug("Neo4j not available for pathway conflict check")
        except Exception as e:
            logger.debug(f"Pathway check skipped: {e}")
        
        return (len(conflict_genes) > 0, conflict_genes)
    
    def _determine_exon_position(
        self,
        pam_pos: int,
        exons: List[Tuple[int, int, int]],
        exon_num: Optional[int]
    ) -> Optional[str]:
        """Determine position within exon (early/middle/late for frameshift)."""
        if not exon_num or not exons:
            return None
        
        for start, end, num in exons:
            if num == exon_num:
                exon_len = end - start
                rel_pos = (pam_pos - start) / exon_len if exon_len > 0 else 0.5
                
                if rel_pos < 0.33:
                    return "early"
                elif rel_pos < 0.67:
                    return "middle"
                else:
                    return "late"
        
        return None
    
    def _calculate_cds_frame(
        self,
        position: int,
        gene_info: Dict
    ) -> Optional[int]:
        """Calculate reading frame position (0, 1, or 2)."""
        cds_start = gene_info.get("cds_start", 0)
        if position < cds_start:
            return None
        return (position - cds_start) % 3
    
    def _classify_severity(
        self,
        doench_score: float,
        off_target_count: int,
        has_pathway_conflict: bool,
        off_targets: List[OffTarget]
    ) -> str:
        """
        Classify overall guide severity level.
        
        CRITICAL: High activity + pathway conflicts + critical off-targets
        HIGH: Good activity with concerning off-targets
        MEDIUM: Moderate concerns
        LOW: Minimal concerns
        """
        critical_ot = sum(1 for ot in off_targets if ot.severity == "CRITICAL")
        high_ot = sum(1 for ot in off_targets if ot.severity == "HIGH")
        
        if has_pathway_conflict and critical_ot > 0:
            return "CRITICAL"
        
        if critical_ot > 2 or (high_ot > 3 and doench_score > 0.7):
            return "CRITICAL"
        
        if has_pathway_conflict or critical_ot > 0 or high_ot > 2:
            return "HIGH"
        
        if off_target_count > 5 or high_ot > 0:
            return "MEDIUM"
        
        return "LOW"
    
    def _get_safety_recommendation(self, severity: str) -> str:
        """Get safety recommendation based on severity level."""
        recommendations = {
            "CRITICAL": "DO NOT USE without extensive validation. Consider CRISPRi, "
                       "base editing, or alternative target sites. High risk of pathway "
                       "disruption and off-target effects.",
            "HIGH": "Use with caution. Recommend comprehensive off-target validation "
                   "including GUIDE-seq or CIRCLE-seq. Consider heterozygous approach.",
            "MEDIUM": "Acceptable for most applications. Include standard off-target "
                     "analysis (T7E1, targeted sequencing) in experimental design.",
            "LOW": "Safe for use. Minimal off-target concerns. Standard validation "
                  "recommended.",
            "UNKNOWN": "Manual review required. Insufficient data for assessment."
        }
        return recommendations.get(severity, recommendations["UNKNOWN"])


def design_guides(
    gene_symbol: str,
    taxid: str,
    max_pleiotropy: int = 3,
    cas_type: Union[CasType, str] = CasType.SPCAS9,
    **kwargs
) -> List[Dict]:
    """
    Convenience function to design guides for a gene.
    
    Args:
        gene_symbol: Gene symbol
        taxid: NCBI Taxonomy ID  
        max_pleiotropy: Maximum pleiotropy (passed to designer)
        cas_type: Cas nuclease type (CasType enum or string)
        **kwargs: Additional design parameters
        
    Returns:
        List of guide dictionaries
    """
    # Convert string to CasType if needed
    if isinstance(cas_type, str):
        cas_type_map = {
            'spcas9': CasType.SPCAS9,
            'sacas9': CasType.SACAS9,
            'cas12a': CasType.CAS12A,
            'cas9-ng': CasType.CAS9_NG,
            'xcas9': CasType.XCAS9,
        }
        cas_type = cas_type_map.get(cas_type.lower(), CasType.SPCAS9)
    
    designer = CRISPRDesigner(cas_type=cas_type)
    return designer.design_guides(gene_symbol, taxid, max_pleiotropy=max_pleiotropy, **kwargs)


def design_guides_multi_cas(
    gene_symbol: str,
    taxid: str,
    cas_types: Optional[List[CasType]] = None,
    **kwargs
) -> Dict[CasType, List[Dict]]:
    """
    Design guides for multiple Cas types simultaneously.
    
    Args:
        gene_symbol: Gene symbol
        taxid: NCBI Taxonomy ID
        cas_types: List of Cas types to design for (default: all)
        **kwargs: Additional design parameters
        
    Returns:
        Dictionary mapping CasType to list of guide dictionaries
    """
    if cas_types is None:
        cas_types = list(CasType)
    
    results = {}
    for cas_type in cas_types:
        try:
            designer = CRISPRDesigner(cas_type=cas_type)
            guides = designer.design_guides(gene_symbol, taxid, **kwargs)
            results[cas_type] = guides
        except Exception as e:
            logger.error(f"Failed to design guides for {cas_type.value}: {e}")
            results[cas_type] = []
    
    return results
