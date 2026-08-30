"""ProductProblem / Evidence / ProductOpportunity 持久化。

决策：Phase 4/5 提供具体的 SQL 实现（不抽象接口），当前只有一套存储。
"""

from sqlalchemy import select

from app.models.evidence import EvidenceModel
from app.models.opportunity import ProductOpportunityModel
from app.models.problem import ProductProblemModel
from app.schemas.clustering import ClusteringResult
from app.schemas.enums import PrimaryCategory, ProblemStatus, Severity
from app.schemas.evidence import Evidence
from app.schemas.opportunity import ProductOpportunity
from app.schemas.problem import ProductProblem


def _problem_to_model(p: ProductProblem) -> ProductProblemModel:
    return ProductProblemModel(
        id=p.id,
        title=p.title,
        description=p.description,
        category=p.category.value if p.category else None,
        severity=p.severity.value if p.severity else None,
        affected_segments=p.affected_segments,
        confidence=p.confidence,
        cohesion_score=p.cohesion_score,
        status=p.status.value,
        needs_review=p.needs_review,
        evidence_count=p.evidence_count,
        priority_score=p.priority_score,
    )


def _problem_to_schema(m: ProductProblemModel) -> ProductProblem:
    return ProductProblem(
        id=m.id,
        title=m.title,
        description=m.description,
        category=PrimaryCategory(m.category) if m.category else None,
        severity=Severity(m.severity) if m.severity else None,
        affected_segments=m.affected_segments or [],
        confidence=m.confidence,
        cohesion_score=m.cohesion_score,
        status=ProblemStatus(m.status),
        needs_review=m.needs_review,
        evidence_count=m.evidence_count,
        priority_score=m.priority_score,
    )


def _evidence_to_model(e: Evidence) -> EvidenceModel:
    return EvidenceModel(
        id=e.id,
        product_problem_id=e.product_problem_id,
        feedback_item_id=e.feedback_item_id,
        analysis_id=e.analysis_id,
        relevance_score=e.relevance_score,
    )


def _evidence_to_schema(m: EvidenceModel) -> Evidence:
    return Evidence(
        id=m.id,
        product_problem_id=m.product_problem_id,
        feedback_item_id=m.feedback_item_id,
        analysis_id=m.analysis_id,
        relevance_score=m.relevance_score,
    )


def _opportunity_to_model(o: ProductOpportunity) -> ProductOpportunityModel:
    return ProductOpportunityModel(
        id=o.id,
        product_problem_id=o.product_problem_id,
        title=o.title,
        summary=o.summary,
        recommendation=o.recommendation,
        expected_impact=o.expected_impact,
        confidence=o.confidence,
        evidence_refs=o.evidence_refs,
    )


class SQLProblemRepository:
    """问题 / 证据 / 机会的 SQL 持久化。"""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save(self, result: ClusteringResult) -> None:
        if not result.problems:
            return
        with self._session_factory() as session:
            session.add_all([_problem_to_model(p) for p in result.problems])
            session.add_all([_evidence_to_model(e) for e in result.evidence])
            session.commit()

    def list_problems(self) -> list[ProductProblem]:
        with self._session_factory() as session:
            models = session.scalars(select(ProductProblemModel)).all()
            return [_problem_to_schema(m) for m in models]

    def list_evidence(self) -> list[Evidence]:
        with self._session_factory() as session:
            models = session.scalars(select(EvidenceModel)).all()
            return [_evidence_to_schema(m) for m in models]

    def update_priorities(self, problems: list[ProductProblem]) -> None:
        """把排序后的 priority_score / status 写回已有问题。"""
        with self._session_factory() as session:
            for p in problems:
                model = session.get(ProductProblemModel, p.id)
                if model is not None:
                    model.priority_score = p.priority_score
                    model.status = p.status.value
            session.commit()

    def save_opportunity(self, opportunity: ProductOpportunity) -> None:
        with self._session_factory() as session:
            session.add(_opportunity_to_model(opportunity))
            session.commit()
