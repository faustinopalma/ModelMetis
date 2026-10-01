import copy
import hashlib
from collections import Counter

CLASSES = tuple(f"C{number:02d}" for number in range(1, 9))
SEED_CELLS = ((1, 0), (2, 1), (8, 0))
EVALUATION_PROFILES = (5, 7)
REVIEW_BUDGET = 16


def fingerprint(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def partition(records):
    if len(records) != 128:
        raise ValueError("Expected all 128 whole Ottawa acquisitions.")
    for field in ("id", "group_id", "audio_sha256"):
        if len({record[field] for record in records}) != len(records):
            raise ValueError(f"Duplicate acquisition identity: {field}")
    expected = {(condition, profile, load) for condition in CLASSES
                for profile in range(1, 9) for load in (0, 1)}
    actual = {(record["condition_id"], record["profile"], record["load"])
              for record in records}
    if actual != expected:
        raise ValueError("Expected eight classes, eight profiles and two loads exactly once.")
    result = {role: [] for role in ("seed", "stream", "evaluation")}
    for record in records:
        cell = (record["profile"], record["load"])
        role = ("evaluation" if record["profile"] in EVALUATION_PROFILES else
                "seed" if cell in SEED_CELLS else "stream")
        result[role].append(record["id"])
    for role in result:
        result[role].sort(key=lambda identifier: fingerprint("ottawa-memory-v1:" + identifier))
    lookup = {record["id"]: record for record in records}
    for role, count in (("seed", 3), ("stream", 9), ("evaluation", 4)):
        if Counter(lookup[identifier]["condition_id"] for identifier in result[role]) != {
            condition: count for condition in CLASSES
        }:
            raise ValueError("Unbalanced registered partition.")
    return result


def initial_state(split, labels, arm):
    if arm not in {"fixed", "adaptive"} or set(labels) != set(split["seed"]):
        raise ValueError("Only registered seed labels may initialize an arm.")
    if Counter(labels.values()) != {condition: 3 for condition in CLASSES}:
        raise ValueError("Expected three seed labels per class.")
    return {"arm": arm, "bank": dict(labels), "position": 0, "stage": "summary",
            "reviews": 0, "version": 0, "candidates": [], "events": []}


def validate_decision(decision, evidence_ids, query_evidence):
    if set(decision) != {"decision", "condition_id", "candidates", "evidence", "explanation"}:
        raise ValueError("Unexpected decision fields.")
    action, condition = decision["decision"], decision["condition_id"]
    candidates = decision["candidates"]
    if (action not in {"accept", "review"} or not isinstance(candidates, list)
            or not all(isinstance(item, str) and item in CLASSES for item in candidates)
            or len(candidates) > 2 or len(candidates) != len(set(candidates))
            or (action == "accept" and (condition not in CLASSES
                                       or (candidates and condition not in candidates)))
            or (action == "review" and condition is not None)):
        raise ValueError("Invalid acceptance or review decision.")
    citations = decision["evidence"]
    if (not isinstance(citations, list) or not citations
            or not all(isinstance(item, str) and item in evidence_ids for item in citations)
            or query_evidence not in citations
            or not any(item.endswith(".CARD") for item in citations)
            or (action == "accept" and f"{condition}.CARD" not in citations)
            or not isinstance(decision["explanation"], str)
            or not decision["explanation"].strip()):
        raise ValueError("Decision requires bound query/class evidence and an explanation.")


def record_decision(state, split, query_id, stage, decision, request_hash, response_hash):
    if (state["position"] >= len(split["stream"])
            or query_id != split["stream"][state["position"]]
            or stage != state["stage"] or stage not in {"summary", "retrieval"}):
        raise ValueError("Decision is out of order or outside the registered stream.")
    if (decision["decision"] not in {"accept", "review"}
            or (decision["decision"] == "accept" and decision["condition_id"] not in CLASSES)
            or (decision["decision"] == "review" and decision["condition_id"] is not None)):
        raise ValueError("Unsupported decision.")
    result = copy.deepcopy(state)
    event = {"kind": "decision", "query_id": query_id, "stage": stage,
             "bank_version": state["version"], "decision": copy.deepcopy(decision),
             "request_sha256": request_hash, "response_sha256": response_hash}
    result["events"].append(event)
    if decision["decision"] == "review" and stage == "summary":
        result.update(stage="retrieval", candidates=list(decision["candidates"]))
    elif decision["decision"] == "review" and result["reviews"] < REVIEW_BUDGET:
        result.update(stage="human", candidates=[])
    else:
        if decision["decision"] == "review":
            event["human_status"] = "budget_exhausted"
        result.update(position=state["position"] + 1, stage="summary", candidates=[])
    return result


def apply_review(state, split, query_id, condition_id):
    if (state["stage"] != "human" or state["reviews"] >= REVIEW_BUDGET
            or state["position"] >= len(split["stream"])
            or query_id != split["stream"][state["position"]]
            or query_id in state["bank"] or condition_id not in CLASSES):
        raise ValueError("Oracle access requires a pending, budgeted stream review.")
    result = copy.deepcopy(state)
    if state["arm"] == "adaptive":
        result["bank"][query_id] = condition_id
        result["version"] += 1
    result["events"].append({"kind": "human", "query_id": query_id,
                             "condition_id": condition_id,
                             "origin": "simulated_human_from_publisher",
                             "added_to_bank": state["arm"] == "adaptive"})
    result.update(position=state["position"] + 1, stage="summary", candidates=[],
                  reviews=state["reviews"] + 1)
    return result


def score_state(state, split, truth):
    completed = set(split["stream"][:state["position"]])
    final = {}
    for event in state["events"]:
        if event["kind"] == "decision" and event["query_id"] in completed:
            final[event["query_id"]] = event["decision"]
    if set(final) != completed:
        raise ValueError("Completed stream cases must retain their original decisions.")
    accepted = {identifier: decision["condition_id"] for identifier, decision in final.items()
                if decision["decision"] == "accept"}
    wrong = sum(condition != truth[identifier] for identifier, condition in accepted.items())
    return {"stream_completed": len(completed), "stream_total": len(split["stream"]),
            "correct_automatic": len(accepted) - wrong, "wrong_automatic": wrong,
            "review_required": len(completed) - len(accepted),
            "automatic_coverage": len(accepted) / len(completed) if completed else None,
            "accepted_label_error": wrong / len(accepted) if accepted else None,
            "human_reviews": state["reviews"], "initial_labels": len(split["seed"]),
            "total_labels_revealed": len(split["seed"]) + state["reviews"],
            "bank_size": len(state["bank"]), "bank_version": state["version"],
            "scope": "All stream classes are represented; unknown rejection is unmeasured."}