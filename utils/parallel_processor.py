from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from planner.langgraph_planner import run_langgraph


def process_single_contract(contract_text, contract_id):
    """
    Wrapper to safely process one contract
    """
    try:
        # small delay to avoid burst calls
        time.sleep(1)

        result = run_langgraph(contract_text, contract_id)
        return {"status": "success", "data": result}

    except Exception as e:
        return {"status": "error", "error": str(e)}


def process_multiple_contracts(contract_map):
    """
    contract_map = {contract_id: contract_text}
    """
    results = {}

    # 🔥 LIMIT WORKERS (VERY IMPORTANT)
    with ThreadPoolExecutor(max_workers=2) as executor:

        futures = {
            executor.submit(process_single_contract, text, cid): cid
            for cid, text in contract_map.items()
        }

        for future in as_completed(futures):
            cid = futures[future]

            try:
                results[cid] = future.result()
            except Exception as e:
                results[cid] = {"status": "error", "error": str(e)}

    return results