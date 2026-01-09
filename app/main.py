"""
FastAPI Application - Payment Reconciliation Service
"""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router, set_payment_service
from app.services.payment_service import PaymentService

# Get static files directory
STATIC_DIR = Path(__file__).parent / "static"

# Initialize services on module load
api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("[WARNING] OPENROUTER_API_KEY not set - LLM features will be disabled")

payment_service = PaymentService(api_key=api_key)
set_payment_service(payment_service)
print("[INFO] Payment Reconciliation Service initialized")

# Create FastAPI app
app = FastAPI(
    title="Payment Reconciliation API",
    description="LLM-driven intelligent payment reconciliation service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Serve frontend page"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "service": "Payment Reconciliation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "frontend": "Frontend not found - please check static files"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
