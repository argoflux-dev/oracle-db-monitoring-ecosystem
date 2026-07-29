# Oracle DB Metrics Monitoring & Alerting Ecosystem

An infrastructure project designed to automate Oracle Database monitoring using Prometheus, HashiCorp Vault, and Ansible. The system is engineered based on **Zero Trust Architecture** principles and is fully managed as Code (IaC).

## 🏗️ System Architecture

The ecosystem is split into two distinct environments:
1. **Local Database Circuit**: A Python agent operating inside an isolated `venv` environment using **Oracle Thick Mode** (powered by Oracle Instant Client to support legacy database versions like Oracle 11g). The agent collects active session metrics and pushes them to the Pushgateway via a push model.
2. **Telemetry Circuit (VPS)**: A collection of isolated Docker containers interconnected within a private bridge network.

## 🔐 Secret Management & Security

* **HashiCorp Vault**: The cornerstone of system security. No database passwords or master credentials are stored in plaintext on disk or in process environment variables. The local Python script (`main.py`) authenticates against the Vault API using the `hvac` client at startup and pulls database credentials directly into volatile RAM.
* **Ansible Vault**: Administrator's local configuration secrets are encrypted using the AES-256 algorithm (`credentials.yml`). Decryption occurs exclusively in memory during the playbook execution.
* **Network Isolation**: All inter-container traffic (Prometheus -> Alertmanager, Alertmanager -> SMTP) is strictly isolated within the internal Docker `monitoring` bridge network.

## 📈 Tech Stack
* **Orchestration & Deployment**: Ansible (utilizing dynamic Jinja2 templates)
* **Containerization**: Docker / Docker Compose
* **Secret Storage**: HashiCorp Vault (KV v2 engine)
* **Metrics Collection**: Prometheus v3, Prometheus Pushgateway
* **Alerting**: Prometheus Alertmanager v0.25 (integrated with Mail.ru SMTP via STARTTLS protocol to successfully bypass TSPU/DPI network blocks)
* **Visualization**: Grafana v11

## 🚀 Deployment Guide

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
oracle_db_port: 1521
oracle_db_service_name: "your_service_name"
smtp_password: "your_mail_ru_app_specific_password"
```

### 2. Deploy Telemetry Circuit to VPS
Run the remote playbook from the `ansible` folder to clone the repository on the VPS, generate configurations from Jinja2 templates, and spin up the Docker infrastructure:

```bash
ansible-playbook -i inventory.ini playbook-rmt.yml --ask-vault-pass
```

### 3. Launch Local Metrics Exporter Agent
Run the local playbook to terminate any previously hung monitoring agents, bind the Oracle Instant Client environment paths, and start the Python exporter process in the background:

```bash
ansible-playbook -i inventory.ini playbook-loc.yml
```
