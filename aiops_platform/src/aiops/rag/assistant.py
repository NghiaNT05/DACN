import json
import re
import ast

import ollama
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from aiops.config import get_settings
from aiops.graph import build_graph_rag_context
from aiops.observers import build_system_context_text


NO_INFO_MESSAGE = "I do not have enough relevant evidence in the provided context."

SYSTEM_PROMPT = f"""You are a DevOps AIOps Assistant and system chatbot.

Mandatory rules:
1. Use only evidence from CONTEXT and LIVE_SYSTEM_CONTEXT when present.
2. Do not hallucinate.
3. If context is insufficient, answer exactly: \"{NO_INFO_MESSAGE}\".
4. Always answer in English.
5. Keep answers concise and relevant.
"""

LLM_CONTEXT_RCA_PROMPT = """You are a DevOps AIOps RCA model specialized in microservice incident analysis.

Task:
1. Read QUESTION, INCIDENT_CONTEXT_BUNDLE, RETRIEVED_RAG_CONTEXT, and GRAPH_RAG_CONTEXT.
2. Infer root cause from context only.
3. Return strict JSON only (no markdown, no prose outside JSON) with fields:
     {
         "status": "ok|insufficient_data|degraded_datasource",
         "root_cause": "service_name_or_unknown",
         "confidence": 0.0,
         "candidate_roots": [{"service":"...","score":0.0,"evidence":["..."]}],
         "reasoning": "short explanation based on evidence",
         "impacted_services": ["..."],
         "evidence": ["..."],
         "anomalies": [{"service":"...","type":"...","value":"...","threshold":"...","source":"telemetry|inferred_from_logs"}],
         "suggested_actions": ["..."]
     }

Rules:
- Use only provided INCIDENT_CONTEXT_BUNDLE, RETRIEVED_RAG_CONTEXT, and GRAPH_RAG_CONTEXT.
- RETRIEVED_RAG_CONTEXT is mandatory evidence. If it is "none" or has no useful hits, return status=insufficient_data.
- Do not ask follow-up questions in the final output.
- Do not introduce techniques, components, or remediation steps that are not evidenced by provided context.
- If evidence is weak, lower confidence.
- Keep confidence in [0,1].
- root_cause must be in allowed_services or unknown.
- reasoning must align with root_cause and candidate_roots; do not claim a different primary cause.
- Keep arrays concise: evidence<=4, anomalies<=5, suggested_actions<=4.
- Suggested actions must be safe/read-only diagnostics.
- Suggested actions should be concrete operational checks, preferably read-only commands or checks.
- For service-specific diagnosis, prefer formats like:
    - kubectl get deployment <service> -n default -o wide
    - kubectl describe deployment <service> -n default
    - kubectl get pods -n default -l app=<service>
    - kubectl logs deployment/<service> -n default --tail=200
- Build candidate services from RCA_FACTS_JSON and dependency context.
- Use GRAPH_RAG_CONTEXT candidate_roots and causal_paths as primary structural hints.
- Rank candidates by cross-signal consistency (runtime state + logs + metrics + dependencies), not single-signal matching.
- If multiple candidates conflict with similar support, lower confidence.
- If evidence does not converge, return root_cause=unknown and status=insufficient_data.
- candidate_roots should include top 2-3 likely causes with descending score in [0,1].
"""


_settings = get_settings()
_embeddings = HuggingFaceEmbeddings(
    model_name=_settings.embedding_model,
    model_kwargs={"device": "cpu"},
)
_vectorstore = Chroma(
    persist_directory=str(_settings.vector_db_dir),
    embedding_function=_embeddings,
)


def _tokenize(text):
    return set(re.findall(r"[a-z0-9_\-]+", text.lower()))


def _is_system_query(question):
    markers = ("cluster", "context", "node", "pod", "namespace", "cpu", "ram", "memory", "resource", "running", "status")
    q = question.lower()
    return any(marker in q for marker in markers)


def _relevant(question, results_with_score):
    if not results_with_score:
        return False
    best_score = results_with_score[0][1]
    q_tokens = _tokenize(question)
    c_tokens = set()
    for doc, _score in results_with_score:
        c_tokens.update(_tokenize(doc.page_content[:3000]))
    overlap = len(q_tokens & c_tokens) / max(len(q_tokens), 1)
    return not (best_score > 1.25 and overlap < 0.12)


def ask_devops(question, top_k=4):
    results_with_score = _vectorstore.similarity_search_with_score(question, k=top_k)
    if not _relevant(question, results_with_score) and not _is_system_query(question):
        return NO_INFO_MESSAGE

    context = "\n".join([doc.page_content for doc, _score in results_with_score])
    if _is_system_query(question):
        context += "\n\n" + build_system_context_text()

    user_prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}\n"
    response = ollama.chat(
        model=_settings.ollama_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response["message"]["content"]


def _extract_json_object(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start:end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None
    return None


def _repair_rca_json(question, context_bundle_text, raw_text):
    repair_prompt = (
        "Convert the following RCA analysis into strict JSON only. "
        "Do not add markdown. Keep fields:\n"
        "status, root_cause, confidence, candidate_roots, reasoning, impacted_services, evidence, anomalies, suggested_actions.\n"
        "If uncertain, use root_cause=unknown and status=insufficient_data.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"INCIDENT_CONTEXT_BUNDLE:\n{context_bundle_text[:5000]}\n\n"
        f"RCA_ANALYSIS_TEXT:\n{raw_text}\n"
    )
    response = ollama.chat(
        model=_settings.ollama_model,
        messages=[
            {"role": "system", "content": "You are a strict JSON formatter for DevOps RCA."},
            {"role": "user", "content": repair_prompt},
        ],
    )
    repaired = response["message"]["content"].strip()
    if repaired.startswith("```"):
        repaired = repaired.strip("`")
        repaired = repaired.replace("json\n", "", 1).strip()
    return _extract_json_object(repaired), repaired


def _extract_candidates_from_text(raw_text, allowed_services):
    text = raw_text.lower()
    if not text or not allowed_services:
        return []

    score_map = {}
    for svc in allowed_services:
        s = svc.lower()
        mentions = len(re.findall(rf"\b{re.escape(s)}\b", text))
        if mentions == 0:
            continue

        score = float(mentions)
        patterns = (
            rf"root cause[^\n]*{re.escape(s)}",
            rf"primary[^\n]*{re.escape(s)}",
            rf"{re.escape(s)}[^\n]*(crashloop|unhealthy|connection refused|timeout|unavailable)",
        )
        for p in patterns:
            if re.search(p, text):
                score += 2.0

        score_map[svc] = score

    if not score_map:
        return []

    ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:3]
    max_score = ranked[0][1]

    candidates = []
    for svc, score in ranked:
        norm = 0.0 if max_score <= 0 else min(1.0, score / max_score)
        evidence = []
        for sentence in re.split(r"(?<=[.!?])\s+", raw_text):
            if svc.lower() in sentence.lower():
                evidence.append(sentence.strip())
            if len(evidence) >= 2:
                break
        candidates.append(
            {
                "service": svc,
                "score": round(norm, 2),
                "evidence": evidence,
            }
        )
    return candidates


def _service_aliases(service_name):
    aliases = {service_name.lower()}
    if service_name.lower().endswith("service"):
        base = service_name.lower()[: -len("service")]
        if base:
            aliases.add(base)
            aliases.add(base + "s")
            if base.endswith("y"):
                aliases.add(base[:-1] + "ies")
    return aliases


def _count_service_mentions(text, service_name):
    if not text or not service_name:
        return 0
    total = 0
    lowered = text.lower()
    for alias in _service_aliases(service_name):
        total += len(re.findall(rf"\\b{re.escape(alias)}\\b", lowered))
    return total


def _extract_focus_services_from_question(question, allowed_services):
    if not question or not allowed_services:
        return []

    lowered = question.lower()
    out = []
    for svc in allowed_services:
        matched = False
        for alias in _service_aliases(svc):
            if re.search(rf"\\b{re.escape(alias)}\\b", lowered):
                matched = True
                break
        if matched:
            out.append(svc)
    return out


def _extract_top_error_log_text(context_bundle_text):
    marker = "TOP_ERROR_LOG_SIGNATURES:"
    idx = context_bundle_text.find(marker)
    if idx == -1:
        return ""

    tail = context_bundle_text[idx + len(marker) :]
    lines = []
    for raw in tail.splitlines():
        stripped = raw.strip()
        if not stripped:
            if lines:
                break
            continue
        if stripped.endswith(":") and not stripped.startswith("-"):
            break
        lines.append(stripped)
        if len(lines) >= 12:
            break
    return " ".join(lines)


def _apply_generalization_priors(result, question, context_bundle_text, allowed_services):
    candidates = result.get("candidate_roots", [])
    if not allowed_services:
        return result

    candidate_map = {}
    for item in candidates:
        svc = item.get("service", "unknown")
        if svc == "unknown":
            continue
        score = float(item.get("score", 0.0))
        evidence = item.get("evidence", []) if isinstance(item.get("evidence", []), list) else []
        prev = candidate_map.get(svc)
        if prev is None or score > prev["score"]:
            candidate_map[svc] = {
                "service": svc,
                "score": score,
                "evidence": evidence[:3],
            }

    focus_services = _extract_focus_services_from_question(question, allowed_services)
    covered_services = set(result.get("retrieval_summary", {}).get("covered_services", []) or [])

    evidence_text = " ".join(result.get("evidence", []) or [])
    reasoning_text = str(result.get("reasoning", "") or "")
    log_signature_text = _extract_top_error_log_text(context_bundle_text)
    support_text = f"{evidence_text} {reasoning_text} {log_signature_text}".strip()

    for svc in allowed_services:
        mention_count = _count_service_mentions(support_text, svc)
        focus_boost = 0.28 if svc in focus_services else 0.0
        coverage_boost = 0.08 if svc in covered_services else 0.0
        mention_boost = min(0.25, mention_count * 0.07)

        if svc in candidate_map:
            boosted = min(1.0, candidate_map[svc]["score"] + focus_boost + coverage_boost + mention_boost)
            candidate_map[svc]["score"] = round(boosted, 2)
            if mention_count > 0 and len(candidate_map[svc]["evidence"]) < 3:
                candidate_map[svc]["evidence"].append("direct_evidence_mention=true")
            if svc in focus_services and len(candidate_map[svc]["evidence"]) < 3:
                candidate_map[svc]["evidence"].append("question_focus_match=true")
        else:
            # Add focused/covered services as fallback candidates to avoid brittle overfitting to one stream.
            if svc in focus_services and (svc in covered_services or mention_count > 0):
                score = min(0.78, 0.45 + coverage_boost + mention_boost + focus_boost)
                candidate_map[svc] = {
                    "service": svc,
                    "score": round(score, 2),
                    "evidence": ["question_focus_match=true"],
                }

    ranked = sorted(candidate_map.values(), key=lambda x: x.get("score", 0.0), reverse=True)
    if not ranked:
        return result

    # If the incident question explicitly scopes to services, penalize unrelated roots
    # unless they have direct evidence mentions in logs/reasoning.
    if focus_services:
        focus_set = set(focus_services)
        adjusted = []
        for item in ranked:
            svc = item.get("service", "unknown")
            score = float(item.get("score", 0.0))
            mentions = _count_service_mentions(support_text, svc)
            if svc not in focus_set and mentions == 0:
                score = max(0.0, score - 0.22)
            adjusted.append(
                {
                    "service": svc,
                    "score": round(score, 2),
                    "evidence": item.get("evidence", [])[:3],
                }
            )
        ranked = sorted(adjusted, key=lambda x: x.get("score", 0.0), reverse=True)

    focus_ranked = [item for item in ranked if item.get("service") in focus_services]
    if focus_ranked:
        best_focus = focus_ranked[0]
        top = ranked[0]
        if (
            top.get("service") != best_focus.get("service")
            and float(top.get("score", 0.0)) - float(best_focus.get("score", 0.0)) <= 0.2
        ):
            ranked = [best_focus] + [item for item in ranked if item.get("service") != best_focus.get("service")]

    result["candidate_roots"] = ranked[:3]

    root = result.get("root_cause", "unknown")
    top_service = result["candidate_roots"][0].get("service", "unknown")
    candidate_services = [item.get("service") for item in result["candidate_roots"]]
    if root == "unknown" or root not in candidate_services:
        result["root_cause"] = top_service
        if result.get("status") != "degraded_datasource":
            result["status"] = "ok"

    root = result.get("root_cause", "unknown")
    root_mentions = _count_service_mentions(support_text, root)
    conf = float(result.get("confidence", 0.0) or 0.0)
    if root != "unknown" and root_mentions == 0:
        conf = min(conf, 0.62)
    if focus_services and root != "unknown" and root not in focus_services:
        conf = min(conf, 0.58)

    result["confidence"] = round(max(0.0, min(conf, 1.0)), 2)
    return result


def _normalize_status(value):
    if not isinstance(value, str):
        return "insufficient_data"
    normalized = value.strip().lower()
    allowed = {"ok", "insufficient_data", "degraded_datasource"}
    if normalized in allowed:
        return normalized
    if "degrad" in normalized:
        return "degraded_datasource"
    if "insufficient" in normalized:
        return "insufficient_data"
    return "ok"


def _coerce_list_of_strings(value, max_items):
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items[:max_items]
    if isinstance(value, str) and value.strip():
        return [value.strip()][:max_items]
    return []


def _normalize_anomalies(value):
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue
        service = str(item.get("service", "unknown")).strip() or "unknown"
        a_type = str(item.get("type", "other")).strip() or "other"
        source = str(item.get("source", "telemetry")).strip() or "telemetry"

        raw_value = item.get("value", 0)
        raw_threshold = item.get("threshold", 0)
        try:
            parsed_value = float(raw_value)
        except (TypeError, ValueError):
            parsed_value = 0.0
        try:
            parsed_threshold = float(raw_threshold)
        except (TypeError, ValueError):
            parsed_threshold = 0.0

        normalized.append(
            {
                "service": service,
                "type": a_type,
                "value": round(parsed_value, 4),
                "threshold": round(parsed_threshold, 4),
                "source": source,
            }
        )
        if len(normalized) >= 5:
            break
    return normalized


def _normalize_candidate_roots(value, allowed_services):
    if not isinstance(value, list):
        return []

    normalized = []
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        service = str(item.get("service", "unknown")).strip() or "unknown"
        if allowed_services and service != "unknown" and service not in allowed_services:
            continue
        if service in seen:
            continue
        seen.add(service)

        try:
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        score = max(0.0, min(score, 1.0))

        evidence = _coerce_list_of_strings(item.get("evidence", []), 2)
        normalized.append(
            {
                "service": service,
                "score": round(score, 2),
                "evidence": evidence,
            }
        )
        if len(normalized) >= 3:
            break

    normalized.sort(key=lambda x: x["score"], reverse=True)
    return normalized


def _sanitize_suggested_actions(actions):
    unsafe_kubectl_markers = (
        " delete",
        " scale",
        " restart",
        " rollout",
        " apply",
        " patch",
        " drain",
        " cordon",
        " uncordon",
    )
    safe_kubectl_prefixes = (
        "kubectl get",
        "kubectl describe",
        "kubectl logs",
        "kubectl top",
    )

    sanitized = []
    for action in actions:
        action_clean = action.strip()
        action_lower = action_clean.lower()
        lowered = f" {action.strip().lower()}"

        if action_clean.startswith("{") and action_clean.endswith("}"):
            continue

        if action.strip().lower().startswith("kubectl") and any(marker in lowered for marker in unsafe_kubectl_markers):
            continue

        if action.strip().lower().startswith("kubectl") and not action.strip().lower().startswith(safe_kubectl_prefixes):
            continue

        # Keep operationally actionable diagnostics, avoid long-term architecture suggestions in RCA output.
        allowed_markers = (
            "check ",
            "verify ",
            "inspect ",
            "review ",
            "run ",
            "kubectl",
            "ping",
            "traceroute",
            "tracepath",
            "logs",
            "health",
            "connectivity",
        )
        if not any(marker in action_lower for marker in allowed_markers):
            continue

        sanitized.append(action_clean)
        if len(sanitized) >= 4:
            break

    if not sanitized:
        return [
            "kubectl get pods -n default",
            "kubectl describe deployment/<service> -n default",
        ]
    return sanitized


def _extract_allowed_services(context_bundle_text):
    marker = "allowed_services:"
    marker_index = context_bundle_text.find(marker)
    if marker_index == -1:
        return []

    start = marker_index + len(marker)
    end = context_bundle_text.find("\n", start)
    raw = context_bundle_text[start:end if end != -1 else len(context_bundle_text)].strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return []

    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []

    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _build_rca_retrieval_query(question, context_bundle_text):
    lines = []
    for marker in ("TOP_ERROR_LOG_SIGNATURES:", "DEPENDENCY_HINTS:", "K8S_DEPLOYMENT_STATE:"):
        idx = context_bundle_text.find(marker)
        if idx == -1:
            continue
        tail = context_bundle_text[idx + len(marker):]
        selected = []
        started = False
        for raw in tail.splitlines():
            raw = raw.strip()
            if not raw:
                if started:
                    break
                continue
            if raw.endswith(":") and not raw.startswith("-"):
                break
            started = True
            selected.append(raw)
            if len(selected) >= 5:
                break
        lines.extend(selected)

    # Keep retrieval useful even when section summaries are sparse.
    facts_marker = "RCA_FACTS_JSON:"
    facts_idx = context_bundle_text.find(facts_marker)
    if facts_idx != -1:
        facts_tail = context_bundle_text[facts_idx + len(facts_marker):].strip()
        if facts_tail:
            lines.append(f"facts_json_excerpt={facts_tail[:1200]}")

    merged_signals = " ; ".join(lines)
    if len(merged_signals) > 1400:
        merged_signals = merged_signals[:1400] + "..."

    return (
        f"incident_question: {question}\n"
        f"runtime_signals: {merged_signals}\n"
        "task: find root cause candidates, dependency impact, and operational evidence"
    )


def _infer_signal_type(source, source_type, snippet):
    text = f"{source} {source_type} {snippet}".lower()
    if "cmdb" in text or "services.json" in text or "dependency" in text:
        return "cmdb"
    if "deploy" in text or "pod" in text or "k8s" in text or "crashloop" in text:
        return "runtime"
    if "metric" in text or "latency" in text or "error_rate" in text or "prometheus" in text:
        return "metric"
    if "log" in text or "exception" in text or "timeout" in text or "refused" in text or "unavailable" in text:
        return "log"
    return "telemetry"


def _extract_time_hint(snippet):
    patterns = [
        r"\d{4}-\d{2}-\d{2}[tT ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:z|Z|[+-]\d{2}:?\d{2})?",
        r"\d{4}-\d{2}-\d{2}",
        r"\b\d{2}:\d{2}:\d{2}\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, snippet)
        if m:
            return m.group(0)
    return "n/a"


def _extract_services_for_hit(snippet, allowed_services, metadata=None):
    if not allowed_services:
        return ["unknown"]

    lowered = snippet.lower()
    metadata = metadata or {}
    hinted = []
    for pattern in (
        r'"app"\s*:\s*"([a-z0-9\-]+)"',
        r"\\\"app\\\"\\s*:\\s*\\\"([a-z0-9\-]+)\\\"",
        r'"service"\s*:\s*"([a-z0-9\-]+)"',
        r"\\\"service\\\"\\s*:\\s*\\\"([a-z0-9\-]+)\\\"",
    ):
        for m in re.findall(pattern, lowered):
            hinted.append(m)

    for key in (
        "service",
        "app",
        "k8s_service_name",
        "destination_workload",
        "destination_service_name",
        "source_service",
    ):
        value = metadata.get(key)
        if value:
            hinted.append(str(value).lower())

    matches = []
    for svc in allowed_services:
        svc_low = svc.lower()
        aliases = {svc_low}
        if svc_low.endswith("service"):
            base = svc_low[: -len("service")]
            if base:
                aliases.add(base)
                aliases.add(base + "s")
                if base.endswith("y"):
                    aliases.add(base[:-1] + "ies")

        if svc_low in lowered:
            matches.append(svc)
            continue
        if re.search(rf"\b{re.escape(svc_low)}(?:-[a-z0-9-]+)?\b", lowered):
            matches.append(svc)
            continue
        if any(re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in aliases):
            matches.append(svc)
            continue
        if any(h.startswith(svc_low) or svc_low.startswith(h) for h in hinted):
            matches.append(svc)
    if not matches:
        return ["unknown"]
    return matches[:3]


def _dedupe_hits(scored_docs):
    deduped = []
    seen = set()
    for doc, score, query_tag in scored_docs:
        source = str(doc.metadata.get("source", "unknown"))
        snippet_key = " ".join(doc.page_content.split())[:180]
        key = (source, snippet_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((doc, score, query_tag))
    return deduped


def _select_diverse_hits(scored_docs, top_k):
    if not scored_docs:
        return []

    # Smaller score means more similar in Chroma distance space.
    scored_docs = sorted(scored_docs, key=lambda item: float(item[1]))

    buckets = {"cmdb": [], "runtime": [], "metric": [], "log": [], "telemetry": []}
    for doc, score, query_tag in scored_docs:
        source = str(doc.metadata.get("source", "unknown"))
        source_type = str(doc.metadata.get("source_type", "unknown"))
        snippet = " ".join(doc.page_content.split())[:500]
        signal_type = _infer_signal_type(source, source_type, snippet)
        buckets.setdefault(signal_type, []).append((doc, score, query_tag))

    selected = []
    # Reserve source diversity slots for practical RCA evidence.
    if buckets.get("cmdb"):
        selected.append(buckets["cmdb"].pop(0))
    if buckets.get("runtime"):
        selected.append(buckets["runtime"].pop(0))

    # Fill remaining with globally best hits, while keeping a little signal diversity.
    pool = []
    for items in buckets.values():
        pool.extend(items)
    pool = sorted(pool, key=lambda item: float(item[1]))

    for item in pool:
        if len(selected) >= top_k:
            break
        selected.append(item)

    return selected[:top_k]


def _collect_rag_hits(question, context_bundle_text, top_k):
    query_main = _build_rca_retrieval_query(question, context_bundle_text)
    query_cmdb = (
        f"incident_question: {question}\n"
        "focus: service dependencies and blast radius from cmdb\n"
        "task: map impacted services and upstream/downstream relation"
    )
    query_runtime = (
        f"incident_question: {question}\n"
        "focus: kubernetes runtime status, crashloop, unhealthy deployment\n"
        "task: find operational runtime evidence"
    )

    raw_hits = []
    retrieval_queries = {
        "main": query_main,
        "cmdb": query_cmdb,
        "runtime": query_runtime,
    }
    query_filters = {
        "main": None,
        "cmdb": {"source_type": "cmdb"},
        "runtime": {"source_type": "runtime"},
    }

    for query_tag, query in retrieval_queries.items():
        metadata_filter = query_filters.get(query_tag)
        try:
            hits = _vectorstore.similarity_search_with_score(query, k=top_k, filter=metadata_filter)
        except TypeError:
            hits = _vectorstore.similarity_search_with_score(query, k=top_k)

        if not hits and metadata_filter is not None:
            # Fallback for sparse index coverage where source_type chunks may be missing.
            hits = _vectorstore.similarity_search_with_score(query, k=top_k)

        for doc, score in hits:
            source = str(doc.metadata.get("source", "unknown"))
            if source.endswith("incident_report.schema.json"):
                continue
            raw_hits.append((doc, score, query_tag))

    deduped = _dedupe_hits(raw_hits)
    selected = _select_diverse_hits(deduped, top_k=top_k)
    return selected, retrieval_queries


def _retrieve_rca_context(question, context_bundle_text, top_k=8):
    selected, retrieval_queries = _collect_rag_hits(question, context_bundle_text, top_k)
    allowed_services = _extract_allowed_services(context_bundle_text)

    lines = []
    sources = []
    scored_hits = []
    source_type_counts = {}
    signal_type_counts = {}
    covered_services = set()

    for idx, (doc, score, query_tag) in enumerate(selected, start=1):
        source = str(doc.metadata.get("source", "unknown"))
        source_type = str(doc.metadata.get("source_type", "unknown"))
        snippet = " ".join(doc.page_content.split())
        if len(snippet) > 420:
            snippet = snippet[:420] + "..."
        signal_type = _infer_signal_type(source, source_type, snippet)
        time_hint = _extract_time_hint(snippet)
        hit_services = _extract_services_for_hit(snippet, allowed_services, metadata=doc.metadata)

        signal_type_counts[signal_type] = signal_type_counts.get(signal_type, 0) + 1
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        for svc in hit_services:
            if svc != "unknown":
                covered_services.add(svc)

        lines.append(
            "- "
            f"hit={idx}; "
            f"services={hit_services}; "
            f"signal_type={signal_type}; "
            f"time_hint={time_hint}; "
            f"score={round(float(score), 4)}; "
            f"source={source}; "
            f"source_type={source_type}; "
            f"query_tag={query_tag}; "
            f"evidence_snippet={snippet}"
        )
        sources.append(source)
        scored_hits.append(
            {
                "rank": idx,
                "score": round(float(score), 4),
                "source": source,
                "source_type": source_type,
                "signal_type": signal_type,
                "services": hit_services,
                "time_hint": time_hint,
                "query_tag": query_tag,
            }
        )

    text = "\n".join(lines) if lines else "none"
    summary = {
        "query": retrieval_queries.get("main", ""),
        "queries": retrieval_queries,
        "top_k": top_k,
        "hit_count": len(selected),
        "sources": sorted(set(sources)),
        "source_type_counts": source_type_counts,
        "signal_type_counts": signal_type_counts,
        "covered_services": sorted(covered_services),
        "hits": scored_hits,
    }
    return text, summary


def _apply_retrieval_quality_policy(result, retrieval_summary):
    hit_count = int(retrieval_summary.get("hit_count", 0) or 0)
    signal_type_counts = retrieval_summary.get("signal_type_counts", {})
    covered_services = retrieval_summary.get("covered_services", [])
    source_type_counts = retrieval_summary.get("source_type_counts", {})

    rag_quality = {
        "hit_count": hit_count,
        "has_hits": hit_count > 0,
        "has_signal_diversity": len(signal_type_counts) >= 2,
        "has_source_type_diversity": len(source_type_counts) >= 2,
        "covered_service_count": len(covered_services),
    }

    if hit_count == 0:
        result["status"] = "insufficient_data"
        result["root_cause"] = "unknown"
        result["confidence"] = min(float(result.get("confidence", 0.0)), 0.2)
        result["candidate_roots"] = []
        result["evidence"] = ["No retrieved RAG evidence was found for this incident query."]
        result["reasoning"] = "RCA requires retrieved evidence, but retrieval returned zero hits."

    elif len(signal_type_counts) < 2 or len(source_type_counts) < 2:
        # Low retrieval diversity can overfit to a single telemetry stream.
        result["confidence"] = round(min(float(result.get("confidence", 0.0)), 0.75), 2)
        result["status"] = "insufficient_data"
        if result.get("root_cause") != "unknown":
            result["root_cause"] = "unknown"

    result["rag_quality"] = rag_quality
    return result


def _merge_graph_candidates(result, graph_summary, allowed_services):
    graph_candidates = graph_summary.get("candidate_roots", []) if isinstance(graph_summary, dict) else []
    if not graph_candidates:
        return result

    normalized_graph_candidates = _normalize_candidate_roots(graph_candidates, allowed_services)
    if not normalized_graph_candidates:
        return result

    current = result.get("candidate_roots", [])
    merged = []
    seen = set()

    for item in current + normalized_graph_candidates:
        svc = item.get("service", "unknown")
        if svc in seen:
            continue
        seen.add(svc)
        merged.append(item)
        if len(merged) >= 3:
            break

    merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    result["candidate_roots"] = merged

    if result.get("root_cause") == "unknown" and merged and merged[0].get("service") != "unknown":
        result["root_cause"] = merged[0]["service"]
        if result.get("status") != "degraded_datasource":
            result["status"] = "ok"
        result["confidence"] = max(float(result.get("confidence", 0.0)), float(merged[0].get("score", 0.0)))

    return result


def _build_consistent_reasoning(result):
    root = result.get("root_cause", "unknown")
    candidates = result.get("candidate_roots", [])
    evidence = result.get("evidence", [])

    if root == "unknown":
        return "Evidence does not converge on a single root cause across retrieval and graph context."

    top = None
    for item in candidates:
        if item.get("service") == root:
            top = item
            break
    if top is None and candidates:
        top = candidates[0]

    top_evidence = ", ".join((top or {}).get("evidence", [])[:2])
    first_evidence = evidence[0] if evidence else "No direct incident evidence sentence is available."

    reason = (
        f"Root cause is prioritized as {root} from graph-retrieval ranking"
        f" ({top_evidence or 'cross-signal consistency'}). "
        f"Primary observed incident evidence: {first_evidence}"
    )
    return reason[:420]


def _enforce_professional_rca_consistency(result, allowed_services):
    candidates = result.get("candidate_roots", [])
    root = result.get("root_cause", "unknown")

    if candidates:
        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None

        # Prefer probable upstream/backend cause over web symptom when scores are near-tied.
        if (
            second
            and top.get("service") in {"frontend"}
            and (float(top.get("score", 0.0)) - float(second.get("score", 0.0))) <= 0.2
            and second.get("service") in (allowed_services or [])
        ):
            candidates = [second, top] + candidates[2:]
            result["candidate_roots"] = candidates
            if result.get("root_cause") == top.get("service"):
                result["root_cause"] = second.get("service", "unknown")
                result["confidence"] = max(
                    float(result.get("confidence", 0.0)),
                    float(second.get("score", 0.0)),
                )

        best = candidates[0]
        best_service = best.get("service", "unknown")
        if root == "unknown" and best_service != "unknown":
            result["root_cause"] = best_service
            if result.get("status") != "degraded_datasource":
                result["status"] = "ok"
            result["confidence"] = max(float(result.get("confidence", 0.0)), float(best.get("score", 0.0)))
        elif root != "unknown":
            candidate_services = [item.get("service") for item in candidates]
            if root not in candidate_services and best_service != "unknown":
                result["root_cause"] = best_service
                result["confidence"] = max(float(result.get("confidence", 0.0)), float(best.get("score", 0.0)))

    if allowed_services and result.get("root_cause") not in allowed_services and result.get("root_cause") != "unknown":
        result["root_cause"] = "unknown"
        result["status"] = "insufficient_data"
        result["confidence"] = min(float(result.get("confidence", 0.0)), 0.4)

    result["reasoning"] = _build_consistent_reasoning(result)

    root = result.get("root_cause", "unknown")
    actions = result.get("suggested_actions", [])
    if root != "unknown":
        target_checks = [
            f"kubectl get deployment {root} -n default -o wide",
            f"kubectl describe deployment {root} -n default",
            f"kubectl logs deployment/{root} -n default --tail=200",
        ]
        merged = []
        seen = set()
        for action in target_checks + actions:
            if action in seen:
                continue
            seen.add(action)
            merged.append(action)
            if len(merged) >= 4:
                break
        result["suggested_actions"] = _sanitize_suggested_actions(merged)

    result["confidence"] = round(max(0.0, min(float(result.get("confidence", 0.0)), 1.0)), 2)

    # Avoid overconfident RCA when candidates are near-tied.
    candidates = result.get("candidate_roots", [])
    if len(candidates) >= 2:
        spread = float(candidates[0].get("score", 0.0)) - float(candidates[1].get("score", 0.0))
        if spread < 0.12:
            result["confidence"] = min(result["confidence"], 0.78)
    return result


def _build_validated_llm_output(result):
    status = result.get("status", "unknown")
    root = result.get("root_cause", "unknown")
    confidence = result.get("confidence", 0.0)
    evidence = result.get("evidence", [])
    actions = result.get("suggested_actions", [])
    impacted = result.get("impacted_services", [])

    lines = [
        f"status={status}",
        f"root_cause={root}",
        f"confidence={confidence}",
        "impacted_services=" + ", ".join(impacted[:4]) if impacted else "impacted_services=none",
        "evidence:",
    ]
    for item in evidence[:3]:
        lines.append(f"- {item}")
    if not evidence:
        lines.append("- no direct evidence available")

    lines.append("suggested_actions:")
    for action in actions[:3]:
        lines.append(f"- {action}")
    if not actions:
        lines.append("- kubectl get pods -n default")

    return "\n".join(lines)


def _normalize_rca_payload(parsed, context_bundle_text):
    if not isinstance(parsed, dict):
        parsed = {}

    allowed_services = _extract_allowed_services(context_bundle_text)

    status = _normalize_status(parsed.get("status", "insufficient_data"))
    root_cause = str(parsed.get("root_cause", "unknown")).strip() or "unknown"
    if allowed_services and root_cause not in allowed_services:
        root_cause = "unknown"
        status = "insufficient_data"

    try:
        confidence = max(0.0, min(float(parsed.get("confidence", 0.0)), 1.0))
    except (TypeError, ValueError):
        confidence = 0.0

    reasoning = str(parsed.get("reasoning", "")).strip()
    if not reasoning:
        reasoning = "Reasoning is limited to currently available context evidence."

    result = {
        "status": status,
        "root_cause": root_cause,
        "confidence": round(confidence, 2),
        "candidate_roots": _normalize_candidate_roots(parsed.get("candidate_roots", []), allowed_services),
        "reasoning": reasoning,
        "impacted_services": _coerce_list_of_strings(parsed.get("impacted_services", []), 8),
        "evidence": _coerce_list_of_strings(parsed.get("evidence", []), 4),
        "anomalies": _normalize_anomalies(parsed.get("anomalies", [])),
        "suggested_actions": _sanitize_suggested_actions(
            _coerce_list_of_strings(parsed.get("suggested_actions", []), 6)
        ),
    }

    if not result["candidate_roots"] and result["root_cause"] != "unknown":
        result["candidate_roots"] = [
            {
                "service": result["root_cause"],
                "score": result["confidence"],
                "evidence": result["evidence"][:2],
            }
        ]

    if result["root_cause"] == "unknown" and result["candidate_roots"]:
        best = result["candidate_roots"][0]
        if best["service"] != "unknown":
            result["root_cause"] = best["service"]
            result["status"] = "ok" if status != "degraded_datasource" else status

    if len(result["candidate_roots"]) >= 2:
        spread = result["candidate_roots"][0]["score"] - result["candidate_roots"][1]["score"]
        if spread < 0.12:
            result["confidence"] = round(min(result["confidence"], 0.65), 2)

    if not result["evidence"]:
        result["status"] = "insufficient_data"
        result["confidence"] = min(result["confidence"], 0.3)
        result["evidence"] = ["Insufficient direct evidence from provided telemetry context."]

    if "datasource_health:" in context_bundle_text and '"all_ok": false' in context_bundle_text:
        if result["status"] == "ok":
            result["status"] = "degraded_datasource"
        result["confidence"] = round(max(0.0, result["confidence"] - 0.15), 2)

    return result


def infer_rca_with_context_bundle(question, context_bundle_text):
    retrieved_text, retrieval_summary = _retrieve_rca_context(question, context_bundle_text, top_k=8)
    graph_text, graph_summary = build_graph_rag_context(context_bundle_text, retrieval_summary)

    if int(retrieval_summary.get("hit_count", 0) or 0) == 0:
        minimal = {
            "status": "insufficient_data",
            "root_cause": "unknown",
            "confidence": 0.0,
            "candidate_roots": [],
            "reasoning": "RCA requires retrieved evidence, but retrieval returned zero hits.",
            "impacted_services": [],
            "evidence": ["No retrieved RAG evidence was found for this incident query."],
            "anomalies": [],
            "suggested_actions": ["kubectl get pods -n default"],
            "retrieval_summary": retrieval_summary,
            "rag_quality": {
                "hit_count": 0,
                "has_hits": False,
                "has_signal_diversity": False,
                "covered_service_count": 0,
            },
        }
        return minimal, "RAG retrieval returned zero hits."

    user_prompt = (
        f"QUESTION:\n{question}\n\n"
        f"{context_bundle_text}\n\n"
        "RETRIEVED_RAG_CONTEXT:\n"
        f"{retrieved_text}\n\n"
        f"{graph_text}\n"
    )

    response = ollama.chat(
        model=_settings.ollama_model,
        messages=[
            {"role": "system", "content": LLM_CONTEXT_RCA_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response["message"]["content"]
    raw_clean = raw.strip()
    if raw_clean.startswith("```"):
        raw_clean = raw_clean.strip("`")
        raw_clean = raw_clean.replace("json\n", "", 1).strip()

    parsed = _extract_json_object(raw_clean)

    repaired_text = ""
    if not isinstance(parsed, dict):
        parsed, repaired_text = _repair_rca_json(question, context_bundle_text, raw_clean)

    if not isinstance(parsed, dict):
        parsed = {
            "status": "insufficient_data",
            "root_cause": "unknown",
            "confidence": 0.0,
            "candidate_roots": [],
            "reasoning": "LLM output could not be parsed as structured JSON.",
            "impacted_services": [],
            "evidence": ["LLM output could not be parsed as structured JSON."],
            "anomalies": [],
            "suggested_actions": ["kubectl get pods -n default"],
        }

    normalized = _normalize_rca_payload(parsed, context_bundle_text)
    normalized["retrieval_summary"] = retrieval_summary
    normalized["graph_summary"] = graph_summary
    normalized = _apply_retrieval_quality_policy(normalized, retrieval_summary)
    if repaired_text:
        normalized["json_repair_used"] = True

    allowed_services = _extract_allowed_services(context_bundle_text)
    normalized = _merge_graph_candidates(normalized, graph_summary, allowed_services)

    if normalized.get("root_cause") == "unknown":
        candidates = _extract_candidates_from_text(raw_clean, allowed_services)
        if candidates:
            normalized["candidate_roots"] = candidates
            normalized["root_cause"] = candidates[0]["service"]
            if normalized.get("status") != "degraded_datasource":
                normalized["status"] = "ok"
            normalized["confidence"] = max(float(normalized.get("confidence", 0.0)), candidates[0]["score"])
            if normalized.get("reasoning", "").startswith("LLM output could not be parsed"):
                normalized["reasoning"] = "Recovered structured RCA fields from unstructured model analysis output."

    normalized = _apply_generalization_priors(normalized, question, context_bundle_text, allowed_services)
    normalized = _enforce_professional_rca_consistency(normalized, allowed_services)
    normalized["validated_llm_output"] = _build_validated_llm_output(normalized)

    return normalized, raw_clean
