"""通义万相（DashScope）文生图 — 音色封面。"""

from __future__ import annotations

import time
from typing import Any

import httpx

from voice_platform.config import get_settings


class WanxError(Exception):
    def __init__(self, message: str, *, code: str = "WANX_ERROR") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class WanxClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.dashscope_api_key.strip()
        self._base = settings.dashscope_base_url.rstrip("/")
        self._model = settings.dashscope_wanx_model
        self._size = settings.dashscope_wanx_size
        self._poll_interval = settings.dashscope_wanx_poll_interval_sec
        self._poll_timeout = settings.dashscope_wanx_poll_timeout_sec
        self._negative = settings.dashscope_wanx_negative_prompt

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def generate_png(self, *, prompt: str) -> bytes:
        if not self.enabled:
            raise WanxError("未配置 DASHSCOPE_API_KEY", code="WANX_NOT_CONFIGURED")

        task_id = self._create_task(prompt)
        image_url = self._wait_for_image_url(task_id)
        return self._download(image_url)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }

    def _create_task(self, prompt: str) -> str:
        url = f"{self._base}/services/aigc/text2image/image-synthesis"
        payload: dict[str, Any] = {
            "model": self._model,
            "input": {
                "prompt": prompt,
                "negative_prompt": self._negative,
            },
            "parameters": {
                "size": self._size,
                "n": 1,
            },
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
        data = self._json_or_error(resp)
        output = data.get("output") or {}
        task_id = output.get("task_id")
        if not task_id:
            raise WanxError("万相未返回 task_id", code="WANX_BAD_RESPONSE")
        return str(task_id)

    def _wait_for_image_url(self, task_id: str) -> str:
        url = f"{self._base}/tasks/{task_id}"
        deadline = time.monotonic() + self._poll_timeout
        with httpx.Client(timeout=30.0) as client:
            while time.monotonic() < deadline:
                resp = client.get(url, headers={"Authorization": f"Bearer {self._api_key}"})
                data = self._json_or_error(resp)
                output = data.get("output") or {}
                status = str(output.get("task_status") or "").upper()
                if status in {"SUCCEEDED", "SUCCESS"}:
                    results = output.get("results") or []
                    if not results:
                        raise WanxError("万相任务成功但无图片结果", code="WANX_EMPTY_RESULT")
                    first = results[0]
                    image_url = first.get("url") if isinstance(first, dict) else None
                    if not image_url:
                        raise WanxError("万相结果缺少图片 URL", code="WANX_EMPTY_RESULT")
                    return str(image_url)
                if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                    msg = output.get("message") or output.get("code") or status
                    raise WanxError(f"万相生成失败: {msg}", code="WANX_TASK_FAILED")
                time.sleep(self._poll_interval)
        raise WanxError("万相生成超时", code="WANX_TIMEOUT")

    def _download(self, url: str) -> bytes:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content

    @staticmethod
    def _json_or_error(resp: httpx.Response) -> dict[str, Any]:
        try:
            data = resp.json()
        except Exception as exc:
            raise WanxError(f"万相响应解析失败: {resp.text[:200]}", code="WANX_BAD_RESPONSE") from exc
        if resp.status_code >= 400:
            msg = data.get("message") or data.get("code") or resp.text[:200]
            raise WanxError(f"万相 API 错误: {msg}", code="WANX_API_ERROR")
        if data.get("code"):
            raise WanxError(f"万相 API 错误: {data.get('message') or data['code']}", code="WANX_API_ERROR")
        return data
