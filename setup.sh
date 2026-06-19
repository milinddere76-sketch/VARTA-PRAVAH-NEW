#!/bin/bash
# Helper script to setup SSH keys and Swap file on Hetzner

echo "🚀 Starting Hetzner server setup..."

# 1. Register SSH Key
mkdir -p /root/.ssh
public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCYcWkpCyWhAMUnXWrWN1mOM1lplupWDDSoZj4G8y5+yEKKds12zzxvVA16gGHD8MmxJCJ/wj89wEgzPY3JtLsraf62A0Kz+mBcZWUR8qBF701CPDWY1jVzGJmN/rKd6CoqWRF/f9iwmX/jhr17LHFXJay48DqNUZNSzjmqWm/U2tVAbNrxSFv1tUTYOdKCHBiUsAIYk4ymtraiSaaeGFg35WTIiB0LkAxkAGxwV9y2gwUWbB4XU6PXSOhdXT3BVBky0Zn2HaVL+mYp9Dk97pfw7WRnZtDvOFfIAqI72gl5uvwugHv2yIzltuIMlLDRjHQzPAGP7FvEs/dYI0EWJ0fb"

if ! grep -q "AAAAB3NzaC1yc2EAAAADAQABAAABAQCYcWkp" /root/.ssh/authorized_keys 2>/dev/null; then
    echo "$public_key" >> /root/.ssh/authorized_keys
    echo "✅ SSH public key registered!"
else
    echo "ℹ️ SSH public key already registered."
fi

chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys

# 2. Setup Swap Space (4GB)
if [ ! -f /swapfile ]; then
    echo "Creating 4GB Swap file..."
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap space created and activated!"
else
    echo "ℹ️ Swap file already exists."
fi

# Show status
free -h
swapon --show

echo "🎉 Hetzner server setup successfully completed!"
