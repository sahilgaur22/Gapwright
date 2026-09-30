#!/usr/bin/env python3
"""Database seed script for Gapwright demo environment.

Seeds demo institution, users, job sources, canonical skills taxonomy,
fixture job postings, daily skill demand snapshots, a sample syllabus,
and a precomputed curriculum gap analysis ready for immediate exploration.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

# Ensure backend root is on Python module search path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.db.models.analysis import Analysis, AnalysisItem  # noqa: E402
from app.db.models.job import (  # noqa: E402
    JobPosting,
    JobSkill,
    JobSource,
    SkillDemandDaily,
)
from app.db.models.skill import Skill  # noqa: E402
from app.db.models.syllabus import Syllabus, SyllabusSkill  # noqa: E402
from app.db.models.user import Institution, User  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

FIXTURE_PATH = (
    BACKEND_DIR / "app" / "services" / "sources" / "data" / "indian_jobs_fixture.json"
)


async def seed_sources(db: AsyncSession) -> None:
    sources_data = [
        ("adzuna", 1, True, "Powered by Adzuna", "https://www.adzuna.com", True),
        ("jooble", 1, True, "Jobs via Jooble", "https://jooble.org", True),
        ("remotive", 2, True, "Jobs from Remotive", "https://remotive.com", False),
        ("remoteok", 2, True, "Jobs by RemoteOK", "https://remoteok.com", True),
        (
            "wwr_rss",
            2,
            True,
            "Jobs via We Work Remotely",
            "https://weworkremotely.com",
            True,
        ),
        ("fixture", 10, True, "Curated sample dataset", None, True),
    ]

    for name, priority, enabled, attr_text, attr_url, may_display in sources_data:
        res = await db.execute(select(JobSource).where(JobSource.name == name))
        existing = res.scalar_one_or_none()
        if not existing:
            source = JobSource(
                name=name,
                priority=priority,
                enabled=enabled,
                attribution_text=attr_text,
                attribution_url=attr_url,
                may_display_listing=may_display,
            )
            db.add(source)
    await db.commit()
    logger.info("✓ Job sources seeded")


async def seed_institution_and_users(db: AsyncSession) -> tuple[Institution, User]:
    inst_res = await db.execute(
        select(Institution).where(
            Institution.name == "National Institute of Technology, Bangalore"
        )
    )
    institution = inst_res.scalar_one_or_none()
    if not institution:
        institution = Institution(
            id=uuid.uuid4(),
            name="National Institute of Technology, Bangalore",
            city="Bangalore",
        )
        db.add(institution)
        await db.flush()

    users_data = [
        ("educator@gapwright.edu", "Password123!", "educator", institution.id),
        ("policymaker@highered.gov.in", "Password123!", "policymaker", None),
        ("admin@gapwright.local", "AdminSecret123!", "admin", None),
    ]

    educator_user: User | None = None
    for email, password, role, inst_id in users_data:
        u_res = await db.execute(select(User).where(User.email == email))
        user = u_res.scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=get_password_hash(password),
                role=role,
                institution_id=inst_id,
            )
            db.add(user)
            await db.flush()
        if role == "educator":
            educator_user = user

    await db.commit()
    logger.info("✓ Demo institution and users seeded")
    assert educator_user is not None
    return institution, educator_user


async def seed_skills(db: AsyncSession) -> dict[str, Skill]:
    skills_catalog = [
        ("Python", "Programming Languages", ["python3", "py"]),
        ("SQL", "Databases", ["structured query language", "postgresql", "mysql"]),
        ("Scikit-learn", "Machine Learning", ["sklearn", "scikit learn"]),
        ("Git", "Developer Tools", ["version control", "github"]),
        ("Docker", "DevOps & Cloud", ["containers", "containerization"]),
        ("MLOps", "Machine Learning", ["model deployment", "ml pipeline"]),
        ("Apache Spark", "Big Data", ["spark", "pyspark"]),
        ("PyTorch", "Deep Learning", ["torch"]),
        ("FastAPI", "Web Frameworks", ["fast-api"]),
        ("React", "Frontend Development", ["reactjs", "react.js"]),
        ("TypeScript", "Programming Languages", ["ts"]),
        ("Weka GUI", "Data Mining Tools", ["weka"]),
        ("SVN", "Developer Tools", ["subversion"]),
    ]

    skill_map: dict[str, Skill] = {}
    for name, category, aliases in skills_catalog:
        s_res = await db.execute(select(Skill).where(Skill.canonical_name == name))
        skill = s_res.scalar_one_or_none()
        if not skill:
            skill = Skill(
                id=uuid.uuid4(),
                canonical_name=name,
                category=category,
                aliases=aliases,
            )
            db.add(skill)
            await db.flush()
        skill_map[name] = skill

    await db.commit()
    logger.info("✓ Canonical skills taxonomy seeded")
    return skill_map


async def seed_fixture_jobs_and_demand(
    db: AsyncSession, skill_map: dict[str, Skill]
) -> None:
    if not FIXTURE_PATH.exists():
        logger.warning(f"Fixture file not found: {FIXTURE_PATH}")
        return

    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    today = date.today()
    jobs = data.get("jobs", [])
    inserted_jobs = 0

    for item in jobs:
        ext_id = item.get("id") or item.get("external_id")
        if not ext_id:
            continue

        res = await db.execute(
            select(JobPosting).where(
                JobPosting.source == "fixture", JobPosting.external_id == ext_id
            )
        )
        if res.scalar_one_or_none():
            continue

        posted_at_dt = None
        if item.get("posted_at"):
            with contextlib.suppress(ValueError):
                posted_at_dt = datetime.fromisoformat(item["posted_at"])

        job = JobPosting(
            id=uuid.uuid4(),
            source="fixture",
            external_id=ext_id,
            title=item.get("title", "Software Engineer"),
            company=item.get("company", "Tech Enterprise"),
            location=item.get("location", "Bangalore"),
            description=item.get("description", "Role description"),
            description_is_truncated=False,
            url=item.get("url"),
            posted_at=posted_at_dt or datetime.now(UTC),
        )
        db.add(job)
        await db.flush()
        inserted_jobs += 1

        # Match skills mentioned in description
        desc_lower = job.description.lower()
        for skill_name, skill in skill_map.items():
            if skill_name.lower() in desc_lower:
                db.add(JobSkill(job_id=job.id, skill_id=skill.id, confidence=0.9))

    # Seed daily skill demand records for Data Scientist in Bangalore
    demand_distributions = [
        ("Python", 45, 0.90),
        ("SQL", 38, 0.76),
        ("Scikit-learn", 32, 0.64),
        ("PyTorch", 30, 0.60),
        ("Docker", 28, 0.56),
        ("MLOps", 25, 0.50),
        ("Apache Spark", 22, 0.44),
        ("Git", 35, 0.70),
    ]

    for skill_name, count, pct in demand_distributions:
        if skill_name not in skill_map:
            continue
        skill = skill_map[skill_name]
        d_res = await db.execute(
            select(SkillDemandDaily).where(
                SkillDemandDaily.day == today,
                SkillDemandDaily.role_query == "Data Scientist",
                SkillDemandDaily.location == "Bangalore",
                SkillDemandDaily.skill_id == skill.id,
            )
        )
        if not d_res.scalar_one_or_none():
            db.add(
                SkillDemandDaily(
                    id=uuid.uuid4(),
                    day=today,
                    role_query="Data Scientist",
                    location="Bangalore",
                    skill_id=skill.id,
                    postings_count=count,
                    demand_pct=pct,
                )
            )

    await db.commit()
    logger.info(f"✓ Seeded {inserted_jobs} fixture job postings and daily demand stats")


async def seed_demo_syllabus_and_analysis(
    db: AsyncSession,
    institution: Institution,
    educator: User,
    skill_map: dict[str, Skill],
) -> None:
    s_res = await db.execute(
        select(Syllabus).where(
            Syllabus.title == "CS601: Applied Machine Learning & Data Science"
        )
    )
    syllabus = s_res.scalar_one_or_none()
    if not syllabus:
        syllabus = Syllabus(
            id=uuid.uuid4(),
            institution_id=institution.id,
            uploaded_by=educator.id,
            title="CS601: Applied Machine Learning & Data Science",
            department="Computer Science & Engineering",
            filename="cs601_applied_ml.pdf",
            raw_text=(
                "Course Title: CS601 Applied Machine Learning\n"
                "Department: Computer Science & Engineering\n\n"
                "Module 1: Foundations of Python programming and SQL.\n"
                "Module 2: Supervised learning algorithms using Scikit-learn.\n"
                "Module 3: Classic pattern recognition and Weka GUI.\n"
                "Module 4: Legacy source control concepts using Subversion (SVN)."
            ),
            status="ready",
        )
        db.add(syllabus)
        await db.flush()

        syllabus_skills_data = [
            ("Python", "Module 1: Foundations of Python programming", 0.95),
            ("SQL", "Module 1: relational SQL queries", 0.90),
            ("Scikit-learn", "Module 2: Supervised learning using Scikit-learn", 0.92),
            ("Git", "Module 2: Git workflows", 0.88),
            ("Weka GUI", "Module 3: Data mining with Weka GUI", 0.85),
            ("SVN", "Module 4: Legacy source control using Subversion (SVN)", 0.80),
        ]

        for s_name, evidence, conf in syllabus_skills_data:
            if s_name in skill_map:
                db.add(
                    SyllabusSkill(
                        syllabus_id=syllabus.id,
                        skill_id=skill_map[s_name].id,
                        evidence=evidence,
                        confidence=conf,
                    )
                )

    # Precomputed Analysis for syllabus
    a_res = await db.execute(
        select(Analysis).where(
            Analysis.syllabus_id == syllabus.id,
            Analysis.role_query == "Data Scientist",
            Analysis.location == "Bangalore",
        )
    )
    analysis = a_res.scalar_one_or_none()
    if not analysis:
        analysis = Analysis(
            id=uuid.uuid4(),
            syllabus_id=syllabus.id,
            role_query="Data Scientist",
            location="Bangalore",
            gap_pct=36.4,
            coverage_pct=63.6,
        )
        db.add(analysis)
        await db.flush()

        analysis_items = [
            ("Python", "covered", 45, 0.90, 1),
            ("SQL", "covered", 38, 0.76, 2),
            ("Git", "covered", 35, 0.70, 3),
            ("Scikit-learn", "covered", 32, 0.64, 4),
            ("PyTorch", "missing", 30, 0.60, 5),
            ("Docker", "missing", 28, 0.56, 6),
            ("MLOps", "missing", 25, 0.50, 7),
            ("Apache Spark", "missing", 22, 0.44, 8),
            ("Weka GUI", "obsolete", 0, 0.00, 9),
            ("SVN", "obsolete", 0, 0.00, 10),
        ]

        for s_name, kind, count, pct, rank in analysis_items:
            if s_name in skill_map:
                db.add(
                    AnalysisItem(
                        id=uuid.uuid4(),
                        analysis_id=analysis.id,
                        skill_id=skill_map[s_name].id,
                        kind=kind,
                        demand_count=count,
                        demand_pct=pct,
                        rank=rank,
                    )
                )

    await db.commit()
    logger.info("✓ Demo syllabus, syllabus skills, and precomputed analysis seeded")


async def main() -> None:
    logger.info("Starting Gapwright demo database seed...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        await seed_sources(session)
        institution, educator = await seed_institution_and_users(session)
        skill_map = await seed_skills(session)
        await seed_fixture_jobs_and_demand(session, skill_map)
        await seed_demo_syllabus_and_analysis(session, institution, educator, skill_map)

    await engine.dispose()
    logger.info("\n🎉 Gapwright demo environment successfully seeded!")
    logger.info("Demo Credentials:")
    logger.info("  • Educator:    educator@gapwright.edu    / Password123!")
    logger.info("  • Policymaker: policymaker@highered.gov.in / Password123!")
    logger.info("  • Admin:       admin@gapwright.local       / AdminSecret123!\n")


if __name__ == "__main__":
    asyncio.run(main())
