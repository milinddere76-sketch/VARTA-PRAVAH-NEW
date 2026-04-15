import paramiko

def fix_server():
    server = "157.180.24.243"
    user = "root"
    passw = "bjPTVWtCx3j9"

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, username=user, password=passw, timeout=15, 
                      look_for_keys=False, allow_agent=False)
        
        commands = [
            "docker ps -a --format 'table {{.Names}}\\t{{.Status}}'",
            "cd /root/vartapravah && docker compose up -d 2>&1 | tail -20",
            "docker ps --format 'table {{.Names}}\\t{{.Status}}'",
        ]
        
        for cmd in commands:
            print(f"\n--- {cmd} ---")
            stdin, stdout, stderr = client.exec_command(cmd)
            stdout.channel.recv_exit_status()
            print(stdout.read().decode() + stderr.read().decode())
            
        client.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    fix_server()
