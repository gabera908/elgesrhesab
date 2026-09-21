"""واجهات المشاريع — إدارة مشاريع المؤسسة الممولة (مانح/منحة/برنامج/موازنة)."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models.account import CostCenter
from app.models.partner import Partner
from app.models.project import PROJECT_STATUSES, Project
from app.models.user import User

router = APIRouter(prefix="/api/projects", tags=["Projects"])

class ProjectBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=200)
    donor_id: Optional[uuid.UUID] = None
    grant_reference: Optional[str] = Field(None, max_length=100)
    program: Optional[str] = Field(None, max_length=200)
    status: str = "draft"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_total: Decimal = Decimal("0")
    currency: str = Field("EGP", max_length=10)
    manager: Optional[str] = Field(None, max_length=200)
    cost_center_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        s, e = self.start_date, self.end_date
        if s and e and e < s:
            raise ValueError("end_after_start")
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    donor_id: Optional[uuid.UUID] = None
    grant_reference: Optional[str] = Field(None, max_length=100)
    program: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_total: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=10)
    manager: Optional[str] = Field(None, max_length=200)
    cost_center_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectOut(ProjectBase):
    id: uuid.UUID
    is_active: bool
    donor_name: Optional[str] = None
    cost_center_name: Optional[str] = None

    class Config:
        from_attributes = True


PROJECT_LABELS = {
    "draft": "مسودة",
    "active": "نشط",
    "on_hold": "موقوف مؤقتاً",
    "completed": "مكتمل",
    "closed": "مقفل مالياً",
    "cancelled": "ملغي",
}


def _enrich(projects: List[Project], db: Session) -> List[ProjectOut]:
    """يرفق أسماء المانحين ومراكز التكلفة باستعلامين فقط (لا N+1)."""
    donor_ids = {p.donor_id for p in projects if p.donor_id}
    cc_ids = {p.cost_center_id for p in projects if p.cost_center_id}
    donors = (
        {d.id: d for d in db.scalars(select(Partner).where(Partner.id.in_(donor_ids))).all()}
        if donor_ids
        else {}
    )
    ccs = (
        {c.id: c for c in db.scalars(select(CostCenter).where(CostCenter.id.in_(cc_ids))).all()}
        if cc_ids
        else {}
    )
    out: List[ProjectOut] = []
    for p in projects:
        row = ProjectOut.model_validate(p)
        row.donor_name = donors[p.donor_id].name if p.donor_id in donors else None
        row.cost_center_name = ccs[p.cost_center_id].name if p.cost_center_id in ccs else None
        out.append(row)
    return out


def _check_refs(donor_id, cc_id, db: Session) -> None:
    if donor_id and db.get(Partner, donor_id) is None:
        raise HTTPException(status_code=404, detail="donor_not_found")
    if cc_id and db.get(CostCenter, cc_id) is None:
        raise HTTPException(status_code=404, detail="cc_not_found")


@router.get("", response_model=List[ProjectOut])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None,
    donor_id: Optional[uuid.UUID] = None,
    active_only: bool = True,
    search: Optional[str] = None,
):
    """قائمة المشاريع مع فلترة بالحالة والمانح والبحث."""
    stmt = select(Project).order_by(Project.code)
    if active_only:
        stmt = stmt.where(Project.is_active == True)  # noqa: E712
    if status_filter:
        if status_filter not in PROJECT_STATUSES:
            raise HTTPException(status_code=422, detail="bad_status")
        stmt = stmt.where(Project.status == status_filter)
    if donor_id:
        stmt = stmt.where(Project.donor_id == donor_id)
    if search:
        stmt = stmt.where(
            (Project.name.ilike(f"%{search}%")) | (Project.code.ilike(f"%{search}%"))
        )
    return _enrich(db.scalars(stmt).all(), db)


@router.get("/statuses")
async def get_statuses():
    """حالات المشروع المتاحة."""
    return [{"value": k, "label": v} for k, v in PROJECT_LABELS.items()]

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_permission("partners", "create")),
    db: Session = Depends(get_db),
):
    if payload.status not in PROJECT_STATUSES:
        raise HTTPException(status_code=422, detail="bad_status")
    if db.scalar(select(Project).where(Project.code == payload.code)):
        raise HTTPException(status_code=409, detail="code_exists")
    _check_refs(payload.donor_id, payload.cost_center_id, db)
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return _enrich([project], db)[0]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="not_found")
    return _enrich([project], db)[0]


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    current_user: User = Depends(require_permission("partners", "update")),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="not_found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in PROJECT_STATUSES:
        raise HTTPException(status_code=422, detail="bad_status")
    _check_refs(data.get("donor_id"), data.get("cost_center_id"), db)
    start = data.get("start_date", project.start_date)
    end = data.get("end_date", project.end_date)
    if start and end and end < start:
        raise HTTPException(status_code=422, detail="end_after_start")
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return _enrich([project], db)[0]


@router.post("/{project_id}/deactivate")
async def deactivate_project(
    project_id: uuid.UUID,
    current_user: User = Depends(require_permission("partners", "delete")),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="not_found")
    project.is_active = False
    db.commit()
    return {"message": "deactivated"}

