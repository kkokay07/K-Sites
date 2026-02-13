"""
Help content and documentation for K-Sites analytical terms
"""

ANALYTICAL_TERMS = {
    "pleiotropy_score": {
        "title": "Pleiotropy Score",
        "icon": "fa-project-diagram",
        "short_description": "Measures how many different biological processes a gene is involved in",
        "detailed_explanation": """
            <p>The <strong>Pleiotropy Score</strong> quantifies the degree to which a gene influences multiple, 
            seemingly unrelated phenotypic traits or biological processes.</p>
            
            <h6>How it's calculated:</h6>
            <ul>
                <li>Counts the number of Biological Process GO terms associated with the gene</li>
                <li>Adds KEGG pathway degree (if Neo4j is enabled)</li>
                <li>Uses exponential decay scoring to penalize highly pleiotropic genes</li>
            </ul>
            
            <h6>Score Range:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr><td class="text-success"><strong>0-2</strong></td><td>Highly specific - excellent CRISPR target</td></tr>
                    <tr><td class="text-info"><strong>2-5</strong></td><td>Moderately specific - good target</td></tr>
                    <tr><td class="text-warning"><strong>5-10</strong></td><td>Broadly involved - use with caution</td></tr>
                    <tr><td class="text-danger"><strong>>10</strong></td><td>Highly pleiotropic - may cause unintended effects</td></tr>
                </table>
            </div>
            
            <h6>Why it matters:</h6>
            <p>Genes with low pleiotropy scores are preferred for CRISPR experiments because knocking them out 
            is less likely to cause widespread, unpredictable phenotypic changes. High pleiotropy may indicate 
            essential genes or hub genes in regulatory networks.</p>
        """,
        "reference": "Based on GO term enrichment and KEGG pathway analysis"
    },
    
    "specificity_score": {
        "title": "Specificity Score",
        "icon": "fa-bullseye",
        "short_description": "Inverse measure of pleiotropy - higher is more specific",
        "detailed_explanation": """
            <p>The <strong>Specificity Score</strong> is calculated as <code>10 - pleiotropy_score</code>, 
            providing an intuitive measure where higher values indicate more specific genes.</p>
            
            <h6>Interpretation:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr><td class="text-success"><strong>8-10</strong></td><td>Highly specific to your pathway of interest</td></tr>
                    <tr><td class="text-info"><strong>5-8</strong></td><td>Moderately specific</td></tr>
                    <tr><td class="text-warning"><strong>2-5</strong></td><td>Low specificity</td></tr>
                    <tr><td class="text-danger"><strong>0-2</strong></td><td>Very broad involvement</td></tr>
                </table>
            </div>
            
            <h6>Usage:</h6>
            <p>Use this score to quickly identify the most specific targets for your CRISPR screen. 
            Genes with specificity scores above 7 are generally considered safe candidates for knockout studies.</p>
        """,
        "reference": "Derived from pleiotropy score calculation"
    },
    
    "composite_score": {
        "title": "Composite Score",
        "icon": "fa-star",
        "short_description": "Weighted combination of specificity, evidence quality, and literature support",
        "detailed_explanation": """
            <p>The <strong>Composite Score</strong> integrates multiple factors to rank genes by their 
            suitability as CRISPR targets.</p>
            
            <h6>Formula:</h6>
            <div class="alert alert-light">
                <code>Composite = (Specificity × 0.4) + (Evidence Quality × 0.3) + (Literature Score × 0.2) + (Conservation × 0.1)</code>
            </div>
            
            <h6>Components:</h6>
            <ul>
                <li><strong>Specificity (40%):</strong> Based on pleiotropy score</li>
                <li><strong>Evidence Quality (30%):</strong> Experimental vs computational evidence</li>
                <li><strong>Literature Score (20%):</strong> PubMed citation count and relevance</li>
                <li><strong>Conservation (10%):</strong> Cross-species conservation of gene function</li>
            </ul>
            
            <h6>Range:</h6>
            <p>0-10 scale, where higher scores indicate better overall candidates for CRISPR targeting.</p>
        """,
        "reference": "Multi-factorial weighted scoring algorithm"
    },
    
    "evidence_quality": {
        "title": "Evidence Quality",
        "icon": "fa-check-double",
        "short_description": "Reliability of GO annotations based on evidence codes",
        "detailed_explanation": """
            <p>The <strong>Evidence Quality</strong> score reflects the reliability of Gene Ontology annotations 
            based on the types of evidence supporting them.</p>
            
            <h6>Evidence Code Hierarchy:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr class="table-success">
                        <td><strong>EXP</strong></td>
                        <td>Experimental</td>
                        <td>Direct experimental evidence (highest quality)</td>
                    </tr>
                    <tr class="table-success">
                        <td><strong>IDA</strong></td>
                        <td>Direct Assay</td>
                        <td>Direct experimental assay</td>
                    </tr>
                    <tr class="table-success">
                        <td><strong>IMP</strong></td>
                        <td>Mutant Phenotype</td>
                        <td>Evidence from mutant studies</td>
                    </tr>
                    <tr class="table-info">
                        <td><strong>ISO</strong></td>
                        <td>Sequence Orthology</td>
                        <td>Inferred from orthologs</td>
                    </tr>
                    <tr class="table-warning">
                        <td><strong>IEA</strong></td>
                        <td>Electronic Annotation</td>
                        <td>Computational prediction (lowest quality)</td>
                    </tr>
                </table>
            </div>
            
            <h6>Score Calculation:</h6>
            <p>Weighted average based on the proportion of experimental vs computational evidence codes 
            associated with the gene's GO annotations.</p>
        """,
        "reference": "Gene Ontology Evidence Codes (https://geneontology.org/docs/guide-go-evidence-codes/)"
    },
    
    "doench_score": {
        "title": "Doench Score (On-Target Efficiency)",
        "icon": "fa-crosshairs",
        "short_description": "Predicts how efficiently a gRNA will cleave its target site",
        "detailed_explanation": """
            <p>The <strong>Doench Score</strong> (also known as the on-target activity score) predicts the 
            cutting efficiency of a CRISPR guide RNA at its intended target site.</p>
            
            <h6>Score Range:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr><td class="text-success"><strong>0.6-1.0</strong></td><td>High activity - excellent guide</td></tr>
                    <tr><td class="text-info"><strong>0.4-0.6</strong></td><td>Moderate activity - acceptable</td></tr>
                    <tr><td class="text-warning"><strong>0.2-0.4</strong></td><td>Low activity - consider alternatives</td></tr>
                    <tr><td class="text-danger"><strong>0.0-0.2</strong></td><td>Poor activity - avoid</td></tr>
                </table>
            </div>
            
            <h6>Factors Considered:</h6>
            <ul>
                <li>GC content (optimal: 40-60%)</li>
                <li>Position-specific nucleotide preferences</li>
                <li>Thermodynamic features of the guide</li>
                <li>Secondary structure predictions</li>
                <li>Position within the gene (early exons preferred)</li>
            </ul>
            
            <h6>Reference:</h6>
            <p>Doench et al., "Optimized sgRNA design to maximize activity and minimize off-target effects of CRISPR-Cas9", 
            Nature Biotechnology (2016)</p>
        """,
        "reference": "Doench et al., Nat Biotechnol (2016)"
    },
    
    "cfd_off_targets": {
        "title": "CFD Off-Target Score",
        "icon": "fa-radiation",
        "short_description": "Predicted number of off-target sites in the genome",
        "detailed_explanation": """
            <p>The <strong>Cumulative Fraction Detected (CFD)</strong> score predicts the likelihood of 
            off-target cleavage at sites throughout the genome that are similar to the intended target.</p>
            
            <h6>How it's calculated:</h6>
            <ul>
                <li>Scans the genome for sequences similar to the gRNA</li>
                <li>Allows up to 4 mismatches in various positions</li>
                <li>Scores each potential off-target based on mismatch position and type</li>
                <li>Summarizes high-confidence off-target predictions</li>
            </ul>
            
            <h6>Interpretation:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr><td class="text-success"><strong>0-1</strong></td><td>Excellent specificity</td></tr>
                    <tr><td class="text-info"><strong>2-4</strong></td><td>Good specificity</td></tr>
                    <tr><td class="text-warning"><strong>5-10</strong></td><td>Moderate off-target risk</td></tr>
                    <tr><td class="text-danger"><strong>>10</strong></td><td>High off-target risk - validate carefully</td></n                    </tr>
                </table>
            </div>
            
            <h6>Mitigation:</h6>
            <p>High off-target counts can be mitigated by using high-fidelity Cas9 variants or performing 
            off-target validation experiments (GUIDE-seq, CIRCLE-seq).</p>
        """,
        "reference": "Doench et al., Nature Biotechnology (2016)"
    },
    
    "safety_level": {
        "title": "Safety Level",
        "icon": "fa-shield-alt",
        "short_description": "Overall safety recommendation based on multiple risk factors",
        "detailed_explanation": """
            <p>The <strong>Safety Level</strong> provides an overall assessment of the risk associated 
            with knocking out a particular gene.</p>
            
            <h6>Safety Levels:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr class="table-success">
                        <td><strong>LOW</strong></td>
                        <td>Safe target - proceed with standard protocols</td>
                    </tr>
                    <tr class="table-info">
                        <td><strong>MEDIUM</strong></td>
                        <td>Generally safe - some validation recommended</td>
                    </tr>
                    <tr class="table-warning">
                        <td><strong>HIGH</strong></td>
                        <td>Use with caution - comprehensive validation required</td>
                    </tr>
                    <tr class="table-danger">
                        <td><strong>CRITICAL</strong></td>
                        <td>High risk - may be essential or highly pleiotropic</td>
                    </tr>
                </table>
            </div>
            
            <h6>Risk Factors Considered:</h6>
            <ul>
                <li>Pleiotropy score (high = higher risk)</li>
                <li>Predicted phenotype severity (lethal = critical)</li>
                <li>Off-target potential</li>
                <li>Literature evidence of essentiality</li>
                <li>Cross-species conservation</li>
            </ul>
        """,
        "reference": "K-Sites integrated safety assessment algorithm"
    },
    
    "pathway_conflict": {
        "title": "Pathway Conflict",
        "icon": "fa-exclamation-triangle",
        "short_description": "Indicates if off-targets share pathways with the target gene",
        "detailed_explanation": """
            <p>A <strong>Pathway Conflict</strong> occurs when a gRNA's predicted off-targets are located 
            in genes that participate in the same biological pathways as the intended target gene.</p>
            
            <h6>Why it matters:</h6>
            <p>Off-target effects in pathway-related genes can confound experimental results. If both 
            the target and off-target affect the same pathway, it becomes difficult to attribute 
            phenotypic changes to the intended target.</p>
            
            <h6>Detection:</h6>
            <p>Requires Neo4j database with KEGG pathway information. The system checks if off-target 
            genes share KEGG pathways with the target gene.</p>
            
            <h6>Recommendations:</h6>
            <ul>
                <li><strong>No conflict:</strong> Preferred guides</li>
                <li><strong>Conflict detected:</strong> Consider alternative guides or include pathway 
                analysis in experimental design</li>
            </ul>
        """,
        "reference": "KEGG pathway analysis via Neo4j graph database"
    },
    
    "phenotype_prediction": {
        "title": "RAG Phenotype Prediction",
        "icon": "fa-brain",
        "short_description": "AI-powered prediction of knockout phenotypes from literature",
        "detailed_explanation": """
            <p><strong>Retrieval-Augmented Generation (RAG)</strong> phenotype prediction uses AI to 
            analyze scientific literature and predict the likely phenotypic consequences of gene knockout.</p>
            
            <h6>How it works:</h6>
            <ol>
                <li>Queries PubMed for papers about the target gene</li>
                <li>Retrieves relevant abstracts and metadata</li>
                <li>Uses language models to extract phenotype information</li>
                <li>Classifies severity: LETHAL, SEVERE, MODERATE, MILD, or UNKNOWN</li>
            </ol>
            
            <h6>Severity Categories:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr class="table-danger"><td><strong>LETHAL</strong></td><td>Knockout causes organism death</td></tr>
                    <tr class="table-warning"><td><strong>SEVERE</strong></td><td>Major developmental or physiological defects</td></tr>
                    <tr class="table-info"><td><strong>MODERATE</strong></td><td>Detectable but manageable phenotypes</td></tr>
                    <tr class="table-success"><td><strong>MILD</strong></td><td>Subtle or conditional phenotypes</td></tr>
                    <tr class="table-secondary"><td><strong>UNKNOWN</strong></td><td>Insufficient data for prediction</td></tr>
                </table>
            </div>
            
            <h6>Limitations:</h6>
            <p>Prediction quality depends on literature availability. Well-studied genes have more 
            accurate predictions than poorly characterized genes.</p>
        """,
        "reference": "RAG-based NLP pipeline using PubMed and SentenceTransformers"
    },
    
    "gc_content": {
        "title": "GC Content",
        "icon": "fa-percentage",
        "short_description": "Percentage of G and C nucleotides in the gRNA",
        "detailed_explanation": """
            <p><strong>GC Content</strong> is the percentage of guanine (G) and cytosine (C) nucleotides 
            in the 20-nucleotide gRNA sequence.</p>
            
            <h6>Optimal Range:</h6>
            <p><strong>40-60%</strong> is considered optimal for CRISPR activity.</p>
            
            <h6>Effects:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr><td class="text-danger"><strong>&lt;30%</strong></td><td>Low activity - unstable binding</td></tr>
                    <tr><td class="text-success"><strong>40-60%</strong></td><td>Optimal - stable binding, high activity</td></tr>
                    <tr><td class="text-warning"><strong>&gt;70%</strong></td><td>May increase off-targets</td></tr>
                </table>
            </div>
            
            <h6>Rationale:</h6>
            <p>GC content affects binding stability and specificity. Too low = weak binding; 
            too high = potential off-target binding to GC-rich regions.</p>
        """,
        "reference": "General CRISPR design guidelines"
    },
    
    "conservation_score": {
        "title": "Cross-Species Conservation",
        "icon": "fa-globe",
        "short_description": "Degree to which gene function is conserved across species",
        "detailed_explanation": """
            <p>The <strong>Conservation Score</strong> measures how well a gene's function is preserved 
            across different species, indicating its functional importance.</p>
            
            <h6>How it's calculated:</h6>
            <ul>
                <li>Checks for orthologs in model organisms</li>
                <li>Compares GO term conservation</li>
                <li>Evaluates sequence similarity</li>
            </ul>
            
            <h6>Interpretation:</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr><td class="text-info"><strong>0.0-0.3</strong></td><td>Species-specific function</td></tr>
                    <tr><td class="text-success"><strong>0.3-0.7</strong></td><td>Moderately conserved</td></tr>
                    <tr><td class="text-warning"><strong>0.7-1.0</strong></td><td>Highly conserved - likely essential</td></tr>
                </table>
            </div>
            
            <h6>Usage:</h6>
            <p>Highly conserved genes may be essential and more challenging to knockout. 
            Species-specific genes might be better targets for selective studies.</p>
        """,
        "reference": "Cross-species ortholog analysis via UniProt and NCBI"
    }
}


METHODOLOGY_SECTIONS = [
    {
        "title": "Overview",
        "icon": "fa-microscope",
        "content": """
            <p>K-Sites is a comprehensive CRISPR guide RNA design platform that integrates multiple 
            biological databases and AI-powered analysis to identify optimal gene targets and design 
            high-quality gRNAs.</p>
            
            <p>The platform follows a multi-step pipeline from gene selection to gRNA design with 
            pathway-aware off-target filtering.</p>
        """
    },
    {
        "title": "Step 1: Gene Discovery",
        "icon": "fa-search",
        "content": """
            <p>The pipeline begins by querying the <strong>QuickGO</strong> database to retrieve all 
            genes annotated with the selected Gene Ontology (GO) term in the specified organism.</p>
            
            <p>Users can filter by evidence type:</p>
            <ul>
                <li><strong>Experimental:</strong> Only experimentally validated annotations</li>
                <li><strong>Computational:</strong> Includes computational predictions</li>
                <li><strong>All:</strong> All available evidence types</li>
            </ul>
            
            <p>This step typically returns 10-500 genes depending on the GO term specificity.</p>
        """
    },
    {
        "title": "Step 2: Pleiotropy Scoring",
        "icon": "fa-project-diagram",
        "content": """
            <p>Each discovered gene is scored for <strong>pleiotropy</strong> - the degree to which it 
            participates in multiple biological processes.</p>
            
            <p>The scoring algorithm:</p>
            <ol>
                <li>Queries all GO annotations for the gene</li>
                <li>Counts unique Biological Process terms</li>
                <li>Retrieves KEGG pathway memberships (if Neo4j available)</li>
                <li>Calculates exponential decay score</li>
            </ol>
            
            <p>Genes with low pleiotropy scores are prioritized as they are more likely to produce 
            specific, interpretable phenotypes upon knockout.</p>
        """
    },
    {
        "title": "Step 3: Evidence Quality Assessment",
        "icon": "fa-check-double",
        "content": """
            <p>GO annotations are evaluated based on their <strong>evidence codes</strong>:</p>
            
            <ul>
                <li><strong>Experimental (EXP, IDA, IMP, IGI, IEP):</strong> Direct experimental evidence</li>
                <li><strong>Phylogenetic (IBA, IBD, IKR, IRD):</strong> Evidence from related species</li>
                <li><strong>Computational (ISS, ISO, ISA, ISM, IGC, IBA, IBD):</strong> Predicted annotations</li>
                <li><strong>Author Statements (TAS, NAS):</strong> Non-traceable statements</li>
                <li><strong>Electronic (IEA):</strong> Automated predictions (lowest confidence)</li>
            </ul>
            
            <p>Genes with higher proportions of experimental evidence receive better scores.</p>
        """
    },
    {
        "title": "Step 4: Literature Mining",
        "icon": "fa-book",
        "content": """
            <p>The system queries <strong>PubMed</strong> to gather supporting literature:</p>
            
            <ul>
                <li>Search for gene knockout/deletion studies</li>
                <li>Extract reported phenotypes</li>
                <li>Assess viability data</li>
                <li>Count relevant publications</li>
            </ul>
            
            <p>When enabled, the <strong>RAG (Retrieval-Augmented Generation)</strong> system uses 
            natural language processing to predict knockout phenotypes based on the literature corpus.</p>
        """
    },
    {
        "title": "Step 5: gRNA Design",
        "icon": "fa-cut",
        "content": """
            <p>For each selected gene, the platform designs gRNAs using optimized algorithms:</p>
            
            <ol>
                <li><strong>Target Identification:</strong> Find all NGG PAM sites in exonic regions</li>
                <li><strong>Efficiency Scoring:</strong> Calculate Doench scores for each potential guide</li>
                <li><strong>Specificity Analysis:</strong> Predict off-target sites using CFD scoring</li>
                <li><strong>Position Optimization:</strong> Prioritize early exons and coding regions</li>
                <li><strong>Filtering:</strong> Remove guides with poly-T tracks or extreme GC content</li>
            </ol>
            
            <p>Typically 20-50 high-quality gRNAs are designed per gene.</p>
        """
    },
    {
        "title": "Step 6: Pathway-Aware Off-Target Analysis",
        "icon": "fa-network-wired",
        "content": """
            <p>When <strong>Neo4j</strong> is enabled, the system performs advanced pathway analysis:</p>
            
            <ul>
                <li>Map target gene to KEGG pathways</li>
                <li>Identify pathway neighbors</li>
                <li>Check if off-target genes share pathways with target</li>
                <li>Flag potential pathway conflicts</li>
            </ul>
            
            <p>This prevents selection of gRNAs that could confound results by affecting the same 
            biological pathway through off-target effects.</p>
        """
    },
    {
        "title": "Step 7: Safety Assessment",
        "icon": "fa-shield-alt",
        "content": """
            <p>The final step integrates all analyses to provide safety recommendations:</p>
            
            <ul>
                <li>Combine pleiotropy, phenotype, and off-target data</li>
                <li>Assess risk of essential gene knockout</li>
                <li>Generate specific experimental recommendations</li>
                <li>Flag guides requiring additional validation</li>
            </ul>
            
            <p>Safety levels range from LOW (safe to proceed) to CRITICAL (may be lethal/essential).</p>
        """
    },
    {
        "title": "Output Generation",
        "icon": "fa-file-export",
        "content": """
            <p>Results are provided in multiple formats:</p>
            
            <ul>
                <li><strong>HTML Report:</strong> Interactive, publication-ready summary</li>
                <li><strong>CSV Tables:</strong> Gene and gRNA data for spreadsheets</li>
                <li><strong>JSON:</strong> Complete data for programmatic access</li>
                <li><strong>FASTA:</strong> gRNA sequences for ordering</li>
                <li><strong>GenBank:</strong> Annotated sequences</li>
            </ul>
            
            <p>All results include detailed metadata, quality scores, and safety recommendations 
            to support experimental design decisions.</p>
        """
    }
]


FAQ_ITEMS = [
    {
        "question": "What is the difference between pleiotropy score and specificity score?",
        "answer": "Pleiotropy score measures how many processes a gene is involved in (0=specific, high=broad). Specificity score is simply 10 minus the pleiotropy score, so higher values indicate more specific genes. Both convey the same information but in opposite directions."
    },
    {
        "question": "How many gRNAs should I design per gene?",
        "answer": "We recommend testing 3-5 gRNAs per gene to account for variable activity. K-Sites designs 20 high-quality gRNAs per gene by default, ranked by Doench score, giving you plenty of options to choose from."
    },
    {
        "question": "What is a 'good' Doench score?",
        "answer": "Doench scores above 0.6 indicate high activity guides. Scores between 0.4-0.6 are acceptable for most applications. Avoid guides with scores below 0.2 unless no better options exist."
    },
    {
        "question": "Should I enable Neo4j pathway analysis?",
        "answer": "If you have Neo4j configured with KEGG data, enabling pathway analysis provides valuable insights about off-targets in related pathways. However, the tool works well without it using GO-based analysis only."
    },
    {
        "question": "How accurate is the phenotype prediction?",
        "answer": "Phenotype prediction accuracy depends on literature availability for the gene. Well-studied genes (like TP53) have highly accurate predictions, while poorly characterized genes may return 'UNKNOWN'. Always validate predictions experimentally."
    },
    {
        "question": "What if my gene has a high pleiotropy score?",
        "answer": "High pleiotropy doesn't necessarily mean you shouldn't target the gene, but be prepared for complex phenotypes. Consider: 1) Using heterozygous knockouts, 2) Including pathway analysis in your interpretation, 3) Validating with multiple gRNAs."
    },
    {
        "question": "Can I use K-Sites for CRISPRi/a (interference/activation)?",
        "answer": "Yes! While K-Sites is optimized for knockout studies, the gRNA designs are suitable for CRISPRi/a. For CRISPRi, prefer promoters/TSS-proximal guides. For CRISPRa, prefer distal enhancer regions."
    },
    {
        "question": "How long does an analysis take?",
        "answer": "Typical runtime is 2-5 minutes for 5-10 genes. Factors affecting speed: number of genes, phenotype prediction (adds ~1 min/gene), Neo4j availability (can speed up pathway analysis), and database response times."
    }
]
