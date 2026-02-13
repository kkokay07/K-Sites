/**
 * K-Sites Web Application - Results Page JavaScript
 */

// Global state
let currentJob = null;
let resultsData = null;
let statusCheckInterval = null;

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    const jobId = document.getElementById('jobId')?.dataset.jobId;
    
    if (jobId) {
        loadJobStatus(jobId);
        
        // If job is still running, start polling
        if (document.getElementById('statusBadge')?.textContent.trim().toLowerCase() !== 'completed') {
            startStatusPolling(jobId);
        } else {
            loadResults(jobId);
        }
    }
    
    // Setup search
    document.getElementById('guideSearch')?.addEventListener('input', debounce(searchGuides, 300));
});

// ============================================================================
// Status Polling
// ============================================================================

function startStatusPolling(jobId) {
    statusCheckInterval = setInterval(() => {
        checkJobStatus(jobId);
    }, 3000); // Check every 3 seconds
}

function stopStatusPolling() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

async function checkJobStatus(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/status`);
        const data = await response.json();
        
        updateStatusDisplay(data);
        updateProgressDisplay(data);
        
        if (data.status === 'completed') {
            stopStatusPolling();
            showResults(data);
            loadResults(jobId);
        } else if (data.status === 'failed') {
            stopStatusPolling();
            showError(data.error_message);
        }
        
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

function updateProgressDisplay(job) {
    // Update progress bar
    const progressBar = document.getElementById('progressBar');
    if (progressBar && job.progress_percent !== undefined) {
        progressBar.style.width = `${job.progress_percent}%`;
        progressBar.setAttribute('aria-valuenow', job.progress_percent);
        progressBar.textContent = `${job.progress_percent}%`;
    }
    
    // Update current step
    const currentStep = document.getElementById('currentStep');
    if (currentStep && job.current_step) {
        currentStep.textContent = job.current_step;
    }
    
    // Update ETA
    const etaDisplay = document.getElementById('etaDisplay');
    const etaTime = document.getElementById('etaTime');
    if (etaDisplay && etaTime && job.estimated_completion) {
        const eta = new Date(job.estimated_completion);
        const now = new Date();
        
        if (eta > now) {
            const diffMs = eta - now;
            const diffMins = Math.round(diffMs / 60000);
            
            if (diffMins < 1) {
                etaTime.textContent = 'Less than a minute';
            } else if (diffMins === 1) {
                etaTime.textContent = 'About 1 minute';
            } else if (diffMins < 60) {
                etaTime.textContent = `About ${diffMins} minutes`;
            } else {
                const hours = Math.floor(diffMins / 60);
                const mins = diffMins % 60;
                etaTime.textContent = `${hours}h ${mins}m`;
            }
            etaDisplay.style.display = 'block';
        } else {
            etaTime.textContent = 'Any moment now...';
            etaDisplay.style.display = 'block';
        }
    }
    
    // Update step indicators
    const steps = [
        { pct: 5, selector: '#progressSteps li:nth-child(1)' },
        { pct: 15, selector: '#progressSteps li:nth-child(2)' },
        { pct: 30, selector: '#progressSteps li:nth-child(3)' },
        { pct: 60, selector: '#progressSteps li:nth-child(4)' },
        { pct: 85, selector: '#progressSteps li:nth-child(5)' },
        { pct: 100, selector: '#progressSteps li:nth-child(6)' }
    ];
    
    steps.forEach(step => {
        const el = document.querySelector(step.selector);
        if (el) {
            if (job.progress_percent >= step.pct) {
                el.classList.add('list-group-item-success');
                const icon = el.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-check-circle text-success me-2';
                }
            }
        }
    });
}

async function loadJobStatus(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/status`);
        const data = await response.json();
        currentJob = data;
        
    } catch (error) {
        console.error('Error loading job status:', error);
    }
}

function updateStatusDisplay(job) {
    const badge = document.getElementById('statusBadge');
    if (badge) {
        badge.className = `status-badge status-${job.status}`;
        badge.textContent = job.status.toUpperCase();
    }
}

function showResults(job) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('errorState').style.display = 'none';
    document.getElementById('resultsContent').style.display = 'block';
    
    // Update summary numbers
    if (job.total_genes_found !== undefined) {
        document.getElementById('avgGuidesPerGene').textContent = 
            job.genes_processed > 0 ? (job.total_grnas / job.genes_processed).toFixed(1) : '-';
    }
    
    // Setup download links
    document.getElementById('downloadHtml').href = `/api/jobs/${job.id}/download/html`;
    document.getElementById('downloadHtml').style.display = 'inline-block';
    document.getElementById('downloadJson').href = `/api/jobs/${job.id}/download/json`;
    document.getElementById('downloadJson').style.display = 'inline-block';
}

function showError(message) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('resultsContent').style.display = 'none';
    document.getElementById('errorState').style.display = 'block';
    document.getElementById('errorMessage').textContent = message || 'Unknown error occurred';
}

function addLogEntry(message) {
    const log = document.getElementById('progressLog');
    if (log) {
        const entry = document.createElement('div');
        entry.className = 'mb-1';
        entry.innerHTML = `<span class="text-muted">[${new Date().toLocaleTimeString()}]</span> ${message}`;
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
    }
}

// ============================================================================
// Load and Display Results
// ============================================================================

async function loadResults(jobId) {
    try {
        const response = await fetch(`/api/jobs/${jobId}/results`);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        resultsData = data.results;
        
        renderGenes(resultsData.genes);
        renderAllGuides(resultsData.genes);
        renderSummary(resultsData);
        
    } catch (error) {
        console.error('Error loading results:', error);
    }
}

function renderGenes(genes) {
    const container = document.getElementById('genesContainer');
    
    if (!genes || genes.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>No genes passed the filters.
            </div>
        `;
        return;
    }
    
    container.innerHTML = genes.map((gene, index) => `
        <div class="grna-card">
            <div class="d-flex justify-content-between align-items-start mb-3">
                <div>
                    <h5 class="mb-1">
                        <span class="badge bg-secondary me-2">#${index + 1}</span>
                        ${gene.symbol}
                    </h5>
                    <p class="text-muted mb-0 small">${gene.description || 'No description available'}</p>
                </div>
                <div class="text-end">
                    <div class="mb-1">
                        <span class="score-badge ${getPleiotropyClass(gene.pleiotropy_score)}">
                            Pleiotropy: ${gene.pleiotropy_score?.toFixed(2) || 'N/A'}
                        </span>
                    </div>
                    <div>
                        <span class="score-badge score-high">
                            ${gene.guides?.length || 0} gRNAs
                        </span>
                    </div>
                </div>
            </div>
            
            <!-- Gene Details -->
            <div class="row g-2 mb-3 small text-muted">
                <div class="col-md-3">
                    <i class="fas fa-star me-1"></i>Specificity: ${gene.specificity_score?.toFixed(1) || 'N/A'}
                </div>
                <div class="col-md-3">
                    <i class="fas fa-chart-line me-1"></i>Composite: ${gene.composite_score?.toFixed(1) || 'N/A'}
                </div>
                <div class="col-md-3">
                    <i class="fas fa-check-circle me-1"></i>Evidence: ${gene.evidence_quality?.toFixed(2) || 'N/A'}
                </div>
                <div class="col-md-3">
                    <i class="fas fa-book me-1"></i>Literature: ${gene.literature_support?.toFixed(2) || 'N/A'}
                </div>
            </div>
            
            <!-- Top gRNAs -->
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Sequence</th>
                            <th>Position</th>
                            <th>Doench Score</th>
                            <th>Off-targets</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(gene.guides || []).slice(0, 5).map(guide => `
                            <tr>
                                <td>
                                    <code class="sequence-box">${guide.seq}</code>
                                    <small class="text-muted">PAM: ${guide.pam_sequence}</small>
                                </td>
                                <td>${guide.position}</td>
                                <td>
                                    <span class="score-badge ${getScoreClass(guide.doench_score)}">
                                        ${guide.doench_score?.toFixed(2) || 'N/A'}
                                    </span>
                                </td>
                                <td>${guide.cfd_off_targets || 0}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" 
                                            onclick='showGuideDetails(${JSON.stringify(guide).replace(/'/g, "&#39;")})'>
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            
            ${(gene.guides || []).length > 5 ? `
                <div class="text-center">
                    <button class="btn btn-sm btn-link" onclick="toggleAllGuides('${gene.symbol}')">
                        Show all ${gene.guides.length} gRNAs
                    </button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function renderAllGuides(genes) {
    const container = document.getElementById('guidesContainer');
    
    if (!genes || genes.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>No gRNAs designed.
            </div>
        `;
        return;
    }
    
    // Flatten all guides with gene info
    const allGuides = [];
    genes.forEach(gene => {
        (gene.guides || []).forEach(guide => {
            allGuides.push({
                ...guide,
                gene_symbol: gene.symbol,
                gene_pleiotropy: gene.pleiotropy_score
            });
        });
    });
    
    // Sort by Doench score
    allGuides.sort((a, b) => (b.doench_score || 0) - (a.doench_score || 0));
    
    container.innerHTML = `
        <div class="table-responsive">
            <table class="table table-hover" id="allGuidesTable">
                <thead class="table-light">
                    <tr>
                        <th>Rank</th>
                        <th>Gene</th>
                        <th>Sequence</th>
                        <th>Doench Score</th>
                        <th>Specificity</th>
                        <th>Off-targets</th>
                        <th>GC%</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${allGuides.map((guide, index) => `
                        <tr data-search="${guide.seq.toLowerCase()} ${guide.gene_symbol.toLowerCase()}">
                            <td><span class="badge bg-secondary">${index + 1}</span></td>
                            <td><strong>${guide.gene_symbol}</strong></td>
                            <td>
                                <code class="sequence-box">${guide.seq}</code>
                            </td>
                            <td>
                                <span class="score-badge ${getScoreClass(guide.doench_score)}">
                                    ${guide.doench_score?.toFixed(2) || 'N/A'}
                                </span>
                            </td>
                            <td>${guide.specificity_score?.toFixed(2) || 'N/A'}</td>
                            <td>${guide.cfd_off_targets || 0}</td>
                            <td>${((guide.gc_content || 0) * 100).toFixed(0)}%</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" 
                                        onclick='showGuideDetails(${JSON.stringify(guide).replace(/'/g, "&#39;")})'>
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function renderSummary(data) {
    const container = document.getElementById('summaryContainer');
    const genes = data.genes || [];
    
    // Calculate statistics
    const stats = {
        totalGenes: genes.length,
        totalGuides: genes.reduce((sum, g) => sum + (g.guides?.length || 0), 0),
        avgPleiotropy: genes.reduce((sum, g) => sum + (g.pleiotropy_score || 0), 0) / genes.length || 0,
        avgDoench: genes.flatMap(g => g.guides || []).reduce((sum, g) => sum + (g.doench_score || 0), 0) / 
                   genes.flatMap(g => g.guides || []).length || 0
    };
    
    container.innerHTML = `
        <div class="row g-4">
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header bg-primary text-white">
                        <h6 class="mb-0"><i class="fas fa-chart-bar me-2"></i>Statistics</h6>
                    </div>
                    <div class="card-body">
                        <table class="table table-borderless">
                            <tr>
                                <td class="text-muted">Total Genes:</td>
                                <td class="fw-bold">${stats.totalGenes}</td>
                            </tr>
                            <tr>
                                <td class="text-muted">Total gRNAs:</td>
                                <td class="fw-bold">${stats.totalGuides}</td>
                            </tr>
                            <tr>
                                <td class="text-muted">Average gRNAs/Gene:</td>
                                <td class="fw-bold">${(stats.totalGuides / stats.totalGenes).toFixed(1)}</td>
                            </tr>
                            <tr>
                                <td class="text-muted">Average Pleiotropy:</td>
                                <td class="fw-bold">${stats.avgPleiotropy.toFixed(2)}</td>
                            </tr>
                            <tr>
                                <td class="text-muted">Average Doench Score:</td>
                                <td class="fw-bold">${stats.avgDoench.toFixed(3)}</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header bg-success text-white">
                        <h6 class="mb-0"><i class="fas fa-trophy me-2"></i>Top Performers</h6>
                    </div>
                    <div class="card-body">
                        <h6 class="text-muted">Highest Specificity Genes</h6>
                        <ul class="list-group list-group-flush mb-3">
                            ${genes
                                .sort((a, b) => (b.specificity_score || 0) - (a.specificity_score || 0))
                                .slice(0, 3)
                                .map(g => `
                                    <li class="list-group-item d-flex justify-content-between">
                                        ${g.symbol}
                                        <span class="badge bg-success">${g.specificity_score?.toFixed(1)}</span>
                                    </li>
                                `).join('')}
                        </ul>
                        
                        <h6 class="text-muted">Best gRNA Designs</h6>
                        <ul class="list-group list-group-flush">
                            ${genes
                                .flatMap(g => (g.guides || []).map(guide => ({...guide, gene: g.symbol})))
                                .sort((a, b) => (b.doench_score || 0) - (a.doench_score || 0))
                                .slice(0, 3)
                                .map(g => `
                                    <li class="list-group-item d-flex justify-content-between">
                                        <code>${g.seq}</code> <small>(${g.gene})</small>
                                        <span class="badge bg-primary">${g.doench_score?.toFixed(2)}</span>
                                    </li>
                                `).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ============================================================================
// Helper Functions
// ============================================================================

function getScoreClass(score) {
    if (!score) return 'score-low';
    if (score >= 0.6) return 'score-high';
    if (score >= 0.4) return 'score-medium';
    return 'score-low';
}

function getPleiotropyClass(score) {
    if (!score && score !== 0) return 'score-medium';
    if (score <= 2) return 'score-high';  // Low pleiotropy is good
    if (score <= 5) return 'score-medium';
    return 'score-low';
}

function showGuideDetails(guide) {
    const modal = new bootstrap.Modal(document.getElementById('guideModal'));
    const content = document.getElementById('guideModalContent');
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted">Sequence Information</h6>
                <div class="sequence-box mb-3">${guide.seq}</div>
                <table class="table table-sm">
                    <tr><td class="text-muted">PAM:</td><td><code>${guide.pam_sequence}</code></td></tr>
                    <tr><td class="text-muted">Position:</td><td>${guide.position}</td></tr>
                    <tr><td class="text-muted">Strand:</td><td>${guide.strand}</td></tr>
                    <tr><td class="text-muted">Exon:</td><td>${guide.exon_number} (${guide.exon_position})</td></tr>
                    <tr><td class="text-muted">GC Content:</td><td>${((guide.gc_content || 0) * 100).toFixed(1)}%</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6 class="text-muted">Scoring</h6>
                <table class="table table-sm">
                    <tr>
                        <td class="text-muted">Doench Score:</td>
                        <td><span class="score-badge ${getScoreClass(guide.doench_score)}">${guide.doench_score?.toFixed(3) || 'N/A'}</span></td>
                    </tr>
                    <tr>
                        <td class="text-muted">Specificity:</td>
                        <td>${guide.specificity_score?.toFixed(3) || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td class="text-muted">Off-targets:</td>
                        <td>${guide.cfd_off_targets || 0}</td>
                    </tr>
                    <tr>
                        <td class="text-muted">Pathway Conflict:</td>
                        <td>${guide.pathway_conflict ? 'Yes' : 'No'}</td>
                    </tr>
                    <tr>
                        <td class="text-muted">Severity:</td>
                        <td><span class="badge bg-${guide.severity_level === 'HIGH' ? 'danger' : guide.severity_level === 'MEDIUM' ? 'warning' : 'info'}">${guide.severity_level}</span></td>
                    </tr>
                </table>
            </div>
        </div>
        
        ${guide.safety_recommendation ? `
            <div class="alert alert-warning mt-3">
                <h6><i class="fas fa-shield-alt me-2"></i>Safety Recommendation</h6>
                <p class="mb-0">${guide.safety_recommendation}</p>
            </div>
        ` : ''}
    `;
    
    modal.show();
}

function toggleAllGuides(geneSymbol) {
    // This would show all guides for a specific gene
    // For now, switch to the All gRNAs tab and filter
    document.getElementById('guides-tab').click();
    document.getElementById('guideSearch').value = geneSymbol;
    searchGuides({ target: { value: geneSymbol } });
}

function searchGuides(event) {
    const query = event.target.value.toLowerCase();
    const rows = document.querySelectorAll('#allGuidesTable tbody tr');
    
    rows.forEach(row => {
        const searchData = row.dataset.search || '';
        row.style.display = searchData.includes(query) ? '' : 'none';
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
