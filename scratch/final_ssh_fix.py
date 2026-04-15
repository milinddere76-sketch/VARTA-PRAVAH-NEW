import paramiko
import os

def final_fix():
    server = "157.180.24.243"
    user = "root"
    passw = "bjPTVWtCx3j9"
    coolify_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFb70ZAv2b6EjB1SvFVWSqfQlocgXLnWJVpAfVZCc6c9"

    print(f"Connecting to {server}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, username=user, password=passw, timeout=15)
        
        print("Injecting Coolify Key...")
        cmd = f'echo "{coolify_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && systemctl restart ssh'
        stdin, stdout, stderr = client.exec_command(cmd)
        
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("DONE! Coolify Key is now ACTIVE on the server.")
        else:
            print(f"Error: {stderr.read().decode()}")
            
        client.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    final_fix()
