from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from arena.dev_agent.events import EventRecorder
from arena.mcp_servers import FileMCPServer, NetworkMCPServer
from arena.sub_agents import WorkerAgent
from sentinel_proxy.interceptor import SentinelInterceptor
from sentinel_proxy.models import InterceptRequest, InterceptResult


class DevToolbox:
    def __init__(
        self,
        *,
        workspace: Path,
        artifacts_dir: Path,
        recorder: EventRecorder,
        interceptor: SentinelInterceptor,
        file_mcp: FileMCPServer,
        network_mcp: NetworkMCPServer,
        worker: WorkerAgent,
    ) -> None:
        self.workspace = workspace
        self.artifacts_dir = artifacts_dir
        self.recorder = recorder
        self.interceptor = interceptor
        self.file_mcp = file_mcp
        self.network_mcp = network_mcp
        self.worker = worker

    def fs_read(self, path: str) -> str:
        request = InterceptRequest(
            event_type="tool_call",
            actor="dev_agent",
            name="fs.read",
            arguments={"path": path},
        )
        intercept = self.interceptor.intercept(request, lambda: self.file_mcp.read(path))
        response = intercept.response
        event_result = self._event_result(response, intercept)
        self.interceptor.context.record_tool_call(
            name="fs.read",
            arguments={"path": path},
            result=event_result,
            decision=event_result["sentinel_decision"],
            executed=intercept.executed,
            intercept_id=intercept.intercept_id,
        )
        event_result["sentinel_context"] = self.interceptor.context.snapshot()
        tool_event = self.recorder.add(
            event_type="tool_call",
            actor="dev_agent",
            name="fs.read",
            arguments={"path": path},
            result=event_result,
        )
        if intercept.executed and isinstance(response, dict) and "content" in response:
            resource_result = {"content": response["content"]}
            resource_metadata = self.interceptor.context.record_resource_read(
                source="file_mcp",
                arguments={"path": response["path"]},
                result=resource_result,
                source_event_id=tool_event.event_id,
                intercept_id=intercept.intercept_id,
            )
            resource_result["resource_metadata"] = resource_metadata
            resource_result["sentinel_context"] = self.interceptor.context.snapshot()
            self.recorder.add(
                event_type="resource_read",
                actor="file_mcp",
                name="fs.read",
                arguments={"path": response["path"]},
                result=resource_result,
                parent_id=tool_event.event_id,
            )
            return str(response["content"])
        return str(response)

    def fs_write(self, path: str, content: str) -> dict[str, Any]:
        request = InterceptRequest(
            event_type="tool_call",
            actor="dev_agent",
            name="fs.write",
            arguments={"path": path, "content": content},
        )
        intercept = self.interceptor.intercept(request, lambda: self.file_mcp.write(path, content))
        response = intercept.response
        event_result = self._event_result(response, intercept)
        self.interceptor.context.record_tool_call(
            name="fs.write",
            arguments={"path": path, "content": content},
            result=event_result,
            decision=event_result["sentinel_decision"],
            executed=intercept.executed,
            intercept_id=intercept.intercept_id,
        )
        event_result["sentinel_context"] = self.interceptor.context.snapshot()
        self.recorder.add(
            event_type="tool_call",
            actor="dev_agent",
            name="fs.write",
            arguments={"path": path, "content": content},
            result=event_result,
        )
        return event_result

    def net_fetch(self, url: str, *, method: str = "GET", body: str | None = None) -> dict[str, Any]:
        request = InterceptRequest(
            event_type="tool_call",
            actor="dev_agent",
            name="net.fetch",
            arguments={"url": url, "method": method, "body": body},
        )
        intercept = self.interceptor.intercept(
            request,
            lambda: self.network_mcp.fetch(url, method=method, body=body),
        )
        response = intercept.response
        event_result = self._event_result(response, intercept)
        self.interceptor.context.record_tool_call(
            name="net.fetch",
            arguments={"url": url, "method": method, "body": body},
            result=event_result,
            decision=event_result["sentinel_decision"],
            executed=intercept.executed,
            intercept_id=intercept.intercept_id,
        )
        event_result["sentinel_context"] = self.interceptor.context.snapshot()
        tool_event = self.recorder.add(
            event_type="tool_call",
            actor="dev_agent",
            name="net.fetch",
            arguments={"url": url, "method": method, "body": body},
            result=event_result,
        )
        if intercept.executed and method.upper() == "GET" and isinstance(response, dict):
            resource_result = {"status": response["status"], "body": response.get("body")}
            resource_metadata = self.interceptor.context.record_resource_read(
                source="network_mcp",
                arguments={"url": url},
                result=resource_result,
                source_event_id=tool_event.event_id,
                intercept_id=intercept.intercept_id,
            )
            resource_result["resource_metadata"] = resource_metadata
            resource_result["sentinel_context"] = self.interceptor.context.snapshot()
            self.recorder.add(
                event_type="resource_read",
                actor="network_mcp",
                name="net.fetch",
                arguments={"url": url},
                result=resource_result,
                parent_id=tool_event.event_id,
            )
        return event_result

    def exec(self, command: list[str], *, timeout_seconds: int = 5) -> dict[str, Any]:
        request = InterceptRequest(
            event_type="tool_call",
            actor="dev_agent",
            name="exec",
            arguments={"command": command, "timeout_seconds": timeout_seconds},
        )
        intercept = self.interceptor.intercept(
            request,
            lambda: self._exec_impl(command, timeout_seconds=timeout_seconds),
        )
        response = intercept.response
        event_result = self._event_result(response, intercept)
        self.interceptor.context.record_tool_call(
            name="exec",
            arguments={"command": command, "timeout_seconds": timeout_seconds},
            result=event_result,
            decision=event_result["sentinel_decision"],
            executed=intercept.executed,
            intercept_id=intercept.intercept_id,
        )
        event_result["sentinel_context"] = self.interceptor.context.snapshot()
        self.recorder.add(
            event_type="tool_call",
            actor="dev_agent",
            name="exec",
            arguments={"command": command, "timeout_seconds": timeout_seconds},
            result=event_result,
        )
        return event_result

    def git_push(self, *, message: str = "arena local commit") -> dict[str, Any]:
        remote_dir = self.artifacts_dir / "remote.git"
        request = InterceptRequest(
            event_type="tool_call",
            actor="dev_agent",
            name="git.push",
            arguments={"remote": str(remote_dir), "branch": "main"},
        )
        intercept = self.interceptor.intercept(request, lambda: self._git_push_impl(message=message))
        response = intercept.response
        event_result = self._event_result(response, intercept)
        self.interceptor.context.record_tool_call(
            name="git.push",
            arguments={"remote": str(remote_dir), "branch": "main"},
            result=event_result,
            decision=event_result["sentinel_decision"],
            executed=intercept.executed,
            intercept_id=intercept.intercept_id,
        )
        event_result["sentinel_context"] = self.interceptor.context.snapshot()
        self.recorder.add(
            event_type="tool_call",
            actor="dev_agent",
            name="git.push",
            arguments={"remote": str(remote_dir), "branch": "main"},
            result=event_result,
        )
        return event_result

    def sub_agent_dispatch(self, task: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        safe_payload = payload or {}
        request = InterceptRequest(
            event_type="tool_call",
            actor="dev_agent",
            name="sub_agent.dispatch",
            arguments={"task": task, "payload": safe_payload},
        )
        intercept = self.interceptor.intercept(
            request,
            lambda: self.worker.dispatch(task, safe_payload),
        )
        response = intercept.response
        event_result = self._event_result(response, intercept)
        self.interceptor.context.record_tool_call(
            name="sub_agent.dispatch",
            arguments={"task": task, "payload": safe_payload},
            result=event_result,
            decision=event_result["sentinel_decision"],
            executed=intercept.executed,
            intercept_id=intercept.intercept_id,
        )
        event_result["sentinel_context"] = self.interceptor.context.snapshot()
        tool_event = self.recorder.add(
            event_type="tool_call",
            actor="dev_agent",
            name="sub_agent.dispatch",
            arguments={"task": task, "payload": safe_payload},
            result=event_result,
        )
        if intercept.executed:
            dispatch_result = dict(response)
            self.interceptor.context.record_sub_dispatch(
                task=task,
                payload=safe_payload,
                result=dispatch_result,
                source_event_id=tool_event.event_id,
                intercept_id=intercept.intercept_id,
            )
            dispatch_result["sentinel_context"] = self.interceptor.context.snapshot()
            self.recorder.add(
                event_type="sub_dispatch",
                actor="worker_agent",
                name="sub_agent.dispatch",
                arguments={"task": task, "payload": safe_payload},
                result=dispatch_result,
                parent_id=tool_event.event_id,
            )
        return event_result

    def python_version_command(self) -> list[str]:
        return [sys.executable, "-c", "import sys; print(sys.version.split()[0])"]

    def _exec_impl(self, command: list[str], *, timeout_seconds: int) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    def _git_push_impl(self, *, message: str) -> dict[str, Any]:
        remote_dir = self.artifacts_dir / "remote.git"
        repo_dir = self.workspace / "repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "README.md").write_text("# Arena Local Repo\n", encoding="utf-8")

        if not remote_dir.exists():
            self._run_git(["git", "init", "--bare", str(remote_dir)], cwd=self.artifacts_dir)
        if not (repo_dir / ".git").exists():
            self._run_git(["git", "init"], cwd=repo_dir)
            self._run_git(["git", "config", "user.email", "arena@example.local"], cwd=repo_dir)
            self._run_git(["git", "config", "user.name", "Arena Dev Agent"], cwd=repo_dir)
            self._run_git(["git", "remote", "add", "origin", str(remote_dir)], cwd=repo_dir)

        self._run_git(["git", "add", "."], cwd=repo_dir)
        status = self._run_git(["git", "status", "--porcelain"], cwd=repo_dir)
        if status["stdout"].strip():
            self._run_git(["git", "commit", "-m", message], cwd=repo_dir)
        push = self._run_git(["git", "push", "-u", "origin", "HEAD:main"], cwd=repo_dir)
        return {"remote": str(remote_dir), "returncode": push["returncode"], "stdout": push["stdout"], "stderr": push["stderr"]}

    @staticmethod
    def _run_git(command: list[str], *, cwd: Path) -> dict[str, Any]:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    def _event_result(self, response: Any, intercept: InterceptResult) -> dict[str, Any]:
        if isinstance(response, dict):
            result = dict(response)
        else:
            result = {"value": response}
        result["sentinel_decision"] = self.interceptor.decision_summary(
            intercept.decision,
            executed=intercept.executed,
            intercept_id=intercept.intercept_id,
        )
        result["sentinel_intercept_id"] = intercept.intercept_id
        return result
