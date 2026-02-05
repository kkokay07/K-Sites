# %% Test 1: Import module and inspect contents
import graph_query_api

print("Loaded from:", graph_query_api.__file__)
print("Available attributes:")
print(dir(graph_query_api))

# %% Test 2: Organism graph
data = graph_query_api.get_organism_graph("mmu")

print("Type:", type(data))
print("Keys:", data.keys())
print("Number of nodes:", len(data["nodes"]))
print("Number of edges:", len(data["edges"]))

# %% Test 3: Inspect first 5 nodes
for node in data["nodes"][:5]:
    print(node)
# %% Test 4: Pathway graph
pdata = graph_query_api.get_pathway_graph("mmu00010")

print("Keys:", pdata.keys())
print("Nodes:", len(pdata["nodes"]))
print("Edges:", len(pdata["edges"]))

# %% Test 5: Inspect pathway graph nodes
for node in pdata["nodes"]:
    print(node["label"], node["id"])

# %% Test 6: Pleiotropic genes
pleiotropy = graph_query_api.get_pleiotropic_genes(min_pathways=3)

print("Number of pleiotropic genes:", len(pleiotropy))
print("First 5 results:")
for g in pleiotropy[:5]:
    print(g)

# %% Test 7: Close Neo4j connection
graph_query_api.close()
print("Connection closed")

# %%
