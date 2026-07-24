import os
import time
import hvac
import oracledb
# Импортируем инструменты для работы с метриками Prometheus
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# ВНИМАНИЕ: Мы убрали load_dotenv()! Переменные теперь прилетают напрямую в память процесса от Ansible

try:
    oracledb.init_oracle_client()
    print("[INFO] Oracle Client initialized in Thick mode successfully at startup.")
except Exception as e:
    print(f"[CRITICAL] Failed to initialize Thick mode: {e}")


def get_secrets_from_vault():
    """Получение чувствительных данных из хранилища HashiCorp Vault на VPS"""
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    
    print(f"[INFO] Connect to Vault at: {vault_addr}")
    
    if not vault_token:
        raise ValueError("[CRITICAL] VAULT_TOKEN environment variable is missing!")
    if not vault_addr:
        raise ValueError("[CRITICAL] VAULT_ADDR environment variable is missing!")
        
    try:
        # Инициализируем клиент Vault
        client = hvac.Client(url=vault_addr, token=vault_token)
        
        # Читаем секрет. Путь 'oracle' строго соответствует тому, что создал Ansible
        read_response = client.secrets.kv.v2.read_secret_version(path='oracle')
        credentials = read_response['data']['data']
        
        print("[SUCCESS] Secrets successfully retrieved from Vault.")
        return credentials
    except Exception as e:
        print(f"[CRITICAL] Failed to read secrets from Vault: {e}")
        raise e


def get_total_sessions(username, password):
    """Подключение к СУБД Oracle и сбор метрики количества активных сессий"""
    try:        
        dsn = oracledb.makedsn(
            host=os.getenv("ORACLE_DB_HOST"),
            port=int(os.getenv("ORACLE_DB_PORT", 1521)),
            service_name=os.getenv("ORACLE_DB_SERVICE_NAME")
        )

        connection = oracledb.connect(user=username, password=password, dsn=dsn)
        cursor = connection.cursor()

        # Запрос считает только активных пользователей, отсекая системные процессы Oracle
        query = "SELECT COUNT(*) FROM v$session WHERE type = 'USER' AND status = 'ACTIVE'"
        cursor.execute(query)
        
        # Извлекаем числовое значение из кортежа (например, из (5,) получаем 5)
        total_sessions = cursor.fetchone()[0]
        
        print(f"[SUCCESS] Number of active user sessions: {total_sessions}")
        
        cursor.close()
        connection.close()
        return total_sessions
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch session metrics: {e}")
        return None


def main():
    print("[START] Starting the Oracle DB Monitoring Agent...")
    
    # 1. Получаем реальные секреты из Vault ОДИН раз при старте агента
    try:
        credentials = get_secrets_from_vault()
    except Exception:
        print("[STOP] Agent initialization failed due to Vault error.")
        return
        
    db_user = credentials.get("username")
    db_password = credentials.get("password")
    
    # 2. Инициализируем реестр метрик Prometheus
    # Нам нужен кастомный реестр (CollectorRegistry), чтобы метрики не дублировались в памяти при циклах
    registry = CollectorRegistry()
    
    # Создаем саму метрику типа Gauge (датчик, который может расти и падать)
    # Первый параметр - имя метрики в Prometheus, второй - её описание
    sessions_gauge = Gauge(
        'oracle_active_user_sessions', 
        'Current number of active user sessions in Oracle DB',
        registry=registry
    )
    
    # Получаем адрес Pushgateway на VPS (например, 217.197.115.100:9091)
    pushgateway_addr = os.getenv("PUSHGATEWAY_ADDR")
    if not pushgateway_addr:
        print("[CRITICAL] PUSHGATEWAY_ADDR environment variable is missing!")
        return

    print("[INFO] The agent is running and ready to collect and push metrics.")
    
    try:
        while True:
            # Передаем в функцию сбора те пароли, которые мы только что достали из Vault
            current_sessions = get_total_sessions(db_user, db_password)
            
            if current_sessions is not None:
                # Обновляем значение датчика в локальной памяти Python
                sessions_gauge.set(current_sessions)
                
                # Отправляем (пушим) метрику в Pushgateway на VPS
                # job='oracle_exporter' — это ярлык, по которому Prometheus сгруппирует эти данные
                try:
                    push_to_gateway(pushgateway_addr, job='oracle_exporter', registry=registry)
                    print(f"[SUCCESS] Metrics successfully pushed to Pushgateway at {pushgateway_addr}")
                except Exception as push_err:
                    print(f"[ERROR] Failed to push metrics to Pushgateway: {push_err}")
            
            # Ждем 10 секунд до следующего сбора
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("[STOP] The agent was stopped by the user.")


if __name__ == "__main__":
    main()
