import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.project import TASK_STATUSES, TASK_TYPES, Project, WorkflowTask
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.services.email_service import send_rubric_request_email, send_survey_email
from app.services.role_access import is_system_admin

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _require_admin(user: User = Depends(get_current_user)) -> User:
    # This advisor-onboarding workflow engine isn't wired into the app's permission system (no "projects"
    # module exists in Admin > Roles) and isn't linked from the Sidebar nav -- it's unused, forgotten
    # functionality that one of its own task types (Fetch Advisor List) can turn into an open SSRF/email
    # relay for ANY logged-in account, vendor and engineer portals included. Until it has a real owner and
    # a real permission card, keep it admin-only rather than open to every authenticated role.
    if not is_system_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return user


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_out(t: WorkflowTask) -> TaskOut:
    return TaskOut.model_validate(t)


def _project_summary(tasks: list[WorkflowTask]) -> dict:
    counts = {s.lower(): 0 for s in TASK_STATUSES}
    counts["total"] = len(tasks)
    for t in tasks:
        key = t.status.lower()
        counts[key] = counts.get(key, 0) + 1
    return counts


def _get_tasks(db: Session, project_id: int) -> list[WorkflowTask]:
    return list(db.scalars(
        select(WorkflowTask)
        .where(WorkflowTask.project_id == project_id)
        .order_by(WorkflowTask.sequence)
    ))


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ProjectOut])
def list_projects(status: str | None = None, db: Session = Depends(get_db), _=Depends(_require_admin)):
    q = select(Project).order_by(Project.updated_at.desc())
    if status:
        q = q.where(Project.status == status)
    return list(db.scalars(q))


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(_require_admin)):
    project = Project(
        title=body.title,
        description=body.description,
        status=body.status,
        owner_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = _get_tasks(db, project_id)
    detail = ProjectDetail.model_validate(project)
    detail.tasks = [_task_out(t) for t in tasks]
    detail.summary = _project_summary(tasks)
    return detail


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db), _=Depends(_require_admin)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(project, field, val)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------

@router.post("/{project_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def add_task(project_id: int, body: TaskCreate, db: Session = Depends(get_db), _=Depends(_require_admin)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if body.task_type not in TASK_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid task_type. Choose from: {TASK_TYPES}")
    task = WorkflowTask(
        project_id=project_id,
        task_name=body.task_name,
        task_type=body.task_type,
        sequence=body.sequence,
        advisor_id=body.advisor_id,
        input_data=body.input_data,
        status="Pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_out(task)


@router.patch("/{project_id}/tasks/{task_id}", response_model=TaskOut)
def update_task(project_id: int, task_id: int, body: TaskUpdate, db: Session = Depends(get_db), _=Depends(_require_admin)):
    task = db.get(WorkflowTask, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(task, field, val)
    db.commit()
    db.refresh(task)
    return _task_out(task)


@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    task = db.get(WorkflowTask, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


@router.post("/{project_id}/tasks/{task_id}/reset", response_model=TaskOut)
def reset_task(project_id: int, task_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    task = db.get(WorkflowTask, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "Pending"
    task.output_data = None
    task.error_message = None
    task.started_at = None
    task.completed_at = None
    db.commit()
    db.refresh(task)
    return _task_out(task)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

@router.post("/{project_id}/run", response_model=dict)
def run_project(project_id: int, resume: bool = False, db: Session = Depends(get_db), _=Depends(_require_admin)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "Active"
    db.commit()

    tasks = _get_tasks(db, project_id)
    accumulated: dict = {}
    results = []

    for task in tasks:
        if resume and task.status in ("Completed", "Skipped"):
            if task.output_data:
                try:
                    accumulated.update(json.loads(task.output_data))
                except Exception:
                    pass
            results.append({"task_id": task.id, "task_name": task.task_name, "status": task.status})
            continue

        result = _execute_task(task, {**accumulated}, db)
        results.append(result)

        if result["status"] == "Completed" and task.output_data:
            try:
                accumulated.update(json.loads(task.output_data))
            except Exception:
                pass
        elif result["status"] == "Failed":
            return {"project_id": project_id, "status": "Failed", "failed_at": task.task_name, "tasks": results}

    project.status = "Completed"
    db.commit()
    return {"project_id": project_id, "status": "Completed", "tasks": results}


@router.post("/{project_id}/tasks/{task_id}/run", response_model=dict)
def run_task(project_id: int, task_id: int, input_override: dict | None = None, db: Session = Depends(get_db), _=Depends(_require_admin)):
    task = db.get(WorkflowTask, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    result = _execute_task(task, input_override or {}, db)
    return result


def _execute_task(task: WorkflowTask, extra_context: dict, db: Session) -> dict:
    stored_input = {}
    if task.input_data:
        try:
            stored_input = json.loads(task.input_data)
        except Exception:
            pass

    context = {**stored_input, **extra_context}

    task.status = "Running"
    task.started_at = _now()
    task.error_message = None
    db.commit()

    try:
        output = _run_handler(task, context)
        task.status = "Completed"
        task.output_data = json.dumps(output, default=str)
        task.completed_at = _now()
        db.commit()
        return {"task_id": task.id, "task_name": task.task_name, "status": "Completed", "output": output}
    except Exception as e:
        task.status = "Failed"
        task.error_message = str(e)
        task.completed_at = _now()
        db.commit()
        return {"task_id": task.id, "task_name": task.task_name, "status": "Failed", "error": str(e)}


def _reject_internal_targets(url: str) -> None:
    """SSRF guard for the one task type that makes the server fetch an arbitrary caller-supplied URL.
    Blocks anything that isn't a plain public http(s) host: the scheme, and every IP that hostname
    resolves to (not just the literal string, so "localhost" or a DNS-rebinding hostname can't sneak
    past a string check)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("api_url must be a plain http(s) URL")
    try:
        resolved = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, None)}
    except OSError as exc:
        raise ValueError(f"Could not resolve api_url host: {exc}") from exc
    for addr in resolved:
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError("api_url may not point at an internal or reserved address")


def _run_handler(task: WorkflowTask, ctx: dict) -> dict:
    t = task.task_type

    if t == "Add Advisor":
        advisor_id = task.advisor_id or ctx.get("advisor_id")
        if not advisor_id:
            raise ValueError("advisor_id is required for Add Advisor task")
        return {"advisor_id": advisor_id, "advisor_name": ctx.get("advisor_name", ""), "added": True}

    if t == "Fetch Advisor List":
        api_url = ctx.get("api_url")
        if not api_url:
            raise ValueError("api_url is required in input_data for Fetch Advisor List task")
        _reject_internal_targets(api_url)
        query = ctx.get("query", {})
        if query:
            api_url = api_url + "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "application/json"}
        if ctx.get("api_key"):
            headers["Authorization"] = f"Bearer {ctx['api_key']}"
        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ValueError(f"Advisor API returned HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise ValueError(f"Advisor API request failed: {e.reason}") from e
        advisors = data if isinstance(data, list) else data.get("advisors", data.get("results", []))
        return {"advisors": advisors, "total": len(advisors)}

    if t == "Send Rubric Request":
        advisor_id = task.advisor_id or ctx.get("advisor_id")
        advisor_email = ctx.get("advisor_email")
        if not advisor_id:
            raise ValueError("advisor_id is required")
        if not advisor_email:
            raise ValueError("advisor_email is required in input_data")
        send_rubric_request_email(
            to=advisor_email,
            advisor_name=ctx.get("advisor_name"),
            rubric_link=ctx.get("rubric_link") or ctx.get("link"),
            instructions=ctx.get("instructions") or ctx.get("message"),
        )
        return {"advisor_id": advisor_id, "advisor_email": advisor_email,
                "rubric_request_sent": True, "sent_at": _now(), "channel": "email"}

    if t == "Rubric Validation":
        advisor_id = task.advisor_id or ctx.get("advisor_id")
        rubric_response = ctx.get("rubric_response", {})
        required_fields = ctx.get("required_fields", [])
        missing = [f for f in required_fields if not rubric_response.get(f)]
        return {"advisor_id": advisor_id, "valid": len(missing) == 0,
                "missing_fields": missing, "rubric_response": rubric_response, "validated_at": _now()}

    if t == "Send Survey":
        advisor_id = task.advisor_id or ctx.get("advisor_id")
        advisor_email = ctx.get("advisor_email")
        if not advisor_id:
            raise ValueError("advisor_id is required")
        if not advisor_email:
            raise ValueError("advisor_email is required in input_data")
        send_survey_email(
            to=advisor_email,
            advisor_name=ctx.get("advisor_name"),
            survey_name=ctx.get("survey_name", "Advisor Survey"),
            survey_link=ctx.get("survey_link") or ctx.get("link"),
        )
        return {"advisor_id": advisor_id, "advisor_email": advisor_email,
                "survey_name": ctx.get("survey_name", "Advisor Survey"),
                "survey_sent": True, "sent_at": _now(), "channel": "email"}

    if t == "Gather Responses":
        responses = ctx.get("responses", [])
        return {"total_responses": len(responses), "responses": responses, "gathered_at": _now()}

    raise ValueError(f"Unknown task type: {t}")
