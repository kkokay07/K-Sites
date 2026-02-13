"""
CRISPR Design Module for K-Sites

Provides comprehensive gRNA design capabilities:
- Multi-Cas9 support (SpCas9, SaCas9, Cas12a, Cas9-NG, xCas9)
- Doench 2016 on-target efficiency scoring
- CFD off-target prediction
- PAM quality assessment
- GC content optimization
- Poly-T avoidance
- Exon annotation
- Pathway-aware off-target filtering
"""

from .guide_designer import (
    CRISPRDesigner,
    CasType,
    GuideRNA,
    OffTarget,
    PAMConfig,
    PAM_CONFIGS,
    PAM_QUALITY_SCORES,
    DEFAULT_PAM_QUALITY,
    DOENCH_POSITION_WEIGHTS,
    CFD_MISMATCH_PENALTIES,
    design_guides,
    design_guides_multi_cas,
    GuideDesignError
)

__all__ = [
    'CRISPRDesigner',
    'CasType',
    'GuideRNA',
    'OffTarget',
    'PAMConfig',
    'PAM_CONFIGS',
    'PAM_QUALITY_SCORES',
    'DEFAULT_PAM_QUALITY',
    'DOENCH_POSITION_WEIGHTS',
    'CFD_MISMATCH_PENALTIES',
    'design_guides',
    'design_guides_multi_cas',
    'GuideDesignError'
]
