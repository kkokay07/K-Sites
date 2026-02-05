import streamlit as st
import networkx as nx
from pyvis.network import Network
import tempfile
import pandas as pd

import graph_query_api

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(layout="wide")
st.title("KEGG Systems Biology Explorer")

# =====================================================
# SIDEBAR
# =====================================================
organism = st.sidebar.selectbox("Organism", ["mmu", "hsa"])

pathways = graph_query_api.get_pathways_for_organism(organism)
pathway_map = {"All pathways": None}
for p in pathways:
    pathway_map[f"{p['id']} - {p['name']}"] = p["id"]

selected_pathway = st.sidebar.selectbox("Pathway", list(pathway_map.keys()))

min_pleiotropy = st.sidebar.slider("Pleiotropy threshold", 2, 10, 3)

# =====================================================
# LOAD GRAPH
# =====================================================
if pathway_map[selected_pathway] is None:
    graph = graph_query_api.get_organism_graph(organism)
else:
    graph = graph_query_api.get_pathway_graph(pathway_map[selected_pathway])

nodes, edges = graph["nodes"], graph["edges"]

gene_counts = graph_query_api.get_gene_pathway_counts()
pleiotropic = {g["gene"]
               for g in graph_query_api.get_pleiotropic_genes(min_pleiotropy)}

# =====================================================
# BUILD NETWORK
# =====================================================
G = nx.Graph()
for n in nodes:
    nid, label = n["id"], n["label"]

    if label == "Organism":
        color, size = "#1f77b4", 35
    elif label == "Pathway":
        color, size = "#ff7f0e", 25
    else:
        color = "#d62728" if nid in pleiotropic else "#2ca02c"
        size = 22 if nid in pleiotropic else 15

    G.add_node(
        nid,
        label=nid,
        color=color,
        size=size,
        title=f"{label}: {nid}"
    )

for e in edges:
    G.add_edge(e["source"], e["target"])

# =====================================================
# VISUALIZE
# =====================================================
net = Network(height="700px", width="100%")
net.from_nx(G)
net.repulsion(node_distance=180)

tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
net.save_graph(tmp.name)
st.components.v1.html(open(tmp.name).read(), height=750)

# =====================================================
# ANALYTICS PANEL
# =====================================================
st.subheader("Graph analytics")

degree_df = pd.DataFrame(
    [{"node": n, "degree": d} for n, d in G.degree()],
).sort_values("degree", ascending=False)

st.write("Top hubs")
st.dataframe(degree_df.head(10))

# =====================================================
# GENE CLICK → ANALYSIS
# =====================================================
gene_nodes = [n["id"] for n in nodes if n["label"] == "Gene"]

st.subheader("Gene-level analysis")

selected_gene = st.selectbox("Select a gene", sorted(gene_nodes))

if selected_gene:
    st.markdown("### Gene overview")
    st.write(f"Gene: {selected_gene}")
    st.write(f"Number of pathways: {gene_counts.get(selected_gene, 1)}")

    # Knockout simulation
    st.markdown("### Knockout impact simulation")
    neighborhood = graph_query_api.get_gene_neighborhood(selected_gene)

    if neighborhood:
        st.write("Affected pathways and genes:")
        st.dataframe(pd.DataFrame(neighborhood))
    else:
        st.write("No downstream effects detected")

    # RAG placeholder
    st.markdown("### Biological interpretation (RAG-ready)")
    st.info(
        "This panel will display literature-based explanations "
        "and phenotype predictions for the selected gene."
    )
