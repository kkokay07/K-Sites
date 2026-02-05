import streamlit as st
import networkx as nx
from pyvis.network import Network
import tempfile
import os

import graph_query_api


# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(
    page_title="KEGG Graph Visualization",
    layout="wide"
)

st.title("KEGG Organism–Pathway–Gene Network")

st.markdown(
    """
This interactive graph shows relationships between:
- **Organisms**
- **Pathways**
- **Genes**

Colors indicate entity types.  
Genes involved in multiple pathways (pleiotropic genes) are highlighted.
"""
)

# =====================================================
# SIDEBAR CONTROLS
# =====================================================
st.sidebar.header("Controls")

organism = st.sidebar.selectbox(
    "Select organism",
    options=["mmu", "hsa"]
)

view_mode = st.sidebar.radio(
    "View mode",
    options=["Whole organism", "Single pathway"]
)

pathway_id = None
if view_mode == "Single pathway":
    pathway_id = st.sidebar.text_input(
        "Enter pathway ID (e.g., mmu00010)"
    ).strip()

min_pleiotropy = st.sidebar.slider(
    "Highlight genes with at least N pathways",
    min_value=2,
    max_value=10,
    value=3
)


# =====================================================
# LOAD GRAPH DATA
# =====================================================
if view_mode == "Whole organism":
    graph_data = graph_query_api.get_organism_graph(organism)
else:
    if not pathway_id:
        st.warning("Please enter a pathway ID.")
        st.stop()
    graph_data = graph_query_api.get_pathway_graph(pathway_id)

nodes = graph_data["nodes"]
edges = graph_data["edges"]

pleiotropic = {
    g["gene"]: g["pathway_count"]
    for g in graph_query_api.get_pleiotropic_genes(min_pleiotropy)
}


# =====================================================
# BUILD NETWORKX GRAPH
# =====================================================
G = nx.Graph()

for node in nodes:
    node_id = node["id"]
    label = node["label"]

    # Color by type
    if label == "Organism":
        color = "#1f77b4"   # blue
        size = 35
    elif label == "Pathway":
        color = "#ff7f0e"   # orange
        size = 25
    else:  # Gene
        if node_id in pleiotropic:
            color = "#d62728"  # red for pleiotropic genes
            size = 22
        else:
            color = "#2ca02c"  # green
            size = 15

    G.add_node(
        node_id,
        label=node_id,
        color=color,
        size=size
    )

for edge in edges:
    G.add_edge(edge["source"], edge["target"])


# =====================================================
# PYVIS VISUALIZATION
# =====================================================
net = Network(
    height="750px",
    width="100%",
    bgcolor="#ffffff",
    font_color="black"
)

net.from_nx(G)

net.repulsion(
    node_distance=180,
    central_gravity=0.2,
    spring_length=200,
    spring_strength=0.05,
    damping=0.09
)

# Save to temp file and display
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    net.save_graph(tmp_file.name)
    html_path = tmp_file.name

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

st.components.v1.html(html, height=800, scrolling=True)

os.unlink(html_path)


# =====================================================
# LEGEND
# =====================================================
st.markdown(
    """
### Legend
- **Blue**: Organism  
- **Orange**: Pathway  
- **Green**: Gene  
- **Red**: Pleiotropic gene (in multiple pathways)
"""
)

# =====================================================
# CLEANUP
# =====================================================
graph_query_api.close()
