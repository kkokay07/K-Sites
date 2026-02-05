# %% KEGG → Neo4j ingestion script
"""
KEGG → Neo4j ingestion script

This script:
- Connects to a local Neo4j instance
- Ingests Organisms → Pathways → Genes from KEGG
- Creates a biological knowledge graph
- Is safe to run multiple times (uses MERGE)

Run this script from terminal:
    python ingest_kegg_to_neo4j.py
"""

import requests
from neo4j import GraphDatabase
import sys

# =====================================================
# NEO4J CONNECTION CONFIGURATION
# =====================================================
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "kkokay07"

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

# =====================================================
# UTILITY: RUN CYPHER QUERY
# =====================================================
def run_query(query, parameters=None):
    with driver.session() as session:
        session.run(query, parameters or {})

# =====================================================
# STEP 1: CREATE CONSTRAINTS (SAFE TO RUN MULTIPLE TIMES)
# =====================================================
def create_constraints():
    queries = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organism) REQUIRE o.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Pathway) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE"
    ]
    for q in queries:
        run_query(q)

# =====================================================
# STEP 2: LOAD ORGANISM LIST FROM KEGG
# =====================================================
def load_kegg_organisms():
    url = "https://rest.kegg.jp/list/organism"
    response = requests.get(url).text.strip().split("\n")

    organisms = {}
    for line in response:
        parts = line.split("\t")
        if len(parts) >= 3:
            organisms[parts[1]] = parts[2]

    return organisms

# =====================================================
# STEP 3: CREATE ORGANISM NODE
# =====================================================
def create_organism(org_code, org_name):
    query = """
    MERGE (o:Organism {id: $id})
    SET o.name = $name
    """
    run_query(query, {"id": org_code, "name": org_name})

# =====================================================
# STEP 4: INGEST PATHWAYS FOR AN ORGANISM
# =====================================================
def ingest_pathways(org_code):
    url = f"https://rest.kegg.jp/list/pathway/{org_code}"
    response = requests.get(url).text.strip()

    if not response:
        return

    lines = response.split("\n")

    for line in lines:
        pid, pname = line.split("\t")
        pid = pid.replace("path:", "")

        query = """
        MATCH (o:Organism {id: $org})
        MERGE (p:Pathway {id: $pid})
        SET p.name = $pname
        MERGE (o)-[:HAS_PATHWAY]->(p)
        """
        run_query(query, {
            "org": org_code,
            "pid": pid,
            "pname": pname
        })

# =====================================================
# STEP 5: INGEST GENES AND LINK TO PATHWAYS
# =====================================================
def ingest_genes(org_code):
    url = f"https://rest.kegg.jp/link/pathway/{org_code}"
    response = requests.get(url).text.strip()

    if not response:
        return

    lines = response.split("\n")

    for line in lines:
        gene, pathway = line.split("\t")
        gene_id = gene.replace(f"{org_code}:", "")
        pathway_id = pathway.replace("path:", "")

        query = """
        MATCH (p:Pathway {id: $pid})
        MERGE (g:Gene {id: $gid})
        MERGE (p)-[:HAS_GENE]->(g)
        """
        run_query(query, {
            "pid": pathway_id,
            "gid": gene_id
        })

# =====================================================
# STEP 6: INGEST A SINGLE ORGANISM (PIPELINE)
# =====================================================
def ingest_organism(org_code, org_name):
    print(f"Ingesting organism: {org_code} ({org_name})")

    create_organism(org_code, org_name)
    ingest_pathways(org_code)
    ingest_genes(org_code)

    print(f"Completed ingestion for {org_code}")

# =====================================================
# MAIN EXECUTION
# =====================================================
def main():
    create_constraints()

    organisms = load_kegg_organisms()

    # ---- CHANGE THIS LIST AS NEEDED ----
    organisms_to_ingest = [
        "mmu",  # mouse
        "hsa"   # human
    ]

    for org_code in organisms_to_ingest:
        if org_code not in organisms:
            print(f"Skipping unknown organism: {org_code}")
            continue

        ingest_organism(org_code, organisms[org_code])

    print("KEGG ingestion completed successfully.")
    driver.close()

# =====================================================
# ENTRY POINT
# =====================================================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user")
        driver.close()
        sys.exit(0)

# %%
