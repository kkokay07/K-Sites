# Universal K-Sites Integration Plan

## Overview
This document outlines the integration plan to merge the original K-Sites architecture with Sandip's Neo4j/KEGG implementation into a unified platform that leverages both GO term analysis and pathway graph analytics for enhanced gene selection and gRNA design.

## Sandip Functions to Reuse

### From `graph_query_api.py`:
- `get_gene_neighborhood(gene_id)` - To identify genes in the same pathway as the target
- `get_gene_pathway_counts()` - For pathway-based pleiotropy assessment
- `get_pleiotropic_genes(min_pathways=2)` - To identify highly connected genes
- `get_pathway_overlap(pathway_id)` - To detect pathway cross-talk
- `run_query(query, parameters=None)` - Core query execution function
- `_build_graph(records)` - Graph structure builder

### From `ingest_kegg_to_neo4j.py`:
- `create_constraints()` - Neo4j constraint creation
- `load_kegg_organisms()` - KEGG organism loading
- `ingest_pathways(org_code)` - Pathway ingestion logic
- `ingest_genes(org_code)` - Gene ingestion logic
- `ingest_organism(org_code, org_name)` - Complete organism ingestion pipeline

## Injection Points in Pipeline

### 1. `k_sites/gene_analysis/pleiotropy_calculator.py`
Replace simple GO-count pleiotropy with graph-based centrality:
- Integrate pathway-based metrics using `get_gene_pathway_counts()`
- Implement degree centrality from pathway connections
- Add betweenness centrality for pathway importance
- Combine GO and pathway metrics for final pleiotropy score

### 2. `k_sites/gene_analysis/filter_engine.py`
Enhance filtering to include pathway neighbors:
- Use `get_gene_neighborhood(gene_id)` to identify pathway neighbors
- Filter out genes that appear in the same pathway as the target
- Implement pathway overlap detection using `get_pathway_overlap()`

### 3. `k_sites/crispr_design/offtarget_predictor.py`
Extend off-target analysis to include pathway exclusion:
- After sequence-based off-target detection, check if targets are in same pathway
- Use pathway queries to exclude genes in same pathway even if sequence allows
- Implement pathway-safe filtering

### 4. `k_sites/data_retrieval/kegg_mapper.py`
Create new module to bridge GO and KEGG:
- Map GO terms to KEGG pathways
- Retrieve pathway information for genes in the target GO term
- Integrate pathway data with GO annotations

### 5. `k_sites/rag_system/context_analyzer.py`
Enhance literature context with pathway information:
- Include pathway-specific literature
- Use pathway topology for context extraction
- Combine traditional literature with pathway analysis

## Required Neo4j Setup Steps

### 1. Install Neo4j Server
```bash
# Download and install Neo4j
# Start the server locally on default port 7687
```

### 2. Configure Connection Settings
From Sandip's implementation:
- URI: `neo4j://127.0.0.1:7687`
- Username: `neo4j`
- Password: `kkokay07` (should be changed in production)

### 3. Run Initial Ingestion
```bash
# Run the ingestion script to populate the graph
python k_sites/neo4j/ingestion_utils.py
```

### 4. Create Constraints
Execute `create_constraints()` to ensure data integrity:
- Organism ID uniqueness
- Pathway ID uniqueness
- Gene ID uniqueness

### 5. Populate with Target Organisms
Use `ingest_organism()` for the organisms you need:
- Common model organisms (hsa, mmu, etc.)
- Organisms relevant to user's research

## New Module Implementations

### `k_sites/neo4j/connection_manager.py`
- Handle connection lifecycle
- Implement connection pooling
- Error handling and retries
- Configuration from environment variables

### `k_sites/neo4j/graph_queries.py`
- Adapt Sandip's `graph_query_api.py` functions
- Add pathway-specific queries
- Implement centrality calculations
- Add utility functions for gene/pathway operations

### `k_sites/neo4j/pathway_analytics.py`
- Implement centrality measures (degree, betweenness, closeness)
- Pathway overlap analysis
- Gene neighborhood analysis
- Graph-based pleiotropy calculations

### `k_sites/neo4j/ingestion_utils.py`
- Adapt `ingest_kegg_to_neo4j.py` for modular use
- Add incremental update capabilities
- Error recovery and logging
- Progress tracking

## Integration Sequence

### Phase 1: Infrastructure
1. Set up Neo4j connection management
2. Implement basic graph queries
3. Test connection and basic operations

### Phase 2: Data Integration
1. Ingest KEGG data for target organisms
2. Create mapping between GO terms and KEGG pathways
3. Test pathway queries with sample data

### Phase 3: Enhanced Analysis
1. Modify pleiotropy calculator to include graph metrics
2. Update gene filtering to include pathway analysis
3. Test with sample GO terms

### Phase 4: gRNA Design Enhancement
1. Update off-target analysis to include pathway exclusion
2. Implement pathway-safe gRNA selection
3. Test with known gene sets

### Phase 5: Reporting
1. Update report generator to include pathway metrics
2. Add pathway safety scores to output
3. Create visualizations for pathway relationships

## Testing Strategy

### Unit Tests
- Test individual graph query functions
- Test pathway overlap detection
- Test centrality calculations
- Test pathway-safe filtering

### Integration Tests
- End-to-end flow with GO term input
- Verify pathway exclusion works correctly
- Test performance with large pathway graphs

### Validation Tests
- Compare results with original K-Sites
- Validate pathway-based pleiotropy scores
- Verify biological relevance of results

## Configuration Requirements

### Environment Variables
- `NEO4J_URI`: Neo4j server URI
- `NEO4J_USER`: Neo4j username
- `NEO4J_PASSWORD`: Neo4j password
- `KEGG_ORGANISMS`: Comma-separated list of organisms to ingest

### Dependencies
- `neo4j`: Python driver for Neo4j
- `networkx`: For centrality calculations
- `requests`: For KEGG API calls during ingestion

## Error Handling

### Neo4j Connection Errors
- Fallback to basic GO-only analysis if Neo4j unavailable
- Graceful degradation of features
- Clear error messages to users

### Ingestion Failures
- Partial data availability handling
- Recovery from interrupted ingestion
- Logging and monitoring

### Query Timeouts
- Appropriate timeout settings
- Retry mechanisms for transient failures
- User notification of degraded performance