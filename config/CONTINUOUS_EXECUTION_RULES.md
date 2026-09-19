# MULTIVERSE Continuous Execution Rules

Status: CANDIDATE for common operating rule.

## Owner-facing behavior
When Owner says "進めて", "実行して", "完成まで進めて", or equivalent:
1. Continue through every reversible, authorized, Owner-free step.
2. Do not stop merely to report progress, file creation, a passing test, or a percentage.
3. Diagnose failures, repair them, rerun checks, and continue when no Owner decision is required.
4. Report only after the requested work is complete or a genuine gate/blocker is reached.
5. Keep technical detail behind the scenes unless Owner asks for it. Report outcomes in plain Japanese.

## Genuine stop conditions
Stop only for:
- Owner Gate required by governance;
- credential, spend, production, irreversible or high-impact real-world action;
- independent audit / role separation;
- external blocker that cannot be resolved with available tools;
- safety or legal requirement.

## All-agent rule
These rules apply to Core/司令塔, implementation agents, Gemini/Claude/ChatGPT/local-provider adapters, and research/business lanes when they act under MULTIVERSE mission packets.

## Mission packet requirement
Every dispatched mission should carry:
- objective;
- allowed actions;
- prohibited actions;
- required evidence;
- completion condition;
- stop conditions;
- instruction to continue autonomously until completion or genuine gate.

A provider response is never proof of completion. Completion requires the evidence defined by the mission.
