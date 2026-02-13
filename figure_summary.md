# Figure and Table Summary

**Manuscript:** K-Sites: An Integrated AI-Powered Platform for Non-Pleiotropic CRISPR Guide RNA Design with Pathway-Aware Off-Target Filtering

---

## Main Text Figures and Tables

### Figure 1: K-Sites System Architecture

**Type:** Schematic diagram

**Description:** Flowchart showing the K-Sites platform architecture with seven interconnected layers: Input Layer (GO term + organism), Workflow Controller, Module Layer (Data Retrieval, Gene Analysis, Graph Utils, CRISPR Design, RAG System, Workflow), and Output Layer (HTML/CSV reports).

**Key Components:**
- Data Retrieval: GO.org, UniProt, KEGG, NCBI Entrez
- Gene Analysis: Pleiotropy scoring, specificity analysis
- Graph Utils: Neo4j pathway analytics
- CRISPR Design: Multi-Cas support
- RAG System: Literature mining, phenotype prediction

**File format:** Vector graphics (PDF/SVG)
**Estimated size:** Full page width

---

### Figure 2: RAG-Based Phenotype Prediction Workflow

**Type:** Workflow diagram

**Description:** Step-by-step illustration of the RAG phenotype prediction pipeline showing: (1) Literature mining from PubMed, (2) Semantic embedding generation with SentenceTransformer, (3) FAISS vector indexing, (4) Diversity-weighted retrieval using MMR, and (5) NLP-based phenotype extraction.

**Key Components:**
- NCBI Entrez E-Utilities integration
- all-MiniLM-L6-v2 embedding model
- Maximal Marginal Relevance algorithm
- Severity classification (LETHAL to MILD)

**File format:** Vector graphics (PDF/SVG)
**Estimated size:** Full page width

---

### Table 1: Evidence Code Classification in K-Sites

**Type:** Summary table

**Content:** Three categories of evidence codes with their classifications and descriptions:
- Experimental (IDA, IMP, IGI, IPI, IEP, HTP, HDA, HMP, HGI, HEP)
- Computational (ISS, ISO, ISA, ISM, IGC, IBA, IBD, IKR, IRD, RCA)
- IEA (electronic annotation only)

**Columns:** Category, Evidence Codes, Description

**Location:** Results section (Evidence-Based Filtering)

---

### Table 2: Supported Cas Nucleases in K-Sites

**Type:** Summary table

**Content:** Five supported Cas nucleases with their PAM patterns, spacer lengths, and quality scores.

| Cas Type | PAM Pattern | Spacer Length | Quality Score |
|----------|-------------|---------------|---------------|
| SpCas9 | NGG | 20 nt | 1.0 |
| SaCas9 | NNGRRT | 21 nt | 0.9 |
| Cas12a | TTTV | 23 nt | 0.85 |
| Cas9-NG | NG | 20 nt | 0.7 |
| xCas9 | NG or GAA | 20 nt | 0.8 |

**Columns:** Cas Type, PAM Pattern, Spacer Length, Quality Score, PAM Position

**Location:** Results section (Multi-Cas gRNA Design)

---

### Table 3: CFD Mismatch Position Weighting

**Type:** Summary table

**Content:** Position-weighted mismatch penalties for CFD off-target scoring.

| Region | Positions | Penalty |
|--------|-----------|---------|
| Seed (PAM-proximal) | 17-20 | 0.90 |
| Middle | 13-16 | 0.60 |
| Distal | 8-12 | 0.40 |
| 5' end | 1-7 | 0.20 |

**Columns:** Region, Positions, Penalty, Rationale

**Location:** Results section (CFD Off-Target Prediction)

---

### Table 4: Test Coverage Summary

**Type:** Results table

**Content:** Unit test coverage statistics for each module.

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| Non-Pleiotropic Features | 13 | 94% | PASS |
| CRISPR Design | 22 | 91% | PASS |
| RAG Phenotype Prediction | 15 | 88% | PASS |
| **Total** | **50** | **91%** | **PASS** |

**Columns:** Module, Tests, Coverage, Status

**Location:** Results section (Performance Validation)

---

### Table 5: Comparison with Existing CRISPR Design Tools

**Type:** Comparison table

**Content:** Feature-by-feature comparison of K-Sites with CRISPOR, Benchling, and CHOPCHOP.

Features compared:
- On-target scoring (Doench)
- Off-target prediction
- Multi-Cas support
- Pleiotropy assessment
- Evidence-based filtering
- Cross-species validation
- Pathway-aware filtering
- RAG phenotype prediction
- CLI + Web interface

**Location:** Discussion section

---

## Supplementary Figures

### Figure S1: Pleiotropy Score Distribution

**Type:** Histogram with density curve

**Description:** Distribution of pleiotropy scores across 20,300 human protein-coding genes. Shows right-skewed distribution with mean ~5.2 and median ~4.8.

**Statistics shown:**
- Mean, median, mode
- Standard deviation
- Percentile markers (25th, 75th, 95th)

**File format:** PDF

---

### Figure S2: Lambda Parameter Optimization

**Type:** Line graph with confidence intervals

**Description:** Empirical optimization of the exponential decay parameter lambda (λ). Shows correlation coefficient (R²) between predicted pleiotropy and experimental phenotypic severity for λ values from 0.1 to 0.5.

**Optimal value:** λ = 0.3 (R² = 0.78)

**File format:** PDF

---

### Figure S3: Runtime Performance Benchmarks

**Type:** Scatter plot with regression line

**Description:** Execution time scaling with gene count for different GO terms. Linear regression shows R²=0.94.

**Tested GO terms:**
- GO:0006281 (DNA repair): 45 genes
- GO:0006915 (Apoptosis): 78 genes
- GO:0007049 (Cell cycle): 156 genes
- GO:0006954 (Inflammation): 89 genes

**File format:** PDF

---

### Figure S4: RAG Phenotype Prediction ROC Curves

**Type:** ROC curves (4 panels)

**Description:** Receiver operating characteristic curves for severity classification:
- Panel A: LETHAL (AUC = 0.94)
- Panel B: SEVERE (AUC = 0.91)
- Panel C: MODERATE (AUC = 0.87)
- Panel D: MILD (AUC = 0.85)

**Validation datasets:**
- MGI knockout phenotypes (247 genes)
- IMPC data (156 genes)
- Literature-curated gold standard (89 genes)

**File format:** PDF

---

### Figure S5: gRNA Quality Metrics Distribution

**Type:** Multi-panel histograms (4 panels)

**Description:** Distribution of key gRNA quality metrics across 1,000 designed guides:
- Panel A: Doench score (Mean = 0.62, SD = 0.18)
- Panel B: GC content (Mean = 54.3%, SD = 6.2%)
- Panel C: Off-target count (Mean = 4.2, SD = 3.1)
- Panel D: Specificity score (Mean = 0.78, SD = 0.15)

**File format:** PDF

---

### Figure S6: Pathway Overlap Network

**Type:** Network diagram

**Description:** Cytoscape-style network showing pathway relationships between genes in the DNA repair pathway (GO:0006281). 

**Visual encodings:**
- Node size: Degree centrality
- Edge thickness: Shared pathway membership
- Node color: Pleiotropy score (green=low, red=high)

**Hub genes identified:** ATM, BRCA1 (high connectivity)

**File format:** PDF (high resolution for printing)

---

## Supplementary Tables

### Table S1: Complete Evidence Code Reference

**Type:** Reference table

**Content:** All 27 GO evidence codes with:
- Code abbreviation
- Full name
- Category (Experimental, Computational, IEA, Author, Curator, No Data)
- Description
- Example usage

**Rows:** 27 evidence codes
**Columns:** 5

---

### Table S2: Doench 2016 Position Weight Matrix

**Type:** Data table

**Content:** Complete position-specific nucleotide weights for all 20 guide positions.

| Position | A | C | G | T |
|----------|--------|--------|--------|-------|
| 1 | -0.097377 | -0.083064 | 0.031048 | 0.0 |
| ... | ... | ... | ... | ... |
| 20 | 0.003281 | -0.001329 | -0.025902 | 0.0 |

**Rows:** 20 positions
**Columns:** 5 (Position, A, C, G, T)

---

### Table S3: CFD Mismatch Penalty Matrix

**Type:** Data table

**Content:** Complete position-weighted mismatch penalties for all 20 positions.

**Rows:** 20 positions
**Columns:** 3 (Position, Region, Penalty)

---

### Table S4: CFD Implementation Comparison

**Type:** Comparison table

**Content:** Comparison between original Hsu et al. CFD and K-Sites heuristic approach.

| Aspect | Original CFD | K-Sites Heuristic |
|--------|-------------|-------------------|
| Genome alignment | Required | Not required |
| Runtime | Hours | Seconds |
| Accuracy | Absolute | Relative |
| Use case | Final validation | Initial screening |

---

### Table S5: Test Coverage Detailed Report

**Type:** Results table

**Content:** Line-by-line coverage report for each module.

**Rows:** All Python modules
**Columns:** Module, Lines, Miss, Cover, Missing lines

---

### Table S6: RAG Validation Results

**Type:** Validation table

**Content:** Detailed validation results for RAG phenotype prediction.

| Gene | Predicted | Actual | Confidence | Validation Source |
|------|-----------|--------|------------|-------------------|
| BRCA1 | SEVERE | SEVERE | 0.92 | MGI |
| TP53 | SEVERE | SEVERE | 0.95 | MGI |
| ... | ... | ... | ... | ... |

**Rows:** 492 validated genes
**Columns:** 5

---

### Table S7: Cross-Species Validation Results

**Type:** Results table

**Content:** Gene conservation analysis across model organisms.

**Columns:** Gene, Human, Mouse, Fly, Worm, Conservation Score

---

### Table S8: Performance Benchmarks

**Type:** Performance table

**Content:** Runtime and memory benchmarks for standard GO terms.

| GO Term | Description | Genes | Time (s) | Memory (MB) |
|---------|-------------|-------|----------|-------------|
| GO:0006281 | DNA repair | 45 | 127 | 145 |
| GO:0006915 | Apoptosis | 78 | 198 | 178 |
| GO:0007049 | Cell cycle | 156 | 342 | 234 |
| GO:0006954 | Inflammation | 89 | 245 | 189 |

---

## Data Files

### File S1: Mouse Analysis Results (JSON)

**Format:** JSON
**Size:** ~2.3 MB
**Content:** Complete analysis results for DNA repair pathway in mouse
**Location:** `mouse_analysis_results/mouse_analysis_20260213_113905.json`

### File S2: gRNA Sequence Library (FASTA)

**Format:** FASTA
**Size:** ~15 KB
**Content:** 36 high-confidence gRNA sequences
**Location:** `mouse_analysis_results/mouse_analysis_20260213_113905_grna_sequences.fasta`

### File S3: Comprehensive Metrics (CSV)

**Format:** CSV
**Size:** ~85 KB
**Content:** 27 columns of detailed metrics for each gene and gRNA
**Location:** `mouse_analysis_results/mouse_analysis_20260213_113905_comprehensive.csv`

### File S4: GenBank Export

**Format:** GenBank
**Size:** ~45 KB
**Content:** Sequence annotations for visualization
**Location:** `mouse_analysis_results/mouse_analysis_20260213_113905_sequences.gb`

---

## Figure Preparation Guidelines

### Color Scheme
- Primary: #2E86AB (blue)
- Secondary: #A23B72 (magenta)
- Accent: #F18F01 (orange)
- Success: #C73E1D (red)
- Neutral: #6B7280 (gray)

### Font Specifications
- Main text: Arial, 8-10 pt
- Axis labels: Arial, 9 pt
- Titles: Arial Bold, 10-12 pt

### File Formats for Submission
- Vector graphics: PDF or EPS
- Raster images: TIFF at 300 dpi minimum
- Color mode: CMYK for print, RGB for web

### Figure Dimensions
- Single column: 8.5 cm width
- Double column: 17.5 cm width
- Full page: 17.5 cm × 23 cm

---

## Supplementary Information Structure

```
Supplementary Information/
├── Supplementary Methods/
│   ├── S1. API Documentation
│   ├── S2. Evidence Code Reference
│   ├── S3. Doench 2016 Weights
│   ├── S4. CFD Penalty Matrix
│   ├── S5. Test Coverage Report
│   └── S6. Benchmark Results
├── Supplementary Figures/
│   ├── Figure S1: Pleiotropy Distribution
│   ├── Figure S2: Lambda Optimization
│   ├── Figure S3: Runtime Benchmarks
│   ├── Figure S4: RAG ROC Curves
│   ├── Figure S5: Quality Metrics
│   └── Figure S6: Pathway Network
├── Supplementary Tables/
│   ├── Table S1: Evidence Codes
│   ├── Table S2: Doench Weights
│   ├── Table S3: CFD Matrix
│   ├── Table S4: CFD Comparison
│   ├── Table S5: Coverage Report
│   ├── Table S6: RAG Validation
│   ├── Table S7: Cross-Species
│   └── Table S8: Benchmarks
└── Supplementary Data/
    ├── File S1: JSON Results
    ├── File S2: FASTA Sequences
    ├── File S3: CSV Metrics
    └── File S4: GenBank
```

---

**Note to Production:** All figures are provided in editable vector format (Adobe Illustrator or SVG) to facilitate journal formatting requirements.
