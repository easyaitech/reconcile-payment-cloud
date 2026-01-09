"""
FastAPI Application - Payment Reconciliation Service
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router, set_payment_service
from app.services.payment_service import PaymentService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    port = os.getenv("PORT", "8000")

    # Use stdout for logging
    print(f"[STARTUP] PORT={port}")
    print(f"[STARTUP] OPENROUTER_API_KEY set: {bool(api_key)}")

    if not api_key:
        print("[WARNING] OPENROUTER_API_KEY not set - LLM features will be disabled")

    print("[STARTUP] Creating PaymentService...")
    payment_service = PaymentService(api_key=api_key)
    print("[STARTUP] PaymentService created")

    set_payment_service(payment_service)

    print("[INFO] Payment Reconciliation Service started")
    yield

    # Shutdown
    print("[INFO] Payment Reconciliation Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Payment Reconciliation API",
    description="LLM-driven intelligent payment reconciliation service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Payment Reconciliation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
