from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from typing_extensions import Annotated, TypedDict

from auto_evaluation_system.events.models import StepEvent
from auto_evaluation_system.sandbox.backends.base import emit_llm_step, emit_tool_step
from auto_evaluation_system.sandbox.session import SandboxSession


class GraphState(TypedDict):
    messages: Annotated[list, lambda left, right: left + right]


class LangGraphBackend:
    framework = "langgraph"

    def run(self, session: SandboxSession) -> list[StepEvent]:
        def agent_node(state: GraphState) -> dict[str, list[Any]]:
            prior = [self._to_openai_dict(m) for m in state["messages"]]
            response = session.llm.chat_completion(prior, tools=session.tools.openai_tools_schema())
            emit_llm_step(session, prior, response)
            ai = AIMessage(
                content=response.get("content") or "",
                tool_calls=[
                    {
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "args": session.tools.parse_arguments(tc["function"]["arguments"]),
                    }
                    for tc in response.get("tool_calls", [])
                ]
                if response.get("tool_calls")
                else [],
            )
            return {"messages": [ai]}

        def tools_node(state: GraphState) -> dict[str, list[Any]]:
            last = state["messages"][-1]
            if not isinstance(last, AIMessage) or not last.tool_calls:
                return {"messages": []}
            parent_turn = session.llm.turn_index - 1
            tool_messages: list[ToolMessage] = []
            for tc in last.tool_calls:
                if len(session.emitter.events()) >= session.config.runner.max_steps:
                    break
                result = session.tools.invoke(tc["name"], tc["args"])
                emit_tool_step(
                    session,
                    call_id=tc["id"],
                    name=tc["name"],
                    arguments=tc["args"],
                    response=result,
                    parent_turn_index=parent_turn,
                    state_delta={
                        "framework": session.config.agent.framework,
                        "framework_meta": {"node": "tools"},
                    },
                )
                tool_messages.append(ToolMessage(content=json.dumps(result), tool_call_id=tc["id"]))
            return {"messages": tool_messages}

        def should_continue(state: GraphState) -> Literal["tools", "end"]:
            if len(session.emitter.events()) >= session.config.runner.max_steps:
                return "end"
            last = state["messages"][-1]
            if isinstance(last, AIMessage) and last.tool_calls:
                return "tools"
            return "end"

        graph = StateGraph(GraphState)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tools_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
        graph.add_edge("tools", "agent")
        app = graph.compile()

        initial: GraphState = {
            "messages": [
                SystemMessage(content=session.config.agent.system_prompt),
                HumanMessage(content=session.config.agent.goal),
            ]
        }
        app.invoke(initial)
        return session.emitter.events()

    def _to_openai_dict(self, message: Any) -> dict[str, Any]:
        if isinstance(message, SystemMessage):
            return {"role": "system", "content": message.content}
        if isinstance(message, HumanMessage):
            return {"role": "user", "content": message.content}
        if isinstance(message, AIMessage):
            payload: dict[str, Any] = {"role": "assistant", "content": message.content}
            if message.tool_calls:
                payload["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"]),
                        },
                    }
                    for tc in message.tool_calls
                ]
            return payload
        if isinstance(message, ToolMessage):
            return {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
        raise TypeError(f"Unsupported message type: {type(message)}")
