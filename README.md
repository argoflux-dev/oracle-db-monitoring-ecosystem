# Oracle DB Metrics Monitoring & Alerting Ecosystem

An infrastructure project designed to automate Oracle Database monitoring and alerting using Prometheus, Alertmanager and Grafana. The system is fully managed as Code (IaC) by Ansible: secrets are encrypted at rest with Ansible Vault and served to the agent at runtime by HashiCorp Vault.

## 🏗️ System Architecture

The ecosystem is split into two distinct environments:
1. **Local Database Circuit**: A Python agent operating inside an isolated `venv` environment using **Oracle Thick Mode** (powered by Oracle Instant Client to support legacy database versions like Oracle 11g). The agent collects active session metrics and pushes them to the Pushgateway via a push model.
2. **Telemetry Circuit (VPS)**: A collection of isolated Docker containers interconnected within a private bridge network.

```
 Local machine                                   VPS
┌──────────────────────┐                ┌──────────────────────────────────────┐
│ main.py (agent)      │                │ 127.0.0.1:8200  Vault                │
│  → 127.0.0.1:8200 ───┼── SSH tunnel ──┼→ 127.0.0.1:9091 Pushgateway          │
│  → 127.0.0.1:9091 ───┼   (port 22)    │ 127.0.0.1:9090  Prometheus           │
└──────────────────────┘                │ 127.0.0.1:9093  Alertmanager         │
                                        │ 0.0.0.0:3000    Grafana (login form) │
 Any device ── http://VPS_IP:3000 ──────┼→                                     │
                                        └──────────────────────────────────────┘
```

## 🔐 Secret Management & Security

* **HashiCorp Vault**: The cornerstone of system security. Database credentials are never stored on the agent's disk: the agent fetches them from Vault into memory at startup. The local Python script (`main.py`) authenticates against the Vault API using the `hvac` client at startup and pulls database credentials directly into volatile RAM.
* **Ansible Vault**: Administrator's local configuration secrets are encrypted using the AES-256 algorithm (`credentials.yml`). Decryption occurs exclusively in memory during the playbook execution.

### Protecting Vault and Pushgateway: loopback binding + SSH tunnel

Docker publishes ports through its own iptables rules, which **bypass UFW**. A mapping such as `"8200:8200"` exposes the service to the whole internet even if UFW denies the port. Therefore:

* **Loopback-only publishing.** In `docker-compose.yml` Vault (8200), Pushgateway (9091), Prometheus (9090) and Alertmanager (9093) are published as `127.0.0.1:<port>:<port>`. They are unreachable from outside the VPS.
* **Encrypted channel for the agent.** The Vault root token and the database credentials would otherwise travel over plain HTTP (no TLS in this setup). `playbook-loc.yml` opens an SSH tunnel (`-L 127.0.0.1:8200:127.0.0.1:8200`, `-L 127.0.0.1:9091:127.0.0.1:9091`) and the agent talks to `127.0.0.1` locally. Everything is encrypted and authenticated by the SSH key.
* **Pushgateway has no authentication.** Keeping it behind the tunnel prevents third parties from injecting, overwriting or deleting metrics (e.g. to mask an outage or to trigger false alerts).
* **Tunnel resilience.** If `autossh` is installed, the tunnel reconnects automatically after network drops; keep-alive options (`ServerAliveInterval`, `ExitOnForwardFailure`) make dead tunnels fail fast.
* **Minimal firewall surface.** The only ports that need to be allowed in UFW are `22/tcp` (SSH and the tunnel) and `3000/tcp` (Grafana). Ports 8200, 9091, 9090 and 9093 must **not** be opened.
* **Secrets hygiene.** The Vault secret creation task runs with `no_log: true`, so database passwords never appear in Ansible output.

### Grafana

Grafana (port 3000) is intentionally published to be reachable from any device and is protected by its own login form. **Change the default `admin/admin` password right after the first login.** Traffic is plain HTTP; put Grafana behind a reverse proxy with TLS if you access it over untrusted networks.

> **Note:** Vault runs in **dev mode** (in-memory storage, root token, no TLS). This is suitable for a demo/test environment. For production use a regular Vault configuration with persistent storage, unseal keys, TLS and a least-privilege read-only policy/token for the agent.

## 📈 Tech Stack
* **Orchestration & Deployment**: Ansible (utilizing dynamic Jinja2 templates)
* **Containerization**: Docker / Docker Compose
* **Secret Storage**: HashiCorp Vault (KV v2 engine)
* **Metrics Collection**: Prometheus v3, Prometheus Pushgateway
* **Alerting**: Prometheus Alertmanager v0.25 (integrated with Mail.ru SMTP via STARTTLS protocol to successfully bypass TSPU/DPI network blocks)
* **Visualization**: Grafana v11

## 🚀 Deployment Guide

### 0. Prerequisites

**On the local machine** (the one running the Python agent and `playbook-loc.yml`):

* Python virtual environment in `agent-exporter/venv` with `requirements.txt` installed, plus Oracle Instant Client.
* An SSH key for the VPS service user (`~/.ssh/LocalVM2VPS`). The tunnel starts in non-interactive mode (`BatchMode=yes`), so a key protected by a passphrase must be loaded into `ssh-agent` first: `ssh-add ~/.ssh/LocalVM2VPS`.
* **`autossh` (recommended)** – keeps the SSH tunnel alive and reconnects it automatically. Without it the playbook falls back to plain `ssh`, and the tunnel will not recover after a network drop.

```bash
# Debian / Ubuntu
sudo apt install autossh
```

`autossh` is only needed on the local machine, nothing extra has to be installed on the VPS.

**On the VPS** (after `bootstrap.yml`) allow only SSH and Grafana in the firewall:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 3000/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

Do not open 8200 / 9091 / 9090 / 9093 – they are reachable only through the tunnel or the internal Docker network.

### 1. Configure Local Secrets
Navigate to the `ansible` directory and create an encrypted secrets file:

```bash
cd ansible

# Create a new encrypted credentials file from scratch
ansible-vault create credentials.yml
```

The `credentials.yml` file must contain the following variables:
```yaml
vault_root_token: "your_vault_token"
db_username: "your_oracle_user"
db_password: "your_oracle_password"
oracle_db_host: "your_db_ip"
oracle_db_port: "your_db_port"
oracle_db_service_name: "your_service_name"
smtp_password: "your_mail_ru_app_specific_password"
```

### 2. Bootstrap the VPS
Run the bootstrap playbook **once on a fresh VPS**, before the first deployment. It installs Docker and Docker Compose, creates the `ansible` service user (member of the `docker` group), adds your public SSH key to it and revokes the passwordless `sudo` of the initial user.

The playbook connects as the initial sudo user of the VPS (`oleg` by default). If your VPS uses a different name, pass it with `-e`, which takes precedence over the playbook variables. The public key `~/.ssh/LocalVM2VPS.pub` must exist locally, and the key itself must already be authorized for the initial user (e.g. `ssh-copy-id -i ~/.ssh/LocalVM2VPS.pub <initial_sudo_user>@<VPS_IP>`).

```bash
ansible-playbook -i inventory.ini bootstrap.yml -e ansible_user=<initial_sudo_user>
```

If `sudo` of the initial user asks for a password, add `-K`. After the run, check that you can log in as the service user: `ssh -i ~/.ssh/LocalVM2VPS ansible@<VPS_IP>`.

### 3. Deploy Telemetry Circuit to VPS
Run the remote playbook from the `ansible` folder to clone the repository on the VPS, generate configurations from Jinja2 templates, and spin up the Docker infrastructure:

```bash
ansible-playbook -i inventory.ini playbook-rmt.yml --ask-vault-pass
```

### 4. Launch Local Metrics Exporter Agent
Run the local playbook. It will:
1. terminate any previously hung monitoring agents and old tunnels;
2. open the SSH tunnel to the VPS (Vault `127.0.0.1:8200`, Pushgateway `127.0.0.1:9091`) using `autossh` if available;
3. wait until the tunnelled ports are listening;
4. bind the Oracle Instant Client environment paths and start the Python exporter in the background.

```bash
ansible-playbook -i inventory.ini playbook-loc.yml
```

The agent log is written to `/tmp/agent_monitoring.log`.

### 5. Verify
* Grafana: `http://<VPS_IP>:3000`
* From any external machine, the protected ports must be closed or filtered:

```bash
nmap -Pn -p 8200,9090,9091,9093 <VPS_IP>
```