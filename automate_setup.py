import paramiko
from scp import SCPClient
import os
import sys

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

def main():
    server = "157.180.24.243"
    user = "root"
    password = "4wRHVHKeEagw"
    
    print(f"--- Connecting to {server}...")
    try:
        ssh = create_ssh_client(server, user, password)
    except Exception as e:
        import traceback
        print(f"[!] Connection failed: {e}")
        traceback.print_exc()
        return

    print("--- Uploading files...")
    with SCPClient(ssh.get_transport()) as scp:
        scp.put("setup_hetzner.sh", "setup_hetzner.sh")
        scp.put("docker-compose.yml", "docker-compose.yml")

    network = "t892o397h64afn1mgn4lndi3_vartapravah-net"
    pg_container = "postgres-t892o397h64afn1mgn4lndi3-164510756285"
    tp_container = "temporal-t892o397h64afn1mgn4lndi3-164510795403"
    worker_container = "backend-worker-t892o397h64afn1mgn4lndi3-164510923981"

    print(f"--- Running Temporal Schema Setup on network {network}...")
    
    # 1. Setup schema
    setup_cmd = f"docker run --rm --network {network} temporalio/auto-setup:1.24.2 temporal-sql-tool --endpoint {pg_container} --port 5432 --user temporal --password temporal --database temporal setup-schema -v 1.10"
    print(f"--- Executing: {setup_cmd}")
    stdin, stdout, stderr = ssh.exec_command(setup_cmd)
    for line in stdout: print(f"[REMOTE] {line.strip()}")
    
    # 2. Update schema
    update_cmd = f"docker run --rm --network {network} temporalio/auto-setup:1.24.2 temporal-sql-tool --endpoint {pg_container} --port 5432 --user temporal --password temporal --database temporal update-schema -d schema/postgresql/v12/temporal/versioned"
    print(f"--- Executing: {update_cmd}")
    stdin, stdout, stderr = ssh.exec_command(update_cmd)
    for line in stdout: print(f"[REMOTE] {line.strip()}")

    print("--- Restarting services to pick up the new database...")
    ssh.exec_command(f"docker restart {tp_container}")
    ssh.exec_command(f"docker restart {worker_container}")

    print("--- Done! Refresh your VartaPravah dashboard in 10 seconds. ---")
    ssh.close()

if __name__ == "__main__":
    main()
