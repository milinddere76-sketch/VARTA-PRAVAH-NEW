# VartaPravah Local-to-Remote Deployer
# Fixed version to avoid encoding issues

$SERVER_IP = "157.180.24.243"
$REMOTE_USER = "root"

Write-Host "--- Starting Deployment to $SERVER_IP ---" -ForegroundColor Cyan

# Check if SSH key exists, if not, generate one
$SSH_DIR = "$HOME\.ssh"
$PUB_KEY = "$SSH_DIR\id_rsa.pub"

if (-not (Test-Path $PUB_KEY)) {
    Write-Host "--- No SSH key found locally. Generating one now ---" -ForegroundColor Yellow
    # Ensure .ssh dir exists
    if (-not (Test-Path $SSH_DIR)) { New-Item -ItemType Directory -Path $SSH_DIR | Out-Null }
    # Generate key
    ssh-keygen -t rsa -b 4096 -f "$SSH_DIR\id_rsa" -N ""
}

Write-Host "--- Uploading setup files to server ---" -ForegroundColor Cyan
scp -O .\setup_hetzner.sh "$($REMOTE_USER)@$($SERVER_IP):~/setup_hetzner.sh"
scp -O .\docker-compose.yml "$($REMOTE_USER)@$($SERVER_IP):~/docker-compose.yml"

Write-Host "--- Running remote installation (this will take a few minutes) ---" -ForegroundColor Cyan
ssh -o StrictHostKeyChecking=no "$($REMOTE_USER)@$($SERVER_IP)" "chmod +x ~/setup_hetzner.sh && ./setup_hetzner.sh"

Write-Host "--- Installation Finished ---" -ForegroundColor Green
Write-Host "Please connect to your server to edit your .env and start the containers:"
Write-Host "ssh $($REMOTE_USER)@$($SERVER_IP)"
