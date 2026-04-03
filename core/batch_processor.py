from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from core.clause_analyzer import analyze_contract


def process_contract_batch(
    batch_items: List[Dict[str, object]],
    analyze_kwargs: Dict[str, object],
    item_callback: Optional[Callable[[Dict[str, object], int, int], None]] = None,
) -> List[Dict[str, object]]:
    if not batch_items:
        return []

    import time

    results = []
    effective_kwargs = dict(analyze_kwargs)

    forced_env = {
        "CLAUSEAI_ENABLE_MULTI_TURN_AGENT_INTERACTION": "0",
        "CLAUSEAI_ENABLE_PARALLEL_CLAUSE_EXTRACTION": "0",
        "CLAUSEAI_AGENT_WORKERS": "1",
        "CLAUSEAI_CLAUSE_WORKERS": "1",
        "CLAUSEAI_AGENT_NUM_PREDICT": "500",
        "CLAUSEAI_DEEP_ANALYSIS": "0",
        "CLAUSEAI_TURBO_MODE": "1",
        "CLAUSEAI_MAX_INDEX_CHUNKS": "6",
    }
    original_env = {key: os.getenv(key) for key in forced_env}
    for key, value in forced_env.items():
        os.environ[key] = value

    inter_file_delay = float(os.getenv("CLAUSEAI_INTER_FILE_DELAY", "5.0"))

    try:
        total = len(batch_items)
        for idx, item in enumerate(batch_items):
            if idx > 0 and inter_file_delay > 0:
                time.sleep(inter_file_delay)

            name = str(item.get("name") or "Untitled")
            pages = item.get("pages") or []
            try:
                result = analyze_contract(pages, **effective_kwargs)
                item_result = {"name": name, "status": "Completed", "result": result}
            except Exception as err:
                item_result = {"name": name, "status": "Failed", "error": str(err)}

            results.append(item_result)
            if item_callback:
                item_callback(item_result, idx + 1, total)
    finally:
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    return results
