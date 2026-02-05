# Universal K-Sites Usage Guide

Universal K-Sites is an AI-powered CRISPR guide RNA design platform that integrates GO term analysis with KEGG pathway graph analytics for safer, more specific gRNA design.

## Quick Start

Get started with K-Sites in 3 commands:

```bash
pip install -e .
export NCBI_EMAIL=you@example.com
k-sites --go-term GO:0006281 --organism "Homo sapiens" --output dna_repair_guides.html
```

## Prerequisites

1. **Python 3.8+** with pip
2. **NCBI Account**: Register at [https://account.ncbi.nlm.nih.gov/](https://account.ncbi.nlm.nih.gov/) and get an API key (optional but recommended)
3. **Neo4j Server** (optional): For pathway-aware analysis, install and run Neo4j locally

## Installation

### Basic Installation
```bash
# Clone or download the K-Sites repository
cd k-sites
pip install -e .
```

### Neo4j Setup (for pathway-aware analysis)
```bash
# 1. Install Neo4j Desktop or run Docker container:
docker run --rm -d --name neo4j -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/kkokay07 neo4j:latest

# 2. Ingest KEGG pathway data:
python -m k_sites.neo4j.ingest_kegg --taxid 9606 --organism "Homo sapiens"
```

## Configuration

Set up your configuration in one of these ways:

### Option 1: Environment Variables
```bash
export NCBI_EMAIL=your.email@example.com
export NCBI_API_KEY=your_ncbi_api_key  # Optional, but increases rate limits
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=kkokay07
```

### Option 2: Configuration File
Create `k-sites.yaml` in your working directory or `~/.openclaw/workspace/k-sites/config/`:

```yaml
neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "${NEO4J_PASSWORD}"  # ← resolved from environment variable

ncbi:
  email: "your.email@example.com"  # Required by NCBI E-Utils
  api_key: "${NCBI_API_KEY}"      # Optional but recommended

pipeline:
  max_pleiotropy: 3
  use_graph: true
  cache_dir: "~/.openclaw/workspace/k-sites/.cache"

reporting:
  include_literature: true
  max_pubmed_results: 5
```

## Running Analyses

### Basic Command
```bash
k-sites --go-term GO:0006281 --organism "Homo sapiens" --output report.html
```

### Advanced Options
```bash
# Specify organism by TaxID
k-sites --go-term GO:0006281 --organism 9606 --output report.html

# Adjust pleiotropy threshold
k-sites --go-term GO:0006281 --organism "Homo sapiens" --output report.html --max-pleiotropy 2

# Disable pathway analysis (GO-only mode)
k-sites --go-term GO:0006281 --organism "Homo sapiens" --output report.html --no-graph

# Use KEGG organism code
k-sites --go-term GO:0006281 --organism hsa --output report.html
```

## Input Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--go-term` | GO term to analyze | `GO:0006281` (DNA repair) |
| `--organism` | Organism (name, TaxID, or KEGG code) | `"Homo sapiens"`, `9606`, `hsa` |
| `--output` | Output HTML report path | `report.html` |
| `--max-pleiotropy` | Max allowed pleiotropy score | `3` (default) |
| `--use-graph` | Enable pathway-aware analysis | Enabled by default if Neo4j available |
| `--no-graph` | Disable pathway analysis | GO-only mode |

## Output Files

### HTML Report (`*.html`)
- Interactive report with gene and gRNA tables
- Expandable sections for detailed gRNA information
- Pathway context and literature information
- Copy-to-clipboard functionality for gRNA sequences

### CSV Export
- Available within the HTML report interface
- Contains all gRNA designs with complete metadata
- Suitable for further analysis or sharing

## Biological Interpretation

### Pleiotropy Score
- **Calculation**: `(GO_BP_count - 1) + (KEGG_pathway_degree)`
- **Interpretation**: Lower scores indicate more specific targets
- **Threshold**: Adjust with `--max-pleiotropy` (default: 3)

### gRNA Quality Metrics
- **Doench Score**: On-target efficiency (0.0-1.0, higher is better)
- **CFD Off-targets**: Potential off-targets with ≤4 mismatches
- **Pathway Conflict**: Indicates if off-targets share KEGG pathways with target

## Common Use Cases

### 1. Pathway-Specific Gene Screening
```bash
# Find specific genes in DNA repair pathway
k-sites --go-term GO:0006281 --organism "Homo sapiens" --output dna_repair_guides.html
```

### 2. Cancer Pathway Analysis
```bash
# Identify pathway-specific targets for cancer research
k-sites --go-term GO:0007165 --organism "Homo sapiens" --output signal_transduction_guides.html
```

### 3. Comparative Analysis
```bash
# Run multiple GO terms and compare results
for go_term in GO:0006281 GO:0006974 GO:0042277; do
  k-sites --go-term $go_term --organism "Mus musculus" --output ${go_term}_mmu.html
done
```

## Troubleshooting

### Common Issues

**Error: "NCBI email not configured"**
- Solution: Set `NCBI_EMAIL` environment variable or configure in YAML file

**Error: "Neo4j connection failed"** 
- Solution: Either start Neo4j server or run with `--no-graph` flag

**Slow performance**
- Solution: Use NCBI API key to increase rate limits

**No genes returned**
- Solution: Verify GO term exists and organism has annotated genes for that term

### Debugging
Run with increased verbosity:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python -m k_sites.cli --go-term GO:0006281 --organism "Homo sapiens" --output report.html
```

## Wet-Lab Workflow

1. **Identify pathway of interest** (e.g., DNA repair, apoptosis)
2. **Find corresponding GO term** (use [AmiGO](http://amigo.geneontology.org/amigo) database)
3. **Run K-Sites analysis** with your organism
4. **Review HTML report** for highest-scoring gRNAs
5. **Select gRNAs** with high Doench scores and minimal pathway conflicts
6. **Order synthesized gRNAs** using sequence from report