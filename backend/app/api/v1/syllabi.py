import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.models.syllabus import Syllabus
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.syllabus import SyllabusListItem, SyllabusRead
from app.services.parsing import (
    DOCXSizeLimitExceededError,
    EmptyDOCXError,
    EmptyPDFError,
    ParsingError,
    PDFSizeLimitExceededError,
    UnsupportedFormatError,
    parse_document,
)

router = APIRouter(prefix="/syllabi", tags=["Syllabi"])

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "",
    response_model=SyllabusRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a syllabus file (PDF or DOCX)",
)
async def upload_syllabus(
    title: Annotated[str, Form(min_length=1, max_length=255)],
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    department: Annotated[str | None, Form(max_length=255)] = None,
) -> Syllabus:
    """Upload a PDF or DOCX syllabus document, validate and parse its contents,

    persist metadata and raw_text, and return the created record.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_mb} MB",
        )

    try:
        raw_text = parse_document(
            contents,
            filename=file.filename,
            content_type=file.content_type,
            clean=True,
            max_size=MAX_UPLOAD_SIZE_BYTES,
        )
    except (PDFSizeLimitExceededError, DOCXSizeLimitExceededError) as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except UnsupportedFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (EmptyPDFError, EmptyDOCXError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from document: {exc}",
        ) from exc

    syllabus = Syllabus(
        id=uuid.uuid4(),
        institution_id=current_user.institution_id,
        uploaded_by=current_user.id,
        title=title.strip(),
        department=department.strip() if department else None,
        filename=file.filename or "unknown",
        raw_text=raw_text,
        status="uploaded",
    )
    db.add(syllabus)
    await db.commit()
    await db.refresh(syllabus)

    return syllabus


@router.get(
    "",
    response_model=list[SyllabusListItem],
    summary="List syllabi scoped to institution",
)
async def list_syllabi(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    department: Annotated[str | None, Query()] = None,
) -> list[Syllabus]:
    """Retrieve syllabi belonging to the current user's institution.

    Admins/policymakers without an institution can view all institution records.
    """
    query = select(Syllabus)

    if current_user.institution_id is not None:
        query = query.where(Syllabus.institution_id == current_user.institution_id)
    elif current_user.role not in ("admin", "policymaker"):
        query = query.where(Syllabus.uploaded_by == current_user.id)

    if department:
        query = query.where(Syllabus.department == department)

    query = query.order_by(Syllabus.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/{syllabus_id}",
    response_model=SyllabusRead,
    summary="Get syllabus details by ID",
)
async def get_syllabus(
    syllabus_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Syllabus:
    """Retrieve full syllabus details including raw_text, scoped to user institution."""
    query = select(Syllabus).where(Syllabus.id == syllabus_id)
    result = await db.execute(query)
    syllabus = result.scalar_one_or_none()

    if not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found",
        )

    # Scoping check
    if current_user.institution_id is not None:
        if syllabus.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Syllabus not found",
            )
    elif current_user.role not in ("admin", "policymaker") and (
        syllabus.uploaded_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found",
        )

    return syllabus
