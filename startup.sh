#!/bin/bash
# Azure App Service Startup Script for SafeApply (React 18 Frontend + FastAPI Backend)

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
