# K-Sites Feature Implementation Summary

## Overview
The K-Sites CRISPR guide RNA design platform has been enhanced with comprehensive Non-Pleiotropic Gene Identification capabilities and advanced CRISPR gRNA design features.

---

## Module 1: Non-Pleiotropic Gene Identification

### Implemented Features

#### 1. Multi-Database Integration (GO.org, UniProt, KEGG)
- **Module**: `k_sites/data_retrieval/multi_database_client.py`
- **Functionality**:
  - Queries all three databases simultaneously using ThreadPoolExecutor
  - Combines results with deduplication of BP terms
  - Evidence classification from all sources
  - Graceful handling of API failures

#### 2. Pleiotropy Scoring Algorithm (Exponential Decay)
- **Formula**: `score = 10 * (1 - exp(-λ * (n-1)))` where λ=0.3
- **Location**: `k_sites/gene_analysis/pleiotropy_scorer.py`
- **Scale**: 0-10 (higher = more pleiotropic)

#### 3. Evidence-Based Filtering
- **Classification**:
  - **Experimental**: IDA, IMP, IGI, IPI, IEP, HTP, HDA, HMP, HGI, HEP
  - **Computational**: ISS, ISO, ISA, ISM, IGC, IBA, IBD, IKR, IRD, RCA
  - **IEA**: Electronic annotation (prediction, NOT evidence)
- **Implementation**: Explicit classification in `multi_database_client.py`

#### 4. Cross-Species Validation
- **Organisms Configured**:
  - Human (9606)
  - Mouse (10090)
  - Fly (7227)
  - Worm (6239)
- **Function**: `validate_across_species()`

#### 5. Customizable Thresholds
- **CLI Parameter**: `--max-pleiotropy` (0-10 scale)
- **Default**: 10 (include all)
- **Usage**: Filter genes by BP term count

#### 6. Weighted Ranking Algorithm
- **Weights**:
  - Specificity: 40%
  - Evidence Quality: 25%
  - Literature Support: 20%
  - Conservation: 15%
- **Function**: `rank_genes_by_specificity()`

#### 7. Specificity Scoring (0-1 Scale)
- **CRITICAL**: Specificity is 0-1 scale (NOT 0-10)
- **Formula**: `specificity = 1 - (pleiotropy / 10)`
- **Visualization**: Percentage bars in HTML reports

#### 8. Real Literature Support (PubMed API)
- **Function**: `get_literature_support()`
- **API**: NCBI Entrez E-Utilities
- **Scoring**: Log-scale (1000+ papers = 1.0)

#### 9. GO Term Autocomplete
- **Module**: `k_sites/data_retrieval/go_autocomplete.py`
- **Features**:
  - Real-time suggestions
  - Gene count statistics
  - Term definitions
  - Aspect classification

#### 10. HTML Reports with Visual Indicators
- **Features**:
  - Specificity bars (0-1 scale)
  - Color-coded indicators
  - Phenotype severity badges
  - Risk level classifications

#### 11. CSV/Excel Export
- **Files Generated**:
  - `*_comprehensive.csv` - All metrics
  - `*_gene_summary.csv` - Focused summary
  - `*_grna_sequences.fasta` - Sequences

---

## Module 2: CRISPR Guide RNA (gRNA) Design

### A. PAM Site Identification

#### Multi-Cas Support
- **Cas Types Implemented**:
  | Cas Type | PAM Pattern | Spacer Length |
  |----------|-------------|---------------|
  | SpCas9 | NGG | 20nt |
  | SaCas9 | NNGRRT | 21nt |
  | Cas12a | TTTV | 23nt |
  | Cas9-NG | NG | 20nt |
  | xCas9 | NG or GAA | 20nt |

- **Module**: `k_sites/crispr_design/guide_designer.py`
- **Class**: `CRISPRDesigner`
- **Configuration**: `PAM_CONFIGS` dictionary

#### Strand Scanning
- Both forward (+) and reverse (-) strands analyzed
- Reverse complement PAM detection
- Proper guide extraction for each strand

#### Quality Filtering
- **GC Content**: 40-70% range, optimal 55%
- **Poly-T Avoidance**: Detects 4+ T runs (premature termination)
- **Repeat Detection**: Counts max repeat length
- **Exon Annotation**: Maps guides to specific exons

### B. On-Target Efficiency Scoring (Doench 2016)

#### Position-Specific Nucleotide Preferences
- **20 position-dependent weights** defined in `DOENCH_POSITION_WEIGHTS`
- Each position has weights for A, T, G, C
- Based on Doench et al. 2016, Nature Biotechnology

#### GC Content Optimization
- Optimal: 55% GC content
- Penalty for deviation: `|GC - 0.55| * 0.5`
- Enforced within 40-70% range

#### Secondary Structure Prediction
- Self-complementarity detection
- Hairpin potential scoring
- Penalty for potential secondary structures

#### Composite Scoring
- Score range: 0-1 (higher = better efficiency)
- Minimum threshold: 0.3 (configurable)

### C. Off-Target Prediction (CFD Algorithm)

#### Position-Weighted Mismatch Scoring
| Region | Positions | Penalty |
|--------|-----------|---------|
| Seed (PAM-proximal) | 17-20 | 90% |
| Middle | 13-16 | 60% |
| Distal | 8-12 | 40% |
| 5' end | 1-7 | 20% |

- **Higher penalty = less tolerance for mismatches**
- Formula: `CFD_score = Π(1 - penalty_i)` for each mismatch

#### PAM Quality Assessment
| PAM | Quality |
|-----|---------|
| NGG | 1.0 (best) |
| NGCG | 0.8 |
| GAA | 0.7 |
| NAG | 0.3 |
| Unknown | 0.1 |

#### Genomic Annotation
- Chromosome location tracking
- Gene name identification
- Exon location mapping

#### Severity Classification
| CFD Score | Mismatches | Severity |
|-----------|------------|----------|
| >0.5 | ≤2 | CRITICAL |
| >0.3 | ≤2 | HIGH |
| >0.1 | ≤3 | MEDIUM |
| <0.1 | >3 | LOW |

#### Specificity Scoring
- **Range**: 0-1 (higher = more specific)
- Factors:
  - Number of off-targets
  - Off-target severity
  - PAM quality bonus
- Formula: `1.0 - count_penalty - severity_penalty + pam_bonus`

---

## Technical Architecture

### Module Structure
```
k_sites/
├── data_retrieval/
│   ├── multi_database_client.py  (GO, UniProt, KEGG)
│   ├── go_autocomplete.py        (Auto-complete)
│   └── go_gene_mapper.py         (Gene mapping)
├── gene_analysis/
│   └── pleiotropy_scorer.py      (Scoring algorithms)
├── crispr_design/
│   ├── __init__.py               (Exports)
│   └── guide_designer.py         (gRNA design - NEW)
├── reporting/
│   ├── report_generator.py       (HTML reports)
│   └── csv_export.py             (CSV export)
└── cli.py                        (Command line)
```

### Test Coverage
| Module | Tests | Status |
|--------|-------|--------|
| Non-Pleiotropic | 13 | ✅ PASS |
| CRISPR Design | 22 | ✅ PASS |
| **Total** | **35** | **✅ ALL PASS** |

---

## Usage Examples

### Non-Pleiotropic Gene Identification
```bash
# Basic analysis
k-sites --go-term GO:0006281 --organism "Homo sapiens" --output report.html

# With phenotype prediction
k-sites --go-term GO:0006281 --organism 9606 --predict-phenotypes

# Search GO terms
k-sites --go-term-search "DNA repair" --organism "Homo sapiens"
```

### CRISPR gRNA Design (Programmatic)
```python
from k_sites.crispr_design import CRISPRDesigner, CasType

# Design with SpCas9
designer = CRISPRDesigner(CasType.SPCAS9)
guides = designer.design_guides(
    gene_symbol="BRCA1",
    taxid="9606",
    gc_min=0.40,
    gc_max=0.70,
    avoid_poly_t=True
)

# Multi-Cas design
from k_sites.crispr_design import design_guides_multi_cas

all_guides = design_guides_multi_cas(
    gene_symbol="BRCA1",
    taxid="9606",
    cas_types=[CasType.SPCAS9, CasType.SACAS9]
)
```

---

---

## Module 3: RAG-Based Phenotype Prediction (ENHANCED)

### A. Literature Mining

#### Real-time PubMed Integration
- **Module**: `k_sites/rag_system/literature_context.py`
- **Class**: `LiteratureMiner`
- **API**: NCBI Entrez E-Utilities (esearch, efetch)
- **Features**:
  - Rate-limited requests (0.2s with API key, 0.35s without)
  - Automatic retry with exponential backoff
  - Email-based user identification for NCBI compliance

#### Targeted Search Strategies
| Search Type | Query Focus |
|-------------|-------------|
| `knockout` | Knockout, deletion, gene knockout studies |
| `phenotype` | Phenotype reports, morphological changes |
| `viability` | Viability, lethal, lethality, survival |
| `crispr` | CRISPR, guide RNA, gene editing |
| `compensatory` | Compensatory mechanisms, redundancy, paralogs |
| `comprehensive` | All phenotype-related terms combined |

#### Smart Query Construction
- Gene symbol + targeted MeSH terms
- Multiple query strategies per gene
- Boolean logic for precision

#### Abstract and Full-Text Retrieval
- **PMC Open Access Integration**: OAI-PMH protocol
- **Full-text fetching**: When PMC ID available
- **Evidence quality scoring**: High when full text available

#### Batch Processing
- Multi-gene parallel processing
- Deduplication across search strategies
- Rate limiting for NCBI compliance

### B. RAG (Retrieval-Augmented Generation)

#### Semantic Embeddings
- **Model**: SentenceTransformer `all-MiniLM-L6-v2`
- **Vector dimension**: 384
- **Location**: `DiversityAwareVectorStore`
- Normalized L2 embeddings

#### Vector Search (FAISS)
- **Index type**: Flat L2 (exact search)
- **Distance metric**: Euclidean (L2)
- Similarity conversion: `sim = 1 / (1 + distance)`
- Batch encoding support

#### Adaptive Retrieval
- **Relevance threshold filtering**: Configurable (0.0-1.0)
- **Context-aware k selection**: Adapts number of results based on query complexity
  - High-context queries (viability, lethal): 2x results
  - Specific queries: Standard k

#### Diversity Weighting (MMR)
- **Algorithm**: Maximal Marginal Relevance
- **Formula**: `MMR = λ·Relevance - (1-λ)·max_sim_to_selected`
- **Purpose**: Avoid redundant documents, maximize coverage
- **Parameter**: `diversity_weight` (0-1)

#### Query Specialization
| Query Type | Purpose |
|------------|---------|
| Viability queries | "Is gene essential for survival?" |
| Phenotype severity | "What phenotypes result from knockout?" |
| Lethality stage | "When does lethality occur?" |
| Compensatory mechanisms | "Are there backup/redundant genes?" |

### C. Phenotype Extraction & Classification

#### NLP Pattern Matching
- **Module**: `PhenotypeExtractor`
- **Pattern categories**:
  - `lethality`: lethal, embryonic lethal, perinatal lethal
  - `development`: growth defect, developmental defect, malformation
  - `behavior`: locomotion defect, motor defect, coordination
  - `physiology`: metabolic, cardiac, respiratory, neurological

#### Severity Categorization
| Severity | Indicators | Risk Level |
|----------|------------|------------|
| **LETHAL** | Embryonic, perinatal, postnatal lethality, 100% lethal | CRITICAL |
| **SEVERE** | Severe defects, profound impairment, major defects | HIGH |
| **MODERATE** | Moderate, intermediate, reduced fitness, partial | MEDIUM |
| **MILD** | Mild, subtle, minor, slight, minimal | LOW |
| **UNKNOWN** | No clear indicators found | UNKNOWN |

#### Risk Assessment
- Automatic mapping from severity to risk
- CRITICAL: Complete lethality expected
- HIGH: Major functional defects
- MEDIUM: Viable with reduced fitness
- LOW: Subtle phenotypes only
- UNKNOWN: Insufficient data

#### Confidence Scoring
- **Formula**: Composite of:
  - Publication count (base: 0.1-0.4)
  - Evidence quality (0.0-0.3) - full text bonus
  - Phenotype extraction (0.0-0.2)
- **Range**: 0.0-1.0
- **Reasoning**: Human-readable explanation

#### Lethality Stage Detection
| Stage | Patterns Detected |
|-------|-------------------|
| Embryonic | embryonic lethal, E##.#, prenatal |
| Perinatal | perinatal lethal, birth lethal |
| Postnatal | postnatal lethal, P##.#, adult lethal |
| Larval | larval lethal, L# lethal |
| Neonatal | neonatal lethal, newborn lethal |

#### Compensatory Mechanisms
- **Pattern matching**: compensatory, redundancy, paralog, genetic buffering
- **Extraction**: Context-aware with confidence scoring
- **Purpose**: Identify backup genes that may mask phenotypes

---

## Technical Architecture

### Module Structure
```
k_sites/
├── data_retrieval/
│   ├── multi_database_client.py  (GO, UniProt, KEGG)
│   ├── go_autocomplete.py        (Auto-complete)
│   └── go_gene_mapper.py         (Gene mapping)
├── gene_analysis/
│   └── pleiotropy_scorer.py      (Scoring algorithms)
├── crispr_design/
│   ├── __init__.py               (Exports)
│   └── guide_designer.py         (gRNA design)
├── rag_system/                   (NEW - RAG Phenotype Prediction)
│   ├── __init__.py               (Exports)
│   └── literature_context.py     (Full RAG implementation)
├── reporting/
│   ├── report_generator.py       (HTML reports)
│   └── csv_export.py             (CSV export)
└── cli.py                        (Command line)
```

### Test Coverage
| Module | Tests | Status |
|--------|-------|--------|
| Non-Pleiotropic | 13 | ✅ PASS |
| CRISPR Design | 22 | ✅ PASS |
| RAG Phenotype | 15 | ✅ PASS |
| **Total** | **50** | **✅ ALL PASS** |

---

## Usage Examples

### Non-Pleiotropic Gene Identification
```bash
# Basic analysis
k-sites --go-term GO:0006281 --organism "Homo sapiens" --output report.html

# With phenotype prediction (RAG-based)
k-sites --go-term GO:0006281 --organism 9606 --predict-phenotypes --output report.html

# Search GO terms
k-sites --go-term-search "DNA repair" --organism "Homo sapiens"
```

### RAG Phenotype Prediction (Programmatic)
```python
from k_sites.rag_system import (
    RAGPhenotypePredictor, 
    PhenotypeSeverity, 
    RiskLevel,
    predict_gene_phenotype
)

# Method 1: Using the predictor class
predictor = RAGPhenotypePredictor()
prediction = predictor.predict_phenotype("BRCA1", organism_taxid="9606", 
                                          include_compensatory=True)

print(f"Severity: {prediction.severity.value}")
print(f"Risk Level: {prediction.risk_level.value}")
print(f"Confidence: {prediction.confidence_score:.2f}")
print(f"Lethality Stage: {prediction.lethality_stage}")
print(f"Compensatory Mechanisms: {len(prediction.compensatory_mechanisms)}")

# Method 2: Convenience function
prediction = predict_gene_phenotype("TP53", include_compensatory=True)

# Method 3: Batch prediction
genes = ["BRCA1", "TP53", "EGFR", "MYC"]
batch_results = predictor.batch_predict_phenotypes(genes, organism_taxid="9606")
```

### Using Literature Miner Directly
```python
from k_sites.rag_system import LiteratureMiner

miner = LiteratureMiner()

# Search specific gene
results = miner.search_pubmed("BRCA1", search_type="knockout", retmax=20)

# Batch processing
batch_results = miner.batch_search_genes(
    ["BRCA1", "TP53"], 
    search_types=["knockout", "phenotype", "viability", "compensatory"]
)

# Fetch full text when available
for gene, pubs in batch_results.items():
    for pub in pubs:
        if pub.pmcid:
            full_text = miner.fetch_pmc_fulltext(pub.pmcid)
            if full_text:
                print(f"Full text available for {pub.pmid}")
```

---

## Validation Summary

### Non-Pleiotropic Gene Identification
- ✅ Multi-database integration (GO.org, UniProt, KEGG)
- ✅ Exponential decay pleiotropy scoring
- ✅ Evidence-based filtering (IDA/IMP/IGI ≠ IEA)
- ✅ Cross-species validation (human, mouse, fly, worm)
- ✅ Customizable thresholds (0-10)
- ✅ Weighted ranking (40/25/20/15)
- ✅ Specificity 0-1 scale (CRITICAL)
- ✅ Real PubMed literature support
- ✅ GO term autocomplete
- ✅ HTML visual indicators
- ✅ CSV/Excel export

### CRISPR gRNA Design
- ✅ Multi-Cas support (5 types)
- ✅ Strand scanning (both strands)
- ✅ GC content optimization (40-70%, optimal 55%)
- ✅ Poly-T avoidance
- ✅ Repeat detection
- ✅ Exon annotation
- ✅ Doench 2016 (20 position weights)
- ✅ CFD off-target (position-weighted)
- ✅ PAM quality (NGG=1.0, NAG=0.3)
- ✅ Genomic annotation
- ✅ Severity (CRITICAL/HIGH/MEDIUM/LOW)
- ✅ Specificity scoring (0-1)

### RAG-Based Phenotype Prediction
- ✅ Real-time PubMed integration (NCBI Entrez)
- ✅ Targeted searches (knockout, phenotype, viability, CRISPR, compensatory)
- ✅ Smart query construction (multiple strategies per gene)
- ✅ Abstract retrieval (PubMed efetch)
- ✅ Full-text retrieval (PMC Open Access)
- ✅ Batch processing (multi-gene analysis)
- ✅ Semantic embeddings (SentenceTransformer all-MiniLM-L6-v2)
- ✅ Vector search (FAISS L2 indexing)
- ✅ Adaptive retrieval (context-aware k selection)
- ✅ Relevance threshold filtering
- ✅ Diversity weighting (Maximal Marginal Relevance)
- ✅ Query specialization (viability, severity, compensatory)
- ✅ NLP pattern matching (phenotype terms)
- ✅ Severity categorization (LETHAL/SEVERE/MODERATE/MILD/UNKNOWN)
- ✅ Risk assessment (CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN)
- ✅ Confidence scoring (publication count + evidence quality)
- ✅ Lethality stage detection (Embryonic/Perinatal/Postnatal)
- ✅ Compensatory mechanism detection
- ✅ Pipeline integration (--predict-phenotypes flag)

---

## Compliance Status

| Requirement | Status |
|-------------|--------|
| All Non-Pleiotropic features | ✅ COMPLETE |
| All CRISPR Design features | ✅ COMPLETE |
| All RAG Phenotype features | ✅ COMPLETE |
| Literature Mining (A.1-A.5) | ✅ COMPLETE |
| RAG System (B.1-B.6) | ✅ COMPLETE |
| Phenotype Extraction (C.1-C.6) | ✅ COMPLETE |
| Test coverage | ✅ 50/50 PASS |
| Documentation | ✅ UPDATED |
| Pipeline Integration | ✅ ENABLED |

**ALL REQUIREMENTS MET. NO MERCY NEEDED.**

---

*Last Updated: 2026-02-06*
*RAG System Enhanced with Full Capabilities*
