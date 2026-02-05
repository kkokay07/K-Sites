#!/usr/bin/env python3
"""
Unified Command-Line Interface for Universal K-Sites

This module serves as the entry point for the Universal K-Sites platform,
integrating both original GO-based analysis and Neo4j/KEGG pathway graph analysis.
"""

import argparse
import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_and_resolve_organism(organism_input):
    """
    Validate and resolve organism input to NCBI TaxID.
    
    Args:
        organism_input (str): Either NCBI TaxID or scientific name
        
    Returns:
        str: Resolved NCBI TaxID
        
    Raises:
        ValueError: If organism cannot be resolved
    """
    # Check if input is already a numeric tax ID
    if organism_input.isdigit():
        return organism_input
    
    # Try to resolve scientific name to TaxID using common mappings first
    common_organisms = {
        "Homo sapiens": "9606",
        "human": "9606",
        "Mus musculus": "10090",
        "mouse": "10090",
        "Saccharomyces cerevisiae": "4932",
        "yeast": "4932",
        "Drosophila melanogaster": "7227",
        "fruit fly": "7227",
        "Caenorhabditis elegans": "6239",
        "worm": "6239",
        "Danio rerio": "7955",
        "zebrafish": "7955",
        "hsa": "9606",  # KEGG code
        "mmu": "10090",  # KEGG code
        "cel": "6239",  # KEGG code
        "dre": "7955",  # KEGG code
        "sce": "4932"   # KEGG code
    }
    
    organism_normalized = organism_input.strip()
    if organism_normalized in common_organisms:
        return common_organisms[organism_normalized]
    
    # Attempt to resolve using NCBI Entrez (simplified approach)
    try:
        # Import here to avoid heavy dependencies if not needed
        from k_sites.data_retrieval.organism_resolver import resolve_organism_to_taxid
        taxid = resolve_organism_to_taxid(organism_input)
        logger.info(f"Resolved '{organism_input}' to TaxID: {taxid}")
        return taxid
    except ImportError:
        logger.warning("Could not import organism resolver, using common mappings only")
        raise ValueError(f"Organism '{organism_input}' not recognized. Please use either a valid NCBI TaxID or one of the common names: {list(common_organisms.keys())}")
    except Exception as e:
        logger.error(f"Failed to resolve organism '{organism_input}': {str(e)}")
        raise ValueError(f"Could not resolve organism '{organism_input}' to a valid NCBI TaxID")


def validate_go_term(go_term):
    """
    Validate GO term format.
    
    Args:
        go_term (str): GO term to validate
        
    Returns:
        str: Validated GO term
        
    Raises:
        ValueError: If GO term format is invalid
    """
    import re
    
    # GO terms are formatted as GO: followed by 7 digits
    pattern = r'^GO:\d{7}$'
    if not re.match(pattern, go_term.upper()):
        raise ValueError(f"Invalid GO term format: {go_term}. Expected format: GO:0000000")
    
    return go_term.upper()


def check_neo4j_availability():
    """
    Check if Neo4j is available and reachable.
    
    Returns:
        bool: True if Neo4j is available, False otherwise
    """
    try:
        from k_sites.neo4j.connection_manager import get_driver
        driver = get_driver()
        
        # Test connection by running a simple query
        with driver.session() as session:
            result = session.run("RETURN 1")
            record = result.single()
            if record and record[0] == 1:
                return True
    except Exception as e:
        logger.debug(f"Neo4j connection test failed: {str(e)}")
        return False
    
    return False


def run_k_sites_analysis(args):
    """
    Execute the main K-Sites analysis workflow.
    
    Args:
        args: Parsed command-line arguments
    """
    logger.info(f"Starting K-Sites analysis for GO term: {args.go_term}, Organism: {args.organism}")
    
    # Validate inputs early
    try:
        taxid = validate_and_resolve_organism(args.organism)
        go_term = validate_go_term(args.go_term)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Check if graph functionality should be enabled
    use_graph = args.use_graph
    if args.use_graph and not os.path.exists("Sandip_created/"):
        logger.warning("--use-graph enabled but Sandip_created/ directory not found, falling back to GO-only mode")
        use_graph = False
    elif args.use_graph and not check_neo4j_availability():
        logger.warning("--use-graph enabled but Neo4j not reachable, falling back to GO-only mode")
        use_graph = False
    
    logger.info(f"Using graph-enhanced analysis: {use_graph}")
    
    # Import required modules
    try:
        if use_graph:
            from k_sites.neo4j.graph_queries import run_query
            from k_sites.neo4j.pathway_analytics import calculate_centrality_metrics
            logger.info("Loaded graph utilities for pathway analysis")
        
        # Import workflow components
        from k_sites.workflow.pipeline import run_k_sites_pipeline
        from k_sites.reporting.report_generator import generate_html_report
        
        # Prepare pipeline parameters
        pipeline_params = {
            'go_term': go_term,
            'organism': taxid,
            'use_graph': use_graph,
            'max_pleiotropy': getattr(args, 'max_pleiotropy', 3),  # Default value
            'evidence_filter': getattr(args, 'evidence_filter', 'experimental'),  # Default evidence filter
            'species_validation': getattr(args, 'species_validation', None),  # Default species list
            'predict_phenotypes': getattr(args, 'predict_phenotypes', False)  # Default to False
        }
        
        # Execute the main pipeline
        logger.info("Running analysis pipeline...")
        results = run_k_sites_pipeline(**pipeline_params)
        
        # Generate output report
        logger.info(f"Generating HTML report at {args.output}")
        generate_html_report(results, args.output)
        
        logger.info("Analysis completed successfully!")
        
    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        logger.error("Make sure all required modules are implemented.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        sys.exit(1)


def main():
    """
    Main entry point for the K-Sites CLI.
    """
    parser = argparse.ArgumentParser(
        description="Universal K-Sites: Advanced CRISPR guide RNA design platform "
                   "integrating GO term analysis with KEGG pathway graph analytics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --go-term GO:0006281 --organism "Homo sapiens" --output report.html
  %(prog)s --go-term GO:0006281 --organism 9606 --output report.html --use-graph
  %(prog)s --go-term GO:0006281 --organism hsa --output results/report.html --no-graph

Note:
  - Organism can be NCBI TaxID (e.g., 9606) or scientific name (e.g., "Homo sapiens")
  - GO term format: GO:0000000 (7 digits after GO:)
  - Graph mode uses Neo4j KEGG pathway data for enhanced pleiotropy assessment
        """
    )
    
    parser.add_argument(
        '--go-term',
        required=True,
        help='GO term to analyze (e.g., "GO:0006281" for DNA repair)'
    )
    
    parser.add_argument(
        '--organism',
        required=True,
        help='Organism as NCBI TaxID (e.g., "9606") or scientific name (e.g., "Homo sapiens")'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output HTML report path'
    )
    
    parser.add_argument(
        '--use-graph',
        action='store_true',
        default=True,
        help='Enable Neo4j pathway-aware pleiotropy analysis (default: true if Neo4j is reachable)'
    )
    
    parser.add_argument(
        '--no-graph',
        action='store_false',
        dest='use_graph',
        help='Disable Neo4j pathway analysis, use GO-only mode'
    )
    
    parser.add_argument(
        '--max-pleiotropy',
        type=int,
        default=3,
        help='Maximum allowed pleiotropy score (default: 3)'
    )
    
    parser.add_argument(
        '--evidence-filter',
        choices=['experimental', 'computational', 'all'],
        default='experimental',
        help='Type of evidence to include (default: experimental)'
    )
    
    parser.add_argument(
        '--species-validation',
        nargs='+',
        help='Species taxids for cross-species validation (space-separated, e.g., 9606 10090 10116)'
    )
    
    parser.add_argument(
        '--predict-phenotypes',
        action='store_true',
        help='Enable RAG-based phenotype prediction using literature mining (default: false)'
    )
    
    # Allow the use_graph flag to be set by default based on Neo4j availability
    args = parser.parse_args()
    
    # If use_graph is still default (True), check Neo4j availability
    if args.use_graph:
        if not os.path.exists("Sandip_created/") or not check_neo4j_availability():
            args.use_graph = False
    
    run_k_sites_analysis(args)


if __name__ == "__main__":
    main()