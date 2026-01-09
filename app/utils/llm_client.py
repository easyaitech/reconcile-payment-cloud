"""
OpenRouter LLM Client - Supports multiple LLM providers through OpenRouter
"""
import os
from typing import Dict, Any, Optional, List
import httpx


class OpenRouterClient:
    """
    OpenRouter API client for LLM requests
    Supports Claude, GPT, and other models through OpenRouter
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY or ANTHROPIC_API_KEY is required")

        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/songchou/reconcile-payment-cloud",
                "X-Title": "Payment Reconciliation Service"
            }
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "anthropic/claude-sonnet-4.5",
        max_tokens: int = 2000,
        temperature: float = 0
    ) -> str:
        """
        Send chat completion request

        Args:
            messages: List of {role, content} messages
            model: Model name (e.g., "anthropic/claude-sonnet-4.5")
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Response text content
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens
        }

        # Debug output
        import sys
        print(f"[DEBUG] LLM request: model={model}, messages={len(messages)}", file=sys.stderr)

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            print(f"[DEBUG] LLM response status: {response.status_code}", file=sys.stderr)

            if response.status_code != 200:
                print(f"[DEBUG] Response body: {response.text}", file=sys.stderr)

            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[DEBUG] LLM error: {e}", file=sys.stderr)
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions for common use cases
async def analyze_reconcilation(
    reconcile_data: Dict[str, Any],
    api_key: Optional[str] = None,
    model: str = "anthropic/claude-sonnet-4.5"
) -> str:
    """Analyze reconciliation results using LLM"""
    client = OpenRouterClient(api_key)

    try:
        summary = reconcile_data.get("summary", {})
        deposit_summary = summary.get("total_deposit", {})
        withdraw_summary = summary.get("total_withdraw", {})

        mismatched = reconcile_data.get("mismatched", [])
        missing_in_channel = reconcile_data.get("missing_in_channel", [])
        missing_in_game = reconcile_data.get("missing_in_game", [])

        prompt = f"""请分析以下支付对账结果，给出专业意见：

【对账汇总】
充值订单：
  - 总数: {deposit_summary.get('count', 0)} 笔
  - 匹配: {deposit_summary.get('matched', 0)} 笔
  - 匹配金额: ¥{deposit_summary.get('matched_amount', 0):.2f}
  - 总金额: ¥{deposit_summary.get('amount', 0):.2f}

提款订单：
  - 总数: {withdraw_summary.get('count', 0)} 笔
  - 匹配: {withdraw_summary.get('matched', 0)} 笔
  - 匹配金额: ¥{withdraw_summary.get('matched_amount', 0):.2f}
  - 总金额: ¥{withdraw_summary.get('amount', 0):.2f}

【异常统计】
- 金额不匹配: {len(mismatched)} 笔
- 渠道缺失: {len(missing_in_channel)} 笔
- 游戏缺失: {len(missing_in_game)} 笔

请分析：
1. 主要问题是什么
2. 可能的原因
3. 建议的处理方式
4. 风险评估

用简洁专业的语言输出报告。"""

        messages = [{"role": "user", "content": prompt}]
        return await client.chat(messages, model=model, max_tokens=2000)
    finally:
        await client.close()


async def check_file_format(
    file_info: str,
    api_key: Optional[str] = None,
    model: str = "anthropic/claude-sonnet-4.5"
) -> Dict[str, Any]:
    """Check file format using LLM"""
    import json
    import re

    client = OpenRouterClient(api_key)

    try:
        prompt = f"""你是一个支付对账系统的配置专家。请检查以下文件格式。

当前系统的标准配置预期：
- 游戏充值文件列名：订单编号、支付渠道、状态、实际金额
- 游戏提款文件列名：订单编号、支付渠道、状态、实际金额
- 渠道文件列名：商户订单号（或平台订单号）、金额、状态

上传文件的实际情况：
{file_info}

请分析：1. 列名是否有变化？
2. 如果有变化，请按以下 JSON 格式输出新的列名映射：
{{
    "has_changes": true,
    "changes": ["列名A变更为列名B", ...],
    "field_mapping": {{
        "deposit": {{"order_id_column": "实际列名", ...}},
        "withdraw": {{...}},
        "channels": {{"渠道名": {{"平台订单号": "实际列名", ...}}}}
    }}
}}

如果没有变化，输出：{{"has_changes": false}}

请只输出 JSON，不要包含其他文字。"""

        messages = [{"role": "user", "content": prompt}]
        response_text = await client.chat(messages, model=model, max_tokens=1500)

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "needs_adaptation": result.get("has_changes", False),
                "changes": result.get("changes", []),
                "suggested_config": {"field_mapping": result.get("field_mapping", {})} if result.get("has_changes") else None
            }

        return {
            "needs_adaptation": False,
            "changes": [],
            "suggested_config": None
        }
    finally:
        await client.close()
