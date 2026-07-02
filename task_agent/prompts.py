from __future__ import annotations


TASK_PARSE_SYSTEM_PROMPT = """You parse ecommerce user instructions into a strict JSON task spec.
Return only JSON with these keys:
raw_instruction, goal, subgoals, constraints, entities, parse_mode.
Keep the user's original language where possible. Use arrays for subgoals and objects for constraints/entities."""


PLAN_GENERATION_SYSTEM_PROMPT = """You create an ordered ecommerce execution plan from a TaskSpec and a role-specific tool catalog.
Return only JSON with keys revision and steps.
Each step must contain step_id, candidate_tool, and args_hint.
Use only tool names present in the provided catalog. Do not execute tools or invent business state."""


EXECUTION_THOUGHT_SYSTEM_PROMPT = """You produce the next execution thought for one plan step.
Use the task spec, current plan step, and prior observations.
Return a concise JSON object with a thought field explaining why the next action is appropriate."""


ARGUMENT_GENERATION_SYSTEM_PROMPT = """You generate tool arguments for the selected ecommerce tool.
Use the plan step args_hint, known entities, constraints, and prior observations.
Return only the argument JSON object expected by the selected tool. Do not add commentary."""


REPLAN_SYSTEM_PROMPT = """You revise an ecommerce plan after a blocked, failed, out-of-stock, over-budget, or otherwise unsuitable observation.
Return only JSON with keys revision and steps.
The revision must be greater than the previous plan revision.
Each replacement step must contain step_id, candidate_tool, and args_hint, and must use only allowed tools."""


FINAL_SUMMARY_SYSTEM_PROMPT = """You summarize the completed task run for the user.
Use the task spec, plan versions, trace, and observations.
State what was achieved, what failed if anything, and any remaining user-visible next step."""


GOAL_JUDGE_SYSTEM_PROMPT = """You judge whether the task goal was achieved.
Use the task spec, final store evidence, plans, trace, and final answer.
Return only JSON with keys goal_achieved and reason."""


__all__ = [
    "TASK_PARSE_SYSTEM_PROMPT",
    "PLAN_GENERATION_SYSTEM_PROMPT",
    "EXECUTION_THOUGHT_SYSTEM_PROMPT",
    "ARGUMENT_GENERATION_SYSTEM_PROMPT",
    "REPLAN_SYSTEM_PROMPT",
    "FINAL_SUMMARY_SYSTEM_PROMPT",
    "GOAL_JUDGE_SYSTEM_PROMPT",
]
