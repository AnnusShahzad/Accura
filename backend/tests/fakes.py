"""
Fake AI provider used by the tests: answers deterministically based on
which agent (generator / evaluator / reprompt / title) is calling.
"""

from __future__ import annotations

import asyncio
import json

from utils.exceptions import AIProviderError


class FakeAI:
    def __init__(self, scores=(90,), answer="Generated answer", fail_with: str | None = None,
                 tool_call: dict | None = None, delay: float = 0.0):
        self.scores = list(scores)
        self.answer = answer
        self.fail_with = fail_with
        self.tool_call = tool_call
        self.delay = delay
        self.calls: list[dict] = []

    async def __call__(self, user_id, provider, model, messages, **kwargs):
        self.calls.append({"provider": provider, "model": model, "messages": messages, **kwargs})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_with:
            raise AIProviderError(self.fail_with)
        last = messages[-1]["content"] or ""
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        if "Evaluate the response" in last:
            score = self.scores.pop(0) if len(self.scores) > 1 else self.scores[0]
            content = json.dumps({"score": score, "reasoning": f"scored {score}"})
        elif "rephrase the original prompt" in last:
            content = "Rephrased prompt"
        elif "generate a very short title" in last:
            content = "Fake Title"
        elif kwargs.get("tools") and self.tool_call and not any(m["role"] == "tool" for m in messages):
            return {"content": "", "usage": usage, "finish_reason": "tool_calls",
                    "tool_calls": [self.tool_call]}
        else:
            tool_outputs = [m["content"] for m in messages if m["role"] == "tool"]
            content = self.answer + (f" [{tool_outputs[0]}]" if tool_outputs else "")
        return {"content": content, "usage": usage, "finish_reason": "stop", "tool_calls": []}

    def install(self, monkeypatch):
        for mod in ("services.generator", "services.evaluator", "services.reprompt",
                    "services.title_generator"):
            monkeypatch.setattr(f"{mod}.chat_completion", self)
        return self
