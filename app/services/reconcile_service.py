"""
Reconcile Service - Executes payment reconciliation
"""
import asyncio
from typing import Dict, Any, Optional
from app.core.reconcile import run_reconcile_sync


class ReconcileService:
    """
    Reconciliation execution service
    Supports dynamic configuration overrides for LLM adaptation
    """

    async def execute(
        self,
        deposit_path: str,
        withdraw_path: str,
        channel_paths: Dict[str, str],
        supplier_name: str = "RED",
        config_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute reconciliation with optional config override

        Args:
            deposit_path: Path to deposit file
            withdraw_path: Path to withdraw file
            channel_paths: Dictionary of {channel_name: file_path}
            supplier_name: Game supplier name
            config_override: LLM-generated configuration override

        Returns:
            Reconciliation results
        """
        # Run in separate thread to avoid blocking
        results = await asyncio.to_thread(
            run_reconcile_sync,
            deposit_path,
            withdraw_path,
            channel_paths,
            supplier_name,
            config_override
        )

        return results

    async def validate_files(
        self,
        deposit_path: str,
        withdraw_path: str,
        channel_paths: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Validate that all required files exist and are readable

        Returns:
            {
                "valid": bool,
                "errors": List[str]
            }
        """
        from pathlib import Path

        errors = []

        # Check deposit file
        if deposit_path and not Path(deposit_path).exists():
            errors.append(f"Deposit file not found: {deposit_path}")

        # Check withdraw file
        if withdraw_path and not Path(withdraw_path).exists():
            errors.append(f"Withdraw file not found: {withdraw_path}")

        # Check channel files
        for channel_name, channel_path in channel_paths.items():
            if not Path(channel_path).exists():
                errors.append(f"Channel file not found: {channel_path} ({channel_name})")

        # At least one deposit or withdraw file required
        if not deposit_path and not withdraw_path:
            errors.append("At least one deposit or withdraw file is required")

        # At least one channel file required
        if not channel_paths:
            errors.append("At least one channel file is required")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
