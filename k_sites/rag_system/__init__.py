"""
RAG-Based Phenotype Prediction System

This module provides comprehensive RAG (Retrieval-Augmented Generation) capabilities
for predicting gene knockout phenotypes by mining and analyzing scientific literature.
"""

from .literature_context import (
    # Core classes
    LiteratureMiner,
    DiversityAwareVectorStore,
    PhenotypeExtractor,
    RAGPhenotypePredictor,
    
    # Data classes
    PhenotypePrediction,
    LiteratureRecord,
    
    # Enums
    PhenotypeSeverity,
    RiskLevel,
    
    # Convenience functions
    predict_gene_phenotype,
    batch_predict_gene_phenotypes,
)

# Make RAG availability check available
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

__all__ = [
    # Main classes
    'LiteratureMiner',
    'DiversityAwareVectorStore', 
    'PhenotypeExtractor',
    'RAGPhenotypePredictor',
    
    # Data classes
    'PhenotypePrediction',
    'LiteratureRecord',
    
    # Enums
    'PhenotypeSeverity',
    'RiskLevel',
    
    # Functions
    'predict_gene_phenotype',
    'batch_predict_gene_phenotypes',
    
    # Flags
    'RAG_AVAILABLE',
]
