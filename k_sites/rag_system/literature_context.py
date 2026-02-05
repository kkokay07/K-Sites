"""
RAG-Based Phenotype Prediction System for K-Sites

This module predicts knockout phenotypes by mining and semantically analyzing scientific literature.
"""

import logging
import os
import requests
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re
from dataclasses import dataclass
from enum import Enum
import json

# Optional imports for RAG functionality
try:
    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer, AutoModel
    import faiss
    import numpy as np
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG libraries not available. Install sentence-transformers, transformers, faiss-cpu, and numpy for full functionality.")

# Set up logging
logger = logging.getLogger(__name__)

# Define phenotype severity categories
class PhenotypeSeverity(Enum):
    LETHAL = "LETHAL"
    SEVERE = "SEVERE"
    MODERATE = "MODERATE"
    MILD = "MILD"
    UNKNOWN = "UNKNOWN"

class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

@dataclass
class PhenotypePrediction:
    severity: PhenotypeSeverity
    risk_level: RiskLevel
    confidence_score: float
    predicted_phenotypes: List[str]
    supporting_evidence: List[Dict]
    lethality_stage: Optional[str] = None
    confidence_reasoning: str = ""

class LiteratureMiner:
    """
    Handles literature mining from PubMed and PMC Open Access.
    """
    
    def __init__(self):
        self.email = os.getenv('NCBI_EMAIL', 'your.email@example.com')
        self.api_key = os.getenv('NCBI_API_KEY', '')  # Optional but recommended for higher rate limits
        
    def search_pubmed(self, gene_symbol: str, search_type: str = "comprehensive") -> List[Dict]:
        """
        Search PubMed for literature related to a gene.
        
        Args:
            gene_symbol: Gene symbol to search for
            search_type: Type of search ("comprehensive", "knockout", "phenotype", "viability", "crispr")
            
        Returns:
            List of publication records
        """
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
        # Construct search query based on type
        if search_type == "knockout":
            query = f"{gene_symbol}[Gene] AND (knockout[Title/Abstract] OR knockout[MeSH Terms] OR mutant[Title/Abstract])"
        elif search_type == "phenotype":
            query = f"{gene_symbol}[Gene] AND (phenotype[Title/Abstract] OR phenotype[MeSH Terms] OR morpholino[Title/Abstract])"
        elif search_type == "viability":
            query = f"{gene_symbol}[Gene] AND (viability[Title/Abstract] OR lethal[Title/Abstract] OR survival[Title/Abstract])"
        elif search_type == "crispr":
            query = f"{gene_symbol}[Gene] AND (CRISPR[Title/Abstract] OR guide[Title/Abstract] OR gRNA[Title/Abstract])"
        else:  # comprehensive
            query = f"{gene_symbol}[Gene] AND (knockout[Title/Abstract] OR phenotype[Title/Abstract] OR mutant[Title/Abstract] OR viability[Title/Abstract])"
        
        # Build parameters for ESearch
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": 100,  # Limit to 100 results for performance
            "retmode": "json",
            "sort": "relevance"
        }
        
        if self.api_key:
            search_params["api_key"] = self.api_key
        
        try:
            # Perform search
            response = requests.get(base_url + "esearch.fcgi", params=search_params, timeout=30)
            response.raise_for_status()
            
            search_results = response.json()
            
            if "esearchresult" not in search_results or "idlist" not in search_results["esearchresult"]:
                logger.warning(f"No publications found for gene {gene_symbol} with search type {search_type}")
                return []
            
            id_list = search_results["esearchresult"]["idlist"]
            if not id_list:
                logger.info(f"No publications found for gene {gene_symbol} with search type {search_type}")
                return []
            
            # Fetch detailed records for the IDs
            pubmed_ids = ",".join(id_list[:20])  # Limit to 20 for detailed fetch to avoid timeouts
            detail_params = {
                "db": "pubmed",
                "id": pubmed_ids,
                "retmode": "xml",
                "retmax": 20
            }
            
            if self.api_key:
                detail_params["api_key"] = self.api_key
            
            detail_response = requests.get(base_url + "efetch.fcgi", params=detail_params, timeout=30)
            detail_response.raise_for_status()
            
            # Note: We're returning basic info since parsing XML is complex
            # In a real implementation, you'd parse the XML properly
            publications = []
            for pmid in id_list[:20]:  # Take the first 20 results
                pub_info = {
                    "pmid": pmid,
                    "gene_symbol": gene_symbol,
                    "search_type": search_type,
                    "abstract": "",  # Would be filled from XML parsing
                    "title": "",
                    "authors": [],
                    "journal": "",
                    "publication_date": ""
                }
                publications.append(pub_info)
            
            logger.info(f"Found {len(publications)} publications for gene {gene_symbol} with search type {search_type}")
            return publications
            
        except Exception as e:
            logger.error(f"Error searching PubMed for {gene_symbol}: {str(e)}")
            return []
    
    def batch_search_genes(self, gene_symbols: List[str]) -> Dict[str, List[Dict]]:
        """
        Perform batch processing of multiple genes.
        
        Args:
            gene_symbols: List of gene symbols to search
            
        Returns:
            Dictionary mapping gene symbols to their publication lists
        """
        results = {}
        
        for gene_symbol in gene_symbols:
            logger.info(f"Searching literature for gene: {gene_symbol}")
            
            # Perform multiple targeted searches
            search_types = ["knockout", "phenotype", "viability", "crispr", "comprehensive"]
            gene_publications = []
            
            for search_type in search_types:
                pubs = self.search_pubmed(gene_symbol, search_type)
                gene_publications.extend(pubs)
            
            # Deduplicate publications
            unique_pubs = {}
            for pub in gene_publications:
                pub_id = pub["pmid"]
                if pub_id not in unique_pubs:
                    unique_pubs[pub_id] = pub
            
            results[gene_symbol] = list(unique_pubs.values())
            
            # Rate limiting to be respectful to NCBI servers
            time.sleep(0.5)
        
        return results

class VectorStore:
    """
    Vector store for semantic search using FAISS.
    """
    
    def __init__(self):
        if not RAG_AVAILABLE:
            logger.warning("Vector store unavailable due to missing dependencies")
            self.model = None
            self.index = None
            self.documents = []
        else:
            # Load pre-trained sentence transformer model
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence transformer model for embeddings")
            except Exception as e:
                logger.error(f"Could not load sentence transformer model: {e}")
                self.model = None
            
            # Initialize FAISS index
            self.index = None
            self.documents = []
    
    def add_documents(self, documents: List[Dict]):
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents with text content
        """
        if not RAG_AVAILABLE or self.model is None:
            logger.warning("Cannot add documents: RAG libraries not available")
            return
        
        texts = []
        for doc in documents:
            # Extract text content from document
            text = f"{doc.get('title', '')}. {doc.get('abstract', '')}"
            texts.append(text)
        
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        # Create FAISS index if it doesn't exist
        if self.index is None:
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
        
        # Add embeddings to index
        self.index.add(embeddings.astype('float32'))
        
        # Store documents
        self.documents.extend(documents)
        logger.info(f"Added {len(documents)} documents to vector store")
    
    def search(self, query: str, k: int = 5, relevance_threshold: float = 0.5) -> List[Tuple[Dict, float]]:
        """
        Perform semantic search in the vector store.
        
        Args:
            query: Search query
            k: Number of results to return
            relevance_threshold: Minimum similarity threshold
            
        Returns:
            List of tuples (document, similarity_score)
        """
        if not RAG_AVAILABLE or self.model is None or self.index is None:
            logger.warning("Cannot perform search: RAG libraries not available or index empty")
            return []
        
        # Generate embedding for query
        query_embedding = self.model.encode([query])
        
        # Perform similarity search
        similarities, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx < len(self.documents) and sim >= relevance_threshold:
                results.append((self.documents[idx], float(sim)))
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Found {len(results)} relevant documents for query: {query}")
        return results

class PhenotypeExtractor:
    """
    Extracts and classifies phenotypes from literature.
    """
    
    def __init__(self):
        # Define regular expression patterns for phenotype terms
        self.phenotype_patterns = {
            "lethality": [
                r"lethal", r"embryonic.*lethal", r"perinatal.*lethal", 
                r"postnatal.*lethal", r"death", r"mortality", r"survival"
            ],
            "development": [
                r"growth.*defect", r"development.*defect", r"morphogenetic.*defect",
                r"abnormal.*development", r"malformation", r"dysplasia"
            ],
            "behavior": [
                r"locomotion.*defect", r"behavior.*defect", r"motor.*defect",
                r"movement.*defect", r"coordination.*defect"
            ],
            "physiology": [
                r"metabolic.*defect", r"cardiac.*defect", r"respiratory.*defect",
                r"neurological.*defect", r"cognitive.*defect"
            ]
        }
        
        # Define severity classification patterns
        self.severity_indicators = {
            PhenotypeSeverity.LETHAL: [
                r"lethal", r"embryonic.*lethal", r"perinatal.*lethal", 
                r"postnatal.*lethal", r"early.*lethal", r"severe.*lethal"
            ],
            PhenotypeSeverity.SEVERE: [
                r"severe", r"major.*defect", r"profound.*impairment", 
                r"significant.*defect", r"substantial.*defect"
            ],
            PhenotypeSeverity.MODERATE: [
                r"moderate", r"intermediate", r"reduced.*fitness", 
                r"growth.*defect", r"minor.*defect"
            ],
            PhenotypeSeverity.MILD: [
                r"mild", r"subtle", r"minor", r"slight", r"small.*change"
            ]
        }
    
    def extract_phenotypes_from_text(self, text: str) -> List[Dict]:
        """
        Extract phenotype terms from text using pattern matching.
        
        Args:
            text: Text to extract phenotypes from
            
        Returns:
            List of extracted phenotypes with details
        """
        phenotypes = []
        
        # Convert text to lowercase for pattern matching
        lower_text = text.lower()
        
        # Check for each phenotype category
        for category, patterns in self.phenotype_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, lower_text, re.IGNORECASE)
                for match in matches:
                    phenotype = {
                        "category": category,
                        "term": match.group(),
                        "position": match.span(),
                        "context": text[max(0, match.start()-100):match.end()+100].strip()
                    }
                    phenotypes.append(phenotype)
        
        return phenotypes
    
    def classify_severity(self, phenotypes: List[Dict], abstract_text: str = "") -> Tuple[PhenotypeSeverity, str]:
        """
        Classify the overall severity based on extracted phenotypes and text.
        
        Args:
            phenotypes: List of extracted phenotypes
            abstract_text: Full text for additional context
            
        Returns:
            Tuple of (severity, reasoning)
        """
        # Combine phenotypes and abstract text for analysis
        combined_text = abstract_text.lower()
        for pheno in phenotypes:
            combined_text += " " + pheno["term"].lower()
        
        # Count severity indicators
        severity_counts = {}
        for severity, patterns in self.severity_indicators.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, combined_text, re.IGNORECASE))
            severity_counts[severity] = count
        
        # Determine overall severity
        if severity_counts[PhenotypeSeverity.LETHAL] > 0:
            return PhenotypeSeverity.LETHAL, f"Lethality terms detected ({severity_counts[PhenotypeSeverity.LETHAL]} instances)"
        elif severity_counts[PhenotypeSeverity.SEVERE] > 0:
            return PhenotypeSeverity.SEVERE, f"Severe phenotype terms detected ({severity_counts[PhenotypeSeverity.SEVERE]} instances)"
        elif severity_counts[PhenotypeSeverity.MODERATE] > 0:
            return PhenotypeSeverity.MODERATE, f"Moderate phenotype terms detected ({severity_counts[PhenotypeSeverity.MODERATE]} instances)"
        elif severity_counts[PhenotypeSeverity.MILD] > 0:
            return PhenotypeSeverity.MILD, f"Mild phenotype terms detected ({severity_counts[PhenotypeSeverity.MILD]} instances)"
        else:
            return PhenotypeSeverity.UNKNOWN, "No clear severity indicators found in literature"
    
    def detect_lethality_stage(self, text: str) -> Optional[str]:
        """
        Detect the stage of lethality if present.
        
        Args:
            text: Text to analyze
            
        Returns:
            Stage of lethality or None
        """
        text_lower = text.lower()
        
        stages = [
            (r"embryonic.*lethal|embryo.*lethal", "Embryonic"),
            (r"perinatal.*lethal", "Perinatal"), 
            (r"postnatal.*lethal|adult.*lethal", "Postnatal"),
            (r"larval.*lethal|juvenile.*lethal", "Juvenile/Larval")
        ]
        
        for pattern, stage in stages:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return stage
        
        return None

class RAGPhenotypePredictor:
    """
    Main class for RAG-based phenotype prediction.
    """
    
    def __init__(self):
        self.literature_miner = LiteratureMiner()
        self.vector_store = VectorStore()
        self.phenotype_extractor = PhenotypeExtractor()
        self.logger = logging.getLogger(__name__)
    
    def predict_phenotype(self, gene_symbol: str, organism_taxid: str = "9606") -> PhenotypePrediction:
        """
        Predict knockout phenotype for a gene using RAG.
        
        Args:
            gene_symbol: Gene symbol to predict phenotype for
            organism_taxid: NCBI Taxonomy ID for the organism
            
        Returns:
            PhenotypePrediction object with results
        """
        self.logger.info(f"Predicting phenotype for gene {gene_symbol} in organism {organism_taxid}")
        
        # Step 1: Mine literature
        publications = self.literature_miner.search_pubmed(gene_symbol, "comprehensive")
        
        if not publications:
            self.logger.warning(f"No literature found for gene {gene_symbol}, returning unknown phenotype")
            return PhenotypePrediction(
                severity=PhenotypeSeverity.UNKNOWN,
                risk_level=RiskLevel.UNKNOWN,
                confidence_score=0.1,
                predicted_phenotypes=[],
                supporting_evidence=[],
                confidence_reasoning="No literature found for this gene"
            )
        
        # Step 2: Add to vector store for semantic search
        self.vector_store.add_documents(publications)
        
        # Step 3: Perform targeted queries to extract phenotype information
        queries = [
            f"What phenotypes result from {gene_symbol} knockout?",
            f"What is the viability of {gene_symbol} mutants?",
            f"What developmental defects occur in {gene_symbol} knockouts?",
            f"Is {gene_symbol} essential for survival?"
        ]
        
        all_relevant_docs = []
        for query in queries:
            relevant_docs = self.vector_store.search(query, k=3)
            all_relevant_docs.extend(relevant_docs)
        
        # Step 4: Extract phenotypes from relevant documents
        all_phenotypes = []
        supporting_evidence = []
        
        for doc, score in all_relevant_docs:
            # Extract phenotypes from document text
            text_content = f"{doc.get('title', '')}. {doc.get('abstract', '')}"
            phenotypes = self.phenotype_extractor.extract_phenotypes_from_text(text_content)
            
            all_phenotypes.extend(phenotypes)
            
            # Add supporting evidence
            evidence = {
                "pmid": doc.get("pmid"),
                "title": doc.get("title"),
                "similarity_score": score,
                "phenotypes_extracted": [p["term"] for p in phenotypes]
            }
            supporting_evidence.append(evidence)
        
        # Step 5: Classify severity and determine risk
        severity, reasoning = self.phenotype_extractor.classify_severity(all_phenotypes, 
                                                                       " ".join([e["title"] for e in supporting_evidence]))
        
        # Determine risk level based on severity
        risk_mapping = {
            PhenotypeSeverity.LETHAL: RiskLevel.CRITICAL,
            PhenotypeSeverity.SEVERE: RiskLevel.HIGH,
            PhenotypeSeverity.MODERATE: RiskLevel.MEDIUM,
            PhenotypeSeverity.MILD: RiskLevel.LOW,
            PhenotypeSeverity.UNKNOWN: RiskLevel.UNKNOWN
        }
        risk_level = risk_mapping.get(severity, RiskLevel.UNKNOWN)
        
        # Detect lethality stage if applicable
        lethality_stage = None
        if severity == PhenotypeSeverity.LETHAL:
            # Look for stage information in supporting text
            full_text = " ".join([e["title"] for e in supporting_evidence])
            lethality_stage = self.phenotype_extractor.detect_lethality_stage(full_text)
        
        # Calculate confidence based on number of publications and evidence quality
        confidence_score = min(1.0, 0.1 + (len(supporting_evidence) * 0.2) + (len(all_phenotypes) * 0.1))
        
        # Create prediction result
        prediction = PhenotypePrediction(
            severity=severity,
            risk_level=risk_level,
            confidence_score=confidence_score,
            predicted_phenotypes=list(set([p["term"] for p in all_phenotypes])),  # Unique phenotypes
            supporting_evidence=supporting_evidence,
            lethality_stage=lethality_stage,
            confidence_reasoning=f"{reasoning}. Based on {len(supporting_evidence)} publications with {len(all_phenotypes)} phenotype terms extracted."
        )
        
        self.logger.info(f"Predicted phenotype for {gene_symbol}: {severity.value}, risk {risk_level.value}, confidence {confidence_score:.2f}")
        return prediction
    
    def batch_predict_phenotypes(self, gene_list: List[str], organism_taxid: str = "9606") -> Dict[str, PhenotypePrediction]:
        """
        Predict phenotypes for multiple genes.
        
        Args:
            gene_list: List of gene symbols
            organism_taxid: NCBI Taxonomy ID for the organism
            
        Returns:
            Dictionary mapping gene symbols to predictions
        """
        results = {}
        
        for gene_symbol in gene_list:
            try:
                prediction = self.predict_phenotype(gene_symbol, organism_taxid)
                results[gene_symbol] = prediction
            except Exception as e:
                self.logger.error(f"Error predicting phenotype for {gene_symbol}: {str(e)}")
                # Add a default prediction for failed genes
                results[gene_symbol] = PhenotypePrediction(
                    severity=PhenotypeSeverity.UNKNOWN,
                    risk_level=RiskLevel.UNKNOWN,
                    confidence_score=0.0,
                    predicted_phenotypes=[],
                    supporting_evidence=[],
                    confidence_reasoning=f"Prediction failed: {str(e)}"
                )
        
        return results

def predict_gene_phenotype(gene_symbol: str, organism_taxid: str = "9606") -> PhenotypePrediction:
    """
    Convenience function to predict phenotype for a single gene.
    
    Args:
        gene_symbol: Gene symbol to predict phenotype for
        organism_taxid: NCBI Taxonomy ID for the organism
        
    Returns:
        PhenotypePrediction object
    """
    predictor = RAGPhenotypePredictor()
    return predictor.predict_phenotype(gene_symbol, organism_taxid)

def batch_predict_gene_phenotypes(gene_list: List[str], organism_taxid: str = "9606") -> Dict[str, PhenotypePrediction]:
    """
    Convenience function to predict phenotypes for multiple genes.
    
    Args:
        gene_list: List of gene symbols
        organism_taxid: NCBI Taxonomy ID for the organism
        
    Returns:
        Dictionary mapping gene symbols to predictions
    """
    predictor = RAGPhenotypePredictor()
    return predictor.batch_predict_phenotypes(gene_list, organism_taxid)