"""
K-Sites: AI-Powered CRISPR Guide RNA Design Platform

A comprehensive tool for designing high-confidence gRNAs with integrated 
GO term and KEGG pathway analysis for reduced pleiotropy.
"""

__version__ = "1.2.0"
__author__ = "K-Sites Development Team"
__description__ = "AI-Powered CRISPR Guide RNA Design Platform with Pathway-Aware Off-Target Filtering"

from k_sites.workflow.pipeline import run_k_sites_pipeline
from k_sites.cli import main

__all__ = [
    "run_k_sites_pipeline", 
    "main",
    "__version__"
]