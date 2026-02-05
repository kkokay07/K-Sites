"""
Report Generator for K-Sites

This module generates publication-ready HTML reports from K-Sites pipeline output.
"""

import json
import html
import csv
import os
from typing import Dict, Any, List
from io import StringIO
import logging

# Set up logging
logger = logging.getLogger(__name__)


def generate_html_report(pipeline_output: dict, output_path: str) -> None:
    """
    Generate a publication-ready HTML report from pipeline output.
    
    Args:
        pipeline_output: Output dictionary from run_k_sites_pipeline
        output_path: Path to save the HTML report
    """
    logger.info(f"Generating HTML report at {output_path}")
    
    try:
        # Extract data from pipeline output
        metadata = pipeline_output.get("metadata", {})
        genes = pipeline_output.get("genes", [])
        
        # Count statistics
        total_genes_screened = len(genes)
        total_guides = sum(len(gene.get("guides", [])) for gene in genes)
        pathway_conflict_guides = sum(
            1 for gene in genes 
            for guide in gene.get("guides", []) 
            if guide.get("pathway_conflict", False)
        )
        
        # Generate the HTML report
        html_content = _generate_report_html(
            metadata, 
            genes, 
            total_genes_screened, 
            total_guides, 
            pathway_conflict_guides
        )
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Generate additional output formats
        _generate_additional_outputs(pipeline_output, output_path)
        
        logger.info(f"Successfully generated HTML report at {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate HTML report: {str(e)}")
        raise


def _generate_additional_outputs(pipeline_output: dict, output_path: str) -> None:
    """
    Generate additional output formats (CSV, FASTA).
    
    Args:
        pipeline_output: Output dictionary from run_k_sites_pipeline
        output_path: Base path for the HTML report (used to determine output directory)
    """
    try:
        # Get the directory of the output path
        output_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        
        # Generate CSV report
        csv_path = os.path.join(output_dir, f"{base_name}_detailed.csv")
        _generate_csv_report(pipeline_output, csv_path)
        
        # Generate FASTA report
        fasta_path = os.path.join(output_dir, f"{base_name}_grna_sequences.fasta")
        _generate_fasta_report(pipeline_output, fasta_path)
        
        logger.info(f"Generated additional output files: {csv_path}, {fasta_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate additional outputs: {str(e)}")


def _generate_csv_report(pipeline_output: dict, csv_path: str) -> None:
    """
    Generate a detailed CSV report with all results.
    
    Args:
        pipeline_output: Output dictionary from run_k_sites_pipeline
        csv_path: Path to save the CSV report
    """
    try:
        genes = pipeline_output.get("genes", [])
        
        # Prepare CSV data
        rows = []
        
        # Add header row
        header = [
            "Gene_Symbol", "Gene_Description", "Entrez_ID", "Pleiotropy_Score", 
            "Specificity_Score", "Evidence_Quality", "Literature_Support", 
            "Conservation_Score", "Composite_Score", "BP_Term_Count",
            "Experimental_Evidence_Count", "Computational_Evidence_Count", 
            "IEA_Evidence_Count", "Guide_Sequence", "Guide_Position", 
            "Doench_Score", "CFD_Off_Targets", "Pathway_Conflict",
            "Phenotype_Severity", "Phenotype_Risk_Level", "Phenotype_Confidence",
            "Phenotype_Lethality_Stage", "Safety_Recommendation"
        ]
        rows.append(header)
        
        # Add data rows
        for gene in genes:
            gene_symbol = gene.get("symbol", "")
            gene_description = gene.get("description", "")
            entrez_id = gene.get("entrez_id", "")
            pleiotropy_score = gene.get("pleiotropy_score", "")
            specificity_score = gene.get("specificity_score", "")
            evidence_quality = gene.get("evidence_quality", "")
            literature_support = gene.get("literature_support", "")
            conservation_score = gene.get("conservation_score", "")
            composite_score = gene.get("composite_score", "")
            bp_term_count = gene.get("bp_term_count", "")
            exp_count = gene.get("experimental_evidence_count", "")
            comp_count = gene.get("computational_evidence_count", "")
            iea_count = gene.get("iea_evidence_count", "")
            
            # Get phenotype prediction if available
            phenotype_pred = gene.get("phenotype_prediction", {})
            if phenotype_pred:
                phenotype_severity = phenotype_pred.get("severity", {}).value if hasattr(phenotype_pred.get("severity", {}), "value") else str(phenotype_pred.get("severity", ""))
                phenotype_risk = phenotype_pred.get("risk_level", {}).value if hasattr(phenotype_pred.get("risk_level", {}), "value") else str(phenotype_pred.get("risk_level", ""))
                phenotype_confidence = phenotype_pred.get("confidence_score", "")
                phenotype_stage = phenotype_pred.get("lethality_stage", "")
                confidence_reasoning = phenotype_pred.get("confidence_reasoning", "")
            else:
                phenotype_severity = ""
                phenotype_risk = ""
                phenotype_confidence = ""
                phenotype_stage = ""
                confidence_reasoning = ""
            
            # Determine safety recommendation based on phenotype and other factors
            if phenotype_pred and phenotype_risk in ["CRITICAL", "HIGH"]:
                safety_recommendation = "Conditional KO/CRISPRi preferred"
            elif pleiotropy_score > 5:
                safety_recommendation = "Consider heterozygous KO"
            else:
                safety_recommendation = "Standard KO acceptable"
            
            # Add rows for each guide
            guides = gene.get("guides", [])
            for guide in guides:
                guide_seq = guide.get("seq", "")
                guide_position = guide.get("position", "")
                doench_score = guide.get("doench_score", "")
                cfd_off_targets = guide.get("cfd_off_targets", "")
                pathway_conflict = guide.get("pathway_conflict", "")
                
                row = [
                    gene_symbol, gene_description, entrez_id, pleiotropy_score,
                    specificity_score, evidence_quality, literature_support,
                    conservation_score, composite_score, bp_term_count,
                    exp_count, comp_count, iea_count,
                    guide_seq, guide_position, doench_score,
                    cfd_off_targets, pathway_conflict,
                    phenotype_severity, phenotype_risk, phenotype_confidence,
                    phenotype_stage, safety_recommendation
                ]
                rows.append(row)
            
            # If no guides, still add the gene information
            if not guides:
                row = [
                    gene_symbol, gene_description, entrez_id, pleiotropy_score,
                    specificity_score, evidence_quality, literature_support,
                    conservation_score, composite_score, bp_term_count,
                    exp_count, comp_count, iea_count,
                    "", "", "", "", "",
                    phenotype_severity, phenotype_risk, phenotype_confidence,
                    phenotype_stage, safety_recommendation
                ]
                rows.append(row)
        
        # Write CSV file
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)
        
        logger.info(f"Generated CSV report at {csv_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate CSV report: {str(e)}")
        raise


def _generate_fasta_report(pipeline_output: dict, fasta_path: str) -> None:
    """
    Generate a FASTA file with all gRNA sequences.
    
    Args:
        pipeline_output: Output dictionary from run_k_sites_pipeline
        fasta_path: Path to save the FASTA report
    """
    try:
        genes = pipeline_output.get("genes", [])
        
        with open(fasta_path, 'w', encoding='utf-8') as fasta_file:
            # Write header comment
            fasta_file.write(f"# K-Sites gRNA sequences\n")
            fasta_file.write(f"# Generated from pipeline output\n\n")
            
            # Write sequences
            for gene in genes:
                gene_symbol = gene.get("symbol", "Unknown")
                guides = gene.get("guides", [])
                
                for i, guide in enumerate(guides):
                    guide_seq = guide.get("seq", "")
                    if guide_seq:
                        # Create header with gene info and guide properties
                        header_info = f"gene:{gene_symbol} pos:{guide.get('position', 'N/A')} doench:{guide.get('doench_score', 'N/A')}"
                        if guide.get("pathway_conflict", False):
                            header_info += " pathway_conflict:YES"
                        
                        fasta_file.write(f">gRNA_{gene_symbol}_{i+1} {header_info}\n")
                        fasta_file.write(f"{guide_seq}\n")
        
        logger.info(f"Generated FASTA report at {fasta_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate FASTA report: {str(e)}")
        raise


def _generate_report_html(
    metadata: Dict[str, Any], 
    genes: list, 
    total_genes_screened: int, 
    total_guides: int, 
    pathway_conflict_guides: int
) -> str:
    """
    Generate the complete HTML report.
    """
    # Escape metadata values for safety
    escaped_go_term = html.escape(metadata.get("go_term", "Unknown"))
    escaped_organism = html.escape(metadata.get("organism", "Unknown"))
    resolved_organism = metadata.get("resolved_organism", {})
    escaped_scientific_name = html.escape(resolved_organism.get("scientific_name", "Unknown"))
    timestamp = metadata.get("timestamp", "")
    execution_duration = metadata.get("execution_duration", 0)
    
    # Build the HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K-Sites CRISPR Design Report - {escaped_go_term}</title>
    <style>
        :root {{
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --danger-color: #e74c3c;
            --light-bg: #f8f9fa;
            --dark-bg: #2c3e50;
            --border-color: #dee2e6;
            --text-color: #212529;
            --text-light: #6c757d;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: white;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--border-color);
        }}
        
        h1 {{
            color: var(--primary-color);
            margin-bottom: 10px;
            font-size: 2.2em;
        }}
        
        .subtitle {{
            color: var(--text-light);
            font-size: 1.1em;
            margin-bottom: 15px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e4edf9 100%);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 4px solid var(--secondary-color);
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }}
        
        .summary-item {{
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .summary-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: var(--primary-color);
        }}
        
        .summary-label {{
            font-size: 0.9em;
            color: var(--text-light);
        }}
        
        .section {{
            margin: 30px 0;
        }}
        
        .section-title {{
            color: var(--primary-color);
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background-color: var(--primary-color);
            color: white;
            font-weight: 600;
        }}
        
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        tr:hover {{
            background-color: #e9f7fe;
        }}
        
        .sequence {{
            font-family: 'SF Mono', Consolas, Monaco, monospace;
            font-size: 0.9em;
            letter-spacing: 0.5px;
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }}
        
        .score-high {{
            color: var(--success-color);
            font-weight: bold;
        }}
        
        .score-medium {{
            color: var(--warning-color);
            font-weight: bold;
        }}
        
        .score-low {{
            color: var(--danger-color);
            font-weight: bold;
        }}
        
        .pathway-conflict {{
            background-color: #fff3cd;
            color: #856404;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        .phenotype-severity {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .phenotype-lethal {{ background-color: #f8d7da; color: #721c24; }}
        .phenotype-severe {{ background-color: #fff3cd; color: #856404; }}
        .phenotype-moderate {{ background-color: #cce7ff; color: #004085; }}
        .phenotype-mild {{ background-color: #d4edda; color: #155724; }}
        .phenotype-unknown {{ background-color: #e2e3e5; color: #6c757d; }}
        
        .risk-level {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .risk-critical {{ background-color: #dc3545; color: white; }}
        .risk-high {{ background-color: #fd7e14; color: white; }}
        .risk-medium {{ background-color: #ffc107; color: #212525; }}
        .risk-low {{ background-color: #28a745; color: white; }}
        .risk-unknown {{ background-color: #6c757d; color: white; }}
        
        .btn-copy {{
            background-color: #e9ecef;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
        }}
        
        .btn-copy:hover {{
            background-color: #dee2e6;
        }}
        
        .btn-download {{
            background-color: var(--secondary-color);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            text-decoration: none;
            display: inline-block;
            margin-right: 10px;
            margin-bottom: 10px;
        }}
        
        .btn-download:hover {{
            background-color: #2980b9;
        }}
        
        .accordion {{
            background-color: white;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 10px;
            overflow: hidden;
        }}
        
        .accordion-header {{
            background-color: #f8f9fa;
            padding: 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }}
        
        .accordion-content {{
            padding: 0;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.2s ease-out;
        }}
        
        .accordion.active .accordion-content {{
            max-height: 1000px;
        }}
        
        .accordion-body {{
            padding: 20px;
        }}
        
        .bio-context {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            border-left: 4px solid var(--secondary-color);
        }}
        
        .abstract {{
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px dashed var(--border-color);
        }}
        
        .abstract-title {{
            font-weight: 600;
            margin-bottom: 5px;
            color: var(--primary-color);
        }}
        
        .abstract-meta {{
            font-size: 0.85em;
            color: var(--text-light);
            margin-bottom: 8px;
        }}
        
        .download-section {{
            text-align: center;
            margin: 40px 0;
            padding: 30px;
            background: linear-gradient(135deg, #e8f4f8 0%, #d4edf9 100%);
            border-radius: 10px;
        }}
        
        .download-btn {{
            display: inline-block;
            background-color: var(--secondary-color);
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1.1em;
            margin: 10px;
            transition: background-color 0.3s;
        }}
        
        .download-btn:hover {{
            background-color: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        .recommendation {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        
        .safety-warning {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        
        .safety-safe {{
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            
            th, td {{
                padding: 8px 10px;
                font-size: 0.9em;
            }}
            
            .sequence {{
                font-size: 0.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>K-Sites CRISPR Design Report</h1>
            <div class="subtitle">GO Term: {escaped_go_term} | Organism: {escaped_scientific_name} | Generated: {timestamp}</div>
        </header>
        
        <div class="summary-card">
            <h2>Executive Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">{total_genes_screened}</div>
                    <div class="summary-label">Genes Screened</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{total_guides}</div>
                    <div class="summary-label">gRNAs Designed</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{len([g for gene in genes for g in gene.get('guides', []) if g.get('doench_score', 0) >= 0.7])}</div>
                    <div class="summary-label">High-Efficacy gRNAs</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{pathway_conflict_guides}</div>
                    <div class="summary-label">Pathway Conflicts</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Safety Recommendations</h2>
            <div class="recommendation">
                <h3>Overall Assessment</h3>
                <p>Based on phenotype predictions and pleiotropy scores, this analysis identifies potential risks and provides recommendations for safe experimental design.</p>
            </div>
            
            <div class="safety-warning">
                <h3>Critical Risks</h3>
                <p>Genes with high predicted lethality or severe phenotypes require conditional knockout approaches or alternative methods like CRISPRi.</p>
            </div>
            
            <div class="safety-safe">
                <h3>Low-Risk Targets</h3>
                <p>Genes with mild or unknown phenotypes and low pleiotropy scores are suitable for standard knockout experiments.</p>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Gene Summary</h2>
            <table>
                <thead>
                    <tr>
                        <th>Gene Symbol</th>
                        <th>Pleiotropy Score</th>
                        <th>Specificity Score</th>
                        <th>Phenotype Severity</th>
                        <th>Risk Level</th>
                        <th>Safety Recommendation</th>
                        <th>gRNAs Available</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add gene rows to the table
    for gene in genes:
        symbol = html.escape(gene.get("symbol", "Unknown"))
        score = gene.get("pleiotropy_score", 0)
        specificity_score = gene.get("specificity_score", 0)
        
        # Get phenotype prediction if available
        phenotype_pred = gene.get("phenotype_prediction", {})
        if phenotype_pred:
            phenotype_severity = phenotype_pred.get("severity", {}).value if hasattr(phenotype_pred.get("severity", {}), "value") else str(phenotype_pred.get("severity", "UNKNOWN"))
            phenotype_risk = phenotype_pred.get("risk_level", {}).value if hasattr(phenotype_pred.get("risk_level", {}), "value") else str(phenotype_pred.get("risk_level", "UNKNOWN"))
            phenotype_confidence = phenotype_pred.get("confidence_score", 0)
        else:
            phenotype_severity = "UNKNOWN"
            phenotype_risk = "UNKNOWN"
            phenotype_confidence = 0
        
        # Determine safety recommendation
        if phenotype_risk in ["CRITICAL", "HIGH"]:
            safety_recommendation = "Conditional KO/CRISPRi"
        elif score > 5:
            safety_recommendation = "Consider heterozygous"
        else:
            safety_recommendation = "Standard KO acceptable"
        
        # Format severity for display
        severity_class = f"phenotype-{phenotype_severity.lower()}" if phenotype_severity != "UNKNOWN" else "phenotype-unknown"
        risk_class = f"risk-{phenotype_risk.lower()}" if phenotype_risk != "UNKNOWN" else "risk-unknown"
        
        guide_count = len(gene.get("guides", []))
        
        html_content += f"""
                    <tr>
                        <td><strong>{symbol}</strong></td>
                        <td>{score:.2f}</td>
                        <td>{specificity_score:.2f}</td>
                        <td><span class="phenotype-severity {severity_class}">{phenotype_severity}</span></td>
                        <td><span class="risk-level {risk_class}">{phenotype_risk}</span></td>
                        <td>{safety_recommendation}</td>
                        <td>{guide_count}</td>
                    </tr>
"""
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">Detailed gRNA Designs</h2>
"""
    
    # Add detailed gRNA information for each gene
    for gene in genes:
        symbol = html.escape(gene.get("symbol", "Unknown"))
        guides = gene.get("guides", [])
        
        if not guides:
            continue
            
        html_content += f"""
            <div class="accordion">
                <div class="accordion-header" onclick="toggleAccordion(this)">
                    {symbol} - {len(guides)} gRNA{'s' if len(guides) != 1 else ''}
                    <span>▼</span>
                </div>
                <div class="accordion-content">
                    <div class="accordion-body">
                        <table>
                            <thead>
                                <tr>
                                    <th>gRNA Sequence (5'→3')</th>
                                    <th>Position</th>
                                    <th>Doench Score</th>
                                    <th>CFD Off-targets</th>
                                    <th>Pathway Conflict</th>
                                    <th>Copy Sequence</th>
                                </tr>
                            </thead>
                            <tbody>
"""
        
        for guide in guides:
            seq = html.escape(guide.get("seq", ""))
            position = guide.get("position", "N/A")
            doench_score = guide.get("doench_score", 0)
            cfd_off_targets = guide.get("cfd_off_targets", "N/A")
            pathway_conflict = guide.get("pathway_conflict", False)
            
            # Determine score class for coloring
            if doench_score >= 0.7:
                score_class = "score-high"
            elif doench_score >= 0.5:
                score_class = "score-medium"
            else:
                score_class = "score-low"
            
            # Format pathway conflict indicator
            if pathway_conflict:
                conflict_indicator = '<span class="pathway-conflict">⚠️ Yes</span>'
            else:
                conflict_indicator = "No"
            
            html_content += f"""
                                <tr>
                                    <td><span class="sequence">{seq}</span></td>
                                    <td>{position}</td>
                                    <td class="{score_class}">{doench_score:.2f}</td>
                                    <td>{cfd_off_targets}</td>
                                    <td>{conflict_indicator}</td>
                                    <td><button class="btn-copy" onclick="copyToClipboard('{seq}')">📋 Copy</button></td>
                                </tr>
"""
        
        html_content += """
                            </tbody>
                        </table>
"""
        
        # Add biological context and phenotype information
        phenotype_pred = gene.get("phenotype_prediction", {})
        if phenotype_pred:
            html_content += f"""
                        <div class="bio-context">
                            <h3>Phenotype Prediction for {symbol}</h3>
                            <p><strong>Severity:</strong> <span class="phenotype-severity {f"phenotype-{phenotype_pred.get('severity', 'UNKNOWN').lower()}"}">{phenotype_pred.get('severity', 'UNKNOWN')}</span></p>
                            <p><strong>Risk Level:</strong> <span class="risk-level {f"risk-{phenotype_pred.get('risk_level', 'UNKNOWN').lower()}"}">{phenotype_pred.get('risk_level', 'UNKNOWN')}</span></p>
                            <p><strong>Confidence Score:</strong> {phenotype_pred.get('confidence_score', 0):.2f}</p>
"""
            if phenotype_pred.get('lethality_stage'):
                html_content += f"<p><strong>Lethality Stage:</strong> {phenotype_pred.get('lethality_stage')}</p>"
            if phenotype_pred.get('confidence_reasoning'):
                html_content += f"<p><strong>Reasoning:</strong> {phenotype_pred.get('confidence_reasoning')}</p>"
            html_content += """
                        </div>
"""
        
        html_content += """
                    </div>
                </div>
            </div>
"""
    
    html_content += """
        </div>
        
        <div class="download-section">
            <h2>Download Full Results</h2>
            <p>Download various file formats for further analysis and experimental planning.</p>
            <a href="./""" + os.path.basename(output_path.replace('.html', '_detailed.csv')) + """" class="download-btn">Download CSV Report</a>
            <a href="./""" + os.path.basename(output_path.replace('.html', '_grna_sequences.fasta')) + """" class="download-btn">Download FASTA Sequences</a>
        </div>
        
        <footer style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border-color); color: var(--text-light); font-size: 0.9em;">
            <p>K-Sites CRISPR Design Platform | Generated by Universal K-Sites Pipeline</p>
            <p>This report contains publication-ready gRNA designs with pathway-aware off-target filtering and phenotype predictions.</p>
            <p>Execution time: {execution_duration:.2f}s</p>
        </footer>
    </div>
    
    <script>
        function toggleAccordion(header) {
            const accordion = header.parentElement;
            accordion.classList.toggle('active');
            const arrow = header.querySelector('span');
            arrow.textContent = accordion.classList.contains('active') ? '▲' : '▼';
        }
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                alert('Copied to clipboard: ' + text);
            }).catch(function(err) {
                console.error('Could not copy text: ', err);
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {
                    document.execCommand('copy');
                    alert('Copied to clipboard: ' + text);
                } catch (err) {
                    console.error('Fallback copy failed', err);
                }
                document.body.removeChild(textArea);
            });
        }
        
        // Initialize accordions to be closed by default
        document.addEventListener('DOMContentLoaded', function() {
            const accordions = document.querySelectorAll('.accordion');
            accordions.forEach(acc => acc.classList.remove('active'));
        });
    </script>
</body>
</html>"""
    
    return html_content