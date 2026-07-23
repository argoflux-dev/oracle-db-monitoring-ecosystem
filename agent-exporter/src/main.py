import os
import time
from dotenv import load_dotenv
import hvac
import oracledb
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

load_dotenv()

try:
    oracledb.init_oracle_client()
    print("[INFO] Oracle Client initialized in Thick mode successfully at startup.")
except Exception as e:
    print(f"[CRITICAL] Failed to initialize Thick mode: {e}")

def get_secrets_from_vault():
    """Retrieving sensitive data from HashiCorp storage"""
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    
    print(f"[INFO] Connect to Vault at: {vault_addr}")
    
    # TODO: Vault query logic:
    # client = hvac.Client(url=vault_addr, token=vault_token)
    # read_response = client.secrets.kv.v2.read_secret_version(path='oracle-db')
    # credentials = read_response['data']['data']
    
    # Temporary stop until Vault is raised:
    return {"username": "placeholder_user", "password": "placeholder_password"}


def get_total_sessions(username, password):
    try:        
        dsn = oracledb.makedsn(
            host=os.getenv("ORACLE_DB_HOST"),
            port=int(os.getenv("ORACLE_DB_PORT", 1521)),
            service_name=os.getenv("ORACLE_DB_SERVICE_NAME")
        )

        connection = oracledb.connect(user=username, password=password, dsn=dsn)
        cursor = connection.cursor()

        # Фильтруем по типу USER (чтобы отсечь системные процессы СУБД) и по статусу ACTIVE
        query = "SELECT COUNT(*) FROM v$session WHERE type = 'USER' AND status = 'ACTIVE'"

        cursor.execute(query)
        total_sessions = cursor.fetchone()[0]
        
        print(f"[SUCCESS] Number of sessions: {total_sessions}")
        
        cursor.close()
        connection.close()
        return total_sessions
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch session metrics: {e}")
        return None

def main():
    print("[START] Starting the Oracle DB Monitoring Agent...")
    
    # Getting secrets from the Vault
    #credentials = get_secrets_from_vault()
    
    print("[START] Starting the Oracle DB Monitoring Agent...")
    print("[INFO] The agent is running and ready to collect metrics.")
    
    try:
        while True:
            get_total_sessions(os.getenv("ORACLE_DB_USER"), os.getenv("ORACLE_DB_PASSWORD"))
            time.sleep(10)
    except KeyboardInterrupt:
        print("[STOP] The agent was stopped by the user.")

if __name__ == "__main__":
    main()
