"""
K-Sites Mouse Gene Analysis Example (Quick Version)

This script runs the K-Sites pipeline on a limited set of mouse genes 
associated with DNA repair (GO:0006281) for faster demonstration.
Results are saved to the mouse_analysis_results directory.
"""

import os
import sys
import logging
from pathlib import Path
import csv
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure K-Sites is on the path
sys.path.insert(0, str(Path(__file__).parent))

# Set required environment variables
os.environ["K_SITES_NCBI_EMAIL"] = "user@example.com"

from k_sites.data_retrieval.organism_resolver import resolve_organism
from k_sites.data_retrieval.go_gene_mapper import get_genes_for_go_term
from k_sites.gene_analysis.pleiotropy_scorer import score_pleiotropy
from k_sites.crispr_design.guide_designer import design_guides
from k_sites.reporting.report_generator import generate_html_report


def run_limited_mouse_analysis(max_genes=5):
    """Run the K-Sites pipeline on a limited set of mouse genes."""
    logger.info("="*70)
    logger.info("K-SITES MOUSE GENE ANALYSIS (QUICK VERSION)")
    logger.info("="*70)
    
    # Create output directory
    output_dir = Path("mouse_analysis_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define parameters
    go_term = "GO:0006281"  # DNA repair
    organism = "Mus musculus"  # Mouse - TaxID: 10090
    max_pleiotropy = 5
    
    logger.info(f"\nAnalysis Parameters:")
    logger.info(f"  GO term: {go_term} (DNA repair)")
    logger.info(f"  Organism: {organism} (TaxID: 10090)")
    logger.info(f"  Max pleiotropy: {max_pleiotropy}")
    logger.info(f"  Max genes to process: {max_genes}")
    
    try:
        # Step 1: Resolve organism
        logger.info("\nStep 1: Resolving organism...")
        organism_info = resolve_organism(organism)
        taxid = organism_info["taxid"]
        logger.info(f"  ✓ Resolved: {organism_info['scientific_name']} (TaxID: {taxid})")
        
        # Step 2: Map GO term to genes
        logger.info(f"\nStep 2: Mapping GO term to genes...")
        genes = get_genes_for_go_term(go_term, taxid, evidence_filter="experimental")
        logger.info(f"  ✓ Found {len(genes)} genes associated with {go_term}")
        
        # Step 3: Process limited number of genes
        logger.info(f"\nStep 3: Processing top {max_genes} genes...")
        processed_genes = []
        start_time = datetime.now()
        
        for i, gene in enumerate(genes[:max_genes]):
            gene_symbol = gene.get("symbol", "unknown")
            logger.info(f"\n  Processing gene {i+1}/{max_genes}: {gene_symbol}")
            
            try:
                # Score pleiotropy
                pleiotropy_score = score_pleiotropy(gene_symbol, taxid, go_term, "experimental")
                logger.info(f"    Pleiotropy score: {pleiotropy_score:.2f}")
                
                # Skip if pleiotropy too high
                if pleiotropy_score > max_pleiotropy:
                    logger.info(f"    Skipped (pleiotropy > {max_pleiotropy})")
                    continue
                
                # Design gRNAs
                guides = design_guides(gene_symbol, taxid, max_pleiotropy)
                logger.info(f"    Designed {len(guides)} gRNAs")
                
                # Create gene result
                gene_result = {
                    "symbol": gene_symbol,
                    "description": gene.get("description", ""),
                    "entrez_id": gene.get("entrez_id", ""),
                    "pleiotropy_score": pleiotropy_score,
                    "specificity_score": 10 - pleiotropy_score,
                    "guides": guides
                }
                
                processed_genes.append(gene_result)
                logger.info(f"    ✓ Successfully processed {gene_symbol}")
                
            except Exception as e:
                logger.warning(f"    ✗ Failed to process {gene_symbol}: {e}")
                continue
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Step 4: Compile results
        results = {
            "metadata": {
                "go_term": go_term,
                "go_term_name": "DNA repair",
                "organism": organism,
                "taxid": taxid,
                "timestamp": start_time.isoformat(),
                "execution_duration": execution_time,
                "max_pleiotropy": max_pleiotropy,
                "max_genes_processed": max_genes
            },
            "genes": processed_genes,
            "statistics": {
                "total_genes_found": len(genes),
                "genes_processed": max_genes,
                "genes_passed_filter": len(processed_genes),
                "total_grnas": sum(len(g.get("guides", [])) for g in processed_genes)
            }
        }
        
        # Step 5: Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON export
        json_path = output_dir / f"mouse_analysis_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n  ✓ JSON export: {json_path}")
        
        # CSV export
        csv_path = output_dir / f"mouse_analysis_{timestamp}.csv"
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'gene_symbol', 'gene_description', 'pleiotropy_score', 
                'specificity_score', 'grna_sequence', 'position', 
                'doench_score', 'cfd_off_targets'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for gene in processed_genes:
                for guide in gene.get('guides', []):
                    writer.writerow({
                        'gene_symbol': gene.get('symbol', ''),
                        'gene_description': gene.get('description', ''),
                        'pleiotropy_score': gene.get('pleiotropy_score', ''),
                        'specificity_score': gene.get('specificity_score', ''),
                        'grna_sequence': guide.get('seq', ''),
                        'position': guide.get('position', ''),
                        'doench_score': guide.get('doench_score', ''),
                        'cfd_off_targets': guide.get('cfd_off_targets', '')
                    })
        logger.info(f"  ✓ CSV export: {csv_path}")
        
        # HTML report (formatted version for pipeline output)
        html_path = output_dir / f"mouse_analysis_{timestamp}.html"
        pipeline_output = {
            "metadata": results["metadata"],
            "genes": processed_genes,
            "statistics": results["statistics"]
        }
        generate_html_report(pipeline_output, str(html_path))
        logger.info(f"  ✓ HTML report: {html_path}")
        
        # Step 6: Display summary
        logger.info("\n" + "="*70)
        logger.info("ANALYSIS COMPLETE")
        logger.info("="*70)
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Genes found: {len(genes)}")
        logger.info(f"Genes processed: {max_genes}")
        logger.info(f"Genes passing filter: {len(processed_genes)}")
        logger.info(f"Total gRNAs designed: {results['statistics']['total_grnas']}")
        
        logger.info("\nProcessed Genes:")
        for i, gene in enumerate(processed_genes):
            logger.info(f"  {i+1}. {gene['symbol']}")
            logger.info(f"     Pleiotropy: {gene['pleiotropy_score']:.2f}")
            logger.info(f"     gRNAs: {len(gene['guides'])}")
            if gene['guides']:
                for j, guide in enumerate(gene['guides'][:2]):
                    logger.info(f"       - {guide['seq']} (Doench: {guide.get('doench_score', 'N/A')})")
        
        logger.info(f"\nOutput files saved to: {output_dir.absolute()}")
        
        return results
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return None


if __name__ == "__main__":
    # Process only 5 genes for quick demonstration
    results = run_limited_mouse_analysis(max_genes=5)
    sys.exit(0 if results else 1)
