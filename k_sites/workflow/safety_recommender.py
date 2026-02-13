"""
Safety Recommendation Module for K-Sites

This module generates comprehensive safety recommendations for CRISPR experiments
based on pleiotropy scores, phenotype predictions, off-target analysis, and
cross-species conservation data.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety level classification for gene knockout."""
    SAFE = "SAFE"                          # Standard KO acceptable
    CAUTION = "CAUTION"                    # Standard KO with validation
    MODERATE_CONCERN = "MODERATE_CONCERN"  # Heterozygous KO recommended
    HIGH_CONCERN = "HIGH_CONCERN"          # Conditional KO/CRISPRi preferred
    AVOID = "AVOID"                        # Alternative strategies required


class RecommendationType(Enum):
    """Types of safety recommendations."""
    STANDARD_KO = "Standard Knockout"
    VALIDATED_KO = "Standard KO with Validation"
    HETEROZYGOUS_KO = "Heterozygous Knockout"
    CONDITIONAL_KO = "Conditional Knockout (Cre-Lox)"
    CRISPRI = "CRISPR Interference (CRISPRi)"
    CRISPRA = "CRISPR Activation (CRISPRa)"
    BASE_EDITING = "Base Editing (C->T or A->G)"
    PRIME_EDITING = "Prime Editing"
    TEMPORAL_CONTROL = "Temporal Control (Tet-ON/OFF)"
    SPATIAL_CONTROL = "Spatial Control (Tissue-specific)"
    ALTERNATIVE_MODEL = "Alternative Model System"
    MULTIPLE_STRATEGIES = "Multiple Complementary Strategies"


@dataclass
class SafetyRecommendation:
    """Comprehensive safety recommendation for a gene knockout."""
    gene_symbol: str
    safety_level: SafetyLevel
    primary_recommendation: RecommendationType
    alternative_recommendations: List[RecommendationType]
    justification: List[str]
    concerns: List[str]
    mitigation_strategies: List[str]
    experimental_considerations: List[str]
    confidence_score: float  # 0.0-1.0
    supporting_evidence: Dict[str, Any]


class SafetyRecommender:
    """
    Generates safety recommendations for CRISPR experiments.
    
    Considers:
    - Pleiotropy score (multi-functionality)
    - Phenotype severity (lethal vs mild)
    - Off-target profiles
    - Pathway conflicts
    - Cross-species conservation
    - Literature support
    """
    
    def __init__(self):
        self.thresholds = {
            "pleiotropy": {
                "low": 3,
                "moderate": 5,
                "high": 8
            },
            "off_target": {
                "tolerable": 2,
                "concerning": 5,
                "critical": 10
            },
            "conservation": {
                "low": 0.3,
                "moderate": 0.6,
                "high": 0.8
            }
        }
    
    def generate_recommendation(
        self,
        gene_symbol: str,
        pleiotropy_score: float,
        phenotype_prediction: Optional[Dict] = None,
        guides: Optional[List[Dict]] = None,
        cross_species_validation: Optional[Dict] = None,
        literature_support: Optional[float] = None
    ) -> SafetyRecommendation:
        """
        Generate comprehensive safety recommendation for a gene.
        
        Args:
            gene_symbol: Target gene symbol
            pleiotropy_score: Calculated pleiotropy score (0-10)
            phenotype_prediction: Phenotype prediction dict with severity, risk_level, etc.
            guides: List of designed gRNAs with off-target data
            cross_species_validation: Cross-species validation data
            literature_support: Literature support score (0-1)
            
        Returns:
            SafetyRecommendation with detailed guidance
        """
        concerns = []
        mitigation_strategies = []
        experimental_considerations = []
        justification = []
        
        # Extract phenotype information
        phenotype_severity = None
        phenotype_risk = None
        phenotype_confidence = 0.0
        lethality_stage = None
        compensatory_mechanisms = []
        
        if phenotype_prediction:
            phenotype_severity = phenotype_prediction.get("severity", {}).get("value") if isinstance(phenotype_prediction.get("severity"), dict) else str(phenotype_prediction.get("severity", ""))
            phenotype_risk = phenotype_prediction.get("risk_level", {}).get("value") if isinstance(phenotype_prediction.get("risk_level"), dict) else str(phenotype_prediction.get("risk_level", ""))
            phenotype_confidence = phenotype_prediction.get("confidence_score", 0.0)
            lethality_stage = phenotype_prediction.get("lethality_stage")
            compensatory_mechanisms = phenotype_prediction.get("compensatory_mechanisms", [])
        
        # Analyze off-targets
        off_target_analysis = self._analyze_off_targets(guides)
        
        # Analyze conservation
        conservation_score = cross_species_validation.get("conservation_score", 0.0) if cross_species_validation else 0.0
        
        # Determine safety level and recommendations
        safety_level, primary_rec, alternative_recs = self._determine_safety_level(
            pleiotropy_score,
            phenotype_risk,
            off_target_analysis,
            conservation_score,
            phenotype_confidence
        )
        
        # Build justification
        justification = self._build_justification(
            pleiotropy_score,
            phenotype_severity,
            phenotype_risk,
            off_target_analysis,
            conservation_score,
            literature_support,
            phenotype_confidence
        )
        
        # Build concerns list
        concerns = self._identify_concerns(
            pleiotropy_score,
            phenotype_severity,
            phenotype_risk,
            off_target_analysis,
            conservation_score,
            compensatory_mechanisms
        )
        
        # Build mitigation strategies
        mitigation_strategies = self._suggest_mitigation_strategies(
            safety_level,
            primary_rec,
            off_target_analysis,
            phenotype_risk,
            compensatory_mechanisms
        )
        
        # Build experimental considerations
        experimental_considerations = self._suggest_experimental_considerations(
            phenotype_severity,
            lethality_stage,
            off_target_analysis,
            primary_rec
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            phenotype_confidence,
            literature_support,
            bool(guides),
            bool(cross_species_validation)
        )
        
        # Compile supporting evidence
        supporting_evidence = {
            "pleiotropy_score": pleiotropy_score,
            "phenotype_severity": phenotype_severity,
            "phenotype_risk": phenotype_risk,
            "off_target_summary": off_target_analysis,
            "conservation_score": conservation_score,
            "compensatory_mechanisms": compensatory_mechanisms,
            "literature_support": literature_support
        }
        
        return SafetyRecommendation(
            gene_symbol=gene_symbol,
            safety_level=safety_level,
            primary_recommendation=primary_rec,
            alternative_recommendations=alternative_recs,
            justification=justification,
            concerns=concerns,
            mitigation_strategies=mitigation_strategies,
            experimental_considerations=experimental_considerations,
            confidence_score=confidence_score,
            supporting_evidence=supporting_evidence
        )
    
    def _analyze_off_targets(self, guides: Optional[List[Dict]]) -> Dict[str, Any]:
        """Analyze off-target profiles from guide RNAs."""
        if not guides:
            return {
                "total_guides": 0,
                "guides_with_severe_off_targets": 0,
                "max_severity": "none",
                "pathway_conflicts": 0,
                "cfd_scores": []
            }
        
        guides_with_severe = 0
        max_severity = "none"
        pathway_conflicts = 0
        cfd_scores = []
        
        severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "none": 0}
        
        for guide in guides:
            severity = guide.get("severity_level", "LOW")
            if severity in ["CRITICAL", "HIGH"]:
                guides_with_severe += 1
            
            if severity_rank.get(severity, 0) > severity_rank.get(max_severity, 0):
                max_severity = severity
            
            if guide.get("pathway_conflicts", 0) > 0 or guide.get("pathway_conflict", False):
                pathway_conflicts += 1
            
            cfd = guide.get("cfd_off_targets", 0)
            if isinstance(cfd, (int, float)):
                cfd_scores.append(cfd)
        
        return {
            "total_guides": len(guides),
            "guides_with_severe_off_targets": guides_with_severe,
            "max_severity": max_severity,
            "pathway_conflicts": pathway_conflicts,
            "cfd_scores": cfd_scores,
            "avg_cfd": sum(cfd_scores) / len(cfd_scores) if cfd_scores else 0
        }
    
    def _determine_safety_level(
        self,
        pleiotropy_score: float,
        phenotype_risk: Optional[str],
        off_target_analysis: Dict,
        conservation_score: float,
        phenotype_confidence: float
    ) -> tuple:
        """Determine safety level and primary/alternative recommendations."""
        
        severe_off_targets = off_target_analysis.get("guides_with_severe_off_targets", 0)
        pathway_conflicts = off_target_analysis.get("pathway_conflicts", 0)
        
        # High concern conditions
        if phenotype_risk in ["CRITICAL", "HIGH"] and phenotype_confidence > 0.5:
            if pleiotropy_score > 8:
                return (
                    SafetyLevel.AVOID,
                    RecommendationType.MULTIPLE_STRATEGIES,
                    [RecommendationType.CRISPRI, RecommendationType.CONDITIONAL_KO, RecommendationType.ALTERNATIVE_MODEL]
                )
            else:
                return (
                    SafetyLevel.HIGH_CONCERN,
                    RecommendationType.CONDITIONAL_KO,
                    [RecommendationType.CRISPRI, RecommendationType.HETEROZYGOUS_KO, RecommendationType.TEMPORAL_CONTROL]
                )
        
        # Phenotype-based decisions
        if phenotype_risk == "CRITICAL":
            return (
                SafetyLevel.HIGH_CONCERN,
                RecommendationType.CONDITIONAL_KO,
                [RecommendationType.CRISPRI, RecommendationType.TEMPORAL_CONTROL]
            )
        
        if phenotype_risk == "HIGH":
            if pleiotropy_score > 5:
                return (
                    SafetyLevel.HIGH_CONCERN,
                    RecommendationType.CRISPRI,
                    [RecommendationType.CONDITIONAL_KO, RecommendationType.HETEROZYGOUS_KO]
                )
            else:
                return (
                    SafetyLevel.MODERATE_CONCERN,
                    RecommendationType.HETEROZYGOUS_KO,
                    [RecommendationType.VALIDATED_KO, RecommendationType.CRISPRI]
                )
        
        # Off-target concerns
        if severe_off_targets > 5 or pathway_conflicts > 3:
            return (
                SafetyLevel.MODERATE_CONCERN,
                RecommendationType.VALIDATED_KO,
                [RecommendationType.CRISPRI, RecommendationType.BASE_EDITING]
            )
        
        # Pleiotropy-based decisions
        if pleiotropy_score > 8:
            return (
                SafetyLevel.HIGH_CONCERN,
                RecommendationType.CRISPRI,
                [RecommendationType.HETEROZYGOUS_KO, RecommendationType.CONDITIONAL_KO]
            )
        
        if pleiotropy_score > 5:
            if conservation_score > 0.8:
                return (
                    SafetyLevel.MODERATE_CONCERN,
                    RecommendationType.HETEROZYGOUS_KO,
                    [RecommendationType.VALIDATED_KO, RecommendationType.CONDITIONAL_KO]
                )
            else:
                return (
                    SafetyLevel.CAUTION,
                    RecommendationType.VALIDATED_KO,
                    [RecommendationType.STANDARD_KO]
                )
        
        if pleiotropy_score > 3:
            return (
                SafetyLevel.CAUTION,
                RecommendationType.STANDARD_KO,
                [RecommendationType.VALIDATED_KO]
            )
        
        # Low concern - standard KO acceptable
        return (
            SafetyLevel.SAFE,
            RecommendationType.STANDARD_KO,
            [RecommendationType.VALIDATED_KO] if severe_off_targets > 0 else []
        )
    
    def _build_justification(
        self,
        pleiotropy_score: float,
        phenotype_severity: Optional[str],
        phenotype_risk: Optional[str],
        off_target_analysis: Dict,
        conservation_score: float,
        literature_support: Optional[float],
        phenotype_confidence: float
    ) -> List[str]:
        """Build human-readable justification for recommendation."""
        justification = []
        
        # Pleiotropy justification
        if pleiotropy_score > 8:
            justification.append(f"Very high pleiotropy score ({pleiotropy_score:.1f}) indicates multiple biological functions")
        elif pleiotropy_score > 5:
            justification.append(f"High pleiotropy score ({pleiotropy_score:.1f}) suggests multiple roles")
        elif pleiotropy_score > 3:
            justification.append(f"Moderate pleiotropy score ({pleiotropy_score:.1f})")
        else:
            justification.append(f"Low pleiotropy score ({pleiotropy_score:.1f}) indicates specific function")
        
        # Phenotype justification
        if phenotype_risk:
            if phenotype_confidence > 0.5:
                justification.append(f"Predicted {phenotype_risk} risk phenotype (confidence: {phenotype_confidence:.2f})")
            else:
                justification.append(f"Low confidence phenotype prediction ({phenotype_confidence:.2f})")
        
        # Off-target justification
        severe_ot = off_target_analysis.get("guides_with_severe_off_targets", 0)
        if severe_ot > 0:
            justification.append(f"{severe_ot} guides have severe off-targets")
        
        pathway_conf = off_target_analysis.get("pathway_conflicts", 0)
        if pathway_conf > 0:
            justification.append(f"{pathway_conf} guides have pathway conflicts")
        
        # Conservation justification
        if conservation_score > 0.8:
            justification.append(f"Highly conserved across species ({conservation_score:.2f})")
        elif conservation_score < 0.3:
            justification.append(f"Low conservation ({conservation_score:.2f}) - may indicate species-specific function")
        
        # Literature justification
        if literature_support and literature_support > 0.8:
            justification.append("Strong literature support for this gene")
        elif literature_support and literature_support < 0.3:
            justification.append("Limited literature available - consider additional validation")
        
        return justification
    
    def _identify_concerns(
        self,
        pleiotropy_score: float,
        phenotype_severity: Optional[str],
        phenotype_risk: Optional[str],
        off_target_analysis: Dict,
        conservation_score: float,
        compensatory_mechanisms: List[str]
    ) -> List[str]:
        """Identify specific concerns for the experiment."""
        concerns = []
        
        if phenotype_risk in ["CRITICAL", "HIGH"]:
            concerns.append(f"Predicted {phenotype_risk.lower()} risk phenotype - may cause lethality or severe defects")
        
        if phenotype_severity == "LETHAL":
            concerns.append("Potential lethality requires careful experimental design")
        
        if pleiotropy_score > 8:
            concerns.append("High pleiotropy may confound phenotype interpretation")
        
        severe_ot = off_target_analysis.get("guides_with_severe_off_targets", 0)
        if severe_ot > 0:
            concerns.append(f"Off-target effects possible in {severe_ot} guide designs")
        
        pathway_conf = off_target_analysis.get("pathway_conflicts", 0)
        if pathway_conf > 0:
            concerns.append("Potential disruption of related pathways")
        
        if conservation_score > 0.8:
            concerns.append("Highly conserved gene - may be essential for basic cellular functions")
        
        if compensatory_mechanisms:
            concerns.append(f"Compensatory mechanisms detected ({len(compensatory_mechanisms)}) - phenotypes may be masked")
        
        return concerns if concerns else ["No major concerns identified"]
    
    def _suggest_mitigation_strategies(
        self,
        safety_level: SafetyLevel,
        primary_rec: RecommendationType,
        off_target_analysis: Dict,
        phenotype_risk: Optional[str],
        compensatory_mechanisms: List[str]
    ) -> List[str]:
        """Suggest strategies to mitigate risks."""
        strategies = []
        
        # Off-target mitigation
        if off_target_analysis.get("guides_with_severe_off_targets", 0) > 0:
            strategies.append("Use high-fidelity Cas variants (SpCas9-HF1, eSpCas9, HypaCas9)")
            strategies.append("Validate off-target effects with whole-genome sequencing")
        
        # Phenotype mitigation
        if phenotype_risk in ["CRITICAL", "HIGH"]:
            strategies.append("Start with conditional or inducible knockdown")
            strategies.append("Monitor phenotype progression carefully")
            strategies.append("Prepare rescue constructs for complementation studies")
        
        # Pleiotropy mitigation
        if primary_rec in [RecommendationType.CRISPRI, RecommendationType.HETEROZYGOUS_KO]:
            strategies.append("Use partial knockdown to study dose-dependent effects")
            strategies.append("Compare results with RNAi data if available")
        
        # Compensatory mechanism mitigation
        if compensatory_mechanisms:
            strategies.append("Consider double-knockout with paralog genes")
            strategies.append("Use time-course experiments to detect delayed compensation")
        
        # General strategies
        if safety_level in [SafetyLevel.HIGH_CONCERN, SafetyLevel.AVOID]:
            strategies.append("Phenotype Analysis of Stems cells & CRISPR-engineered (PASC) approach")
            strategies.append("Phenotype Suppression Screening to identify genetic interactors")
        
        return strategies if strategies else ["Standard validation sufficient"]
    
    def _suggest_experimental_considerations(
        self,
        phenotype_severity: Optional[str],
        lethality_stage: Optional[str],
        off_target_analysis: Dict,
        primary_rec: RecommendationType
    ) -> List[str]:
        """Suggest experimental design considerations."""
        considerations = []
        
        # Lethality stage considerations
        if lethality_stage:
            considerations.append(f"Plan for {lethality_stage.lower()} lethality - harvest samples before expected lethality")
        
        if phenotype_severity == "LETHAL":
            considerations.append("Use heterozygous crosses to maintain line")
            considerations.append("Consider inducible systems for temporal control")
        
        # Off-target considerations
        if off_target_analysis.get("guides_with_severe_off_targets", 0) > 0:
            considerations.append("Use multiple independent gRNAs to confirm on-target effects")
            considerations.append("Include rescue experiments with cDNA")
        
        # Method-specific considerations
        if primary_rec == RecommendationType.CRISPRI:
            considerations.append("Optimize dCas9-KRAB expression levels")
            considerations.append("Verify knockdown efficiency at mRNA and protein levels")
        
        if primary_rec == RecommendationType.CONDITIONAL_KO:
            considerations.append("Verify Cre recombinase efficiency")
            considerations.append("Include littermate controls")
        
        if primary_rec == RecommendationType.HETEROZYGOUS_KO:
            considerations.append("Genotype all offspring carefully")
            considerations.append("Compare heterozygous vs homozygous phenotypes")
        
        # General considerations
        considerations.append("Include appropriate controls (non-targeting gRNA, wild-type)")
        considerations.append("Plan for phenotypic scoring at multiple developmental stages")
        
        return considerations
    
    def _calculate_confidence(
        self,
        phenotype_confidence: float,
        literature_support: Optional[float],
        has_guides: bool,
        has_validation: bool
    ) -> float:
        """Calculate overall confidence in the recommendation."""
        scores = [phenotype_confidence]
        
        if literature_support:
            scores.append(literature_support)
        
        if has_guides:
            scores.append(0.8)  # Having guides adds confidence
        
        if has_validation:
            scores.append(0.7)  # Cross-species validation adds confidence
        
        # Average with weighting
        return sum(scores) / len(scores) if scores else 0.5
    
    def generate_batch_recommendations(
        self,
        genes_data: List[Dict[str, Any]]
    ) -> List[SafetyRecommendation]:
        """
        Generate recommendations for multiple genes.
        
        Args:
            genes_data: List of gene data dictionaries
            
        Returns:
            List of SafetyRecommendation objects
        """
        recommendations = []
        
        for gene_data in genes_data:
            try:
                rec = self.generate_recommendation(
                    gene_symbol=gene_data.get("symbol", "unknown"),
                    pleiotropy_score=gene_data.get("pleiotropy_score", 10),
                    phenotype_prediction=gene_data.get("phenotype_prediction"),
                    guides=gene_data.get("guides"),
                    cross_species_validation=gene_data.get("cross_species_validation"),
                    literature_support=gene_data.get("literature_support")
                )
                recommendations.append(rec)
            except Exception as e:
                logger.error(f"Failed to generate recommendation for {gene_data.get('symbol', 'unknown')}: {e}")
                continue
        
        return recommendations
    
    def format_recommendation_text(self, recommendation: SafetyRecommendation) -> str:
        """Format recommendation as human-readable text."""
        lines = [
            f"Safety Recommendation for {recommendation.gene_symbol}",
            f"{'=' * 60}",
            f"Safety Level: {recommendation.safety_level.value}",
            f"Primary Recommendation: {recommendation.primary_recommendation.value}",
            f"Confidence Score: {recommendation.confidence_score:.2f}",
            f"",
            f"Justification:",
        ]
        
        for i, just in enumerate(recommendation.justification, 1):
            lines.append(f"  {i}. {just}")
        
        lines.extend([
            f"",
            f"Concerns:",
        ])
        
        for concern in recommendation.concerns:
            lines.append(f"  - {concern}")
        
        if recommendation.alternative_recommendations:
            lines.extend([
                f"",
                f"Alternative Strategies:",
            ])
            for alt in recommendation.alternative_recommendations:
                lines.append(f"  - {alt.value}")
        
        lines.extend([
            f"",
            f"Mitigation Strategies:",
        ])
        
        for strategy in recommendation.mitigation_strategies:
            lines.append(f"  - {strategy}")
        
        lines.extend([
            f"",
            f"Experimental Considerations:",
        ])
        
        for consideration in recommendation.experimental_considerations:
            lines.append(f"  - {consideration}")
        
        return "\n".join(lines)


# Convenience function for easy access
def get_safety_recommendation(
    gene_symbol: str,
    pleiotropy_score: float,
    phenotype_prediction: Optional[Dict] = None,
    guides: Optional[List[Dict]] = None,
    cross_species_validation: Optional[Dict] = None,
    literature_support: Optional[float] = None
) -> SafetyRecommendation:
    """Get safety recommendation for a single gene."""
    recommender = SafetyRecommender()
    return recommender.generate_recommendation(
        gene_symbol=gene_symbol,
        pleiotropy_score=pleiotropy_score,
        phenotype_prediction=phenotype_prediction,
        guides=guides,
        cross_species_validation=cross_species_validation,
        literature_support=literature_support
    )
