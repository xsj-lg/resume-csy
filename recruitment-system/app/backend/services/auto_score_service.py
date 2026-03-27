from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from ..repositories.candidate_repository import (
    get_candidate_file_by_id,
    load_profile,
    seed_candidate_profiles,
)
from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import utc_now_iso
from .llm_service import (
    call_llm_chat_stream,
    load_active_prompt,
    load_llm_runtime_config,
    parse_llm_json_response,
    render_prompt_template,
)
from .resume_extract_service import (
    _normalize_resume_text_items as normalize_resume_text_items,
    get_candidate_resume_text,
    normalize_resume_structured_payload,
)
from .score_table_service import (
    build_score_items_from_templates,
    calculate_score_items_max_score,
    dedupe_score_items_for_prompt,
    format_score_table_for_prompt,
    normalize_score_item,
    score_to_float,
)

CHUNKED_JSON_RE = re.compile(r"\{[\s\S]*\}", re.DOTALL)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATASET_ROOT_DIR = ROOT_DIR / "data" / "cv" / "ais"
DB_PATH = ROOT_DIR / "data" / "recruitment.sqlite3"


def _json_loads_or_empty_object(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_resume_text_items(raw_items: Any, *, limit: int = 20) -> list[str]:
    return normalize_resume_text_items(raw_items, limit=limit)


def _resolve_storage_path(storage_rel_path: str) -> Path | None:
    rel_path = (storage_rel_path or "").strip()
    if not rel_path:
        return None
    root = DATASET_ROOT_DIR.resolve()
    file_path = (DATASET_ROOT_DIR / rel_path).resolve()
    try:
        file_path.relative_to(root)
    except ValueError:
        return None
    if file_path.suffix.lower() != ".pdf":
        return None
    return file_path


def _normalize_resume_text_supplement(resume_text: str, *, limit: int = 3500) -> str:
    raw_text = str(resume_text or "").strip()
    if not raw_text:
        return ""
    out_lines: list[str] = []
    seen: set[str] = set()
    total_length = 0
    for line in raw_text.splitlines():
        text = re.sub(r"\s+", " ", str(line or "").strip())
        if not text:
            continue
        if re.fullmatch(r"[0-9A-Za-z_~\-]{24,}", text):
            continue
        if text in seen:
            continue
        seen.add(text)
        out_lines.append(text)
        total_length += len(text) + 1
        if total_length >= limit:
            break
    return "\n".join(out_lines)[:limit]


def _compact_resume_structured_for_prompt(resume_structured: Any) -> dict[str, Any]:
    normalized = (
        normalize_resume_structured_payload(resume_structured)
        if isinstance(resume_structured, dict)
        else normalize_resume_structured_payload({})
    )
    basic_raw = normalized.get("basic")
    basic_obj = basic_raw if isinstance(basic_raw, dict) else {}
    basic: dict[str, str] = {}
    for key in [
        "name",
        "phone",
        "email",
        "location",
        "target_position",
        "highest_education",
        "school_name",
        "major",
        "experience_type",
        "graduation_year",
        "work_years",
    ]:
        value = str(basic_obj.get(key, "")).strip()
        if value:
            basic[key] = value

    def compact_items(items: Any, keys: list[str], *, limit: int, summary_limit: int = 280) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            current: dict[str, Any] = {}
            for key in keys:
                raw_value = raw_item.get(key, "")
                if key == "tech_stack":
                    stack_values = _normalize_resume_text_items(raw_value, limit=8)
                    if stack_values:
                        current[key] = stack_values
                    continue
                value = re.sub(r"\s+", " ", str(raw_value or "").strip())
                if not value:
                    continue
                if key == "summary":
                    value = value[:summary_limit]
                current[key] = value
            if current:
                out.append(current)
            if len(out) >= limit:
                break
        return out

    skills = _normalize_resume_text_items(normalized.get("skills"), limit=15)
    certificates = _normalize_resume_text_items(normalized.get("certificates"), limit=10)
    summary = re.sub(r"\s+", " ", str(normalized.get("summary", "")).strip())[:400]
    scoring_evidence_raw = normalized.get("scoring_evidence")
    scoring_evidence_obj = scoring_evidence_raw if isinstance(scoring_evidence_raw, dict) else {}
    scoring_evidence: dict[str, list[str]] = {}
    for key in [
        "academic_performance",
        "programming_language",
        "algorithm_data_structure",
        "development_tools",
        "technical_breadth",
        "project_depth",
        "code_quality",
        "testing_quality",
        "documentation",
        "learning_ability",
        "communication_collaboration",
        "initiative",
        "logic_expression",
    ]:
        values = _normalize_resume_text_items(scoring_evidence_obj.get(key), limit=5)
        if values:
            scoring_evidence[key] = values

    payload: dict[str, Any] = {}
    if basic:
        payload["basic"] = basic
    if skills:
        payload["skills"] = skills
    if certificates:
        payload["certificates"] = certificates
    if summary:
        payload["summary"] = summary
    if scoring_evidence:
        payload["scoring_evidence"] = scoring_evidence

    education = compact_items(normalized.get("education"), ["school", "degree", "major", "start", "end", "summary"], limit=3)
    if education:
        payload["education"] = education
    work_experience = compact_items(normalized.get("work_experience"), ["company", "title", "start", "end", "summary"], limit=4)
    if work_experience:
        payload["work_experience"] = work_experience
    project_experience = compact_items(
        normalized.get("project_experience"),
        ["name", "role", "start", "end", "tech_stack", "summary"],
        limit=4,
    )
    if project_experience:
        payload["project_experience"] = project_experience
    return payload


def _build_candidate_scoring_inputs(
    *,
    resume_structured: Any,
    resume_text: str,
) -> tuple[dict[str, Any], str]:
    structured_payload = _compact_resume_structured_for_prompt(resume_structured)
    basic_obj = structured_payload.get("basic")
    has_basic = isinstance(basic_obj, dict) and bool(basic_obj)
    has_experience = bool(structured_payload.get("work_experience")) or bool(structured_payload.get("project_experience"))
    has_skills = bool(structured_payload.get("skills"))
    has_scoring_evidence = bool(structured_payload.get("scoring_evidence"))
    needs_resume_supplement = not (has_basic and has_experience and has_skills and has_scoring_evidence)
    resume_supplement = _normalize_resume_text_supplement(resume_text) if needs_resume_supplement else ""
    return structured_payload, resume_supplement


def score_keywords(text: str) -> list[str]:
    raw_parts = re.split(r"[,\n;|，。；、/（）()\[\]\s]+", (text or "").strip())
    out: list[str] = []
    for part in raw_parts:
        token = part.strip().casefold()
        if len(token) < 2:
            continue
        if token in {"以及", "相关", "能力", "经验", "要求"}:
            continue
        out.append(token)
    return out[:8]


def calculate_match_level(total_score: float, max_score: float) -> str:
    if max_score <= 0:
        return "待定"
    ratio = total_score / max_score
    if ratio >= 0.85:
        return "强推荐"
    if ratio >= 0.7:
        return "推荐"
    if ratio >= 0.5:
        return "待定"
    return "不推荐"


def score_with_fallback_rules(
    *,
    candidate_id: str,
    snapshot: dict[str, Any],
    resume_text: str,
    model_name: str = "",
    prompt_id: str = "",
    llm_error_message: str = "",
) -> dict[str, Any]:
    score_items_raw = snapshot.get("score_items")
    if not isinstance(score_items_raw, list):
        score_items_raw = []

    score_items = [
        normalize_score_item(item)
        for item in score_items_raw
        if isinstance(item, dict)
    ]
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for item in score_items:
        dimension_name = item.get("dimension") or "未命名维度"
        point_name = item.get("point") or item.get("criterion") or "未命名评估点"
        grouped.setdefault(str(dimension_name), {}).setdefault(str(point_name), []).append(item)

    resume = str(resume_text or "").casefold()
    dimension_scores: list[dict[str, Any]] = []
    total_score = 0.0
    max_score = 0.0
    risk_flags: list[str] = []

    if not resume.strip():
        risk_flags.append("简历文本提取为空，评分可靠性较低")
    if not score_items:
        risk_flags.append("岗位评分表未配置有效评分项")

    for dimension_name, point_groups in grouped.items():
        dim_score = 0.0
        dim_max = 0.0
        normalized_items: list[dict[str, Any]] = []
        for point_name, point_items in point_groups.items():
            point_max = max(max(float(item.get("score_value", 0.0) or 0.0), 0.0) for item in point_items)
            dim_max += point_max

            best_item: dict[str, Any] | None = None
            best_score = 0.0
            best_evidence: list[str] = []
            for item in point_items:
                criterion = str(item.get("criterion", "")).strip()
                indicator = str(item.get("indicator", "")).strip() or criterion
                item_max = max(float(item.get("score_value", 0.0) or 0.0), 0.0)
                matched_keywords = [
                    token
                    for token in score_keywords(indicator or criterion or point_name or dimension_name)
                    if token and token in resume
                ]
                is_hit = bool(matched_keywords) and bool(resume.strip())
                item_score = item_max if is_hit else 0.0
                if (
                    item_score > best_score
                    or (
                        item_score == best_score
                        and best_item is not None
                        and item_max > max(float(best_item.get("score_value", 0.0) or 0.0), 0.0)
                    )
                    or best_item is None
                ):
                    best_item = item
                    best_score = item_score
                    best_evidence = matched_keywords[:3] if matched_keywords else []

            dim_score += best_score
            selected_standard = ""
            if best_item is not None:
                selected_standard = str(best_item.get("criterion", "")).strip() or str(best_item.get("indicator", "")).strip()
            normalized_items.append(
                {
                    "item_name": point_name,
                    "selected_standard": selected_standard or ("命中关键词" if best_score > 0 else "证据不足"),
                    "item_score": round(best_score, 2),
                    "evidence": best_evidence,
                    "reason": "简历命中评分标准关键词" if best_score > 0 else "简历中未发现充分证据，按保守策略给低分",
                    "confidence": "high" if best_score > 0 else "low",
                }
            )

        total_score += dim_score
        max_score += dim_max
        dimension_scores.append(
            {
                "dimension_name": dimension_name,
                "dimension_max": round(dim_max, 2),
                "dimension_score": round(dim_score, 2),
                "items": normalized_items,
            }
        )

    match_level = calculate_match_level(total_score, max_score)
    summary = f"规则评分完成，总分 {round(total_score, 2)}/{round(max_score, 2)}，结论：{match_level}。"

    payload = {
        "score_id": uuid.uuid4().hex,
        "candidate_id": candidate_id,
        "score_source": "fallback",
        "score_status": "success",
        "model_name": model_name,
        "prompt_id": prompt_id,
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "match_level": match_level,
        "summary": summary,
        "risk_flags": risk_flags,
        "dimension_scores": dimension_scores,
        "error_message": llm_error_message,
        "created_at": utc_now_iso(),
    }
    if llm_error_message:
        payload["score_status"] = "fallback"
        payload["risk_flags"] = risk_flags + [f"LLM 调用失败，已降级规则评分：{llm_error_message}"]
    return payload


def _sum_dimension_item_scores(items: Any) -> float:
    if not isinstance(items, list):
        return 0.0
    return sum(
        score_to_float(item.get("item_score", item.get("score", item.get("score_value", 0))))
        for item in items
        if isinstance(item, dict)
    )


def normalize_llm_auto_score_output(
    raw_output: dict[str, Any],
    *,
    fallback_max_score: float = 0.0,
) -> dict[str, Any]:
    raw_obj = raw_output if isinstance(raw_output, dict) else {}
    raw_dimension_scores = raw_obj.get("dimension_scores")
    if not isinstance(raw_dimension_scores, list):
        raw_dimension_scores = raw_obj.get("dimensions")
    dimensions_list = raw_dimension_scores if isinstance(raw_dimension_scores, list) else []

    dimension_scores: list[dict[str, Any]] = []
    for raw_dim in dimensions_list:
        if not isinstance(raw_dim, dict):
            continue
        dimension_name = str(
            raw_dim.get("dimension_name", "")
            or raw_dim.get("dimension", "")
            or raw_dim.get("name", "")
        ).strip() or "未命名维度"
        dimension_max = score_to_float(
            raw_dim.get("dimension_max", raw_dim.get("max_score", raw_dim.get("max", 0)))
        )
        dimension_score = score_to_float(
            raw_dim.get("dimension_score", raw_dim.get("score", raw_dim.get("score_value", 0)))
        )

        raw_items = raw_dim.get("items")
        items_list = raw_items if isinstance(raw_items, list) else []
        normalized_items: list[dict[str, Any]] = []
        for raw_item in items_list:
            if not isinstance(raw_item, dict):
                continue
            item_name = str(
                raw_item.get("item_name", "")
                or raw_item.get("point", "")
                or raw_item.get("point_name", "")
                or raw_item.get("name", "")
            ).strip()
            selected_standard = str(
                raw_item.get("selected_standard", "")
                or raw_item.get("criterion", "")
                or raw_item.get("indicator", "")
                or raw_item.get("standard", "")
            ).strip()
            item_score = score_to_float(
                raw_item.get("item_score", raw_item.get("score", raw_item.get("score_value", 0)))
            )
            evidence = _normalize_resume_text_items(raw_item.get("evidence"), limit=6)
            reason = str(raw_item.get("reason", "")).strip()
            confidence = str(raw_item.get("confidence", "")).strip().lower()
            if confidence not in {"high", "medium", "low"}:
                confidence = "high" if item_score > 0 else "low"
            normalized_items.append(
                {
                    "item_name": item_name,
                    "selected_standard": selected_standard,
                    "item_score": round(item_score, 2),
                    "evidence": evidence,
                    "reason": reason,
                    "confidence": confidence,
                }
            )

        if normalized_items:
            dimension_score = _sum_dimension_item_scores(normalized_items)

        dimension_scores.append(
            {
                "dimension_name": dimension_name,
                "dimension_max": round(dimension_max, 2),
                "dimension_score": round(dimension_score, 2),
                "items": normalized_items,
            }
        )

    overall_raw = raw_obj.get("overall")
    overall = overall_raw if isinstance(overall_raw, dict) else {}
    total_score = score_to_float(overall.get("total_score", raw_obj.get("total_score", 0)))
    max_score = score_to_float(overall.get("max_score", raw_obj.get("max_score", 0)))
    if dimension_scores:
        total_score = sum(score_to_float(item.get("dimension_score")) for item in dimension_scores)
    if total_score <= 0 and dimension_scores:
        total_score = sum(score_to_float(item.get("dimension_score")) for item in dimension_scores)
    if max_score <= 0 and dimension_scores:
        max_score = sum(score_to_float(item.get("dimension_max")) for item in dimension_scores)
    if max_score <= 0:
        max_score = max(fallback_max_score, 0.0)

    risk_flags = _normalize_resume_text_items(overall.get("risk_flags", raw_obj.get("risk_flags", [])), limit=20)
    match_level = str(overall.get("match_level", raw_obj.get("match_level", ""))).strip()
    if not match_level:
        match_level = calculate_match_level(total_score, max_score)
    summary = str(overall.get("summary", raw_obj.get("summary", ""))).strip()
    if not summary:
        summary = f"LLM 自动评分完成，总分 {round(total_score, 2)}/{round(max_score, 2)}，结论：{match_level}。"

    meta_raw = raw_obj.get("meta")
    meta_obj = meta_raw if isinstance(meta_raw, dict) else {}
    thresholds_raw = meta_obj.get("thresholds")
    thresholds_obj = thresholds_raw if isinstance(thresholds_raw, dict) else {}
    normalized_meta = {
        "job_name": str(meta_obj.get("job_name", "")).strip(),
        "score_table_version": str(meta_obj.get("score_table_version", "")).strip(),
        "max_score": round(max_score, 2),
        "thresholds": {
            "strong_threshold": score_to_float(thresholds_obj.get("strong_threshold")),
            "recommend_threshold": score_to_float(thresholds_obj.get("recommend_threshold")),
            "review_threshold": score_to_float(thresholds_obj.get("review_threshold")),
        },
    }

    return {
        "meta": normalized_meta,
        "dimension_scores": dimension_scores,
        "overall": {
            "total_score": round(total_score, 2),
            "max_score": round(max_score, 2),
            "match_level": match_level,
            "summary": summary,
            "risk_flags": risk_flags,
        },
    }


def call_llm_auto_score(
    *,
    runtime: dict[str, Any],
    snapshot: dict[str, Any],
    resume_text: str,
    resume_structured: Any,
    candidate_id: str,
) -> tuple[dict[str, Any], str]:
    if not bool(runtime.get("enabled", False)):
        return {}, "LLM 未启用"
    model = str(runtime.get("model", "")).strip()
    if not model:
        return {}, "LLM 配置不完整"

    prompt, prompt_error = load_active_prompt(runtime)
    if prompt_error:
        return {}, prompt_error

    system_prompt = str(prompt.get("system_prompt", "")).strip()
    user_prompt_template = str(prompt.get("user_prompt_template", "")).strip()
    if not system_prompt or not user_prompt_template:
        return {}, "Prompt 配置缺失"

    max_score = score_to_float(snapshot.get("max_score", 0))
    score_table_payload = format_score_table_for_prompt(snapshot.get("score_items"))
    if max_score <= 0:
        max_score = score_to_float(score_table_payload.get("max_score", 0))
    strong_threshold = max(round(max_score * 0.85, 2), 1.0)
    recommend_threshold = max(round(max_score * 0.7, 2), 1.0)
    review_threshold = max(round(max_score * 0.5, 2), 1.0)
    candidate_profile_payload, resume_supplement = _build_candidate_scoring_inputs(
        resume_structured=resume_structured,
        resume_text=resume_text,
    )

    variables = {
        "job_name": str(snapshot.get("job_title", "")),
        "job_jd": str(snapshot.get("jd", "")),
        "screening_requirements": json.dumps(snapshot.get("criteria", {}), ensure_ascii=False),
        "score_table_version": str(snapshot.get("score_table_version", "")),
        "score_table_json": json.dumps(score_table_payload, ensure_ascii=False),
        "candidate_id": candidate_id,
        "candidate_profile_json": json.dumps(candidate_profile_payload, ensure_ascii=False),
        "resume_text": resume_supplement,
        "strong_threshold": str(strong_threshold),
        "recommend_threshold": str(recommend_threshold),
        "review_threshold": str(review_threshold),
    }
    user_prompt = render_prompt_template(user_prompt_template, variables)
    output_schema = prompt.get("output_schema")
    if isinstance(output_schema, dict):
        user_prompt += (
            "\n\n[输出结构约束]\n"
            "请仅输出一个 JSON 对象，且字段严格包含：meta、dimension_scores、overall。\n"
            f"schema={json.dumps(output_schema, ensure_ascii=False)}\n"
            "禁止输出 Markdown、解释文本、代码块标记。"
        )

    content, reasoning_content, stream_error = call_llm_chat_stream(
        runtime=runtime,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=float(runtime.get("temperature", 0.2) or 0.2),
        max_tokens=int(runtime.get("max_tokens", 2048) or 2048),
        enable_thinking=True,
    )
    if stream_error:
        return {}, stream_error

    parsed = parse_llm_json_response(str(content or ""))
    if not parsed and reasoning_content:
        parsed = parse_llm_json_response(reasoning_content)
    if not parsed:
        return {}, "LLM 返回内容不是有效 JSON"
    normalized_output = normalize_llm_auto_score_output(
        parsed,
        fallback_max_score=max_score,
    )

    prompt_id = str(prompt.get("prompt_id", "")).strip()
    return {
        "raw_output": normalized_output,
        "model_name": model,
        "prompt_id": prompt_id,
    }, ""


def normalize_llm_score_payload(
    *,
    candidate_id: str,
    raw_output: dict[str, Any],
    model_name: str,
    prompt_id: str,
) -> dict[str, Any]:
    dimension_scores_raw = raw_output.get("dimension_scores")
    dimension_scores = dimension_scores_raw if isinstance(dimension_scores_raw, list) else []
    total_score = score_to_float((raw_output.get("overall") or {}).get("total_score"))
    max_score = score_to_float((raw_output.get("overall") or {}).get("max_score"))
    if isinstance(dimension_scores, list) and dimension_scores:
        total_score = sum(score_to_float(item.get("dimension_score")) for item in dimension_scores if isinstance(item, dict))
    if total_score == 0 and isinstance(dimension_scores, list):
        total_score = sum(score_to_float(item.get("dimension_score")) for item in dimension_scores if isinstance(item, dict))
    if max_score == 0 and isinstance(dimension_scores, list):
        max_score = sum(score_to_float(item.get("dimension_max")) for item in dimension_scores if isinstance(item, dict))

    overall = raw_output.get("overall")
    overall_obj = overall if isinstance(overall, dict) else {}
    risk_flags = overall_obj.get("risk_flags")
    summary = str(overall_obj.get("summary", "")).strip()
    match_level = str(overall_obj.get("match_level", "")).strip()
    if not match_level:
        match_level = calculate_match_level(total_score, max_score)
    if not summary:
        summary = f"LLM 自动评分完成，总分 {round(total_score, 2)}/{round(max_score, 2)}，结论：{match_level}。"

    return {
        "score_id": uuid.uuid4().hex,
        "candidate_id": candidate_id,
        "score_source": "llm",
        "score_status": "success",
        "model_name": model_name,
        "prompt_id": prompt_id,
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "match_level": match_level,
        "summary": summary,
        "risk_flags": risk_flags if isinstance(risk_flags, list) else [],
        "dimension_scores": dimension_scores if isinstance(dimension_scores, list) else [],
        "error_message": "",
        "created_at": utc_now_iso(),
    }


def load_auto_score_by_candidate(
    conn: sqlite3.Connection,
    candidate_id: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT score_id, candidate_id, score_source, score_status, model_name, prompt_id,
               total_score, max_score, match_level, summary, risk_flags_json,
               dimension_scores_json, error_message, created_at
        FROM candidate_auto_scores
        WHERE candidate_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        return None
    try:
        risk_flags: Any = json.loads(row[10] or "[]")
    except json.JSONDecodeError:
        risk_flags = []
    try:
        dimension_scores: Any = json.loads(row[11] or "[]")
    except json.JSONDecodeError:
        dimension_scores = []
    return {
        "score_id": row[0],
        "candidate_id": row[1],
        "score_source": row[2],
        "score_status": row[3],
        "model_name": row[4],
        "prompt_id": row[5],
        "total_score": float(row[6] or 0),
        "max_score": float(row[7] or 0),
        "match_level": row[8] or "",
        "summary": row[9] or "",
        "risk_flags": risk_flags if isinstance(risk_flags, list) else [],
        "dimension_scores": dimension_scores if isinstance(dimension_scores, list) else [],
        "error_message": row[12] or "",
        "created_at": row[13] or "",
    }


def save_auto_score(
    conn: sqlite3.Connection,
    candidate_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    score_id = str(payload.get("score_id", "")).strip() or uuid.uuid4().hex
    now = str(payload.get("created_at", "")).strip() or utc_now_iso()
    conn.execute(
        """
        INSERT INTO candidate_auto_scores (
            score_id, candidate_id, score_source, score_status, model_name, prompt_id,
            total_score, max_score, match_level, summary, risk_flags_json,
            dimension_scores_json, error_message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            score_id,
            candidate_id,
            str(payload.get("score_source", "")),
            str(payload.get("score_status", "")),
            str(payload.get("model_name", "")),
            str(payload.get("prompt_id", "")),
            float(payload.get("total_score", 0) or 0),
            float(payload.get("max_score", 0) or 0),
            str(payload.get("match_level", "")),
            str(payload.get("summary", "")),
            json.dumps(payload.get("risk_flags", []), ensure_ascii=False),
            json.dumps(payload.get("dimension_scores", []), ensure_ascii=False),
            str(payload.get("error_message", "")),
            now,
        ),
    )
    saved = dict(payload)
    saved["score_id"] = score_id
    saved["candidate_id"] = candidate_id
    saved["created_at"] = now
    return saved


def trigger_auto_score_for_candidate(candidate_id: str) -> dict[str, Any]:
    with connect_db(DB_PATH) as conn:
        seed_candidate_profiles(conn)
        conn.commit()
        profile = load_profile(conn, candidate_id)
        file_row = get_candidate_file_by_id(conn, candidate_id)
        if profile is None or file_row is None or int(file_row.get("is_active", 0)) != 1:
            raise ValueError("candidate not found")

        raw_snapshot = str(profile.get("job_snapshot_json", "")).strip()
        if not raw_snapshot:
            raise ValueError("候选人未关联岗位配置")
        snapshot = _json_loads_or_empty_object(raw_snapshot)
        if not snapshot:
            raise ValueError("岗位配置无效")
        if not isinstance(snapshot.get("score_items"), list):
            snapshot["score_items"] = []
        if not snapshot["score_items"] and isinstance(snapshot.get("templates"), list):
            snapshot["score_items"] = build_score_items_from_templates(snapshot)
        if not bool(snapshot.get("auto_score_enabled", False)):
            raise ValueError("岗位未启用自动评分")

        resume_text = get_candidate_resume_text(conn, candidate_id=candidate_id)
        # 解析缓存属于文件级事实，需先提交，避免后续 LLM/评分异常导致缓存回滚丢失。
        conn.commit()

        score_items = dedupe_score_items_for_prompt(snapshot.get("score_items"))
        snapshot["score_items"] = score_items
        snapshot["max_score"] = round(calculate_score_items_max_score(score_items), 2)

        runtime = load_llm_runtime_config()
        llm_result, llm_error = call_llm_auto_score(
            runtime=runtime,
            snapshot=snapshot,
            resume_text=resume_text,
            resume_structured=profile.get("resume_structured"),
            candidate_id=candidate_id,
        )
        if llm_result:
            score_payload = normalize_llm_score_payload(
                candidate_id=candidate_id,
                raw_output=llm_result.get("raw_output", {}),
                model_name=str(llm_result.get("model_name", "")),
                prompt_id=str(llm_result.get("prompt_id", "")),
            )
        else:
            score_payload = score_with_fallback_rules(
                candidate_id=candidate_id,
                snapshot=snapshot,
                resume_text=resume_text,
                model_name=str(runtime.get("model", "")),
                prompt_id=str(runtime.get("active_prompt_id", "")),
                llm_error_message=llm_error,
            )

        saved = save_auto_score(conn, candidate_id, score_payload)
        conn.commit()
    return saved


__all__ = [
    "score_keywords",
    "calculate_match_level",
    "score_with_fallback_rules",
    "normalize_llm_auto_score_output",
    "call_llm_auto_score",
    "normalize_llm_score_payload",
    "load_auto_score_by_candidate",
    "save_auto_score",
    "trigger_auto_score_for_candidate",
]
