# oracle-db-monitoring-ecosystem
A comprehensive solution for monitoring Oracle DBMS performance using Docker, Python, Prometheus, Grafana, HashiCorp Vault, and Ansible.

## Architecture
* `/agent-exporter` — Local Python agent in Docker for collecting DBMS metrics.
* `/infra-telemetry` — server infrastructure (Prometheus, Grafana) on a remote VPS.
* `/ansible` — server-side deployment automation.
