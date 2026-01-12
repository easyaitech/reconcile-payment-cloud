"""
API Routes for Payment Reconciliation Service
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.services.payment_service import PaymentService
from app.utils.storage import save_upload_file
import json


router = APIRouter(prefix="/api/v1")

# Initialize service (will be initialized with API key on startup)
payment_service: Optional[PaymentService] = None


def set_payment_service(service: PaymentService):
    """Set the payment service instance"""
    global payment_service
    payment_service = service


@router.post("/reconcile")
async def reconcile(
    deposit: UploadFile = File(None),
    withdraw: UploadFile = File(None),
    channels: List[UploadFile] = File(...),
    supplier: str = Form("RED"),
    adapt: bool = Form(True),
    analyze: bool = Form(True)
):
    """
    Execute intelligent payment reconciliation

    Args:
        - deposit: Game deposit file (optional)
        - withdraw: Game withdraw file (optional)
        - channels: Payment channel files (at least one required)
        - supplier: Game supplier name (default: RED)
        - adapt: Enable LLM file format adaptation (default: true)
        - analyze: Enable LLM result analysis (default: true)

    Returns:
        {
            "success": true/false,
            "file_check": {...},      # File format check results
            "adaptation": str or None, # Adaptation description
            "data": {...},             # Reconciliation results
            "analysis": str or None    # LLM analysis report
        }
    """
    if payment_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Validate at least one file is provided
    if not deposit and not withdraw:
        raise HTTPException(status_code=400, detail="At least one deposit or withdraw file is required")

    if not channels:
        raise HTTPException(status_code=400, detail="At least one channel file is required")

    # Save uploaded files
    deposit_path = None
    withdraw_path = None
    channel_paths = {}

    if deposit:
        deposit_path = await save_upload_file(deposit, "uploads/")

    if withdraw:
        withdraw_path = await save_upload_file(withdraw, "uploads/")

    for f in channels:
        # Extract channel name from filename
        filename = f.filename or "unknown"
        channel_name = filename.rsplit('.', 1)[0].upper()
        channel_paths[channel_name] = await save_upload_file(f, "uploads/channels/")

    # Execute reconciliation
    results = await payment_service.execute(
        deposit_path or "",
        withdraw_path or "",
        channel_paths,
        supplier,
        adapt,
        analyze
    )

    return results


@router.get("/health")
async def health():
    """Health check endpoint"""
    from app.utils.storage import sanitize_filename

    test_filename = "test file (1).xlsx"
    sanitized = sanitize_filename(test_filename)

    return {
        "status": "ok",
        "service": "reconcile-payment-api",
        "version": "1.0.3",
        "sanitization_test": {
            "input": test_filename,
            "output": sanitized,
            "working": sanitized == "test_file_1.xlsx"
        }
    }


@router.post("/validate")
async def validate_files(
    deposit: UploadFile = File(None),
    withdraw: UploadFile = File(None),
    channels: List[UploadFile] = File(...)
):
    """
    Validate uploaded files without executing reconciliation

    Returns:
        {
            "valid": true/false,
            "files": {...},
            "errors": [...]
        }
    """
    if payment_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Save uploaded files temporarily
    deposit_path = None
    withdraw_path = None
    channel_paths = {}

    if deposit:
        deposit_path = await save_upload_file(deposit, "uploads/")

    if withdraw:
        withdraw_path = await save_upload_file(withdraw, "uploads/")

    for f in channels:
        filename = f.filename or "unknown"
        channel_name = filename.rsplit('.', 1)[0].upper()
        channel_paths[channel_name] = await save_upload_file(f, "uploads/channels/")

    # Validate
    validation = await payment_service.reconcile.validate_files(
        deposit_path or "",
        withdraw_path or "",
        channel_paths
    )

    return {
        "valid": validation["valid"],
        "files": {
            "deposit": deposit_path,
            "withdraw": withdraw_path,
            "channels": channel_paths
        },
        "errors": validation["errors"]
    }


# ==================== 配置管理 API ====================

CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.json"


@router.get("/config")
async def get_config():
    """
    获取配置文件

    Returns:
        {
            "success": true,
            "config": {...}  # 完整配置
        }
    """
    try:
        if not CONFIG_PATH.exists():
            return {"success": False, "error": "配置文件不存在"}

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return {"success": True, "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {str(e)}")


@router.post("/config")
async def update_config(config: Dict[str, Any]):
    """
    更新配置文件

    Args:
        config: 完整的配置对象

    Returns:
        {
            "success": true,
            "message": "配置已保存"
        }
    """
    try:
        # 备份原配置
        if CONFIG_PATH.exists():
            backup_path = CONFIG_PATH.with_suffix('.json.bak')
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                backup_path.write_text(f.read(), encoding='utf-8')

        # 写入新配置
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.post("/config/channel")
async def add_or_update_channel(
    channel_name: str = Form(...),
    order_id_column: str = Form("商户订单号"),
    amount_column: str = Form("金额"),
    status_column: str = Form("状态"),
    success_values: str = Form("成功,success,已完成,1")
):
    """
    添加或更新支付渠道配置

    Args:
        channel_name: 渠道名称 (如: BOSSPAY, antpay)
        order_id_column: 订单号列名
        amount_column: 金额列名
        status_column: 状态列名
        success_values: 成功状态值 (逗号分隔)

    Returns:
        {
            "success": true,
            "message": "渠道配置已更新"
        }
    """
    try:
        # 读取现有配置
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 标准化渠道名（小写）
        channel_key = channel_name.lower()

        # 更新渠道配置
        if "渠道配置" not in config:
            config["渠道配置"] = {}

        config["渠道配置"][channel_key] = {
            "游戏后台表配置": {
                "充值表": {
                    "字段映射": {
                        "订单编号": "订单编号",
                        "支付渠道": "支付渠道",
                        "状态": "状态",
                        "实际金额": "实际金额"
                    },
                    "状态筛选": "成功",
                    "渠道值": channel_key
                },
                "提款表": {
                    "字段映射": {
                        "订单编号": "订单编号",
                        "支付渠道": "支付渠道",
                        "状态": "状态",
                        "实际金额": "实际金额"
                    },
                    "状态筛选": "成功",
                    "渠道值": channel_key
                }
            },
            "渠道表配置": {
                "字段映射": {
                    "平台订单号": order_id_column,
                    "金额": amount_column,
                    "状态": status_column
                },
                "成功状态值": [v.strip() for v in success_values.split(",")]
            }
        }

        # 写回文件
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return {"success": True, "message": f"渠道 {channel_name} 配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存渠道配置失败: {str(e)}")


@router.delete("/config/channel/{channel_name}")
async def delete_channel(channel_name: str):
    """
    删除支付渠道配置

    Args:
        channel_name: 渠道名称

    Returns:
        {
            "success": true,
            "message": "渠道已删除"
        }
    """
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        channel_key = channel_name.lower()

        if "渠道配置" in config and channel_key in config["渠道配置"]:
            del config["渠道配置"][channel_key]

            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            return {"success": True, "message": f"渠道 {channel_name} 已删除"}
        else:
            raise HTTPException(status_code=404, detail=f"渠道 {channel_name} 不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除渠道失败: {str(e)}")


@router.get("/config/channels")
async def get_channels():
    """
    获取所有支付渠道列表

    Returns:
        {
            "success": true,
            "channels": [
                {"name": "BOSSPAY", "order_id_column": "商户订单号", ...},
                ...
            ]
        }
    """
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        channels = []
        for name, cfg in config.get("渠道配置", {}).items():
            channel_cfg = cfg.get("渠道表配置", {})
            channels.append({
                "name": name.upper(),
                "order_id_column": channel_cfg.get("字段映射", {}).get("平台订单号", "商户订单号"),
                "amount_column": channel_cfg.get("字段映射", {}).get("金额", "金额"),
                "status_column": channel_cfg.get("字段映射", {}).get("状态", "状态"),
                "success_values": channel_cfg.get("成功状态值", ["成功"])
            })

        return {"success": True, "channels": channels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取渠道列表失败: {str(e)}")
