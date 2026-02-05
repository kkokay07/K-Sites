"""
Neo4j Graph Database Utilities for Universal K-Sites

This package provides utilities for connecting to and querying
the Neo4j graph database containing KEGG pathway information.
"""

# Initialize Neo4j connection components
from .graph_client import get_graph_client, get_pathway_neighbors, close_graph_client, GraphClient
from .ingest_kegg import ingest_kegg_organism

__version__ = "1.0.0"
__all__ = [
    "get_graph_client",
    "get_pathway_neighbors",
    "close_graph_client",
    "GraphClient",
    "ingest_kegg_organism"
]