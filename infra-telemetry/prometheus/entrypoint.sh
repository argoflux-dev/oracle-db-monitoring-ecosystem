#!/bin/sh
set -e

echo "=== Vault is ready (guaranteed by docker compose) ==="
echo "=== Fetching Grafana Cloud Token ==="

# Просто берем секрет без всяких циклов
VAULT_RESPONSE=$(wget -qO- --header="X-Vault-Token: $VAULT_TOKEN" http://vault:8200/v1/secret/data/grafana)

# Безопасно парсим токен
GRAFANA_CLOUD_TOKEN=$(echo "$VAULT_RESPONSE" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')

if [ -z "$GRAFANA_CLOUD_TOKEN" ]; then
    echo "ERROR: Failed to extract GRAFANA_CLOUD_TOKEN from Vault response!"
    echo "Vault API Response was: $VAULT_RESPONSE"
    exit 1
fi

export GRAFANA_CLOUD_TOKEN
echo "=== Success: Token injected into memory ==="

# Передаем управление Prometheus
exec /bin/prometheus "$@"
