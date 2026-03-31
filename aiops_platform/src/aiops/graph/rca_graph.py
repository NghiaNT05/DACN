import ast
import json
import re


def _extract_allowed_services(context_bundle_text):
    marker = "allowed_services:"
    idx = context_bundle_text.find(marker)
    if idx == -1:
        return []

    start = idx + len(marker)
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
    return [str(x) for x in parsed]


def _extract_facts(context_bundle_text):
    marker = "RCA_FACTS_JSON:\n"
    idx = context_bundle_text.find(marker)
    if idx == -1:
        return {}

    start = idx + len(marker)
    end_marker = "\n\nTELEMETRY_ERRORS:"
    end = context_bundle_text.find(end_marker, start)
    raw = context_bundle_text[start:end if end != -1 else len(context_bundle_text)].strip()

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}
    return parsed


def _collect_seed_services(retrieval_summary):
    seeds = set(retrieval_summary.get("covered_services", []) or [])
    for hit in retrieval_summary.get("hits", []) or []:
        for svc in hit.get("services", []) or []:
            if svc and svc != "unknown":
                seeds.add(str(svc))
    return sorted(seeds)


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


def _extract_log_signature_text(context_bundle_text):
    marker = "TOP_ERROR_LOG_SIGNATURES:"
    idx = context_bundle_text.find(marker)
    if idx == -1:
        return ""

    tail = context_bundle_text[idx + len(marker):]
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
    return " ".join(lines).lower()


def _rank_graph_candidates(facts, seeds, log_signature_text):
    reverse_deps = {}
    for svc, item in facts.items():
        deps = (item or {}).get("dependencies", []) if isinstance(item, dict) else []
        for dep in deps:
            reverse_deps.setdefault(dep, set()).add(svc)

    scores = {}
    evidence = {}

    for svc, item in facts.items():
        if not isinstance(item, dict):
            continue

        score = 0.0
        ev = []

        log_count = float(item.get("log_error_count", 0) or 0)
        metric_count = float(item.get("metric_anomaly_count", 0) or 0)
        runtime = item.get("runtime", {}) or {}
        desired = float(runtime.get("desired", 0) or 0)
        ready = float(runtime.get("ready", 0) or 0)

        if log_count > 0:
            score += min(3.0, log_count / 80.0)
            ev.append(f"log_error_count={int(log_count)}")

        if metric_count > 0:
            score += min(1.0, metric_count / 3.0)
            ev.append(f"metric_anomaly_count={int(metric_count)}")

        if item.get("is_unhealthy"):
            score += 0.8
            ev.append("runtime_unhealthy=true")

        if item.get("is_scaled_to_zero"):
            score += 0.7
            ev.append("scaled_to_zero=true")

        if desired > 0 and ready < desired:
            score += 0.6
            ev.append(f"ready<{int(desired)}")

        if svc in seeds:
            score += 0.4
            ev.append("retrieval_seed=true")

        inbound_from_seed = 0
        for seed in seeds:
            seed_deps = (facts.get(seed, {}) or {}).get("dependencies", [])
            if svc in seed_deps:
                inbound_from_seed += 1
        if inbound_from_seed > 0:
            score += min(2.0, 0.8 + inbound_from_seed * 0.4)
            ev.append(f"depended_by_seed={inbound_from_seed}")

        alias_matches = 0
        for alias in _service_aliases(svc):
            if re.search(rf"\b{re.escape(alias)}\b", log_signature_text):
                alias_matches += 1
        if alias_matches > 0:
            score += min(1.4, 0.6 + alias_matches * 0.4)
            ev.append(f"log_signature_match={alias_matches}")

        # If many other services depend on this one, blast radius is larger.
        dependent_count = len(reverse_deps.get(svc, set()))
        if dependent_count > 0:
            score += min(1.0, dependent_count / 4.0)
            ev.append(f"dependent_services={dependent_count}")

        service_type = str(item.get("service_type", "unknown") or "unknown").lower()
        deps_count = len(item.get("dependencies", []) or [])
        # Frontend/web services with many downstream calls are often symptom services.
        if service_type in ("web", "frontend") and deps_count > 0 and log_count > 0:
            score = max(0.0, score - 1.2)
            ev.append("symptom_service_penalty")

        if score > 0:
            scores[svc] = score
            evidence[svc] = ev[:3]

    if not scores:
        return []

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    max_score = ranked[0][1] if ranked else 0.0

    out = []
    for svc, score in ranked:
        norm = 0.0 if max_score <= 0 else min(1.0, score / max_score)
        out.append(
            {
                "service": svc,
                "score": round(norm, 2),
                "evidence": evidence.get(svc, []),
            }
        )
    return out


def _build_causal_paths(facts, seeds, top_candidates):
    if not facts:
        return []

    paths = []
    for candidate in top_candidates:
        root = candidate.get("service", "")
        if not root:
            continue

        # direct path from a seeded/impacted service to candidate by dependencies
        for seed in seeds:
            if seed == root:
                continue

            deps = (facts.get(seed, {}) or {}).get("dependencies", [])
            if root in deps:
                paths.append(
                    {
                        "from": seed,
                        "to": root,
                        "relation": "depends_on",
                    }
                )

            # two-hop: seed -> mid -> root
            for mid in deps:
                mid_deps = (facts.get(mid, {}) or {}).get("dependencies", [])
                if root in mid_deps:
                    paths.append(
                        {
                            "from": seed,
                            "via": mid,
                            "to": root,
                            "relation": "depends_on_chain",
                        }
                    )

    return paths[:8]


def build_graph_rag_context(context_bundle_text, retrieval_summary):
    allowed_services = _extract_allowed_services(context_bundle_text)
    facts = _extract_facts(context_bundle_text)
    seeds = _collect_seed_services(retrieval_summary)

    # Keep seeds constrained to known services to reduce prompt noise.
    seeds = [s for s in seeds if s in allowed_services]

    log_signature_text = _extract_log_signature_text(context_bundle_text)
    candidates = _rank_graph_candidates(facts, seeds, log_signature_text)
    paths = _build_causal_paths(facts, seeds, candidates)

    lines = [
        "GRAPH_RAG_CONTEXT:",
        f"graph_nodes={len(facts)}",
        f"seed_services={seeds}",
        f"candidate_roots={candidates}",
        f"causal_paths={paths}",
    ]

    summary = {
        "node_count": len(facts),
        "seed_services": seeds,
        "candidate_roots": candidates,
        "causal_paths": paths,
    }
    return "\n".join(lines), summary
