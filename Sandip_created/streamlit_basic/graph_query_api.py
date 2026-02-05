"""
Graph Query API for KEGG Neo4j Graph

This module provides reusable functions to query:
- Organisms
- Pathways
- Genes
- Pleiotropic relationships

All functions return JSON-ready dictionaries:
{
  "nodes": [...],
  "edges": [...]
}
"""

from neo4j import GraphDatabase

# =====================================================
# NEO4J CONNECTION
# =====================================================
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "kkokay07"

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

# =====================================================
# INTERNAL HELPER
# =====================================================


def run_query(query, parameters=None):
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]

# =====================================================
# HELPER: FORMAT GRAPH OUTPUT
# =====================================================


def format_graph(records):
    nodes = {}
    edges = []

    for r in records:
        for key, value in r.items():
            if hasattr(value, "id"):  # Neo4j Node
                node_id = value["id"]
                if node_id not in nodes:
                    nodes[node_id] = {
                        "id": node_id,
                        "label": list(value.labels)[0],
                        "properties": dict(value)
                    }

        if "source" in r and "target" in r:
            edges.append({
                "source": r["source"],
                "target": r["target"],
                "type": r.get("type", "")
            })

    return {
        "nodes": list(nodes.values()),
        "edges": edges
    }

# =====================================================
# QUERY 1: ORGANISM → PATHWAYS → GENES
# =====================================================


def get_organism_graph(org_code):
    query = """
    MATCH (o:Organism {id:$org})-[:HAS_PATHWAY]->(p)-[:HAS_GENE]->(g)
    RETURN o, p, g
    """
    records = run_query(query, {"org": org_code})

    nodes = []
    edges = []

    for r in records:
        nodes.append({
            "id": r["o"]["id"],
            "label": "Organism",
            "properties": r["o"]
        })
        nodes.append({
            "id": r["p"]["id"],
            "label": "Pathway",
            "properties": r["p"]
        })
        nodes.append({
            "id": r["g"]["id"],
            "label": "Gene",
            "properties": r["g"]
        })

        edges.append({
            "source": r["o"]["id"],
            "target": r["p"]["id"],
            "type": "HAS_PATHWAY"
        })
        edges.append({
            "source": r["p"]["id"],
            "target": r["g"]["id"],
            "type": "HAS_GENE"
        })

    return _unique_graph(nodes, edges)


# =====================================================
# QUERY 2: PATHWAY → GENES
# =====================================================


def get_pathway_graph(pathway_id):
    query = """
    MATCH (p:Pathway {id:$pid})-[:HAS_GENE]->(g)
    RETURN p, g
    """
    records = run_query(query, {"pid": pathway_id})

    nodes = []
    edges = []

    for r in records:
        nodes.append({
            "id": r["p"]["id"],
            "label": "Pathway",
            "properties": r["p"]
        })
        nodes.append({
            "id": r["g"]["id"],
            "label": "Gene",
            "properties": r["g"]
        })

        edges.append({
            "source": r["p"]["id"],
            "target": r["g"]["id"],
            "type": "HAS_GENE"
        })

    return _unique_graph(nodes, edges)


# =====================================================
# QUERY 3: PLEIOTROPIC GENES
# =====================================================


def get_pleiotropic_genes(min_pathways=2):
    query = """
    MATCH (g:Gene)-[:HAS_GENE]-(p:Pathway)
    WITH g, count(p) AS pathway_count
    WHERE pathway_count >= $minp
    RETURN g, pathway_count
    ORDER BY pathway_count DESC
    """
    records = run_query(query, {"minp": min_pathways})

    return [
        {
            "gene": r["g"]["id"],
            "pathway_count": r["pathway_count"]
        }
        for r in records
    ]

# =====================================================
# INTERNAL: REMOVE DUPLICATES
# =====================================================


def _unique_graph(nodes, edges):
    node_map = {}

    for n in nodes:
        node_map[n["id"]] = n

    unique_edges = []
    seen = set()

    for e in edges:
        key = (e["source"], e["target"], e["type"])
        if key not in seen:
            seen.add(key)
            unique_edges.append(e)

    return {
        "nodes": list(node_map.values()),
        "edges": unique_edges
    }


# =====================================================
# CLEANUP
# =====================================================


def close():
    driver.close()
