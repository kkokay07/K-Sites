"""
Graph Query API for KEGG Neo4j Graph
"""

from neo4j import GraphDatabase

# =====================================================
# NEO4J CONNECTION (GLOBAL, STREAMLIT SAFE)
# =====================================================
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "kkokay07"

_driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD),
    max_connection_lifetime=3600,
    max_connection_pool_size=10
)

# =====================================================
# CORE QUERY RUNNER
# =====================================================


def run_query(query, parameters=None):
    with _driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]

# =====================================================
# GRAPH QUERIES
# =====================================================


def get_organism_graph(org_code):
    query = """
    MATCH (o:Organism {id:$org})-[:HAS_PATHWAY]->(p)-[:HAS_GENE]->(g)
    RETURN o, p, g
    """
    records = run_query(query, {"org": org_code})
    return _build_graph(records)


def get_pathway_graph(pathway_id):
    query = """
    MATCH (p:Pathway {id:$pid})-[:HAS_GENE]->(g)
    RETURN p, g
    """
    records = run_query(query, {"pid": pathway_id})
    return _build_graph(records)


def get_pathways_for_organism(org_code):
    query = """
    MATCH (:Organism {id:$org})-[:HAS_PATHWAY]->(p:Pathway)
    RETURN p.id AS id, p.name AS name
    ORDER BY p.id
    """
    return run_query(query, {"org": org_code})

# =====================================================
# ANALYTICS
# =====================================================


def get_gene_pathway_counts():
    query = """
    MATCH (g:Gene)-[:HAS_GENE]-(p:Pathway)
    RETURN g.id AS gene, count(p) AS pathway_count
    """
    return {r["gene"]: r["pathway_count"] for r in run_query(query)}


def get_pleiotropic_genes(min_pathways=2):
    query = """
    MATCH (g:Gene)-[:HAS_GENE]-(p:Pathway)
    WITH g, count(p) AS pathway_count
    WHERE pathway_count >= $minp
    RETURN g.id AS gene, pathway_count
    ORDER BY pathway_count DESC
    """
    return run_query(query, {"minp": min_pathways})


def get_pathway_overlap(pathway_id):
    query = """
    MATCH (p1:Pathway {id:$pid})<-[:HAS_GENE]-(g:Gene)-[:HAS_GENE]->(p2:Pathway)
    WHERE p1 <> p2
    RETURN p2.id AS pathway, count(g) AS shared_genes
    ORDER BY shared_genes DESC
    """
    return run_query(query, {"pid": pathway_id})

# =====================================================
# KNOCKOUT SIMULATION SUPPORT
# =====================================================


def get_gene_neighborhood(gene_id):
    query = """
    MATCH (g:Gene {id:$gid})-[:HAS_GENE]->(p:Pathway)
    OPTIONAL MATCH (p)<-[:HAS_GENE]-(g2:Gene)
    RETURN p.id AS pathway, collect(DISTINCT g2.id) AS affected_genes
    """
    return run_query(query, {"gid": gene_id})

# =====================================================
# INTERNAL GRAPH BUILDER
# =====================================================


def _build_graph(records):
    nodes = {}
    edges = set()

    for r in records:
        for obj in r.values():
            if isinstance(obj, dict) and "id" in obj:
                label = "Gene" if "gene" in obj.get("id", "").lower() else None

        if "o" in r:
            nodes[r["o"]["id"]] = {"id": r["o"]["id"],
                                   "label": "Organism", "properties": r["o"]}
        if "p" in r:
            nodes[r["p"]["id"]] = {"id": r["p"]["id"],
                                   "label": "Pathway", "properties": r["p"]}
        if "g" in r:
            nodes[r["g"]["id"]] = {"id": r["g"]["id"],
                                   "label": "Gene", "properties": r["g"]}

        if "o" in r and "p" in r:
            edges.add((r["o"]["id"], r["p"]["id"], "HAS_PATHWAY"))
        if "p" in r and "g" in r:
            edges.add((r["p"]["id"], r["g"]["id"], "HAS_GENE"))

    return {
        "nodes": list(nodes.values()),
        "edges": [{"source": s, "target": t, "type": e} for s, t, e in edges]
    }
