#!/bin/sh
set -e

echo "=== Vault Entrypoint: Waiting for Vault to become available ==="

# Цикл ожидания, пока DNS имя vault и порт 8200 не станут доступны
until wget -qO- http://vault:8200/v1/sys/health > /dev/null 2>&1; do
    echo "Vault is unavailable or DNS is not ready yet - sleeping 2s..."
    sleep 2
done

echo "=== Vault is UP! Fetching Grafana Cloud Token ==="

# Запрашиваем JSON из Vault
VAULT_RESPONSE=$(wget -qO- --header="X-Vault-Token: $VAULT_TOKEN" http://vault:8200/v1/secret/data/grafana)

# Парсинг JSON
GRAFANA_CLOUD_TOKEN=$(echo "$VAULT_RESPONSE" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')

if [ -z "$GRAFANA_CLOUD_TOKEN" ]; then
    echo "ERROR: Failed to extract GRAFANA_CLOUD_TOKEN from Vault response!"
    exit 1
fi

export GRAFANA_CLOUD_TOKEN
echo "=== Success: Token injected into memory ==="

# Передаем управление оригинальному бинарю Prometheus
exec /bin/prometheus "$@"
