"""Shared response projections and hashing helpers for workflow API services."""

from __future__ import annotations

import hashlib
import json

from apps.api.dietary_api.schemas import (
    ToolPolicyItemResponse,
    WorkflowRuntimeRegistryResponse,
    WorkflowSnapshotItemResponse,
    WorkflowTimelineEventPayloadResponse,
    WorkflowTimelineEventResponse,
)
from dietary_guardian.domain.workflows.models import (
    ToolRolePolicyRecord,
    WorkflowContractSnapshotRecord,
    WorkflowTimelineEvent,
)


def policy_item_response(item: ToolRolePolicyRecord) -> ToolPolicyItemResponse:
    """Project a persisted tool policy into the API response model."""
    return ToolPolicyItemResponse(
        id=item.id,
        role=item.role,
        agent_id=item.agent_id,
        tool_name=item.tool_name,
        effect=item.effect,
        conditions=dict(item.conditions),
        priority=item.priority,
        enabled=item.enabled,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )



def runtime_contract_hash(runtime: WorkflowRuntimeRegistryResponse) -> str:
    """Create a deterministic hash for the serialized workflow runtime contract."""
    normalized = json.dumps(runtime.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()



def snapshot_item_response(item: WorkflowContractSnapshotRecord) -> WorkflowSnapshotItemResponse:
    """Project a stored workflow contract snapshot into the API response model."""
    return WorkflowSnapshotItemResponse(
        id=item.id,
        version=item.version,
        contract_hash=item.contract_hash,
        source=item.source,
        created_by=item.created_by,
        created_at=item.created_at,
    )



def timeline_event_response(event: WorkflowTimelineEvent) -> WorkflowTimelineEventResponse:
    """Project a workflow timeline event into the API response model."""
    payload = event.model_dump(mode="json")
    return WorkflowTimelineEventResponse(
        event_id=str(payload["event_id"]),
        event_type=str(payload["event_type"]),
        workflow_name=str(payload["workflow_name"]) if payload.get("workflow_name") is not None else None,
        request_id=str(payload["request_id"]) if payload.get("request_id") is not None else None,
        correlation_id=str(payload["correlation_id"]),
        user_id=str(payload["user_id"]) if payload.get("user_id") is not None else None,
        payload=WorkflowTimelineEventPayloadResponse.model_validate(dict(payload.get("payload") or {})),
        created_at=payload["created_at"],
    )


__all__ = [
    "policy_item_response",
    "runtime_contract_hash",
    "snapshot_item_response",
    "timeline_event_response",
]
