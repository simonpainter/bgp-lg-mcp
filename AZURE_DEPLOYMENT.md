# Azure App Service Deployment Guide

This guide walks you through deploying the BGP Looking Glass MCP Server to Microsoft Azure App Service.

## Prerequisites

- Azure subscription with an active account
- Azure CLI installed (`az` command)
- Git repository with this code pushed to GitHub/Azure Repos

## Step 1: Create Azure App Service

### Via Azure Portal

1. Navigate to **App Services** → **Create a new Web App**
2. Configure:
   - **Resource Group**: Create new or use existing
   - **Name**: Choose a unique name (e.g., `bgp-lg-mcp`)
   - **OS**: Linux
   - **Runtime**: Python 3.11 or 3.12
   - **App Service Plan**: At least Basic tier (B1 or higher)

3. Click **Create**

### Via Azure CLI

```bash
# Create resource group
az group create --name bgp-lg-rg --location eastus

# Create App Service Plan
az appservice plan create \
  --name bgp-lg-plan \
  --resource-group bgp-lg-rg \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group bgp-lg-rg \
  --plan bgp-lg-plan \
  --name bgp-lg-mcp \
  --runtime "PYTHON|3.12"
```

## Step 2: Configure Startup Command

After creating the App Service:

```bash
az webapp config set \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg \
  --startup-file "bash startup.sh"
```

## Step 3: Enable Always On

Prevents cold starts between requests:

```bash
az webapp config set \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg \
  --always-on true
```

## Step 4: Deploy Your Code

### Option A: Git Deployment (Recommended)

```bash
# Configure Git deployment
az webapp deployment source config-zip \
  --resource-group bgp-lg-rg \
  --name bgp-lg-mcp \
  --src deploy.zip

# Or use App Service Build Service
az webapp up \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg
```

### Option B: Direct File Upload

```bash
# Zip your project
zip -r deploy.zip . \
  -x "\.git/*" "\.venv/*" "__pycache__/*"

# Deploy
az webapp deployment source config-zip \
  --resource-group bgp-lg-rg \
  --name bgp-lg-mcp \
  --src deploy.zip
```

## Step 5: Monitor and Verify

### Check Deployment Status

```bash
# View app details
az webapp show \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg

# Get app URL
az webapp show \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg \
  --query defaultHostName \
  --output tsv
```

### View Live Logs

```bash
# Stream logs in real-time
az webapp log tail \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg
```

### Test the Health Endpoint

```bash
# Get your app URL
APP_URL=$(az webapp show \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg \
  --query defaultHostName \
  --output tsv)

# Test health check
curl https://${APP_URL}/health
```

### Test MCP Endpoint

```bash
# Test the MCP endpoint
curl https://${APP_URL}/mcp/
```

Expected response: SSE connection (requires proper client)

## Step 6: Optional - Set Up CI/CD Pipeline

Create `.github/workflows/azure-deploy.yml` for GitHub Actions:

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v
      continue-on-error: true
    
    - name: Deploy to Azure
      uses: azure/webapps-deploy@v2
      with:
        app-name: bgp-lg-mcp
        package: '.'
        publish-profile: ${{ secrets.AZURE_PUBLISH_PROFILE }}
```

To get the publish profile:
1. Go to App Service in Azure Portal
2. Click **Download publish profile**
3. In GitHub: Settings → Secrets and variables → New repository secret
4. Name: `AZURE_PUBLISH_PROFILE`
5. Value: Paste the downloaded profile content

## Configuration

### Environment Variables

Set environment variables in Azure Portal:

1. Navigate to **Settings** → **Configuration** → **Application settings**
2. Add any required variables:

```
FASTMCP_LOG_LEVEL=INFO
```

### Custom Domain

To use a custom domain:

1. Go to **Settings** → **Custom domains**
2. Follow Azure's domain verification process
3. Update DNS records with your domain provider

## Troubleshooting

### Cold Start Issues

**Problem**: First request times out

**Solution**:
- Ensure "Always On" is enabled
- Use at least Basic tier (B1)
- Check startup logs: `az webapp log tail`

### Module Not Found

**Problem**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**:
- Verify `requirements.txt` has all dependencies
- Check startup command runs pip install
- View deployment logs: `az webapp deployment log show`

### Health Check Fails

**Problem**: `/health` endpoint returns error

**Solution**:
- Verify `config.json` is present
- Check file permissions
- Review logs: `az webapp log tail`

### MCP Endpoint Not Responding

**Problem**: Cannot connect to `/mcp/`

**Solution**:
- Verify server is running: `curl https://{app-url}/health`
- Check for port binding issues in logs
- Ensure streamable-http transport is used

## Performance Tuning

### Increase Worker Processes

For higher load, edit `startup.sh`:

```bash
# Change from:
-w 1

# To (for multiple cores):
-w 2  # or based on your App Service tier
```

### Scaling Options

Vertical scaling (Azure Portal):
1. Go to **Scale up** → Choose higher tier (Standard, Premium)
2. Click **Apply**

Horizontal scaling:
1. Go to **Scale out** → Configure auto-scale rules
2. Note: Requires stateless configuration (currently supported)

## Cost Optimization

- **Basic tier (B1)**: ~$10-15/month for low traffic
- **Standard tier (S1)**: ~$50/month for higher traffic
- Use **Free tier** for testing only (limited resources)

## Environment Variables Configuration

The BGP Looking Glass MCP server supports environment variables for flexible deployment:

### Available Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSPORT_MODE` | `streamable-http` | Server transport: `stdio`, `sse`, or `streamable-http` |
| `SERVER_HOST` | `127.0.0.1` | Listen address (use `0.0.0.0` for Azure) |
| `SERVER_PORT` | `8000` | Listen port |
| `CONFIG_PATH` | `./config.json` | Path to configuration file |
| `BGP_SERVER_TIMEOUT` | (config default) | BGP connection timeout in seconds |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |

### Setting Environment Variables in Azure

1. **Via Azure Portal**:
   - Go to your App Service → **Settings** → **Configuration**
   - Click **New application setting**
   - Add each variable (e.g., `TRANSPORT_MODE=streamable-http`)
   - Click **Save**

2. **Via Azure CLI**:
   ```bash
   az webapp config appsettings set \
     --resource-group bgp-lg-rg \
     --name bgp-lg-mcp \
     --settings TRANSPORT_MODE=streamable-http SERVER_HOST=0.0.0.0 LOG_LEVEL=INFO
   ```

3. **Via local .env file** (for development):
   ```bash
   # Copy the example
   cp .env.example .env
   
   # Edit with your settings
   nano .env
   
   # Load before running
   export $(cat .env | xargs)
   python3 server.py
   ```

### Azure-Specific Recommendations

For optimal Azure App Service deployment, set these variables:

```bash
TRANSPORT_MODE=streamable-http
SERVER_HOST=0.0.0.0
LOG_LEVEL=INFO
```

Azure automatically provides the `PORT` environment variable, which the application uses for `SERVER_PORT`.

## Security Best Practices

1. **Enable HTTPS**: Azure enforces HTTPS by default
2. **Restrict IPs**: Configure access restrictions in **Networking**
3. **Use Managed Identity**: For Azure resource access
4. **Monitor**: Set up alerts in **Monitor** → **Alerts**
5. **Sensitive Config**: Store secrets (if needed) in **Key Vault** and reference via Managed Identity



## Cleanup

To delete all resources:

```bash
# Delete App Service (will prompt for confirmation)
az webapp delete \
  --name bgp-lg-mcp \
  --resource-group bgp-lg-rg

# Delete App Service Plan
az appservice plan delete \
  --name bgp-lg-plan \
  --resource-group bgp-lg-rg

# Delete entire resource group
az group delete \
  --name bgp-lg-rg
```

## Support

- Azure Documentation: https://learn.microsoft.com/azure/
- FastMCP Docs: https://gofastmcp.com/
- BGP Looking Glass MCP: Check GitHub issues
