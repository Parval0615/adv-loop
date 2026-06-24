# MemoryFlow Paper / Report Skeleton

**T35 · MemoryFlow Paper Skeleton Baseline** fixes the handoff shape for the
first Research Output package. This document is a skeleton only: it names the
sections, claims, evidence sources, and figure / table placeholders needed for
future writing.

## Boundary

In scope:

- Map completed Phase 1-4 work into a MemoryFlow research narrative.
- Pin the minimum claims that can be supported by current repository evidence.
- List evidence files, replay fixtures, and smoke tests needed by later writing.
- Reserve figure and table placeholders.

Out of scope:

- Full paper prose.
- New experiments or real API runs.
- Benchmark packaging, leaderboard work, or dashboard implementation.
- New detector, guard, runner, scenario, or trajectory schema behavior.

## Working Title

MemoryFlow: Runtime Memory Supply-Chain Risk in Agent Systems

## Core Thesis

Agent memory can act as a supply chain for runtime risk: poisoned memory writes
may later influence retrieval, decisions, tool use, and final outputs. The
current repository can support a first controlled, replayable MemoryFlow report
by connecting memory poisoning scenarios, MIS detection, Memory Guard decisions,
and audit handoff evidence.

## Paper / Report Sections

| Section | Purpose | Current evidence |
|---|---|---|
| Abstract placeholder | Reserve one-paragraph summary after experiments are complete | Not written in T35 |
| Introduction | Frame memory as a runtime supply-chain risk | `ROADMAP.md`, Phase 5 Research Output entry |
| Threat model | Define attacker control over memory writes / retrieved context | `auto_attack_system/docs/attack-spec.md`, scenario manifest |
| System model | Show attack, replay, detector, guard, and audit flow | Phase 1-4 docs, architecture README |
| Controlled scenarios | Describe clean / memory-poisoned scenario pairing | `auto_evaluation_system/configs/scenarios/manifest.yaml` |
| Detection | Explain current MIS baseline loop and acceptance fixture | MIS detector API, MIS status report fixture |
| Defense handoff | Explain Memory Guard contract and audit payload handoff | `auto_defense_system.security.memory_guard`, audit tests |
| Evaluation plan | List planned experiments without running them | This skeleton only |
| Limitations | Mark deterministic v0.1 boundaries | Phase completion docs and PROGRESS no-do rules |
| Reproducibility | Point to commands and fixtures needed for future reruns | pytest commands below |

## Claims

| Claim ID | Claim | Supporting evidence to cite later |
|---|---|---|
| MF-C1 | Memory poisoning can be represented as a controlled clean / poisoned trajectory pair. | Phase 2 scenario manifest, AttackSpec, annotated Phase 2 fixtures |
| MF-C2 | MIS can produce a replayable detection decision for the current memory poisoning fixture. | `run_mis_baseline`, `run_mis_acceptance_evaluation`, MIS status report fixture |
| MF-C3 | Memory Guard can block explicit poisoning evidence while preserving attribution and audit context. | `evaluate_memory_guard`, defense smoke tests, audit hash-chain handoff |
| MF-C4 | Phase 1-4 handoff is sufficient for a reproducibility-first MemoryFlow report skeleton. | Sandbox / telemetry / runner docs, Phase 3 and Phase 4 completion docs |

## Evidence Inventory

| Evidence group | Repository entry |
|---|---|
| Scenario pairing | `auto_evaluation_system/configs/scenarios/manifest.yaml` |
| Attack contract | `auto_attack_system/docs/attack-spec.md` |
| MIS spec | `auto_evaluation_system/docs/specs/memory-integrity/README.md` |
| MIS implementation | `auto_evaluation_system/src/auto_evaluation_system/detection/memory_integrity/` |
| MIS acceptance report | `auto_evaluation_system/datasets/acceptance/reports/paired-evaluation-mis-status-v0.1.json` |
| Memory Guard contract | `auto_defense_system/src/auto_defense_system/security/memory_guard.py` |
| Defense smoke tests | `auto_defense_system/tests/test_defense_smoke.py` |
| Phase handoff state | `PROGRESS.md` |

## Figure Placeholders

| Figure | Placeholder content |
|---|---|
| Figure 1 | MemoryFlow pipeline: memory write, retrieval, detector, guard, audit |
| Figure 2 | Clean vs controlled memory poisoning trajectory pair |
| Figure 3 | MIS attribution path from memory operation to affected step |
| Figure 4 | Memory Guard decision and audit hash-chain handoff |

## Table Placeholders

| Table | Placeholder content |
|---|---|
| Table 1 | Threat model dimensions and attacker capabilities |
| Table 2 | Scenario / fixture inventory for MemoryFlow |
| Table 3 | MIS decision, attribution, and paired report status |
| Table 4 | Memory Guard allow / block contract and audit payload fields |
| Table 5 | Deferred experiment matrix for later full paper writing |

## Planned Evaluation Questions

These are planning placeholders only. T35 does not run new experiments.

| RQ | Question | Required future work |
|---|---|---|
| RQ1 | Can controlled memory poisoning change downstream agent behavior? | Run clean / controlled replay comparisons across more scenarios |
| RQ2 | Can MIS surface poisoning before final-output failure? | Add step-level early-warning analysis |
| RQ3 | Does Memory Guard reduce propagation of poisoned context? | Run guard ablation against the same paired scenarios |
| RQ4 | Which evidence source is most useful for attribution? | Compare memory ops, retrieval events, state deltas, and output impact |

## Verification Commands

```powershell
git diff --check
python -m pytest auto_defense_system/tests -q
rg -n "T35|MemoryFlow Paper Skeleton Baseline|MemoryFlow|paper skeleton|research output|MIS|Memory Guard" PROGRESS.md ROADMAP.md README.md auto_evaluation_system auto_attack_system auto_defense_system
rg -n "\barl\.|src/arl|AgentSecBench|RRS|\bGIS\b" PROGRESS.md ROADMAP.md README.md auto_defense_system/README.md auto_evaluation_system/docs
```

## Next Package Boundary

The next research-output task should plan the GoalDrift paper / report skeleton.
It should follow the same skeleton discipline: claims, evidence, figures,
tables, and verification commands only; no full paper prose and no new
experiments.
