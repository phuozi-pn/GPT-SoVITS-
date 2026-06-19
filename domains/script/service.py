from __future__ import annotations

import json
import re
from typing import Any

import httpx

from domains.compliance.gateway import ComplianceError, ComplianceGateway
from voice_platform.config import Settings, get_settings
from voice_platform.script.schemas import ScreenplayLineSchema

_SYSTEM_PROMPT = """你是配音剧本结构化助手。把用户输入的文本拆成可对白合成的列表。

只输出 JSON，格式严格为：
{"lines":[{"character":"角色名","text":"台词内容"}]}

规则：
1. 对话归属到说话角色；叙述、环境、动作描写 character 用「旁白」
2. 不得编造原文没有的内容；保持原文用语
3. 角色名简短且全文统一（如 方源、白凝冰）
4. 同角色连续对白可合并为一条 lines 项
5. 不要输出 markdown 或其它说明文字"""


class ScriptParseServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class ScriptParseService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        gateway: ComplianceGateway | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._gateway = gateway or ComplianceGateway()

    def is_enabled(self) -> bool:
        return bool(self._settings.script_parse_llm_enabled and self._settings.deepseek_api_key.strip())

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "provider": "deepseek",
            "model": self._settings.deepseek_model,
        }

    def parse_smart(self, text: str) -> list[ScreenplayLineSchema]:
        if not self.is_enabled():
            raise ScriptParseServiceError(
                "LLM_DISABLED",
                "AI 剧本分段未启用，请在服务端配置 DEEPSEEK_API_KEY",
                503,
            )

        max_len = self._settings.script_parse_max_chars
        try:
            cleaned = self._gateway._validate_text(text, max_len=max_len)
        except ComplianceError as exc:
            raise ScriptParseServiceError(exc.code, exc.message, exc.http_status) from exc

        if self._settings.script_parse_llm_mock:
            return self._mock_lines(cleaned)

        raw = self._call_deepseek(cleaned)
        return self._parse_llm_payload(raw)

    def _mock_lines(self, text: str) -> list[ScreenplayLineSchema]:
        if "白凝冰" in text:
            return [
                ScreenplayLineSchema(character="方源", text="你给我出来。"),
                ScreenplayLineSchema(character="白凝冰", text="你以为逃得掉吗？"),
            ]
        return [ScreenplayLineSchema(character="旁白", text=text[:500])]

    def _call_deepseek(self, text: str) -> str:
        url = f"{self._settings.deepseek_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._settings.deepseek_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.deepseek_api_key.strip()}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self._settings.script_parse_timeout_sec)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ScriptParseServiceError(
                "LLM_UNAVAILABLE",
                "无法连接 DeepSeek API",
                502,
            ) from exc

        if resp.status_code >= 400:
            detail = resp.text[:240]
            raise ScriptParseServiceError(
                "LLM_ERROR",
                f"DeepSeek 返回错误 ({resp.status_code}): {detail}",
                502,
            )

        try:
            body = resp.json()
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ScriptParseServiceError(
                "LLM_BAD_RESPONSE",
                "DeepSeek 响应格式异常",
                502,
            ) from exc

    def _parse_llm_payload(self, content: str) -> list[ScreenplayLineSchema]:
        raw_json = content.strip()
        fence = _JSON_FENCE.search(raw_json)
        if fence:
            raw_json = fence.group(1).strip()

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ScriptParseServiceError(
                "LLM_BAD_RESPONSE",
                "DeepSeek 未返回有效 JSON",
                502,
            ) from exc

        lines_raw = data.get("lines") if isinstance(data, dict) else None
        if not isinstance(lines_raw, list) or not lines_raw:
            raise ScriptParseServiceError(
                "LLM_BAD_RESPONSE",
                "JSON 中缺少 lines 数组",
                502,
            )

        out: list[ScreenplayLineSchema] = []
        for item in lines_raw:
            if not isinstance(item, dict):
                continue
            character = str(item.get("character", "")).strip()
            line_text = str(item.get("text", "")).strip()
            if not character or not line_text:
                continue
            if len(character) > 24:
                character = character[:24]
            out.append(ScreenplayLineSchema(character=character, text=line_text))

        if not out:
            raise ScriptParseServiceError(
                "LLM_BAD_RESPONSE",
                "未解析到有效对白行",
                502,
            )
        return out
