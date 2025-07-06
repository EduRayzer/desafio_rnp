import time
import requests
import platform
import subprocess
from prometheus_client import start_http_server, Gauge, Counter
from pymongo import MongoClient
from datetime import datetime

# Configurações
TARGET_URLS = [
    "http://google.com",
    "youtube.com", 
    "http://rnp.br"
]
PING_COUNT = 4 
EXPORTER_PORT = 8000 

# Configurações do MongoDB
MONGO_URI = "mongodb://mongodb:27017/" 
MONGO_DB_NAME = "web_monitor_db"
MONGO_COLLECTION_NAME = "monitor_results"

# Métricas do Prometheus 
ping_latency_ms = Gauge(
    'web_ping_latency_ms',
    'Latência média de ping (RTT) em milissegundos',
    ['target_url']
)
ping_packet_loss_percent = Gauge(
    'web_ping_packet_loss_percent',
    'Porcentagem de perda de pacotes de ping',
    ['target_url']
)
http_response_time_ms = Gauge(
    'web_http_response_time_ms',
    'Tempo de resposta HTTP em milissegundos',
    ['target_url']
)
http_status_code = Gauge(
    'web_http_status_code',
    'Código de status HTTP da resposta',
    ['target_url']
)
http_requests_total = Counter(
    'web_http_requests_total',
    'Total de requisições HTTP',
    ['target_url', 'status_code']
)


# --- Funções de Conexão com MongoDB ---
mongo_client = None
mongo_db = None
mongo_collection = None

def init_mongodb():
    global mongo_client, mongo_db, mongo_collection
    max_retries = 5
    retry_delay = 5 

    for i in range(max_retries):
        try:
            print(f"Tentando conectar ao MongoDB em {MONGO_URI} (Tentativa {i+1}/{max_retries})...")
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # A linha abaixo vai tentar uma operação para verificar a conexão
            mongo_client.admin.command('ping')
            mongo_db = mongo_client[MONGO_DB_NAME]
            mongo_collection = mongo_db[MONGO_COLLECTION_NAME]
            print("Conectado ao MongoDB com sucesso!")
            return
        except Exception as e:
            print(f"Erro ao conectar ao MongoDB: {e}")
            if i < max_retries - 1:
                print(f"Reconectando em {retry_delay} segundos...")
                time.sleep(retry_delay)
            else:
                print("Falha ao conectar ao MongoDB após várias tentativas. Continuando sem persistência de DB.")
                mongo_client = None 

# Funções de Teste 
def run_ping_test(target_url):
    
    try:
        hostname = target_url.replace("http://", "").replace("https://", "").split("/")[0]
        if platform.system() == "Windows":
            command = ["ping", "-n", str(PING_COUNT), hostname]
        else:
            command = ["ping", "-c", str(PING_COUNT), hostname]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        output = result.stdout

        rtt_match = None
        loss_match = None
        if platform.system() == "Windows":
            for line in output.splitlines():
                if "Média =" in line:
                    rtt_match = line.split("Média =")[1].split("ms")[0].strip()
                if "Perdidos =" in line:
                    loss_match = line.split("Perdidos =")[1].split("(")[1].split("%")[0].strip()
        else:
            for line in output.splitlines():
                if "rtt min/avg/max/mdev" in line:
                    rtt_match = line.split("=")[1].split("/")[1].strip()
                if "packet loss" in line:
                    loss_match = line.split(",")[2].split("%")[0].strip()

        rtt = float(rtt_match) if rtt_match else float('nan')
        packet_loss = float(loss_match) if loss_match else float('nan')
        return rtt, packet_loss
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar ping para {target_url}: {e.stderr}")
        return float('nan'), 100.0
    except Exception as e:
        print(f"Erro inesperado no ping para {target_url}: {e}")
        return float('nan'), 100.0

def run_http_test(target_url):
    
    start_time = time.time()
    status_code = None
    try:
        response = requests.get(target_url, timeout=5)
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        status_code = response.status_code
        return response_time_ms, status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro HTTP para {target_url}: {e}")
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        if isinstance(e, requests.exceptions.Timeout):
            status_code = 408
        else:
            status_code = 0
        return response_time_ms, status_code
    except Exception as e:
        print(f"Erro inesperado no HTTP para {target_url}: {e}")
        return float('nan'), 0

def collect_metrics():
    """Coleta todas as métricas para as URLs alvo e as armazena no MongoDB e no Prometheus."""
    for url in TARGET_URLS:
        print(f"Coletando métricas para: {url}")
        current_timestamp = datetime.now()

        # Teste de Ping
        rtt, packet_loss = run_ping_test(url)
        if not (rtt == float('nan')):
            ping_latency_ms.labels(target_url=url).set(rtt)
        if not (packet_loss == float('nan')):
            ping_packet_loss_percent.labels(target_url=url).set(packet_loss)
        print(f"  Ping - RTT: {rtt:.2f}ms, Perda: {packet_loss:.2f}%")

        # Teste HTTP
        response_time, status = run_http_test(url)
        if not (response_time == float('nan')):
            http_response_time_ms.labels(target_url=url).set(response_time)
        if status is not None:
            http_status_code.labels(target_url=url).set(status)
            http_requests_total.labels(target_url=url, status_code=status).inc()
        print(f"  HTTP - Tempo: {response_time:.2f}ms, Status: {status}")

        #  Armazenar no MongoDB 
        if mongo_collection is not None:
            try:
                result_doc = {
                    "timestamp": current_timestamp,
                    "target_url": url,
                    "ping": {
                        "rtt_ms": rtt,
                        "packet_loss_percent": packet_loss
                    },
                    "http": {
                        "response_time_ms": response_time,
                        "status_code": status
                    }
                }
                mongo_collection.insert_one(result_doc)
                print(f"  Resultados para {url} armazenados no MongoDB.")
            except Exception as e:
                print(f"Erro ao inserir dados no MongoDB para {url}: {e}")
        else:
            print("  MongoDB não conectado, ignorando persistência de dados.")

if __name__ == '__main__':
    # Inicia o servidor HTTP para expor as métricas do Prometheus
    start_http_server(EXPORTER_PORT)
    print(f"Servidor de métricas Prometheus iniciado na porta {EXPORTER_PORT}")

    # Inicializa a conexão com o MongoDB
    init_mongodb()

    # Loop principal para coletar métricas periodicamente
    while True:
        collect_metrics()
        time.sleep(15) 