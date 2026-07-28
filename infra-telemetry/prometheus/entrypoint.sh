#!/bin/sh
set -e

echo "=== Vault Entrypoint: Waiting for Vault to respond ==="

# Будем пинговать sys/health встроенным wget. 
# 2>/dev/null глушит любые ошибки сети и DNS, пока они не поднялись.
until wget -q --spider http://vault:8200/v1/sys/health 2>/dev/null; do
    echo "Vault is not ready yet - sleeping 2s..."
    sleep 2
done

echo "=== Vault is UP! Fetching Grafana Cloud Token ==="

# Запрашиваем секрет
VAULT_RESPONSE=$(wget -qO- --header="X-Vault-Token: $VAULT_TOKEN" http://vault:8200/v1/secret/data/grafana)

# Безопасно парсим токен
GRAFANA_CLOUD_TOKEN=$(echo "$VAULT_RESPONSE" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')

if [ -z "$GRAFANA_CLOUD_TOKEN" ]; then
    echo "ERROR: Failed to extract GRAFANA_CLOUD_TOKEN from Vault response!"
    exit 1
fi

export GRAFANA_CLOUD_TOKEN
echo "=== Success: Token injected into memory ==="

# Передаем управление Prometheus
exec /bin/prometheus "$@"
