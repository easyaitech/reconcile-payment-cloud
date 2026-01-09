#!/bin/sh
# Use PORT environment variable (Railway sets this), default to 8000
PORT=${PORT:-8000}
>&2 echo "=== START.SH === Port is: $PORT"
>&2 echo "=== START.SH === Executing: uvicorn app.main:app --host 0.0.0.0 --port $PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
