import paramiko

HOST = "100.84.254.18"
USER = "root"
PASSWORD = "311211"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
_, out, _ = ssh.exec_command(
    "docker compose -f /opt/accounting/docker-compose.yml "
    "-f /opt/accounting/docker-compose.lan.yml logs backend --tail 60 2>&1 "
    "| grep -i -A 12 -B 2 'excel\\|Traceback\\|Error' | tail -45",
    timeout=60,
)
print(out.read().decode(errors="replace"), flush=True)
ssh.close()
