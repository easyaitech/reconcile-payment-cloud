"""
Payment Service - Orchestrates the entire reconciliation workflow
"""
from typing import Dict, Any, Optional
from app.services.file_checker import FileCheckerService
from app.services.reconcile_service import ReconcileService
from app.services.claude_service import ClaudeService


class PaymentService:
    """
    LLM-driven intelligent reconciliation service
    Orchestrates file checking, adaptation, execution, and analysis
    """

    def __init__(self, api_key: Optional[str] = None):
        self.file_checker = FileCheckerService(api_key)
        self.reconcile = ReconcileService()
        self.claude = ClaudeService(api_key)

    async def execute(
        self,
        deposit_path: str,
        withdraw_path: str,
        channel_paths: Dict[str, str],
        supplier_name: str = "RED",
        enable_adaptation: bool = True,
        enable_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Execute intelligent reconciliation

        Args:
            deposit_path: Path to deposit file
            withdraw_path: Path to withdraw file
            channel_paths: Dictionary of {channel_name: file_path}
            supplier_name: Game supplier name
            enable_adaptation: Enable LLM file format adaptation
            enable_analysis: Enable LLM result analysis

        Returns:
            {
                "file_check": {...},      # File format check results
                "adaptation": str or None, # Adaptation description
                "data": {...},             # Reconciliation results
                "analysis": str or None    # LLM analysis report
            }
        """
        response = {
            "file_check": None,
            "adaptation": None,
            "data": None,
            "analysis": None,
            "success": False
        }

        config_override = None

        # Step 1: File pre-check (if adaptation enabled)
        if enable_adaptation:
            try:
                check_result = await self.file_checker.check_files(
                    deposit_path, withdraw_path, channel_paths
                )
                response["file_check"] = check_result

                if check_result.get("needs_adaptation"):
                    config_override = check_result.get("suggested_config")
                    response["adaptation"] = f"已应用 LLM 生成的配置: {', '.join(check_result.get('changes', []))}"
            except Exception as e:
                response["adaptation_error"] = str(e)

        # Step 2: Validate files
        validation = await self.reconcile.validate_files(
            deposit_path, withdraw_path, channel_paths
        )
        if not validation["valid"]:
            response["validation_errors"] = validation["errors"]
            return response

        # Step 3: Execute reconciliation
        try:
            results = await self.reconcile.execute(
                deposit_path, withdraw_path, channel_paths,
                supplier_name, config_override
            )
            response["data"] = results

            if "error" not in results:
                response["success"] = True
        except Exception as e:
            response["data"] = {"error": str(e)}
            return response

        # Step 4: Analyze results (if analysis enabled)
        if enable_analysis and "error" not in response.get("data", {}):
            try:
                analysis = await self.claude.analyze_results(response["data"])
                response["analysis"] = analysis
            except Exception as e:
                response["analysis_error"] = str(e)

        return response

    async def quick_reconcile(
        self,
        deposit_path: str,
        withdraw_path: str,
        channel_paths: Dict[str, str],
        supplier_name: str = "RED"
    ) -> Dict[str, Any]:
        """
        Quick reconciliation without LLM features

        Returns:
            Reconciliation results only
        """
        validation = await self.reconcile.validate_files(
            deposit_path, withdraw_path, channel_paths
        )

        if not validation["valid"]:
            return {
                "success": False,
                "validation_errors": validation["errors"]
            }

        results = await self.reconcile.execute(
            deposit_path, withdraw_path, channel_paths, supplier_name
        )

        return {
            "success": "error" not in results,
            "data": results
        }
