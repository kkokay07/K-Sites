# K-Sites Web Application

A comprehensive web interface for the K-Sites CRISPR guide RNA design platform.

**Tagline:** Suite for Knock-out/down Studies

## Features

### 🧬 Hierarchical Organism Selection
1. **Select Kingdom**: Choose from Animals, Plants, Microbes, Fungi, or Other Eukaryotes
2. **Filter Species**: Type to filter or scroll through available species
3. **Direct Selection**: Click to select desired organism

### 🧪 Hierarchical GO Term Selection
1. **Select Category**: Biological Process, Molecular Function, or Cellular Component
2. **Filter Terms**: Search by keyword within category
3. **Direct Entry**: Option to enter GO:XXXXXXX ID directly

### 📊 Advanced Analysis Features
- **Pathway-Aware Analysis**: Neo4j integration for KEGG pathway filtering
- **RAG Phenotype Prediction**: AI-powered literature-based phenotype prediction
- **Smart Gene Limiting**: Real-time gene count validation with suggestions
- **Email Notifications**: Get notified when analysis starts and completes

### 📈 Enhanced Progress Tracking
- **Visual Progress Bar**: Shows exact percentage completion
- **Step-by-Step Status**: See which analysis step is currently running
- **ETA Calculation**: Estimated time of completion based on parameters
- **Email Alerts**: Automatic notifications on job status changes

### 📚 Comprehensive Documentation
- **Help Page**: Detailed explanations of all analytical terms
- **Methodology Guide**: Step-by-step explanation of the pipeline
- **FAQ Section**: Common questions and answers
- **Score Explanations**: Pleiotropy, specificity, Doench scores, etc.

## Installation

### Prerequisites
- Python 3.8+
- K-Sites package installed (`pip install -e ..` from parent directory)
- Optional: Neo4j database for pathway analysis
- Optional: SMTP server for email notifications

### Setup

1. Install webapp dependencies:
```bash
cd /home/iiab/Documents/K-sites/webapp
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
# Required
export K_SITES_NCBI_EMAIL="your-email@example.com"

# Optional: Email notifications
export MAIL_USERNAME="your-email@gmail.com"
export MAIL_PASSWORD="your-app-password"
export MAIL_SERVER="smtp.gmail.com"
export MAIL_PORT=587

# Optional: Neo4j
export K_SITES_NEO4J_URI="bolt://localhost:7687"
export K_SITES_NEO4J_USER="neo4j"
export K_SITES_NEO4J_PASSWORD="password"
```

3. Start the server:
```bash
./start_server.sh
```

4. Open browser: http://localhost:5000

## Usage Workflow

### Starting an Analysis

1. **Enter Email** (optional): For notifications
2. **Select Organism**:
   - Click kingdom (e.g., "Animals")
   - Filter/scroll to find species (e.g., "Mus musculus")
   - Click to select
3. **Select GO Term**:
   - Click category (e.g., "Biological Process")
   - Filter to find term (e.g., "DNA repair")
   - Or enter GO:0006281 directly
4. **Choose Databases**: Select Neo4j for pathway analysis
5. **Set Parameters**:
   - Max genes: 10-50 (lower = faster)
   - Max pleiotropy: 1-20 (lower = more specific)
   - Enable RAG prediction (optional, adds ~1 min/gene)
6. **Review Gene Count**: See available genes and estimated time
7. **Start Analysis**: Submit and wait for completion
8. **View Results**: Interactive dashboard with all gRNAs

### Understanding Results

Visit `/help` for detailed explanations of:
- **Pleiotropy Score**: Gene specificity (0=highly specific)
- **Specificity Score**: Inverse of pleiotropy (10=highly specific)
- **Doench Score**: gRNA efficiency prediction (0.6+=good)
- **CFD Off-targets**: Predicted off-target sites
- **Safety Level**: Overall risk assessment

## API Endpoints

### Hierarchical Selection
- `GET /api/organisms/kingdoms` - List organism kingdoms
- `GET /api/organisms/by-kingdom?kingdom=X&q=Y` - Get species in kingdom
- `GET /api/go-terms/categories` - List GO categories
- `GET /api/go-terms/by-category?category=X&q=Y` - Get terms in category

### Analysis
- `POST /api/analyze/validate` - Validate parameters with gene count
- `POST /api/analyze/start` - Start new job (returns job_id)
- `GET /api/jobs/{id}/status` - Get job status with progress
- `GET /api/jobs/{id}/results` - Get completed results
- `GET /api/jobs/{id}/download/{format}` - Download HTML/JSON

## Email Notifications

Configure email to receive:
1. **Submission confirmation** with job ID
2. **Completion notification** with results summary
3. **Failure alert** with error details

### Gmail Setup
1. Enable 2-Factor Authentication
2. Generate App Password: https://support.google.com/accounts/answer/185833
3. Use App Password (not your regular password)

## Neo4j Pathway Analysis

Enable advanced pathway-aware off-target filtering:

```bash
# Start Neo4j
docker run -d --name neo4j-ksites -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest

# Ingest KEGG data
cd /home/iiab/Documents/K-sites
python -m k_sites.neo4j.ingest_kegg --taxid 9606
```

## Architecture

```
webapp/
├── app.py                 # Flask application
├── config.py             # Configuration classes
├── requirements.txt      # Dependencies
├── start_server.sh      # Startup script
├── utils/
│   ├── hierarchical_data.py  # Organism/GO hierarchies
│   └── help_content.py       # Documentation content
├── static/js/
│   ├── main.js          # Main page JS
│   └── results.js       # Results page JS
├── templates/
│   ├── base.html        # Base layout
│   ├── index.html       # Analysis form
│   ├── results.html     # Results display
│   ├── jobs.html        # Job history
│   └── help.html        # Documentation
└── results/             # Analysis outputs
```

## Database Schema

### AnalysisJob Table
Tracks all analysis jobs with:
- Job ID, status, timestamps
- Current step and progress percentage
- Estimated completion time
- User email for notifications
- All input parameters
- Results summary
- Error messages

## Troubleshooting

### Email not working
- Check MAIL_USERNAME and MAIL_PASSWORD are set
- For Gmail, use App Password, not account password
- Check firewall allows outbound SMTP

### Neo4j not available
- Check Neo4j is running: `docker ps | grep neo4j`
- Verify connection settings in environment variables
- Tool works without Neo4j (GO-only analysis)

### No genes found
- Try a broader GO term
- Verify organism has GO annotations
- Check evidence filter settings

### Analysis timeout
- Reduce max_genes parameter
- Disable phenotype prediction
- Check database connectivity

## License

Same as K-Sites project (MIT License)
