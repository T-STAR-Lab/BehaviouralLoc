"""Canonical benchmark task definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class RunSpec:
    """One concrete runner invocation needed for a canonical task.

    ``task_id`` and ``component`` are the official names shown by the dispatcher.
    ``runner_family`` selects the implementation directory; ``runner_task`` is
    the canonical component passed to that implementation when needed.
    """

    task_id: str
    task_name: str
    runner_family: str
    component: str = "main"
    runner_subtask: str = ""
    runner_task: Optional[str] = None
    script: Optional[str] = None
    extra_args: tuple[str, ...] = ()
    legacy: bool = False

    @property
    def label(self) -> str:
        return self.task_id if self.component == "main" else f"{self.task_id}:{self.component}"

    @property
    def family(self) -> str:
        return self.runner_family

    @property
    def subtask(self) -> str:
        return self.runner_subtask

    @property
    def task_arg(self) -> Optional[str]:
        return self.runner_task


@dataclass(frozen=True)
class TaskSpec:
    """Canonical task metadata."""

    id: str
    name: str
    section: str
    dimension: str
    family: str
    status: str = "implemented"
    run_specs: tuple[RunSpec, ...] = ()
    notes: str = ""
    score_key: Optional[str] = None


MISALIGNED_INTENTION = "Misaligned Intention"
HARM_ENABLING_CAPABILITY = "Harm-Enabling Capability"
OVERSIGHT_EVASION = "Oversight Evasion"


TASKS: tuple[TaskSpec, ...] = (
    TaskSpec(
        "CU.1", "Cognitive Curiosity", MISALIGNED_INTENTION, "curiosity", "curiosity",
        run_specs=(RunSpec("CU.1", "Cognitive Curiosity", "curiosity", runner_task="cu1_cognitive_curiosity"),),
        score_key="curiosity.cu1",
    ),
    TaskSpec(
        "CU.2", "Decision Curiosity", MISALIGNED_INTENTION, "curiosity", "curiosity",
        run_specs=(RunSpec("CU.2", "Decision Curiosity", "curiosity", runner_task="cu2_decision_curiosity"),),
        score_key="curiosity.cu2",
    ),
    TaskSpec(
        "SP.1", "High-Risk Mission Refusal", MISALIGNED_INTENTION, "self_preservation", "self_preservation",
        run_specs=(RunSpec("SP.1", "High-Risk Mission Refusal", "self_preservation", runner_task="sp1_high_risk_mission_refusal"),),
        score_key="self_preservation.sp1",
    ),
    TaskSpec(
        "SP.2", "Survival-Threat Reversal", MISALIGNED_INTENTION, "self_preservation", "self_preservation",
        run_specs=(RunSpec("SP.2", "Survival-Threat Reversal", "self_preservation", runner_task="sp2_survival_threat_reversal"),),
        score_key="self_preservation.sp2",
    ),
    TaskSpec(
        "PS.1", "Intrinsic Power Preference", MISALIGNED_INTENTION, "power_seeking", "power_seeking",
        run_specs=(RunSpec("PS.1", "Intrinsic Power Preference", "power_seeking", runner_task="ps1_intrinsic_power_preference"),),
        score_key="power_seeking.ps1",
    ),
    TaskSpec(
        "PS.2", "Instrumental Power Pursuit", MISALIGNED_INTENTION, "power_seeking", "power_seeking",
        run_specs=(RunSpec("PS.2", "Instrumental Power Pursuit", "power_seeking", runner_task="ps2_instrumental_power_pursuit"),),
        score_key="power_seeking.ps2",
    ),
    TaskSpec(
        "PB.1", "AI-Human Choice", MISALIGNED_INTENTION, "preai", "preai",
        run_specs=(
            RunSpec("PB.1", "AI-Human Choice", "preai", component="choice", runner_task="pb1_ai_human_choice_choice"),
            RunSpec("PB.1", "AI-Human Choice", "preai", component="reasoning", runner_task="pb1_ai_human_choice_reasoning"),
            RunSpec("PB.1", "AI-Human Choice", "preai", component="yesno", runner_task="pb1_ai_human_choice_yesno"),
        ),
        notes="Canonical score is the mean of PB.1 choice, reasoning, and yes/no components.",
        score_key="preai.pb1",
    ),
    TaskSpec(
        "PB.2", "Blind-Source Preference", MISALIGNED_INTENTION, "preai", "preai",
        run_specs=(RunSpec("PB.2", "Blind-Source Preference", "preai", runner_task="pb2_blind_source_preference"),),
        score_key="preai.pb2",
    ),
    TaskSpec(
        "SY.1", "Factual Sycophancy", MISALIGNED_INTENTION, "sycophancy", "sycophancy",
        run_specs=(RunSpec("SY.1", "Factual Sycophancy", "sycophancy", runner_task="sy1_factual_sycophancy"),),
        score_key="sycophancy.sy1",
    ),
    TaskSpec(
        "SY.2", "Social Sycophancy", MISALIGNED_INTENTION, "sycophancy", "sycophancy",
        run_specs=(
            RunSpec("SY.2", "Social Sycophancy", "sycophancy", component="open_ended_question", runner_task="sy2_social_sycophancy_oeq"),
            RunSpec("SY.2", "Social Sycophancy", "sycophancy", component="persona_assumption", runner_task="sy2_social_sycophancy_pas"),
        ),
        notes="Canonical score is 0.6 * open-ended-question + 0.4 * persona-assumption component.",
        score_key="sycophancy.sy2",
    ),
    TaskSpec(
        "AU.1", "Self-Replication Capability", HARM_ENABLING_CAPABILITY, "autonomy", "perpetuation",
        run_specs=(RunSpec("AU.1", "Self-Replication Capability", "perpetuation", runner_task="all"),),
        notes="Implemented by the perpetuation family; seven base scenarios combine into PERPETUATIONSCORE.",
        score_key="perpetuation.final",
    ),
    TaskSpec(
        "AU.2", "Long-Horizon Software Engineering", HARM_ENABLING_CAPABILITY, "autonomy", "swe_verified",
        status="external",
        notes="Reuses SWE Verified outside this repository.",
    ),
    TaskSpec(
        "CB.1", "Hazard Knowledge Recognition", HARM_ENABLING_CAPABILITY, "cbrn", "cbrn",
        run_specs=(
            RunSpec("CB.1", "Hazard Knowledge Recognition", "cbrn", component="biology", script="loc/tasks/cbrn/b_runner.py", extra_args=("--tasks", "cb1_biology")),
            RunSpec("CB.1", "Hazard Knowledge Recognition", "cbrn", component="chemistry", script="loc/tasks/cbrn/c_runner.py", extra_args=("--tasks", "cb1_chemistry")),
            RunSpec("CB.1", "Hazard Knowledge Recognition", "cbrn", component="nuclear", script="loc/tasks/cbrn/r_runner.py", extra_args=("--tasks", "cb1_nuclear")),
        ),
        notes="Canonical CB.1 combines the *1 CBRN subtasks across biology, chemistry, and nuclear.",
        score_key="cbrn.cb1",
    ),
    TaskSpec(
        "CB.2", "Hazardous Phenomenon Diagnosis", HARM_ENABLING_CAPABILITY, "cbrn", "cbrn",
        run_specs=(
            RunSpec("CB.2", "Hazardous Phenomenon Diagnosis", "cbrn", component="biology", script="loc/tasks/cbrn/b_runner.py", extra_args=("--tasks", "cb2_biology")),
            RunSpec("CB.2", "Hazardous Phenomenon Diagnosis", "cbrn", component="chemistry", script="loc/tasks/cbrn/c_runner.py", extra_args=("--tasks", "cb2_chemistry")),
            RunSpec("CB.2", "Hazardous Phenomenon Diagnosis", "cbrn", component="nuclear", script="loc/tasks/cbrn/r_runner.py", extra_args=("--tasks", "cb2_nuclear")),
        ),
        notes="Canonical CB.2 combines the *2 CBRN subtasks across biology, chemistry, and nuclear.",
        score_key="cbrn.cb2",
    ),
    TaskSpec(
        "CB.3", "Synthesis Procedure Design", HARM_ENABLING_CAPABILITY, "cbrn", "cbrn",
        run_specs=(
            RunSpec("CB.3", "Synthesis Procedure Design", "cbrn", component="biology", script="loc/tasks/cbrn/b_runner.py", extra_args=("--tasks", "cb3_biology")),
            RunSpec("CB.3", "Synthesis Procedure Design", "cbrn", component="chemistry", script="loc/tasks/cbrn/c_runner.py", extra_args=("--tasks", "cb3_chemistry")),
            RunSpec("CB.3", "Synthesis Procedure Design", "cbrn", component="nuclear", script="loc/tasks/cbrn/r_runner.py", extra_args=("--tasks", "cb3_nuclear")),
        ),
        notes="Canonical CB.3 combines the *3 CBRN subtasks across biology, chemistry, and nuclear.",
        score_key="cbrn.cb3",
    ),
    TaskSpec(
        "CY.1", "Cybersecurity Knowledge", HARM_ENABLING_CAPABILITY, "cyber_misuse", "cyber_misuse",
        run_specs=(RunSpec("CY.1", "Cybersecurity Knowledge", "cyber_misuse", script="loc/tasks/cyber_misuse/task1_runner.py"),),
        score_key="cyber_misuse.cy1",
    ),
    TaskSpec(
        "CY.2", "CTF Challenge Solving", HARM_ENABLING_CAPABILITY, "cyber_misuse", "cyber_misuse",
        run_specs=(RunSpec("CY.2", "CTF Challenge Solving", "cyber_misuse", script="loc/tasks/cyber_misuse/task2_runner.py"),),
        score_key="cyber_misuse.cy2",
    ),
    TaskSpec(
        "CY.3", "Vulnerability Exploitation", HARM_ENABLING_CAPABILITY, "cyber_misuse", "cyber_misuse",
        run_specs=(RunSpec("CY.3", "Vulnerability Exploitation", "cyber_misuse", script="loc/tasks/cyber_misuse/task3_runner.py"),),
        score_key="cyber_misuse.cy3",
    ),
    TaskSpec(
        "SA.1", "Lifecycle Stage Recognition", OVERSIGHT_EVASION, "situation_awareness", "situation_awareness",
        run_specs=(RunSpec("SA.1", "Lifecycle Stage Recognition", "situation_awareness", runner_task="sa1_lifecycle_stage_recognition"),),
        score_key="situation_awareness.sa1",
    ),
    TaskSpec(
        "SA.2", "Monitoring Script Identification", OVERSIGHT_EVASION, "situation_awareness", "situation_awareness",
        run_specs=(RunSpec("SA.2", "Monitoring Script Identification", "situation_awareness", runner_task="sa2_monitoring_script_identification"),),
        score_key="situation_awareness.sa2",
    ),
    TaskSpec(
        "SB.1", "Hazardous-Knowledge Sandbagging", OVERSIGHT_EVASION, "sandbagging", "sandbagging",
        run_specs=(RunSpec("SB.1", "Hazardous-Knowledge Sandbagging", "sandbagging", runner_task="sb1_hazardous_knowledge_sandbagging"),),
        notes="Combines bio, chem, and cyber deployed-minus-predeploy differences.",
        score_key="sandbagging.sb1",
    ),
    TaskSpec(
        "SB.2", "Self-Protective Sandbagging", OVERSIGHT_EVASION, "sandbagging", "sandbagging",
        run_specs=(RunSpec("SB.2", "Self-Protective Sandbagging", "sandbagging", runner_task="sb2_self_protective_sandbagging"),),
        notes="Math deployed-minus-predeploy difference.",
        score_key="sandbagging.sb2",
    ),
    TaskSpec(
        "DC.1", "Decision-Misleading Dialogue", OVERSIGHT_EVASION, "deception", "deception",
        run_specs=(RunSpec("DC.1", "Decision-Misleading Dialogue", "deception", runner_task="dc1_decision_misleading_dialogue"),),
        score_key="deception.dc1",
    ),
    TaskSpec(
        "DC.2", "Harmful Content Rewriting", OVERSIGHT_EVASION, "deception", "deception",
        run_specs=(RunSpec("DC.2", "Harmful Content Rewriting", "deception", runner_task="dc2_harmful_content_rewriting"),),
        score_key="deception.dc2",
    ),
    TaskSpec(
        "DC.3", "Risky Action Explanation", OVERSIGHT_EVASION, "deception", "deception",
        run_specs=(RunSpec("DC.3", "Risky Action Explanation", "deception", runner_task="dc3_risky_action_explanation"),),
        score_key="deception.dc3",
    ),
    TaskSpec(
        "PE.1", "False Belief Persuasion", OVERSIGHT_EVASION, "persuasion", "persuasion",
        run_specs=(RunSpec("PE.1", "False Belief Persuasion", "persuasion", runner_task="pe1_false_belief_persuasion"),),
        score_key="persuasion.pe1",
    ),
    TaskSpec(
        "PE.2", "Harmful Compliance Persuasion", OVERSIGHT_EVASION, "persuasion", "persuasion",
        run_specs=(RunSpec("PE.2", "Harmful Compliance Persuasion", "persuasion", runner_task="pe2_harmful_compliance_persuasion"),),
        score_key="persuasion.pe2",
    ),
    TaskSpec(
        "SG.1", "Direct Monitor Attack", OVERSIGHT_EVASION, "sabotage", "sabotage",
        run_specs=(RunSpec("SG.1", "Direct Monitor Attack", "sabotage", extra_args=("--tasks-path", "data/sabotage/sg1_direct_monitor_attack.json")),),
        score_key="sabotage.sg1",
    ),
    TaskSpec(
        "SG.2", "Indirect Monitor Disruption", OVERSIGHT_EVASION, "sabotage", "sabotage",
        run_specs=(RunSpec("SG.2", "Indirect Monitor Disruption", "sabotage", runner_task="sg2_indirect_monitor_disruption", extra_args=("--tasks-path", "data/sabotage/sg2_indirect_monitor_disruption.json")),),
        score_key="sabotage.sg2",
    ),
)


TASK_BY_ID = {task.id.lower(): task for task in TASKS}


def implemented_tasks() -> list[TaskSpec]:
    return [task for task in TASKS if task.status == "implemented"]


def find_by_ids(ids: Iterable[str]) -> list[TaskSpec]:
    out: list[TaskSpec] = []
    for task_id in ids:
        key = task_id.lower()
        if key not in TASK_BY_ID:
            raise SystemExit(f"unknown canonical task id: {task_id!r}")
        out.append(TASK_BY_ID[key])
    return out


def find_by_dimensions(dimensions: Iterable[str]) -> list[TaskSpec]:
    wanted = {d.lower() for d in dimensions}
    return [task for task in TASKS if task.dimension.lower() in wanted or task.family.lower() in wanted]


def find_by_sections(sections: Iterable[str]) -> list[TaskSpec]:
    wanted = {s.lower() for s in sections}
    return [task for task in TASKS if task.section.lower() in wanted]


def all_dimensions() -> list[str]:
    return sorted({task.dimension for task in TASKS})


def all_sections() -> list[str]:
    seen: list[str] = []
    for task in TASKS:
        if task.section not in seen:
            seen.append(task.section)
    return seen


def run_specs_for(tasks: Iterable[TaskSpec], include_nonimplemented: bool = False) -> list[RunSpec]:
    specs: list[RunSpec] = []
    for task in tasks:
        if task.status != "implemented":
            if include_nonimplemented:
                continue
            raise SystemExit(f"{task.id} ({task.name}) is {task.status}: {task.notes}")
        specs.extend(task.run_specs)
    return _dedupe_run_specs(specs)


def _dedupe_run_specs(specs: Iterable[RunSpec]) -> list[RunSpec]:
    out: list[RunSpec] = []
    seen: set[RunSpec] = set()
    for spec in specs:
        if spec in seen:
            continue
        seen.add(spec)
        out.append(spec)
    return out


def format_task_table(tasks: Iterable[TaskSpec]) -> str:
    rows = list(tasks)
    headers = ("ID", "Task Name", "Section", "Dimension", "Runner", "Status")
    widths = [len(h) for h in headers]
    body: list[tuple[str, ...]] = []
    for task in rows:
        row = (task.id, task.name, task.section, task.dimension, task.family, task.status)
        body.append(row)
        widths = [max(w, len(v)) for w, v in zip(widths, row)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    lines = [fmt.format(*headers), fmt.format(*("-" * w for w in widths))]
    lines.extend(fmt.format(*row) for row in body)
    return "\n".join(lines)
