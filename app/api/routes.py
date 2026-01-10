"""
API Routes for Payment Reconciliation Service
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from app.services.payment_service import PaymentService
from app.utils.storage import save_upload_file


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
