# Manuscript Submission Checklist

**Manuscript:** K-Sites: An Integrated AI-Powered Platform for Non-Pleiotropic CRISPR Guide RNA Design

**Target Journal:** Nature Methods

---

## Pre-Submission Requirements

### Author Information
- [ ] All author names correctly spelled
- [ ] All author affiliations accurate and complete
- [ ] Corresponding author clearly identified
- [ ] Author contributions statement prepared
- [ ] Competing interests declared (none)

### Manuscript Content
- [ ] Title is concise (<100 characters) and informative
- [ ] Abstract < 250 words
- [ ] Keywords included (5-8 terms)
- [ ] Word count within journal limits (~4,500 words for Nature Methods)
- [ ] All figures referenced in text
- [ ] All tables referenced in text
- [ ] All supplementary materials referenced

### References
- [ ] All citations follow journal format
- [ ] All references are complete (authors, title, journal, year, volume, pages)
- [ ] DOIs included where available
- [ ] No broken URLs
- [ ] Reference list is up-to-date

---

## Figures and Tables

### Main Text Figures
- [ ] **Figure 1:** Architecture diagram (PDF, 300 dpi minimum)
  - [ ] All components clearly labeled
  - [ ] Legend defines all acronyms
  - [ ] Colorblind-friendly palette
  
- [ ] **Figure 2:** RAG workflow diagram (PDF, 300 dpi minimum)
  - [ ] All steps clearly labeled
  - [ ] Input/output examples shown
  - [ ] Legend explains symbols

### Main Text Tables
- [ ] **Table 1:** Evidence code classification
  - [ ] All codes verified correct
  - [ ] Formatting consistent
  
- [ ] **Table 2:** Cas nuclease comparison
  - [ ] PAM patterns verified
  - [ ] All Cas types functional
  
- [ ] **Table 3:** CFD mismatch penalties
  - [ ] Values match Hsu et al. 2013
  - [ ] Position numbers correct (1-indexed)
  
- [ ] **Table 4:** Test coverage summary
  - [ ] All tests currently passing
  - [ ] Coverage percentages accurate
  
- [ ] **Table 5:** Tool comparison
  - [ ] All comparisons verified accurate
  - [ ] No misrepresentation of competitors

### Supplementary Figures
- [ ] Figure S1: Pleiotropy distribution (PDF)
- [ ] Figure S2: Lambda optimization (PDF)
- [ ] Figure S3: Runtime benchmarks (PDF)
- [ ] Figure S4: RAG ROC curves (PDF)
- [ ] Figure S5: Quality metrics (PDF)
- [ ] Figure S6: Pathway network (PDF)

### Supplementary Tables
- [ ] Table S1: Complete evidence codes
- [ ] Table S2: Doench 2016 weights
- [ ] Table S3: CFD penalty matrix
- [ ] Table S4: CFD comparison
- [ ] Table S5: Coverage report
- [ ] Table S6: RAG validation
- [ ] Table S7: Cross-species validation
- [ ] Table S8: Performance benchmarks

---

## Data and Code Availability

### Code Repository
- [ ] GitHub repository is public: https://github.com/KanakaKK/K-sites
- [ ] README is comprehensive
- [ ] Installation instructions work
- [ ] Example usage provided
- [ ] License file included (MIT)
- [ ] Requirements.txt complete

### Documentation
- [ ] API documentation complete
- [ ] CLI help messages informative
- [ ] Web interface documented
- [ ] Troubleshooting guide included

### Test Suite
- [ ] All 50 tests passing
```bash
cd /home/iiab/Documents/K-sites
python -m pytest tests/ -v
```
- [ ] Coverage report generated
- [ ] No critical warnings

### Example Data
- [ ] Mouse analysis results included
- [ ] All file formats work (HTML, CSV, JSON, FASTA, GenBank)
- [ ] Data is anonymized (no personal information)

---

## Supplementary Information

### Content
- [ ] Supplementary Methods are detailed
- [ ] All supplementary figures have legends
- [ ] All supplementary tables have titles
- [ ] Supplementary references are complete
- [ ] File S1 (JSON results) is provided
- [ ] File S2 (FASTA sequences) is provided
- [ ] File S3 (CSV metrics) is provided
- [ ] File S4 (GenBank) is provided

### Organization
- [ ] Supplementary sections are numbered
- [ ] Cross-references are correct
- [ ] Page numbers included (if applicable)

---

## Cover Letter

### Content Checklist
- [ ] Editor's name correct (if known)
- [ ] Journal name correct
- [ ] Manuscript title included
- [ ] Key innovation highlighted
- [ ] Why this journal is appropriate
- [ ] Suggested reviewers listed (5 names)
- [ ] Conflicts of interest declared

### Suggested Reviewers
- [ ] Dr. John Doench (Broad Institute)
- [ ] Dr. Neville Sanjana (NYU)
- [ ] Dr. Jennifer Doudna (UC Berkeley)
- [ ] Dr. Feng Zhang (Broad Institute)
- [ ] Dr. Magda Bienko (Karolinska Institutet)

### Reviewers to Exclude (if any)
- [ ] None declared

---

## Technical Validation

### Code Quality
- [ ] No syntax errors
- [ ] No security vulnerabilities
- [ ] Proper error handling
- [ ] API rate limiting compliant

### Performance
- [ ] Runtime benchmarks current
- [ ] Memory usage documented
- [ ] Scales appropriately

### External Dependencies
- [ ] All APIs functional (NCBI, QuickGO, UniProt)
- [ ] Neo4j integration optional
- [ ] RAG dependencies optional

---

## Journal-Specific Requirements

### Nature Methods Requirements
- [ ] Abstract is unstructured (no headings)
- [ ] Main text sections: Introduction, Results, Discussion, Methods
- [ ] References use numbered citation format
- [ ] Figures are separate files (not embedded)
- [ ] Supplementary Information is separate document

### Formatting
- [ ] Font: Arial or Helvetica, 11 pt
- [ ] Line spacing: Double
- [ ] Margins: 1 inch all sides
- [ ] Page numbers: Bottom center

### Length Guidelines
- [ ] Abstract: <250 words
- [ ] Main text: ~4,500 words (Nature Methods)
- [ ] Figures: Maximum 6-8
- [ ] References: No limit, but be concise
- [ ] Supplementary: No strict limit

---

## Final Checks

### Proofreading
- [ ] Spelling checked (American English)
- [ ] Grammar checked
- [ ] Equations render correctly
- [ ] Special characters display properly
- [ ] Acronyms defined on first use
- [ ] Consistent terminology throughout

### Cross-References
- [ ] All figure citations correct
- [ ] All table citations correct
- [ ] All supplementary citations correct
- [ ] All equation citations correct
- [ ] All section citations correct

### Scientific Accuracy
- [ ] All mathematical formulas verified
- [ ] All statistics are correct
- [ ] All biological claims supported
- [ ] No overstatement of results
- [ ] Limitations acknowledged

### Ethical Compliance
- [ ] No human subjects data
- [ ] No vertebrate animal data (computational only)
- [ ] No dual use research of concern
- [ ] Data availability statement included
- [ ] Code availability statement included

---

## Submission Materials

### Required Files
- [ ] Manuscript (main document)
- [ ] Cover letter
- [ ] Figure files (all)
- [ ] Table files (if separate)
- [ ] Supplementary Information
- [ ] Supplementary Data Files

### File Naming Convention
- [ ] `manuscript.pdf` (or .tex/.docx as required)
- [ ] `cover_letter.pdf`
- [ ] `figure1.pdf`, `figure2.pdf`, etc.
- [ ] `table1.pdf`, `table2.pdf`, etc. (if separate)
- [ ] `supplementary_information.pdf`
- [ ] `supplementary_data.zip`

---

## Post-Submission Actions

### Immediate
- [ ] Confirm submission receipt
- [ ] Note manuscript tracking number
- [ ] Update co-authors on submission

### During Review
- [ ] Monitor email for editor/reviewer queries
- [ ] Respond to queries within 48 hours
- [ ] Prepare for potential revision

### If Accepted
- [ ] Prepare final figures at publication quality
- [ ] Complete author forms
- [ ] Review proofs carefully
- [ ] Pay publication charges (if applicable)

### If Rejected
- [ ] Read reviews carefully
- [ ] Consider revision for another journal
- [ ] Update manuscript based on feedback
- [ ] Resubmit to alternative journal

---

## Emergency Contacts

### Technical Issues
- Repository: https://github.com/KanakaKK/K-sites/issues
- Email: kanakakk@example.com

### Journal Contact
- Nature Methods Editorial Office
- Email: nmeth@nature.com
- Phone: +1-212-726-9200

---

## Timeline

| Task | Target Date | Status |
|------|-------------|--------|
| Final manuscript review | 2026-02-15 | Pending |
| Figure preparation | 2026-02-15 | Pending |
| Supplementary materials | 2026-02-16 | Pending |
| Cover letter finalization | 2026-02-16 | Pending |
| Submission | 2026-02-17 | Pending |

---

**Submission Prepared By:** Kanaka K.K.

**Date:** February 13, 2026

**Version:** 1.0

---

*Checklist completed: [ ] Yes [ ] No*

*If No, list outstanding items:*

