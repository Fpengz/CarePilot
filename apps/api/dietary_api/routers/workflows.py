from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import WorkflowListResponse, WorkflowResponse
from ..services.workflows import get_workflow, list_workflows

router = APIRouter(tags=["workflows"])


@router.get("/api/v1/workflows", response_model=WorkflowListResponse)
def workflows_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> WorkflowListResponse:
    require_action(session, "workflows.read")
    return list_workflows(context=get_context(request))


@router.get("/api/v1/workflows/{correlation_id}", response_model=WorkflowResponse)
def workflow_get(
    correlation_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> WorkflowResponse:
    require_action(session, "workflows.replay")
    return get_workflow(context=get_context(request), correlation_id=correlation_id)
