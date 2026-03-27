from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from .role_user_service import parse_bool_flag

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_LLM_CONFIG_PATH = ROOT_DIR / "config" / "llm-config.json"
ENV_NAME_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
CHUNKED_JSON_RE = re.compile(r"\{[\s\S]*\}", re.DOTALL)


def resolve_config_path(path_text: str, default_path: Path) -> Path:
    raw = (path_text or "").strip()
    if not raw:
        return default_path
    path = Path(raw)
    if path.is_absolute():
        return path
    return (ROOT_DIR / path).resolve()


def safe_read_json(path: Path) -> tuple[dict[str, Any], str]:
    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return {}, f"读取配置失败: {exc}"
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return {}, f"配置文件 JSON 非法: {exc}"
    if not isinstance(parsed, dict):
        return {}, "配置文件必须是对象"
    return parsed, ""


def resolve_llm_api_key(raw_value: str) -> tuple[str, str, bool]:
    value = (raw_value or "").strip()
    if not value:
        return "", "", False
    if ENV_NAME_PATTERN.fullmatch(value):
        resolved = os.environ.get(value, "").strip()
        return resolved, value, bool(resolved)
    return value, "INLINE_SECRET", True


def load_llm_runtime_config() -> dict[str, Any]:
    config_path = resolve_config_path(
        os.environ.get("RESUME_APP_LLM_CONFIG_PATH", ""),
        DEFAULT_LLM_CONFIG_PATH,
    )
    config, error = safe_read_json(config_path)
    runtime: dict[str, Any] = {
        "enabled": False,
        "provider": "",
        "model": "",
        "base_url": "",
        "api_key_env": "",
        "api_key": "",
        "api_key_present": False,
        "temperature": 0.2,
        "max_tokens": 2048,
        "timeout_seconds": 30,
        "prompt_config_path": str(ROOT_DIR / "config" / "llm-prompts.json"),
        "active_prompt_id": "",
        "source": "default",
        "config_path": str(config_path),
        "warning": error,
    }
    if error:
        return runtime

    enabled, enabled_error = parse_bool_flag(
        config.get("enabled"),
        default=False,
        field_name="enabled",
    )
    if enabled_error:
        runtime["warning"] = enabled_error
    runtime["enabled"] = bool(enabled)
    runtime["provider"] = str(config.get("provider", "")).strip()
    runtime["model"] = str(config.get("model", "")).strip()
    runtime["base_url"] = str(config.get("base_url", "")).strip()
    runtime["api_key_env"] = str(config.get("api_key_env", "")).strip()
    try:
        runtime["temperature"] = float(config.get("temperature", 0.2) or 0.2)
    except (TypeError, ValueError):
        runtime["temperature"] = 0.2
    try:
        runtime["max_tokens"] = int(config.get("max_tokens", 2048) or 2048)
    except (TypeError, ValueError):
        runtime["max_tokens"] = 2048
    try:
        runtime["timeout_seconds"] = int(config.get("timeout_seconds", 30) or 30)
    except (TypeError, ValueError):
        runtime["timeout_seconds"] = 30
    prompt_path = resolve_config_path(
        str(config.get("prompt_config_path", "")).strip(),
        ROOT_DIR / "config" / "llm-prompts.json",
    )
    runtime["prompt_config_path"] = str(prompt_path)
    runtime["active_prompt_id"] = str(config.get("active_prompt_id", "")).strip()
    runtime["source"] = "file"

    api_key, api_key_env, api_key_present = resolve_llm_api_key(runtime["api_key_env"])
    runtime["api_key"] = api_key
    runtime["api_key_env"] = api_key_env
    runtime["api_key_present"] = api_key_present
    return runtime


def public_llm_runtime_config() -> dict[str, Any]:
    runtime = load_llm_runtime_config()
    return {
        "enabled": bool(runtime.get("enabled", False)),
        "provider": str(runtime.get("provider", "")),
        "model": str(runtime.get("model", "")),
        "base_url": str(runtime.get("base_url", "")),
        "api_key_env": str(runtime.get("api_key_env", "")),
        "api_key_present": bool(runtime.get("api_key_present", False)),
        "temperature": runtime.get("temperature", 0.2),
        "max_tokens": runtime.get("max_tokens", 2048),
        "timeout_seconds": runtime.get("timeout_seconds", 30),
        "source": str(runtime.get("source", "")),
        "config_path": str(runtime.get("config_path", "")),
        "warning": str(runtime.get("warning", "")),
    }


def load_active_prompt(runtime: dict[str, Any]) -> tuple[dict[str, Any], str]:
    prompt_path = Path(str(runtime.get("prompt_config_path", "")).strip())
    prompt_config, error = safe_read_json(prompt_path)
    if error:
        return {}, error

    prompts = prompt_config.get("prompts")
    if not isinstance(prompts, list):
        return {}, "Prompt 配置缺少 prompts 列表"

    active_prompt_id = str(runtime.get("active_prompt_id", "")).strip()
    default_prompt_id = str(prompt_config.get("default_prompt_id", "")).strip()
    selected: dict[str, Any] | None = None
    for item in prompts:
        if not isinstance(item, dict):
            continue
        prompt_id = str(item.get("prompt_id", "")).strip()
        if active_prompt_id and prompt_id == active_prompt_id:
            selected = item
            break
        if not selected and default_prompt_id and prompt_id == default_prompt_id:
            selected = item
    if selected is None:
        selected = next((item for item in prompts if isinstance(item, dict)), None)
    if selected is None:
        return {}, "Prompt 配置为空"
    return selected, ""


def parse_llm_json_response(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        return {}

    def _try_load_dict(candidate: str) -> dict[str, Any]:
        if not candidate:
            return {}
        try:
            parsed_obj = json.loads(candidate)
            return parsed_obj if isinstance(parsed_obj, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _strip_markdown_fence(candidate: str) -> str:
        cleaned = candidate.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json|JSON)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def _repair_common_json_issues(candidate: str) -> str:
        source = str(candidate or "").strip().lstrip("\ufeff")
        if not source:
            return source

        source = re.sub(r",\s*([}\]])", r"\1", source)

        out: list[str] = []
        i = 0
        n = len(source)
        in_string = False
        escaped = False

        while i < n:
            ch = source[i]

            if not in_string:
                out.append(ch)
                if ch == '"':
                    in_string = True
                i += 1
                continue

            if escaped:
                out.append(ch)
                escaped = False
                i += 1
                continue

            if ch == "\\":
                out.append(ch)
                escaped = True
                i += 1
                continue

            if ch == '"':
                j = i + 1
                while j < n and source[j].isspace():
                    j += 1
                next_non_ws = source[j] if j < n else ""
                if next_non_ws in {",", "}", "]", ":"} or next_non_ws == "":
                    out.append(ch)
                    in_string = False
                else:
                    out.append(r"\"")
                i += 1
                continue

            if ch == "\n":
                out.append(r"\n")
                i += 1
                continue

            if ch == "\r":
                out.append(r"\r")
                i += 1
                continue

            if ch == "\t":
                out.append(r"\t")
                i += 1
                continue

            out.append(ch)
            i += 1

        repaired = "".join(out)
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        return repaired

    candidates: list[str] = [text]
    fenced = _strip_markdown_fence(text)
    if fenced and fenced not in candidates:
        candidates.append(fenced)

    match = CHUNKED_JSON_RE.search(fenced or text)
    if match:
        chunk = match.group(0).strip()
        if chunk and chunk not in candidates:
            candidates.append(chunk)

    for candidate in candidates:
        parsed = _try_load_dict(candidate)
        if parsed:
            return parsed

        repaired = _repair_common_json_issues(candidate)
        parsed = _try_load_dict(repaired)
        if parsed:
            return parsed

    return {}


def _normalize_llm_base_url(base_url: str) -> str:
    value = str(base_url or "").strip()
    if value.endswith("/chat/completions"):
        value = value[: -len("/chat/completions")]
    return value.rstrip("/")


def _normalize_openai_api_key(api_key: str) -> str:
    value = str(api_key or "").strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value


def call_llm_chat_stream(
    *,
    runtime: dict[str, Any],
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    enable_thinking: bool = True,
) -> tuple[str, str, str]:
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _now_ms() -> int:
        return int(time.time() * 1000)

    def _obj_to_dict(obj: Any) -> dict[str, Any]:
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            try:
                dumped = obj.model_dump()
                return dumped if isinstance(dumped, dict) else {}
            except Exception:
                pass
        if hasattr(obj, "dict"):
            try:
                dumped = obj.dict()
                return dumped if isinstance(dumped, dict) else {}
            except Exception:
                pass
        if hasattr(obj, "__dict__"):
            try:
                dumped = dict(vars(obj))
                return dumped if isinstance(dumped, dict) else {}
            except Exception:
                pass
        return {}

    def _get_field(obj: Any, *field_paths: str) -> Any:
        if obj is None:
            return None

        for path in field_paths:
            current = obj
            ok = True
            for part in path.split("."):
                if current is None:
                    ok = False
                    break
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = getattr(current, part, None)
            if ok and current is not None:
                return current
        return None

    def _normalize_text_piece(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, dict):
            text_val = value.get("text")
            if isinstance(text_val, str):
                return text_val
            for key in ("content", "value", "reasoning_content", "reasoning"):
                item = value.get(key)
                if isinstance(item, str):
                    return item
                if isinstance(item, list):
                    merged = "".join(_normalize_text_piece(x) for x in item)
                    if merged:
                        return merged
            return ""
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                piece = _normalize_text_piece(item)
                if piece:
                    parts.append(piece)
            return "".join(parts)
        return ""

    def _safe_json_dumps(data: Any) -> str:
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception:
            return str(data)

    def _build_debug_info() -> dict[str, Any]:
        return {
            "model": model,
            "base_url": base_url,
            "timeout_seconds": timeout_seconds,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "enable_thinking_requested": bool(enable_thinking),
            "enable_thinking_used": None,
            "request_started_ms": None,
            "request_ended_ms": None,
            "duration_ms": None,
            "first_reasoning_ms": None,
            "first_content_ms": None,
            "chunk_count": 0,
            "non_empty_reasoning_chunks": 0,
            "non_empty_content_chunks": 0,
            "finish_reason": None,
            "usage": None,
            "sdk_fallback_used": False,
            "thinking_fallback_used": False,
            "stream_exception": "",
            "request_exception": "",
            "warnings": [],
            "last_chunk_preview": "",
            "response_has_content": False,
            "response_has_reasoning": False,
        }

    def _stream_once(
        *,
        client: Any,
        use_thinking: bool,
        debug_info: dict[str, Any],
    ) -> tuple[str, str, str, dict[str, Any]]:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []

        request_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": _safe_float(temperature, 0.0),
            "max_tokens": _safe_int(max_tokens, 512),
            "stream": True,
        }

        debug_info["enable_thinking_used"] = bool(use_thinking)
        debug_info["request_started_ms"] = _now_ms()

        try:
            try:
                if use_thinking:
                    completion = client.chat.completions.create(
                        **request_kwargs,
                        extra_body={"enable_thinking": True},
                    )
                else:
                    completion = client.chat.completions.create(**request_kwargs)
            except TypeError:
                debug_info["sdk_fallback_used"] = True
                completion = client.chat.completions.create(**request_kwargs)
            except Exception as exc:
                debug_info["request_exception"] = f"{type(exc).__name__}: {exc}"
                return "", "", f"LLM 请求失败: {exc}", debug_info

            for chunk in completion:
                debug_info["chunk_count"] += 1

                chunk_preview = ""
                try:
                    chunk_dict = _obj_to_dict(chunk)
                    if chunk_dict:
                        chunk_preview = _safe_json_dumps(chunk_dict)[:1000]
                    else:
                        chunk_preview = str(chunk)[:1000]
                except Exception:
                    chunk_preview = "<chunk_preview_failed>"
                debug_info["last_chunk_preview"] = chunk_preview

                choices = _get_field(chunk, "choices")
                if not isinstance(choices, list) or not choices:
                    usage_obj = _get_field(chunk, "usage")
                    if usage_obj is not None:
                        debug_info["usage"] = _obj_to_dict(usage_obj) or usage_obj
                    continue

                first_choice = choices[0]
                finish_reason = _get_field(first_choice, "finish_reason")
                if finish_reason:
                    debug_info["finish_reason"] = finish_reason

                delta = _get_field(first_choice, "delta")
                content_piece = _normalize_text_piece(
                    _get_field(delta, "content", "text", "message.content")
                    or _get_field(first_choice, "text", "message.content")
                )
                reasoning_piece = _normalize_text_piece(
                    _get_field(
                        delta,
                        "reasoning_content",
                        "reasoning",
                        "thinking",
                        "reasoning_text",
                        "message.reasoning_content",
                        "message.reasoning",
                    )
                    or _get_field(first_choice, "reasoning_content", "reasoning", "thinking")
                )

                if reasoning_piece:
                    if debug_info["first_reasoning_ms"] is None:
                        debug_info["first_reasoning_ms"] = _now_ms()
                    reasoning_parts.append(reasoning_piece)
                    debug_info["non_empty_reasoning_chunks"] += 1

                if content_piece:
                    if debug_info["first_content_ms"] is None:
                        debug_info["first_content_ms"] = _now_ms()
                    content_parts.append(content_piece)
                    debug_info["non_empty_content_chunks"] += 1

                usage_obj = _get_field(chunk, "usage") or _get_field(first_choice, "usage")
                if usage_obj is not None:
                    debug_info["usage"] = _obj_to_dict(usage_obj) or usage_obj

        except Exception as exc:
            debug_info["stream_exception"] = f"{type(exc).__name__}: {exc}"

            content_text = "".join(content_parts).strip()
            reasoning_text = "".join(reasoning_parts).strip()
            debug_info["response_has_content"] = bool(content_text)
            debug_info["response_has_reasoning"] = bool(reasoning_text)
            debug_info["request_ended_ms"] = _now_ms()
            debug_info["duration_ms"] = debug_info["request_ended_ms"] - debug_info["request_started_ms"]

            return content_text, reasoning_text, f"LLM 流式接收失败: {exc}", debug_info

        content_text = "".join(content_parts).strip()
        reasoning_text = "".join(reasoning_parts).strip()
        debug_info["response_has_content"] = bool(content_text)
        debug_info["response_has_reasoning"] = bool(reasoning_text)
        debug_info["request_ended_ms"] = _now_ms()
        debug_info["duration_ms"] = debug_info["request_ended_ms"] - debug_info["request_started_ms"]

        finish_reason = str(debug_info.get("finish_reason") or "").strip().lower()
        if finish_reason == "length":
            return content_text, reasoning_text, "LLM 响应被 max_tokens 截断", debug_info
        if not content_text:
            warning = f"LLM 流式响应缺少 content，finish_reason={debug_info.get('finish_reason') or 'unknown'}"
            debug_info["warnings"].append(warning)
            return "", reasoning_text, warning, debug_info
        return content_text, reasoning_text, "", debug_info

    api_key = _normalize_openai_api_key(str(runtime.get("api_key", "")).strip())
    base_url = _normalize_llm_base_url(str(runtime.get("base_url", "")).strip())

    if not api_key or not model or not base_url:
        return "", "", "LLM 配置不完整"

    try:
        from openai import OpenAI
    except Exception as exc:
        return "", "", f"OpenAI SDK 不可用: {exc}"

    timeout_seconds = _safe_int(runtime.get("timeout_seconds", 30) or 30, 30)
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return "", "", f"OpenAI Client 初始化失败: {exc}"

    debug_info = _build_debug_info()
    content_text, reasoning_text, error_text, debug_info = _stream_once(
        client=client,
        use_thinking=bool(enable_thinking),
        debug_info=debug_info,
    )

    auto_retry_without_thinking = bool(runtime.get("auto_retry_without_thinking", True))
    need_retry = bool(enable_thinking) and auto_retry_without_thinking and (bool(error_text) or not bool(content_text))
    if need_retry:
        retry_debug_info = _build_debug_info()
        retry_debug_info["thinking_fallback_used"] = True
        retry_debug_info["warnings"].append(
            f"首次请求失败，尝试关闭 thinking 降级重试；首次错误={error_text or '无 content'}"
        )
        retry_content, retry_reasoning, retry_error, retry_debug_info = _stream_once(
            client=client,
            use_thinking=False,
            debug_info=retry_debug_info,
        )
        if retry_content and not retry_error:
            retry_debug_info["warnings"].append("关闭 thinking 后降级重试成功")
            return retry_content, retry_reasoning, ""
        debug_info["warnings"].append(
            f"关闭 thinking 降级重试失败: {retry_error or '仍缺少 content'}"
        )

    return content_text, reasoning_text, error_text


def render_prompt_template(template: str, variables: dict[str, str]) -> str:
    output = template
    for key, value in variables.items():
        output = output.replace(f"{{{{{key}}}}}", value)
    return output


__all__ = [
    "call_llm_chat_stream",
    "load_active_prompt",
    "load_llm_runtime_config",
    "parse_llm_json_response",
    "public_llm_runtime_config",
    "render_prompt_template",
    "resolve_config_path",
    "resolve_llm_api_key",
    "safe_read_json",
]
