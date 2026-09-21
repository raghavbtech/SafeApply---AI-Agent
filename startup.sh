#!/bin/bash
# Azure App Service Startup Script for SafeApply

# Streamlit Interface (Port 8000 for Azure App Service)
streamlit run app.py --server.port 8000 --server.address 0.0.0.0
