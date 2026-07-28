#!/bin/sh
set -e

echo "=== Vault Entrypoint: Fetching Grafana Cloud Token ==="

# Запрашиваем JSON из Vault через встроенный wget
VAULT_RESPONSE=$(wget -qO- --header="X-Vault-Token: $VAULT_TOKEN" http://vault:8200/v1/secret/data/grafana)

# Безопасный парсинг JSON с помощью седа без использования jq
GRAFANA_CLOUD_TOKEN=$(echo "$VAULT_RESPONSE" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')

if [ -z "$GRAFANA_CLOUD_TOKEN" ]; then
    echo "ERROR: Failed to extract GRAFANA_CLOUD_TOKEN from Vault response!"
    exit 1
fi

export GRAFANA_CLOUD_TOKEN
echo "=== Success: Token injected into memory ==="

# Передаем управление оригинальному бинарю Prometheus
# Юзер nobody (id 65534) должен иметь право запускать его
exec /bin/prometheus "$@"
