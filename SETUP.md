# MySalonCast Developer Setup Guide

This guide helps new developers get MySalonCast running locally quickly and securely.

## 🚀 Quick Setup

### 1. Clone and Install Dependencies
```bash
git clone https://github.com/elliottng/my-salon-cast.git
cd my-salon-cast
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
# Copy the template and fill in your values
cp .env.test .env
# Edit .env with your actual configuration
nano .env  # or your preferred editor
```

**Required Settings:**
- `PROJECT_ID`: Your Google Cloud Project ID
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account JSON file

### 3. Set Up Google Cloud Credentials
```bash
# Copy the template and fill in your service account details
cp gcp-credentials.json.test gcp-credentials.json
# Edit with your actual service account key from Google Cloud Console
nano gcp-credentials.json
```

**To get a service account key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to IAM & Admin > Service Accounts
3. Create or select a service account
4. Create a new key (JSON format)
5. Download and save as `gcp-credentials.json`

### 4. Run the Application
```bash
# Start the MCP server
python -m app.mcp_server
```

The server will start on `http://localhost:8000`

## 🏗️ Infrastructure Setup (Optional)

### Terraform Deployment
```bash
cd terraform
# Copy the template and fill in your values
cp terraform.tfvars.test terraform.tfvars
# Edit with your actual configuration
nano terraform.tfvars

# Initialize and deploy
terraform init
terraform plan
terraform apply
```

## 📁 Configuration Files

| File | Purpose | Template Available |
|------|---------|-------------------|
| `.env` | Environment variables | ✅ `.env.test` |
| `gcp-credentials.json` | Google Cloud service account | ✅ `gcp-credentials.json.test` |
| `terraform/terraform.tfvars` | Infrastructure configuration | ✅ `terraform.tfvars.test` |

## 🔒 Security Notes

- **Never commit actual credentials** to git
- All sensitive files are in `.gitignore`
- Template files (`.test`) are safe to commit
- Use different service accounts for dev/staging/prod

## 🆘 Common Issues

### "Google Cloud Storage not available"
- Check your `GOOGLE_APPLICATION_CREDENTIALS` path
- Verify your service account has Storage permissions
- Ensure your project ID is correct

### "Missing required environment variables"
- Copy `.env.test` to `.env` and fill in values
- Check all required variables are set in `.env`

### Database Issues
- The app uses SQLite by default (no setup needed)
- For production, configure Cloud SQL in terraform

## 📞 Getting Help

If you encounter issues:
1. Check the logs in `server.log`
2. Verify all template files have been copied and configured
3. Ensure your Google Cloud project has the required APIs enabled
4. Contact the team for additional support
