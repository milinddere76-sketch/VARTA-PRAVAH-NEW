import paramiko
import os

def fetch_logs():
    server = "157.180.24.243"
    user = "root"
    passw = "bjPTVWtCx3j9"

    print(f"Connecting to {server}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Try password auth explicitly
        client.connect(
            server, 
            username=user, 
            password=passw, 
            timeout=15,
            look_for_keys=False,
            allow_agent=False
        )
        
        print("Fetching worker logs...")
        for cmd in [
            "docker logs vartapravah_worker --tail 60 2>&1",
            "docker ps --format 'table {{.Names}}\\t{{.Status}}'",
        ]:
            print(f"\n--- Running: {cmd} ---")
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            print(out or err)
            
        client.close()
    except Exception as e:
        print(f"Failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    fetch_logs()
