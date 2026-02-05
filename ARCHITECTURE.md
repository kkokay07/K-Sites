# Universal K-Sites Architecture Document

## Overview
Universal K-Sites is a next-generation CRISPR guide RNA design platform that integrates traditional GO term analysis with advanced KEGG pathway graph analytics. The system combines semantic GO annotations with topological pathway relationships to provide more accurate pleiotropy assessment and safer gRNA design.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                INPUT LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  GO Term (e.g., "GO:0006281") + Organism (NCBI TaxID or scientific name)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WORKFLOW CONTROLLER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Coordinates module execution, manages data flow                           │
│  Orchestrates GO and KEGG pathway integration                              │
│  Generates final HTML/CSV reports                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MODULE LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  DATA RETRIEVAL │  │  GENE ANALYSIS  │  │   GRAPH UTILS   │            │
│  │                 │  │                 │  │                 │            │
│  │ • GO annotations│  │ • Graph-based   │  │ • Neo4j         │            │
│  │ • Gene data     │  │   pleiotropy    │  │   connection    │            │
│  │ • Organism data │  │ • Pathway       │  │ • Pathway       │            │
│  │ • KEGG mapping  │  │   overlap       │  │   queries       │            │
│  └─────────────────┘  │ • Centrality    │  │ • Topological   │            │
│                       │   scoring       │  │   analytics     │            │
│                       └─────────────────┘  └─────────────────┘            │
│                              │                       │                     │
│                              ▼                       ▼                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │CRISPR DESIGN    │  │   RAG SYSTEM    │  │    WORKFLOW     │            │
│  │                 │  │                 │  │                 │            │
│  │ • gRNA design   │  │ • PubMed mining │  │ • Pipeline      │            │
│  │ • Scoring       │  │ • Literature    │  │ • Data          │            │
│  │ • Off-target    │  │   context       │  │   orchestration │            │
│  │ • Pathway-safe  │  │ • KEGG lit      │  │ • Integration   │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│           │                       │                       │                │
│           ▼                       ▼                       ▼                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │     CLI         │  │     OTHER       │  │   DEPENDENCY    │            │
│  │                 │  │                 │  │   MANAGEMENT    │            │
│  │ • Command       │  │ • Configuration │  │                 │            │
│  │   interface     │  │ • Logging       │  │ • Neo4j setup   │            │
│  │ • Args parsing  │  │ • Error hand.   │  │ • KEGG ingest   │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  HTML Report: High-confidence gRNAs with integrated GO and KEGG pleiotropy │
│  CSV Export: Detailed metrics including pathway safety scores              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Structure

### `k_sites/` (Root Package)
- `__init__.py`: Package initialization and version info

### `k_sites/data_retrieval/` (Data Access Layer)
- `entrez_client.py`: NCBI Entrez API integration
- `quickgo_client.py`: QuickGO API integration for GO annotations
- `organism_resolver.py`: Scientific name ↔ NCBI TaxID conversion
- `gene_fetcher.py`: Gene information retrieval
- `kegg_mapper.py`: KEGG pathway mapping for GO terms

### `k_sites/gene_analysis/` (Analysis Layer)
- `pleiotropy_calculator.py`: Enhanced pleiotropy scoring using both GO and pathway graph
- `specificity_analyzer.py`: GO term specificity analysis
- `pathway_overlap_detector.py`: Identifies genes in same pathway as target
- `centrality_analyzer.py`: Graph-based centrality measures (degree, betweenness)
- `filter_engine.py`: Gene filtering based on integrated metrics

### `k_sites/neo4j/` (Graph Utilities)
- `__init__.py`: Neo4j connection initialization
- `connection_manager.py`: Handles Neo4j connection lifecycle
- `graph_queries.py`: KEGG pathway graph queries (adapted from Sandip's `graph_query_api.py`)
- `pathway_analytics.py`: Pathway-based analytics and centrality calculations
- `ingestion_utils.py`: KEGG data ingestion utilities (based on `ingest_kegg_to_neo4j.py`)

### `k_sites/crispr_design/` (Design Layer)
- `grna_designer.py`: gRNA design using NGG PAM rules
- `efficiency_scorer.py`: Doench 2016 efficiency scoring
- `cfd_scorer.py`: CFD (Cutting Frequency Determination) scoring
- `offtarget_predictor.py`: Off-target analysis (≤4 mismatches) with pathway exclusion
- `pathway_safe_filter.py`: Filters out gRNAs targeting genes in same pathway
- `validation_engine.py`: gRNA validation pipeline

### `k_sites/rag_system/` (Knowledge Layer)
- `pubmed_miner.py`: PubMed literature mining
- `uniprot_client.py`: UniProt data integration
- `kegg_literature_miner.py`: KEGG-specific literature context
- `context_analyzer.py`: Combined literature and pathway context extraction

### `k_sites/workflow/` (Orchestration Layer)
- `pipeline.py`: Main workflow orchestration with GO and KEGG integration
- `report_generator.py`: HTML/CSV report generation with pathway safety metrics
- `data_aggregator.py`: Results aggregation from all sources

### `k_sites/cli.py` (Interface Layer)
- Command-line interface implementation supporting both original and enhanced functionality

## Enhanced Data Flow

1. **Input Processing**: GO term and organism are validated and normalized
2. **Dual Data Retrieval**: 
   - NCBI Entrez resolves organism and retrieves gene annotations
   - QuickGO provides GO annotations
   - Neo4j KEGG graph provides pathway relationships
3. **Enhanced Gene Filtering**:
   - Traditional GO-based pleiotropy (≤3 GO terms)
   - Graph-based pathway pleiotropy using centrality measures
   - Pathway neighbor analysis to identify genes in same pathway
4. **Pathway-Aware gRNA Design**: 
   - gRNAs designed using NGG PAM rules
   - Off-target analysis excludes genes in same pathway
   - Pathway safety scoring integrated into efficiency metrics
5. **Scoring**: Each gRNA receives:
   - Doench 2016 and CFD efficiency scores
   - Graph-based pathway safety scores
   - Integrated pleiotropy assessment
6. **Literature Context**: Relevant publications from both PubMed and KEGG pathway literature
7. **Report Generation**: Enhanced HTML/CSV reports with pathway safety metrics

## Technology Stack

- **Backend**: Python 3.8+
- **Data Retrieval**: NCBI Entrez E-Utilities, QuickGO REST API
- **Graph Database**: Neo4j with python-neo4j driver
- **Scientific Libraries**: Biopython, NumPy, Pandas
- **Graph Analytics**: NetworkX for centrality calculations
- **Web Requests**: requests library
- **Report Generation**: Jinja2 templates for HTML, built-in CSV module
- **Testing**: pytest for unit testing

## Integration Points with Sandip's Implementation

- **Neo4j Connection**: Reuse connection management from `graph_query_api.py`
- **Pathway Queries**: Adapt pathway graph queries for gene neighborhood analysis
- **KEGG Ingestion**: Leverage ingestion logic from `ingest_kegg_to_neo4j.py`
- **Graph Analytics**: Utilize pathway overlap and centrality measures

## Deployment Considerations

- Modular design enables easy testing and maintenance
- API rate limiting handled appropriately
- Neo4j connection pooling and error handling
- Caching mechanisms for repeated queries
- Configuration management for API keys and Neo4j credentials