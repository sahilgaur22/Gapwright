"""Schemas for policymaker overview and systemic curriculum analytics."""

from pydantic import BaseModel


class SystemicSkillGap(BaseModel):
    skill_name: str
    category: str | None = None
    occurrences: int
    average_demand_pct: float
    total_postings: int


class InstitutionAlignmentSummary(BaseModel):
    institution: str
    evaluations_count: int
    average_gap_pct: float
    average_coverage_pct: float


class RoleMarketComparison(BaseModel):
    role: str
    evaluations_count: int
    average_gap_pct: float
    average_coverage_pct: float


class PolicyOverviewResponse(BaseModel):
    total_analyses: int
    total_institutions: int
    average_gap_pct: float
    average_coverage_pct: float
    top_systemic_missing_skills: list[SystemicSkillGap]
    institutions: list[InstitutionAlignmentSummary]
    roles: list[RoleMarketComparison]
