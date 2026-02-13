"""
RAG Report Generator for K-Sites

Generates detailed literature analysis reports showing:
- PubMed publications retrieved
- Semantic similarity scores
- Phenotype predictions with confidence
- Supporting evidence from literature
"""

import json
import html
import logging
from typing import Dict, List, Any
from pathlib import Path

try:
    from k_sites.rag_system.literature_context import LiteratureMiner, RAGPhenotypePredictor
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)


def generate_rag_report(gene_symbol: str, organism_taxid: str, output_path: str) -> bool:
    """
    Generate a detailed RAG literature analysis report for a gene.
    
    Args:
        gene_symbol: Gene symbol (e.g., "BRCA1")
        organism_taxid: NCBI Taxonomy ID
        output_path: Path to save the HTML report
        
    Returns:
        True if report generated successfully, False otherwise
    """
    if not RAG_AVAILABLE:
        logger.error("RAG system not available. Install sentence-transformers, faiss-cpu, numpy")
        return False
    
    logger.info(f"Generating RAG report for {gene_symbol}...")
    
    try:
        # Mine literature
        miner = LiteratureMiner()
        
        # Search multiple query types
        search_types = ["knockout", "phenotype", "viability", "crispr", "compensatory"]
        all_publications = []
        
        for search_type in search_types:
            try:
                pubs = miner.search_pubmed(gene_symbol, search_type=search_type, retmax=20)
                all_publications.extend(pubs)
            except Exception as e:
                logger.warning(f"Could not search {search_type} for {gene_symbol}: {e}")
        
        # Deduplicate by PMID
        seen_pmids = set()
        unique_publications = []
        for pub in all_publications:
            if pub.pmid not in seen_pmids:
                seen_pmids.add(pub.pmid)
                unique_publications.append(pub)
        
        # Get phenotype prediction
        predictor = RAGPhenotypePredictor()
        prediction = predictor.predict_phenotype(gene_symbol, organism_taxid)
        
        # Generate HTML report
        html_content = _generate_rag_html(
            gene_symbol=gene_symbol,
            organism_taxid=organism_taxid,
            publications=unique_publications,
            prediction=prediction
        )
        
        # Write report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"RAG report generated: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate RAG report: {e}")
        return False


def _generate_rag_html(
    gene_symbol: str,
    organism_taxid: str,
    publications: List[Any],
    prediction: Any
) -> str:
    """Generate HTML content for RAG report."""
    
    # Format phenotype info
    severity = prediction.severity.value if hasattr(prediction.severity, 'value') else str(prediction.severity)
    risk_level = prediction.risk_level.value if hasattr(prediction.risk_level, 'value') else str(prediction.risk_level)
    confidence = prediction.confidence_score
    
    # Severity color
    severity_colors = {
        'LETHAL': '#dc3545',
        'SEVERE': '#fd7e14',
        'MODERATE': '#ffc107',
        'MILD': '#28a745',
        'UNKNOWN': '#6c757d'
    }
    severity_color = severity_colors.get(severity, '#6c757d')
    
    # Risk color
    risk_colors = {
        'CRITICAL': '#dc3545',
        'HIGH': '#fd7e14',
        'MEDIUM': '#ffc107',
        'LOW': '#28a745',
        'UNKNOWN': '#6c757d'
    }
    risk_color = risk_colors.get(risk_level, '#6c757d')
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG Literature Analysis - {html.escape(gene_symbol)}</title>
    <style>
        :root {{
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --danger-color: #e74c3c;
            --light-bg: #f8f9fa;
            --border-color: #dee2e6;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f7fa;
            padding: 20px;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid var(--secondary-color);
        }}
        
        h1 {{ color: var(--primary-color); font-size: 2em; margin-bottom: 10px; }}
        .subtitle {{ color: #666; font-size: 1.1em; }}
        
        .prediction-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .prediction-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .prediction-item {{
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 8px;
        }}
        
        .prediction-value {{
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .prediction-label {{ font-size: 0.9em; opacity: 0.9; }}
        
        .severity-badge, .risk-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.9em;
        }}
        
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: var(--light-bg);
            border-radius: 8px;
        }}
        
        .section-title {{
            color: var(--primary-color);
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.4em;
        }}
        
        .publication {{
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid var(--secondary-color);
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .pub-title {{
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 8px;
            font-size: 1.1em;
        }}
        
        .pub-meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        
        .pub-abstract {{
            color: #333;
            line-height: 1.6;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }}
        
        .pub-links {{
            margin-top: 10px;
        }}
        
        .pub-links a {{
            display: inline-block;
            margin-right: 15px;
            color: var(--secondary-color);
            text-decoration: none;
            font-weight: 500;
        }}
        
        .pub-links a:hover {{ text-decoration: underline; }}
        
        .evidence-quality {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .evidence-high {{ background: #d4edda; color: #155724; }}
        .evidence-medium {{ background: #fff3cd; color: #856404; }}
        .evidence-low {{ background: #f8d7da; color: #721c24; }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .stat-box {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--secondary-color);
        }}
        
        .stat-label {{
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }}
        
        .phenotypes-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }}
        
        .phenotype-tag {{
            background: var(--secondary-color);
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
        }}
        
        .confidence-bar {{
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }}
        
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
            border-radius: 10px;
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 RAG Literature Analysis Report</h1>
            <div class="subtitle">
                Gene: <strong>{html.escape(gene_symbol)}</strong> | 
                Organism TaxID: <strong>{organism_taxid}</strong>
            </div>
        </header>
        
        <div class="prediction-card">
            <h2>🎯 Phenotype Prediction Summary</h2>
            <div class="prediction-grid">
                <div class="prediction-item">
                    <div class="prediction-value">{severity}</div>
                    <div class="prediction-label">Severity</div>
                </div>
                <div class="prediction-item">
                    <div class="prediction-value">{risk_level}</div>
                    <div class="prediction-label">Risk Level</div>
                </div>
                <div class="prediction-item">
                    <div class="prediction-value">{confidence:.0%}</div>
                    <div class="prediction-label">Confidence</div>
                </div>
            </div>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: {confidence * 100}%"></div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 Literature Mining Statistics</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value">{len(publications)}</div>
                    <div class="stat-label">Publications Retrieved</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{len([p for p in publications if p.pmcid])}</div>
                    <div class="stat-label">Open Access (PMC)</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{len([p for p in publications if p.evidence_quality == 'high'])}</div>
                    <div class="stat-label">High-Quality Evidence</div>
                </div>
            </div>
        </div>
"""
    
    # Add predicted phenotypes section
    if prediction.predicted_phenotypes:
        html_content += f"""
        <div class="section">
            <h2 class="section-title">🧬 Predicted Phenotypes</h2>
            <div class="phenotypes-list">
"""
        for phenotype in prediction.predicted_phenotypes[:10]:  # Show top 10
            html_content += f'                <span class="phenotype-tag">{html.escape(str(phenotype))}</span>\n'
        html_content += """
            </div>
        </div>
"""
    
    # Add compensatory mechanisms section
    if prediction.compensatory_mechanisms:
        html_content += f"""
        <div class="section">
            <h2 class="section-title">🔄 Compensatory Mechanisms</h2>
            <ul>
"""
        for mechanism in prediction.compensatory_mechanisms:
            html_content += f'                <li>{html.escape(str(mechanism))}</li>\n'
        html_content += """
            </ul>
        </div>
"""
    
    # Add supporting evidence section
    if prediction.supporting_evidence:
        html_content += """
        <div class="section">
            <h2 class="section-title">📖 Key Supporting Evidence</h2>
"""
        for evidence in prediction.supporting_evidence[:5]:  # Show top 5
            evidence_text = evidence.get('text', '') if isinstance(evidence, dict) else str(evidence)
            source = evidence.get('source', 'Unknown') if isinstance(evidence, dict) else 'Unknown'
            html_content += f"""
            <div class="publication" style="border-left-color: #28a745;">
                <div class="pub-abstract">{html.escape(evidence_text[:500])}{'...' if len(evidence_text) > 500 else ''}</div>
                <div class="pub-meta">Source: {html.escape(str(source))}</div>
            </div>
"""
        html_content += """
        </div>
"""
    
    # Add publications section
    html_content += f"""
        <div class="section">
            <h2 class="section-title">📚 Retrieved Publications ({len(publications)})</h2>
"""
    
    for pub in publications[:20]:  # Show top 20
        # Determine evidence quality class
        quality_class = f"evidence-{pub.evidence_quality}" if hasattr(pub, 'evidence_quality') else "evidence-medium"
        quality_text = pub.evidence_quality.upper() if hasattr(pub, 'evidence_quality') else "MEDIUM"
        
        # Truncate abstract
        abstract = pub.abstract[:800] + '...' if len(pub.abstract) > 800 else pub.abstract
        
        html_content += f"""
            <div class="publication">
                <div class="pub-title">{html.escape(pub.title)}</div>
                <div class="pub-meta">
                    <span class="evidence-quality {quality_class}">{quality_text}</span> | 
                    {html.escape(pub.journal)} | 
                    {html.escape(pub.publication_date)} | 
                    PMID: {pub.pmid}
                </div>
                <div class="pub-abstract">{html.escape(abstract)}</div>
                <div class="pub-links">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{pub.pmid}/" target="_blank">View on PubMed</a>
"""
        if pub.pmcid:
            html_content += f'                    <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/{pub.pmcid}/" target="_blank">View Full Text (PMC)</a>\n'
        
        html_content += """
                </div>
            </div>
"""
    
    if len(publications) > 20:
        html_content += f"""
            <p style="text-align: center; color: #666; margin-top: 20px;">
                ... and {len(publications) - 20} more publications
            </p>
"""
    
    html_content += """
        </div>
        
        <footer style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
            <p>Generated by K-Sites RAG System | Literature Mining with Semantic Analysis</p>
            <p>Using PubMed, PMC Open Access, and SentenceTransformer Embeddings</p>
        </footer>
    </div>
</body>
</html>
"""
    
    return html_content


def generate_batch_rag_report(
    gene_symbols: List[str],
    organism_taxid: str,
    output_dir: str
) -> Dict[str, bool]:
    """
    Generate RAG reports for multiple genes.
    
    Args:
        gene_symbols: List of gene symbols
        organism_taxid: NCBI Taxonomy ID
        output_dir: Directory to save reports
        
    Returns:
        Dictionary mapping gene symbol to success status
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    results = {}
    for gene in gene_symbols:
        output_path = str(Path(output_dir) / f"RAG_report_{gene}.html")
        success = generate_rag_report(gene, organism_taxid, output_path)
        results[gene] = success
    
    return results
