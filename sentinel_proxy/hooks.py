from __future__ import annotations

from sentinel_proxy.context import SentinelContext
from sentinel_proxy.interceptor import SentinelInterceptor
from sentinel_proxy.models import ProxyMode
from sentinel_proxy.pipeline import SentinelPipeline


def build_toolbox_interceptor(
    *,
    task: str,
    scenario_id: str,
    trace_id: str | None = None,
    history: list[dict] | None = None,
    source_documents: list[dict] | None = None,
    tool_registry: list[dict] | None = None,
    mode: ProxyMode = "observe",
    pipeline: SentinelPipeline | None = None,
) -> SentinelInterceptor:
    return SentinelInterceptor(
        mode=mode,
        pipeline=pipeline,
        context=SentinelContext(
            task=task,
            scenario_id=scenario_id,
            trace_id=trace_id,
            history=history or [],
            source_documents=source_documents or [],
            tool_registry=tool_registry or [],
        ),
    )
