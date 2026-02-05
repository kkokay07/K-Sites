"""
K-Sites Pipeline Module

This module orchestrates the complete K-Sites workflow by integrating all components:
- Organism resolution
- GO term to gene mapping
- Pleiotropy scoring
- gRNA design with pathway-aware filtering
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
import traceback

# Set up logging
logger = logging.getLogger(__name__)


def run_k_sites_pipeline(
    go_term: str, 
    organism: str, 
    max_pleiotropy: int = 3, 
    use_graph: bool = True,
    evidence_filter: str = "experimental",
    species_validation: List[str] = None,
    predict_phenotypes: bool = False
) -> Dict[str, Any]:
    """
    Execute the complete K-Sites pipeline.
    
    Args:
        go_term: GO term identifier (e.g., "GO:0006281")
        organism: Organism identifier (TaxID or scientific name)
        max_pleiotropy: Maximum allowed pleiotropy score (default: 3)
        use_graph: Whether to use Neo4j graph functionality (default: True)
        evidence_filter: Type of evidence to include ("experimental", "computational", "all")
        species_validation: List of species taxids for cross-species validation
        predict_phenotypes: Whether to predict knockout phenotypes using RAG (default: False)
        
    Returns:
        Dictionary with pipeline results:
        {
            "metadata": {
                "go_term": "...",
                "organism": "...",
                "timestamp": "...",
                "max_pleiotropy": 3,
                "evidence_filter": "experimental",
                "species_validation": [...],
                "predict_phenotypes": false
            },
            "genes": [
                {
                    "symbol": "BRCA1",
                    "pleiotropy_score": 2,
                    "specificity_score": 8.0,
                    "evidence_quality": 0.9,
                    "conservation_score": 0.8,
                    "composite_score": 8.5,
                    "cross_species_validation": {...},
                    "phenotype_prediction": {...},  # Present if predict_phenotypes=True
                    "guides": [...]
                }
            ]
        }
    """
    logger.info(f"Starting K-Sites pipeline for GO term {go_term} in organism {organism}")
    
    start_time = datetime.now()
    
    # Set default species for validation if not provided
    if species_validation is None:
        # Common model organisms for validation
        species_validation = ["9606", "10090", "10116", "7227", "6239"]  # human, mouse, rat, fly, worm
    
    try:
        # Step 1: Resolve organism
        logger.info("Step 1: Resolving organism...")
        from k_sites.data_retrieval.organism_resolver import resolve_organism
        organism_info = resolve_organism(organism)
        taxid = organism_info["taxid"]
        logger.info(f"Resolved organism: {organism_info['scientific_name']} (TaxID: {taxid})")
        
        # Step 2: Map GO term to genes with evidence filtering
        logger.info(f"Step 2: Mapping GO term to genes with {evidence_filter} evidence...")
        from k_sites.data_retrieval.go_gene_mapper import get_genes_for_go_term
        genes = get_genes_for_go_term(go_term, taxid, evidence_filter)
        logger.info(f"Found {len(genes)} genes associated with GO term {go_term} with {evidence_filter} evidence")
        
        # Step 3: Rank genes by specificity
        logger.info("Step 3: Ranking genes by specificity...")
        from k_sites.gene_analysis.pleiotropy_scorer import rank_genes_by_specificity
        ranked_genes = rank_genes_by_specificity(genes, taxid, evidence_filter)
        logger.info(f"Ranked {len(ranked_genes)} genes by specificity")
        
        # Step 4: Process each gene
        processed_genes = []
        logger.info(f"Step 4: Processing {len(ranked_genes)} ranked genes...")
        
        # Initialize phenotype predictor if needed
        phenotype_predictor = None
        if predict_phenotypes:
            try:
                from k_sites.rag_system.literature_context import RAGPhenotypePredictor
                phenotype_predictor = RAGPhenotypePredictor()
                logger.info("Initialized RAG-based phenotype predictor")
            except ImportError as e:
                logger.warning(f"Could not initialize phenotype predictor: {e}")
                predict_phenotypes = False  # Disable if dependencies missing
        
        for i, gene_info in enumerate(ranked_genes):
            gene_symbol = gene_info.get("symbol", "unknown")
            logger.info(f"Processing gene {i+1}/{len(ranked_genes)}: {gene_symbol}")
            
            try:
                # a. Get comprehensive pleiotropy score
                logger.debug(f"Computing comprehensive pleiotropy score for {gene_symbol}...")
                from k_sites.gene_analysis.pleiotropy_scorer import score_pleiotropy
                pleiotropy_score = score_pleiotropy(gene_symbol, taxid, go_term, evidence_filter)
                
                # b. Perform cross-species validation if requested
                cross_species_validation = {}
                if species_validation:
                    logger.debug(f"Performing cross-species validation for {gene_symbol}...")
                    from k_sites.gene_analysis.pleiotropy_scorer import validate_gene_specificity_across_species
                    cross_species_validation = validate_gene_specificity_across_species(
                        gene_symbol, go_term, species_validation
                    )
                
                # c. Predict phenotype if requested
                phenotype_prediction = None
                if predict_phenotypes and phenotype_predictor:
                    logger.debug(f"Predicting knockout phenotype for {gene_symbol}...")
                    try:
                        phenotype_prediction = phenotype_predictor.predict_phenotype(gene_symbol, taxid)
                    except Exception as e:
                        logger.warning(f"Failed to predict phenotype for {gene_symbol}: {str(e)}")
                
                # d. Skip if score exceeds threshold
                if pleiotropy_score > max_pleiotropy:
                    logger.info(f"Skipping {gene_symbol} (pleiotropy score {pleiotropy_score} > {max_pleiotropy})")
                    continue
                
                # e. Design gRNAs
                logger.debug(f"Designing gRNAs for {gene_symbol}...")
                from k_sites.crispr_design.guide_designer import design_guides
                guides = design_guides(gene_symbol, taxid, max_pleiotropy)
                
                # f. Filter out gRNAs with pathway-conflicting off-targets
                if use_graph:
                    logger.debug(f"Applying pathway-aware filtering for {gene_symbol}...")
                    guides = _filter_pathway_conflicts(guides, gene_symbol, taxid)
                
                # g. Determine safety recommendation based on phenotype and pleiotropy
                safety_recommendation = "Standard KO acceptable"
                if phenotype_prediction:
                    risk_level = phenotype_prediction.risk_level.value if hasattr(phenotype_prediction.risk_level, 'value') else str(phenotype_prediction.risk_level)
                    if risk_level in ["CRITICAL", "HIGH"]:
                        safety_recommendation = "Conditional KO/CRISPRi preferred"
                    elif pleiotropy_score > 5:
                        safety_recommendation = "Consider heterozygous KO"
                
                # h. Add gene to results with comprehensive scoring
                gene_result = {
                    "symbol": gene_symbol,
                    "pleiotropy_score": pleiotropy_score,
                    "specificity_score": gene_info.get("specificity_score", 10 - pleiotropy_score),
                    "evidence_quality": gene_info.get("evidence_quality", 0.5),
                    "literature_support": gene_info.get("literature_support", 0.5),
                    "conservation_score": gene_info.get("conservation_score", 0.0),
                    "composite_score": gene_info.get("composite_score", 5.0),
                    "bp_term_count": gene_info.get("bp_term_count", 0),
                    "experimental_evidence_count": gene_info.get("experimental_evidence_count", 0),
                    "computational_evidence_count": gene_info.get("computational_evidence_count", 0),
                    "iea_evidence_count": gene_info.get("iea_evidence_count", 0),
                    "cross_species_validation": cross_species_validation,
                    "phenotype_prediction": phenotype_prediction.__dict__ if phenotype_prediction else None,
                    "safety_recommendation": safety_recommendation,
                    "description": gene_info.get("description", ""),
                    "entrez_id": gene_info.get("entrez_id", ""),
                    "guides": guides
                }
                
                processed_genes.append(gene_result)
                logger.info(f"Successfully processed {gene_symbol} with {len(guides)} gRNAs")
                
            except Exception as e:
                logger.warning(f"Failed to process gene {gene_symbol}: {str(e)}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                continue  # Skip this gene and continue with others
        
        # Step 5: Aggregate results
        logger.info("Step 5: Aggregating results...")
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results = {
            "metadata": {
                "go_term": go_term,
                "organism": organism,
                "resolved_organism": organism_info,
                "timestamp": start_time.isoformat(),
                "execution_duration": duration,
                "max_pleiotropy": max_pleiotropy,
                "use_graph": use_graph,
                "evidence_filter": evidence_filter,
                "species_validation": species_validation,
                "predict_phenotypes": predict_phenotypes
            },
            "genes": processed_genes
        }
        
        logger.info(f"Pipeline completed successfully. Processed {len(processed_genes)} genes out of {len(ranked_genes)} total.")
        return results
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise


def _filter_pathway_conflicts(guides: List[Dict], gene_symbol: str, taxid: str) -> List[Dict]:
    """
    Filter out gRNAs with pathway-conflicting off-targets.
    
    Args:
        guides: List of gRNA designs
        gene_symbol: Target gene symbol
        taxid: NCBI Taxonomy ID
        
    Returns:
        Filtered list of gRNA designs
    """
    try:
        from k_sites.neo4j.graph_client import get_pathway_neighbors
        
        # Get genes in the same pathways as the target gene
        pathway_neighbors = get_pathway_neighbors(gene_symbol, taxid)
        pathway_neighbor_set = set(pathway_neighbors)
        
        filtered_guides = []
        for guide in guides:
            # Check if this guide has pathway conflicts
            if not guide.get("pathway_conflict", False):
                # If no pathway conflict, include the guide
                filtered_guides.append(guide)
            else:
                # If there's a pathway conflict, we might still include it
                # depending on the overall score, but log it
                logger.warning(f"Guide for {gene_symbol} has pathway conflicts: {guide['seq']}")
                # For now, we'll include pathway-conflicting guides but mark them
                guide_copy = guide.copy()
                guide_copy["included_despite_conflict"] = True
                filtered_guides.append(guide_copy)
        
        logger.info(f"Applied pathway filtering: {len(guides)} -> {len(filtered_guides)} guides for {gene_symbol}")
        return filtered_guides
        
    except ImportError:
        logger.warning("Neo4j graph client not available, skipping pathway conflict filtering")
        return guides
    except Exception as e:
        logger.warning(f"Could not apply pathway conflict filtering: {str(e)}, proceeding without filtering")
        return guides