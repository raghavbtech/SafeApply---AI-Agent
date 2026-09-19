# SafeApply — Azure Deployment Guide & Cost Management

This guide documents the production deployment architecture for SafeApply on Microsoft Azure using **Azure Static Web Apps (Frontend)** and **Azure Container Apps (Backend)** with **Azure Blob Storage (Resumes)**, **Azure Cosmos DB (State & Mail Store)**, and **Azure AI Services**.

---

## 1. Cost-Conscious Architecture & Budget Controls

To prevent unexpected billing while maintaining production reliability, SafeApply utilizes serverless consumption and free tiers:

| Component | Target Azure Service | Recommended Tier | Monthly Cost Target |
|---|---|---|---|
| **Frontend UI** | Azure Static Web Apps | **Free Tier** | **$0.00** (Free SSL, global CDN, 100GB bandwidth) |
| **Backend REST API** | Azure Container Apps | **Consumption Tier** (Scale to 0) | **$0.00 - ~$5.00** (180,000 vCPU-sec, 360,000 GiB-sec free/mo) |
| **Resume Storage** | Azure Blob Storage | **Hot/Cool LRS (General Purpose v2)** | **< $0.50** (Minimal storage for PDF/DOCX) |
| **Mail & Audit Store** | Azure Cosmos DB | **Serverless Tier** | **< $1.00** (Pay-per-request, zero idle cost) |
| **Recruitment RAG** | Azure AI Search | **Free Tier (F0)** | **$0.00** (Up to 3 indexes, 50MB storage, 10k docs) |
| **Entity Extraction** | Azure AI Language | **Free Tier (F0)** | **$0.00** (5,000 text records/month) |
| **GenAI Explanation** | Azure AI Foundry | **Pay-as-you-go (Phi-4-mini-instruct)** | **~$1.00 - $3.00** (~$0.07 / 1M input tokens) |

> [!TIP]
> **Zero Idle Cost**: By setting `minReplicas = 0` on Azure Container Apps and using Cosmos DB Serverless, SafeApply incurs zero compute cost when not actively handling traffic.

### Setting Up an Azure Budget Alert
```bash
az consumption budget create \
  --budget-name "SafeApply-Monthly-Budget" \
  --amount 15 \
  --time-grain monthly \
  --start-date "2026-10-01" \
  --end-date "2027-10-01" \
  --notification-key-1 threshold=80 operator=GreaterThan contact-emails="your-email@domain.com"
```

---

## 2. Prerequisites & Local Container Validation

1. **Azure CLI**: Installed and authenticated (`az login`).
2. **Docker**: Installed for building container images.
3. **Resource Group**:
```bash
az group create --name rg-safeapply-prod --location eastus
```

### Local Container Build & Test
```bash
# Build the production Docker container
docker build -t safeapply-backend:latest .

# Run container locally on port 8000
docker run -p 8000:8000 \
  -e SAFEAPPLY_ENV=production \
  -e SAFEAPPLY_SESSION_SECRET="production-random-secret-key-minimum-32-chars-long" \
  safeapply-backend:latest

# Verify health check
curl http://127.0.0.1:8000/health/live
```

---

## 3. Backend Deployment: Azure Container Apps

### Step 1: Create Azure Container Registry (ACR)
```bash
az acr create --resource-group rg-safeapply-prod --name acrsafeapplyprod --sku Basic --admin-enabled true

# Log in and push image
az acr login --name acrsafeapplyprod
docker tag safeapply-backend:latest acrsafeapplyprod.azurecr.io/safeapply-backend:latest
docker push acrsafeapplyprod.azurecr.io/safeapply-backend:latest
```

### Step 2: Create Container Apps Environment
```bash
az containerapp env create \
  --name env-safeapply-prod \
  --resource-group rg-safeapply-prod \
  --location eastus
```

### Step 3: Create Private Resume Storage (Azure Blob Storage)
```bash
az storage account create \
  --name stgsafeapplyprod \
  --resource-group rg-safeapply-prod \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false

# Get connection string
STORAGE_CONN_STR=$(az storage account show-connection-string --name stgsafeapplyprod --resource-group rg-safeapply-prod --query connectionString -o tsv)

# Create private container
az storage container create \
  --name candidate-resumes \
  --account-name stgsafeapplyprod \
  --auth-mode key
```

### Step 4: Deploy the Backend Container App
```bash
az containerapp create \
  --name safeapply-api \
  --resource-group rg-safeapply-prod \
  --environment env-safeapply-prod \
  --image acrsafeapplyprod.azurecr.io/safeapply-backend:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --secrets \
    session-secret="your-production-session-secret-at-least-32-chars" \
    storage-conn="$STORAGE_CONN_STR" \
    openai-key="your-azure-openai-key" \
    search-key="your-azure-search-key" \
    language-key="your-azure-language-key" \
    cosmos-key="your-azure-cosmos-key" \
  --env-vars \
    SAFEAPPLY_ENV="production" \
    PORT="8000" \
    SAFEAPPLY_SESSION_SECRET=secretref:session-secret \
    SAFEAPPLY_COOKIE_SECURE="true" \
    SAFEAPPLY_COOKIE_SAMESITE="lax" \
    AZURE_STORAGE_CONNECTION_STRING=secretref:storage-conn \
    AZURE_STORAGE_CONTAINER="candidate-resumes" \
    AZURE_OPENAI_ENDPOINT="https://your-foundry-endpoint.openai.azure.com/" \
    AZURE_OPENAI_API_KEY=secretref:openai-key \
    AZURE_OPENAI_DEPLOYMENT_NAME="Phi-4-mini-instruct" \
    AZURE_SEARCH_ENDPOINT="https://your-search-service.search.windows.net" \
    AZURE_SEARCH_KEY=secretref:search-key \
    AZURE_SEARCH_INDEX_NAME="safeapply-scam-patterns" \
    AZURE_LANGUAGE_ENDPOINT="https://your-language.cognitiveservices.azure.com/" \
    AZURE_LANGUAGE_KEY=secretref:language-key \
    COSMOS_ENDPOINT="https://your-cosmos.documents.azure.com:443/" \
    COSMOS_KEY=secretref:cosmos-key \
    COSMOS_DATABASE="safeapply" \
    SAFEAPPLY_CORS_ORIGINS="https://your-static-web-app.azurestaticapps.net"
```

---

## 4. Frontend Deployment: Azure Static Web Apps

### Step 1: Build the React Application
```bash
cd frontend
npm install
npm run build
```

### Step 2: Deploy to Azure Static Web Apps
```bash
# Using Azure CLI or GitHub Actions
az staticwebapp create \
  --name safeapply-ui \
  --resource-group rg-safeapply-prod \
  --location eastus2 \
  --source dist/
```

### Step 3: Configure Reverse Proxy / SWA Routing
The file `frontend/staticwebapp.config.json` is automatically recognized by Azure Static Web Apps. It ensures:
- All React router client paths (`/scan`, `/inbox`, `/jobs`, etc.) rewrite to `/index.html`.
- Strict security headers (`X-Frame-Options: DENY`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`).

---

## 5. Verification & Health Monitoring

1. **Liveness Probe**:
   ```bash
   curl -I https://safeapply-api.<app-id>.eastus.azurecontainerapps.io/health/live
   # Expected: HTTP/1.1 200 OK
   ```

2. **Readiness Probe**:
   ```bash
   curl https://safeapply-api.<app-id>.eastus.azurecontainerapps.io/health/ready
   # Expected JSON: {"status":"ready","storage_backend":"...","services":{...}}
   ```

3. **Anonymous Session Issuance**:
   ```bash
   curl -i https://safeapply-api.<app-id>.eastus.azurecontainerapps.io/api/v1/session
   # Expected: Set-Cookie: safeapply_session=...; HttpOnly; Secure; SameSite=lax
   ```

---

## 6. Rollback & Teardown Procedures

### Rollback Container Version
```bash
az containerapp revision set-active \
  --name safeapply-api \
  --resource-group rg-safeapply-prod \
  --revision <previous-revision-name>
```

### Complete Teardown (Stop all billing)
```bash
az group delete --name rg-safeapply-prod --yes --no-wait
```
