"""
File Checker Service - LLM-powered file format detection and adaptation
Uses OpenRouter API to access Claude and other LLMs
"""
import os
import pandas as pd
from typing import Dict, Any, Optional
from app.utils.llm_client import OpenRouterClient, check_file_format


class FileCheckerService:
    """
    LLM-powered file pre-check service
    Detects format changes and suggests configuration adaptations
    """

    def __init__(self, api_key: Optional[str] = None):
        # Support OPENROUTER_API_KEY or ANTHROPIC_API_KEY
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY or ANTHROPIC_API_KEY is required")

        # Default model
        self.model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4.5")
        self.client = OpenRouterClient(api_key=self.api_key)

    async def check_files(
        self,
        deposit_path: str,
        withdraw_path: str,
        channel_paths: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Check uploaded files for format changes

        Args:
            deposit_path: Path to deposit file
            withdraw_path: Path to withdraw file
            channel_paths: Dictionary of {channel_name: file_path}

        Returns:
            {
                "needs_adaptation": bool,
                "changes": List[str],
                "suggested_config": Dict or None
            }
        """
        # Gather file information
        file_info = await self._gather_file_info(deposit_path, withdraw_path, channel_paths)

        # Call LLM to analyze
        try:
            analysis = await check_file_format(
                file_info,
                api_key=self.api_key,
                model=self.model
            )
            return analysis
        except Exception as e:
            # On error, assume no adaptation needed
            return {
                "needs_adaptation": False,
                "changes": [f"LLM analysis failed: {str(e)}"],
                "suggested_config": None
            }

    async def _gather_file_info(
        self,
        deposit_path: str,
        withdraw_path: str,
        channel_paths: Dict[str, str]
    ) -> str:
        """Gather information about uploaded files"""
        info_parts = []

        # Deposit file info
        if deposit_path and self._file_exists(deposit_path):
            deposit_info = self._get_file_columns(deposit_path, "充值文件")
            info_parts.append(deposit_info)

        # Withdraw file info
        if withdraw_path and self._file_exists(withdraw_path):
            withdraw_info = self._get_file_columns(withdraw_path, "提款文件")
            info_parts.append(withdraw_info)

        # Channel files info
        for channel_name, channel_path in channel_paths.items():
            if self._file_exists(channel_path):
                channel_info = self._get_file_columns(channel_path, f"渠道文件-{channel_name}")
                info_parts.append(channel_info)

        return "\n\n".join(info_parts)

    def _file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        from pathlib import Path
        return Path(file_path).exists()

    def _get_file_columns(self, file_path: str, file_type: str) -> str:
        """Extract column names from file"""
        try:
            # Try Excel first
            for header_row in [1, 0]:
                try:
                    df = pd.read_excel(file_path, engine="openpyxl", header=header_row)
                    if len(df.columns) > 1:
                        columns = [str(c) for c in df.columns[:10]]  # First 10 columns
                        sample_data = df.head(3).to_dict(orient="records")
                        return f"""{file_type}:
  列名: {columns}
  示例数据（前3行）:
  {sample_data}"""
                except Exception:
                    continue

            # Try CSV
            df = pd.read_csv(file_path, nrows=3)
            columns = [str(c) for c in df.columns[:10]]
            sample_data = df.head(3).to_dict(orient="records")
            return f"""{file_type}:
  列名: {columns}
  示例数据（前3行）:
  {sample_data}"""

        except Exception as e:
            return f"{file_type}: 读取失败 - {str(e)}"
