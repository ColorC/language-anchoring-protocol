"""Anthropic 兼容 LLM 客户端"""

from __future__ import annotations

import os
from typing import Any

import anthropic

from lap.runtime.tools import ALL_TOOLS


class LLMClient:
    """Anthropic 兼容 API 客户端

    通过环境变量配置:
        ANTHROPIC_BASE_URL  — API endpoint
        ANTHROPIC_AUTH_TOKEN — API key
        ANTHROPIC_MODEL     — 模型名 (默认 qwen3.5-plus)
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ):
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "qwen3.5-plus")
        self.max_tokens = max_tokens
        self.tools = tools or ALL_TOOLS
        resolved_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        # SDK 0.84+ 会从 ANTHROPIC_AUTH_TOKEN 自动读取 bearer token,
        # 与第三方兼容端点 (如 DashScope) 冲突。创建 client 前临时移除。
        saved_auth = os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        try:
            self.client = anthropic.Anthropic(
                base_url=base_url or os.environ.get("ANTHROPIC_BASE_URL"),
                api_key=resolved_key,
            )
        finally:
            if saved_auth is not None:
                os.environ["ANTHROPIC_AUTH_TOKEN"] = saved_auth

    def call(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
    ) -> anthropic.types.Message:
        """调用 LLM，返回 Message 对象"""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
            "tools": self.tools,
        }
        if system:
            kwargs["system"] = system
        return self.client.messages.create(**kwargs)
