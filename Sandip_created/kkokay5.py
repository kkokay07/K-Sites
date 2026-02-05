# %% KEGG pathway analysis tool with RAG integration

import requests
import pandas as pd
from collections import defaultdict
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets

# RAG imports
from Bio import Entrez
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# =====================================================
# RAG CONFIGURATION
# =====================================================
Entrez.email = "kkokay07@gmail.com"
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
vector_index = faiss.IndexFlatL2(384)
rag_documents = []

GENE_RAG_LIMIT = 3

# =====================================================
# STEP 1: Load KEGG Organisms
# =====================================================
org_url = "https://rest.kegg.jp/list/organism"
org_response = requests.get(org_url).text.strip().split('\n')

org_dict = {}
for line in org_response:
    parts = line.split('\t')
    if len(parts) >= 3:
        org_dict[parts[1]] = parts[2]

org_options = [f"{code} - {name}" for code, name in sorted(org_dict.items())]

# =====================================================
# STEP 2: Widgets
# =====================================================
org_selector = widgets.Dropdown(
    options=["Select organism"] + org_options,
    description="Organism:",
    layout=widgets.Layout(width="600px"),
    style={"description_width": "initial"}
)

pathway_selector = widgets.Dropdown(
    options=["Select pathway"],
    description="Pathway:",
    layout=widgets.Layout(width="600px"),
    style={"description_width": "initial"}
)

max_paths_input = widgets.IntText(
    value=1,
    description="Max other pathways:",
    layout=widgets.Layout(width="300px")
)

submit_button = widgets.Button(
    description="Submit and Analyze",
    button_style="success"
)

output_area = widgets.Output()

# =====================================================
# STEP 3: Load pathways dynamically
# =====================================================
def load_pathways(change):
    selected = change["new"]

    if selected == "Select organism":
        pathway_selector.options = ["Select pathway"]
        return

    org_code = selected.split(" - ")[0].strip()
    url = f"https://rest.kegg.jp/list/pathway/{org_code}"
    response = requests.get(url).text.strip()

    if not response:
        pathway_selector.options = ["No pathways found"]
        return

    lines = response.split("\n")
    pathways = [
        f"{line.split('\t')[0].replace('path:', '')} - {line.split('\t')[1]}"
        for line in lines if '\t' in line
    ]

    pathway_selector.options = ["Select pathway"] + sorted(pathways)

org_selector.observe(load_pathways, names="value")

# =====================================================
# STEP 4: KEGG Analysis Logic (UNCHANGED)
# =====================================================
def analyze_kegg_data(selected_code, target_pathway, max_other_paths):
    link_url = f"https://rest.kegg.jp/link/pathway/{selected_code}"
    link_response = requests.get(link_url).text.strip().split('\n')

    records = []
    for line in link_response:
        if '\t' in line:
            gene, pathway = line.split('\t')
            records.append((
                gene.replace(f"{selected_code}:", ""),
                pathway.replace("path:", "")
            ))

    df = pd.DataFrame(records, columns=["Gene ID", "Pathway ID"])

    list_url = f"https://rest.kegg.jp/list/pathway/{selected_code}"
    list_data = requests.get(list_url).text.strip().split('\n')
    pathway_map = {
        line.split('\t')[0].replace("path:", ""): line.split('\t')[1]
        for line in list_data if '\t' in line
    }

    df["Pathway Name"] = df["Pathway ID"].map(pathway_map)

    genes_in_target = df[df["Pathway ID"] == target_pathway]["Gene ID"].unique()
    gene_to_pathways = df.groupby("Gene ID")["Pathway ID"].apply(set).to_dict()

    result_dict = defaultdict(list)

    for gene in genes_in_target:
        other_paths = gene_to_pathways.get(gene, set()) - {target_pathway}
        if len(other_paths) <= max_other_paths:
            result_dict[len(other_paths)].append({
                "Gene ID": gene,
                "Other Pathways": [
                    f"{pid} ({pathway_map.get(pid, 'Unknown')})"
                    for pid in sorted(other_paths)
                ]
            })

    html = f"<h2>Gene Associations for Pathway {target_pathway}</h2>"

    for n in range(max_other_paths + 1):
        html += f"<h3>Genes in target pathway + {n} other pathway(s)</h3>"
        genes = result_dict.get(n, [])

        if genes:
            html += "<table border='1' cellpadding='5'>"
            html += "<tr><th>Gene ID</th><th>Other Pathways</th></tr>"
            for g in genes:
                html += f"<tr><td>{g['Gene ID']}</td><td>{'<br>'.join(g['Other Pathways'])}</td></tr>"
            html += "</table>"
        else:
            html += "<p>Not found</p>"

    display(HTML(html))
    return genes_in_target.tolist()

# =====================================================
# STEP 5: RAG HELPER FUNCTIONS
# =====================================================
def fetch_pubmed(term, max_results=5):
    handle = Entrez.esearch(db="pubmed", term=term, retmax=max_results)
    record = Entrez.read(handle)
    pmids = record.get("IdList", [])

    docs = []
    for pmid in pmids:
        fetch = Entrez.efetch(
            db="pubmed",
            id=pmid,
            rettype="abstract",
            retmode="text"
        )
        docs.append(fetch.read())

    return docs


def build_rag_context(query, docs, title, limit=3000):
    if not docs:
        return f"<h3>{title}</h3><p>No literature found.</p>"

    embeddings = embedding_model.encode(docs)
    vector_index.reset()
    vector_index.add(np.array(embeddings))

    rag_documents.clear()
    rag_documents.extend(docs)

    query_emb = embedding_model.encode([query])
    _, idx = vector_index.search(query_emb, k=min(3, len(docs)))

    context = "\n\n".join(rag_documents[i] for i in idx[0])

    return (
        f"<h3>{title}</h3>"
        f"<pre style='white-space: pre-wrap;'>{context[:limit]}</pre>"
    )


def display_gene_rag_limit_notice(limit):
    html = (
        "<div style='margin-top:15px; padding:10px; border:1px solid #ccc;'>"
        "<b>Note on gene-level explanations</b><br>"
        f"Gene-level biological context and knockout phenotype explanations "
        f"are shown for the first <b>{limit}</b> genes only to maintain "
        "performance and responsiveness. This limitation does not affect "
        "the KEGG pathway analysis results."
        "</div>"
    )
    display(HTML(html))

# =====================================================
# STEP 6: Submit Callback (EXTENDED ONLY)
# =====================================================
def on_submit_clicked(b):
    with output_area:
        clear_output()

        if org_selector.value == "Select organism":
            print("Please select an organism.")
            return

        if pathway_selector.value == "Select pathway":
            print("Please select a pathway.")
            return

        org_code = org_selector.value.split(" - ")[0].strip()
        organism_name = org_selector.value.split(" - ", 1)[1]
        pathway_id, pathway_name = pathway_selector.value.split(" - ", 1)
        max_paths = max_paths_input.value

        print(f"Organism: {org_code}")
        print(f"Target Pathway: {pathway_id}")
        print(f"Max other pathways: {max_paths}\n")

        genes = analyze_kegg_data(org_code, pathway_id, max_paths)

        # Pathway-level RAG
        pathway_docs = fetch_pubmed(f"{pathway_name} pathway")
        display(HTML(build_rag_context(
            f"biological role of {pathway_name} pathway",
            pathway_docs,
            "Pathway biological context"
        )))

        # Gene-level RAG notice
        display_gene_rag_limit_notice(GENE_RAG_LIMIT)

        # Gene-level RAG and knockout reasoning
        for gene in genes[:GENE_RAG_LIMIT]:
            gene_docs = fetch_pubmed(f"{gene} {organism_name}")
            display(HTML(build_rag_context(
                f"biological function of gene {gene}",
                gene_docs,
                f"Gene-level biological context: {gene}",
                limit=2000
            )))

            knockout_docs = fetch_pubmed(f"{gene} knockout {organism_name}")
            display(HTML(build_rag_context(
                f"phenotype of {gene} knockout",
                knockout_docs,
                f"Knockout phenotype evidence: {gene}",
                limit=2500
            )))

submit_button.on_click(on_submit_clicked)

# =====================================================
# STEP 7: Display UI
# =====================================================
display(widgets.VBox([
    org_selector,
    pathway_selector,
    max_paths_input,
    submit_button,
    output_area
]))

# %%
