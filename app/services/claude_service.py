"""
Claude Service - LLM analysis for reconciliation results
Uses OpenRouter API to access Claude and other LLMs
"""
import os
from typing import Dict, Any, Optional
from app.utils.llm_client import OpenRouterClient, analyze_reconcilation


class ClaudeService:
    """
    LLM analysis service for reconciliation results
    Provides intelligent insights and recommendations
    """

    def __init__(self, api_key: Optional[str] = None):
        # Support OPENROUTER_API_KEY or ANTHROPIC_API_KEY
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY or ANTHROPIC_API_KEY is required")

        # Default model for analysis
        self.model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4.5")
        self.client = OpenRouterClient(api_key=self.api_key)

    async def analyze_results(self, reconcile_data: Dict[str, Any]) -> str:
        """
        Analyze reconciliation results and generate insights

        Args:
            reconcile_data: Reconciliation results from ReconcileService

        Returns:
            Analysis report in natural language
        """
        if "error" in reconcile_data:
            return f"对账执行出错: {reconcile_data['error']}"

        try:
            return await analyze_reconcilation(
                reconcile_data,
                api_key=self.api_key,
                model=self.model
            )
        except Exception as e:
            return f"分析失败: {str(e)}"

    async def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000
    ) -> str:
        """
        Generic chat interface

        Args:
            prompt: User prompt
            model: Model override (optional)
            max_tokens: Maximum tokens in response

        Returns:
            LLM response
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            model = model or self.model
            return await self.client.chat(messages, model=model, max_tokens=max_tokens)
        finally:
            await self.client.close()
