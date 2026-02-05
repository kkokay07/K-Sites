# Universal K-Sites Deployment Guide

## 1. Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] Neo4j (optional but recommended):
```bash
docker run -d --name neo4j-ksites \
-p 7687:7687 -p 7474:7474 \
-v ~/.openclaw/workspace/k-sites/neo4j_data:/data \
-e NEO4J_AUTH=neo4j/your_secure_password \
neo4j:5
```

- [ ] NCBI API key (optional but avoids throttling):
```bash
export NCBI_API_KEY=your_key_here
export NCBI_EMAIL=you@example.com
```

## 2. Installation

```bash
# From workspace root (~/.openclaw/workspace/k-sites/)
pip install -e . # Install package + dependencies
k-sites config init # Generates config/k-sites.yaml
# Edit config/k-sites.yaml to set NCBI email + Neo4j credentials
```

## 3. Data Ingestion (one-time setup)

```bash
# Ingest KEGG pathways for human
python -m k_sites.neo4j.ingest_kegg --taxid 9606 --organism "Homo sapiens"
# Optional: ingest mouse
python -m k_sites.neo4j.ingest_kegg --taxid 10090 --organism "Mus musculus"
```

## 4. First Run (GO-only mode — works even without Neo4j)

```bash
k-sites \
--go-term GO:0006281 \
--organism "Homo sapiens" \
--output ~/Desktop/dna_repair_guides.html \
--max-pleiotropy 3
```

## 5. Verify Output

- Open `~/Desktop/dna_repair_guides.html` in browser
- Confirm sections exist: ✅ Executive Summary (genes screened/passed)
- ✅ Gene Table with pleiotropy scores
- ✅ gRNA Table with Doench scores
- ✅ Biological Context (PubMed abstracts)
- ✅ Download CSV button

## 6. Pathway-Aware Mode (with Neo4j)

- Ensure Neo4j container is running (`docker ps`)
- Set credentials in `config/k-sites.yaml` or env vars:
```bash
export NEO4J_PASSWORD=your_secure_password
```

- Re-run command above — report should now show:
- ✅ "Pathway Context" panel per gene
- ✅ ⚠️ icons on gRNAs with pathway-conflicting off-targets

## 7. Troubleshooting (per openclaw_docs.txt §9.4)

| Symptom | Likely Cause | Fix |
|--------|--------------|-----|
| `HTTPError 429` from NCBI | Rate limiting | Set `NCBI_API_KEY`; add `time.sleep(0.3)` in resolver |
| Neo4j auth failed | Wrong password | Check `NEO4J_PASSWORD` env var matches Neo4j container |
| No genes returned | GO term too specific | Try broader term (e.g., `GO:0006259` DNA metabolic process) |
| ModuleNotFoundError | Missing dependency | `pip install -r requirements.txt` |

## 8. OpenClaw Agent Registration (optional)

```bash
openclaw agents register --path ~/.openclaw/workspace/k-sites/.openclaw/agent.yaml
openclaw agents list # Verify "k-sites" appears
```