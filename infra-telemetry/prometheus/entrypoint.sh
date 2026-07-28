#!/bin/sh
set -e

echo "=== Vault Entrypoint: Waiting for Vault port to open ==="

# Проверяем доступность именно TCP-порта 8200 на хосте vault
until nc -z vault 8200; do
    echo "Vault port 8200 is closed or DNS is not ready yet - sleeping 2s..."
    sleep 2
done

echo "=== Vault port is open! Fetching Grafana Cloud Token ==="

# Запрашиваем JSON из Vault (добавим флаг --no-check-certificate на всякий случай)
VAULT_RESPONSE=$(wget -qO- --no-check-certificate --header="X-Vault-Token: $VAULT_TOKEN" http://vault:8200/v1/secret/data/grafana)

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
