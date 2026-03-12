from dataclasses import dataclass
from typing import Dict, Iterable, List

from core.llm_engine import AnalystRole


@dataclass(frozen=True)
class AgentExecutionPlan:
    ordered_roles: List[str]
    stage_by_role: Dict[str, str]
    ordered_stages: List[str]
    max_workers: int


def _priority(role_name: str) -> int:
    role_lower = role_name.lower()
    if "compliance" in role_lower:
        return 0
    if "finance" in role_lower or "financial" in role_lower:
        return 1
    if "legal" in role_lower:
        return 2
    if "operations" in role_lower:
        return 3
    return 4


def _stage_for_role(role_name: str, role: AnalystRole) -> str:
    role_lower = role_name.lower()
    if "compliance" in role_lower:
        return "Running Compliance Agent..."
    if "finance" in role_lower or "financial" in role_lower:
        return "Running Finance Agent..."
    if "legal" in role_lower:
        return "Running Legal Agent..."
    if "operations" in role_lower:
        return "Running Operations Agent..."
    return f"Running {role.title}..."


def _normalize_contract_type(contract_type: str) -> str:
    value = (contract_type or "").strip().lower()
    return value.replace("-", " ").replace("/", " ")


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _select_role_names(
    available_roles: Dict[str, AnalystRole],
    contract_text: str,
    contract_type: str,
    risk_sensitivity: str,
) -> List[str]:
    role_names = list(available_roles.keys())
    if not role_names:
        return []

    by_priority = sorted(role_names, key=_priority)
    selected = set()
    text = (contract_text or "").lower()
    contract_hint = _normalize_contract_type(contract_type)
    risk_mode = (risk_sensitivity or "Balanced").strip().lower()

    # Always keep legal review in the plan when available.
    legal_roles = [name for name in role_names if "legal" in name.lower()]
    if legal_roles:
        selected.add(sorted(legal_roles, key=_priority)[0])
    # Always include operations so execution and delivery risks are visible in breakdown output.
    operations_roles = [name for name in role_names if "operations" in name.lower()]
    if operations_roles:
        selected.add(sorted(operations_roles, key=_priority)[0])

    if _contains_any(contract_hint, ("msa", "vendor", "services", "procurement", "sow")):
        selected.update(name for name in role_names if any(k in name.lower() for k in ("operations", "finance", "legal")))
    if _contains_any(contract_hint, ("employment", "hr", "contractor")):
        selected.update(name for name in role_names if any(k in name.lower() for k in ("legal", "compliance", "operations")))
    if _contains_any(contract_hint, ("loan", "credit", "financ")):
        selected.update(name for name in role_names if any(k in name.lower() for k in ("finance", "legal", "compliance")))
    if _contains_any(contract_hint, ("nda", "privacy", "dpa", "data processing")):
        selected.update(name for name in role_names if any(k in name.lower() for k in ("compliance", "legal")))

    if _contains_any(text, ("gdpr", "hipaa", "sox", "privacy", "security", "audit")):
        selected.update(name for name in role_names if "compliance" in name.lower())
    if _contains_any(text, ("payment", "invoice", "fees", "penalty", "pricing", "indemnity", "liability cap")):
        selected.update(name for name in role_names if "finance" in name.lower())
    if _contains_any(text, ("governing law", "dispute", "arbitration", "breach", "termination")):
        selected.update(name for name in role_names if "legal" in name.lower())
    if _contains_any(text, ("sla", "timeline", "uptime", "delivery", "milestone", "change request")):
        selected.update(name for name in role_names if "operations" in name.lower())

    if risk_mode == "conservative":
        selected.update(name for name in role_names if "compliance" in name.lower() or "finance" in name.lower())
    elif risk_mode == "aggressive":
        # Keep sharper scope for high-confidence findings.
        if len(selected) > 3:
            selected = set(sorted(selected, key=_priority)[:3])

    if not selected:
        # Safe fallback for unknown contracts.
        selected = set(by_priority[: min(3, len(by_priority))])

    ordered = [name for name in by_priority if name in selected]
    return ordered or by_priority


def build_agent_execution_plan(
    available_roles: Dict[str, AnalystRole],
    contract_text: str,
    contract_type: str = "Auto-detect",
    risk_sensitivity: str = "Balanced",
    use_local_llm: bool = False,
    configured_workers: str = "",
) -> AgentExecutionPlan:
    ordered_roles = _select_role_names(
        available_roles=available_roles,
        contract_text=contract_text,
        contract_type=contract_type,
        risk_sensitivity=risk_sensitivity,
    )

    if configured_workers and configured_workers.isdigit():
        worker_cap = max(1, int(configured_workers))
    else:
        worker_cap = 2 if use_local_llm else 4
    max_workers = min(worker_cap, max(1, len(ordered_roles)))

    stage_by_role = {role_name: _stage_for_role(role_name, available_roles[role_name]) for role_name in ordered_roles}
    ordered_stages = [stage_by_role[role_name] for role_name in ordered_roles]

    return AgentExecutionPlan(
        ordered_roles=ordered_roles,
        stage_by_role=stage_by_role,
        ordered_stages=ordered_stages,
        max_workers=max_workers,
    )
