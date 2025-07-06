# Desafio DevOps em Redes - Monitoramento Web

Este repositório contém a resolução para o desafio prático de Analista de Operações Pleno - foco em DevOps, focado no monitoramento de aplicações web e infraestrutura de rede. A solução implementa um agente de monitoramento em container, armazenamento de dados em banco de dados e visualização através de dashboards no Grafana.

---

## 1. High-Level Design (HLD)

A arquitetura da solução foi projetada para ser modular, escalável e de fácil implantação utilizando `Docker` e `Docker Compose`. Ela é composta pelos seguintes serviços principais:

+-----------------+       +----------------+       +----------------+
|                 |       |                |       |                |
|  Agente de      |       |   Prometheus   |       |    Grafana     |
|  Monitoramento  | <---> | (Coletor/DB de | <---> | (Visualização) |
| (Python App)    |       |    Métricas)   |       |                |
|                 |       |                |       |                |
+-----------------+       +----------------+       +----------------+
|       ^
|       |  (Métricas para Prometheus)
|       |
v       |  (Registros Brutos para DB)
+-----------------+
|                 |
|    MongoDB      |
|  (No-SQL DB)    |
|                 |
+-----------------+

**Descrição dos Componentes:**

* **Agente de Monitoramento (`monitor_agent`):** Uma aplicação Python customizada, conteinerizada com Docker, responsável por executar os testes de monitoramento. Ele realiza:
    * **Testes de Ping:** Medição de latência (RTT) e perda de pacotes (%) para alvos de rede específicos (`google.com`, `youtube.com`, `rnp.br`).
    * **Testes HTTP:** Medição do tempo de carregamento de páginas web e captura dos códigos de retorno HTTP (200, 404, etc.) para as mesmas URLs.
    * **Nota sobre `youtube.com`:** Esta URL foi intencionalmente incluída na lista de alvos de monitoramento com a expectativa de que ela retorne um status de erro (geralmente `0` para falha de conexão ou DNS/SSL, ou um código como `404` se for um endpoint HTTP, mas neste caso é uma URL que não é um servidor web padrão). A inclusão de um alvo conhecido por falhar permite demonstrar a capacidade do sistema em **detectar e reportar problemas**, fornecendo insights sobre a robustez do monitoramento e a capacidade de diferenciar entre serviços online e offline/problemáticos.
    * **Exposição de Métricas:** Os resultados são expostos em um endpoint HTTP (`/metrics`) no formato Prometheus.
    * **Persistência de Dados Brutos:** Cada resultado de teste é armazenado como um documento JSON detalhado no MongoDB.

* **MongoDB (`mongodb`):** Um banco de dados No-SQL utilizado para armazenar os resultados brutos e detalhados de cada teste de monitoramento executado pelo agente. Esta camada garante a persistência completa dos dados para análise histórica aprofundada.

* **Prometheus (`prometheus`):** Um sistema de monitoramento e alerta de código aberto. Ele atua como um **Banco de Dados de Séries Temporais (TSDB)**, sendo configurado para raspar (coletar) as métricas expostas pelo Agente de Monitoramento em intervalos regulares. O Prometheus é otimizado para o armazenamento e consulta de dados temporais, sendo a fonte primária de dados para os dashboards no Grafana.

* **Grafana (`grafana`):** Uma plataforma de código aberto para análise e visualização interativa de dados. Ele se conecta ao Prometheus para criar dashboards ricos e dinâmicos, que permitem a visualização em tempo real e histórica das métricas de rede e web coletadas.

---

## 2. Soluções Adotadas e Justificativas

Esta seção detalha as escolhas tecnológicas e a abordagem para cada requisito.

### 2.1. Agente de Monitoramento (Python em Container Docker)

* **Tecnologia:** `Python` com as bibliotecas `requests` (para HTTP), `subprocess` (para ping via CLI) e `prometheus_client` (para exposição de métricas).
* **Justificativa:** Python foi escolhido pela sua simplicidade, rapidez de desenvolvimento e vasto ecossistema de bibliotecas, tornando-o ideal para a criação de um agente leve e eficiente. Além disso, **minha experiência prévia e proficiência com Python** permitiram um desenvolvimento ágil e robusto do agente. A conteinerização com Docker garante isolamento, portabilidade e fácil implantação em qualquer ambiente que suporte Docker. A inclusão de uma URL intencionalmente malformada (`youtube.com`) serve para validar a capacidade do sistema em **capturar e apresentar diferentes cenários de erro ou falha de conexão**, não apenas sucessos.

### 2.2. Testes de Rede (Ping e HTTP)

* **Implementação:** As funções `run_ping_test` e `run_http_test` no `agent.py` executam os testes.
    * **Ping:** Utiliza o comando `ping` nativo do sistema operacional (`iputils-ping` instalado no container) para medir RTT e perda de pacotes, garantindo medições precisas da camada de rede.
    * **HTTP:** Emprega a biblioteca `requests` para simular o carregamento de páginas, capturando o tempo de resposta e o código de status HTTP.
* **Justificativa:** A abordagem híbrida (CLI para ping, biblioteca para HTTP) oferece robustez e precisão para ambos os tipos de teste de rede.

### 2.3. Armazenamento de Resultados (MongoDB e Prometheus)

Este requisito foi abordado com uma estratégia de persistência em dois níveis:

* **MongoDB (Banco de Dados No-SQL):**
    * **Onde:** Os resultados brutos de cada teste são inseridos em uma coleção (`monitor_results`) no MongoDB pelo agente Python.
    * **Justificativa:** Atende diretamente ao requisito de "Banco de Dados (SQL ou No-SQL)". O MongoDB, como um banco de dados No-SQL baseado em documentos, é flexível para armazenar estruturas de dados variadas e é uma excelente escolha para logs e registros detalhados de eventos.
* **Prometheus (Banco de Dados de Séries Temporais - TSDB):**
    * **Onde:** As métricas agregadas (RTT médio, % de perda, tempo de resposta, último status code) são expostas pelo agente e coletadas pelo Prometheus.
    * **Justificativa:** O Prometheus é a ferramenta padrão da indústria para monitoramento de séries temporais. Sua otimização para ingestão e consulta de métricas temporais, combinada com sua integração nativa com o Grafana, o torna ideal para a visualização dinâmica de dados de monitoramento.

### 2.4. Dashboards no Grafana para Visualização

* **Implementação:** O Grafana é configurado para utilizar o Prometheus como sua fonte de dados. Dashboards foram criados com painéis específicos para cada métrica, incluindo gráficos de linha e painéis de status/tabela.
* **Justificativa:** O Grafana oferece uma interface poderosa e flexível para criar visualizações claras e personalizáveis. Permite a rápida identificação de problemas e tendências, transformando dados brutos em inteligência operacional acionável.

---

## 3. Instruções de Execução

Siga os passos abaixo para subir a aplicação e acessar os dashboards de monitoramento.

### Pré-requisitos

Certifique-se de ter as seguintes ferramentas instaladas em seu ambiente:

* **Git:** Para clonar o repositório.
* **Docker:** Para rodar os containers.
* **Docker Compose:** Para orquestrar os múltiplos serviços.

### Passos para Execução

1.  **Clone o Repositório:**
    ```bash
    git clone [URL_DO_SEU_REPOSITORIO]
    cd [pasta_do_seu_repositorio]
    ```

2.  **Suba os Containers:**
    Navegue até o diretório raiz do projeto (onde está o `docker-compose.yml`) e execute:
    ```bash
    docker-compose up --build -d
    ```
    * `--build`: Garante que a imagem do `monitor_agent` seja construída/reconstruída com as dependências corretas.
    * `-d`: Roda os containers em modo detached (em segundo plano).

3.  **Verifique o Status dos Containers:**
    Confirme se todos os serviços estão em execução:
    ```bash
    docker-compose ps ou docker ps -a
    ```
    Você deverá ver todos os serviços (`monitor_agent`, `prometheus`, `grafana`, `mongodb`) com o status `Up`.

4.  **Acesse o Grafana:**
    Abra seu navegador e vá para: `http://localhost:3000`
    * **Usuário:** `admin`
    * **Senha:** `desafio_rnp123`  É **altamente recomendável** alterá-la no primeiro login.)

    Após o login, você deve ser capaz de navegar para o dashboard "Monitoramento Web RNP" (ou o nome que você deu) e ver os gráficos populando com os dados.

### (Opcional) Verificando a Persistência no MongoDB

Para confirmar que os dados brutos estão sendo armazenados no MongoDB:

1.  Acesse o shell do container MongoDB:
    ```bash
    docker exec -it mongodb bash
    ```
2.  Entre no shell do MongoDB:
    ```bash
    mongosh
    ```
3.  Mude para o banco de dados e visualize os documentos:
    ```javascript
    use web_monitor_db
    db.monitor_results.find().pretty()
    ```
    Você deverá ver os documentos JSON detalhando cada teste de monitoramento.

---

## 4. Prints dos Dashboards do Grafana

* **Dashboard Geral de Monitoramento Web:**
    ![Screenshot do Dashboard Geral](images/dashboard_geral.png) * Este dashboard apresenta uma visão consolidada do status de ping (latência e perda de pacotes) e HTTP (tempo de resposta e códigos de status) para todas as URLs monitoradas. Ele permite a rápida identificação de problemas e tendências.
* **Detalhe de Latência e Perda de Pacotes:**
    ![Screenshot Detalhe Latencia Perda](images/latencia_perda.png)
    * Foco nos gráficos de linha para latência de ping e porcentagem de perda de pacotes, mostrando a estabilidade da conexão de rede ao longo do tempo.
* **Detalhe de Tempo de Resposta e Status HTTP:**
    ![Screenshot Detalhe HTTP](images/tempo_status_http.png)
    * Exibe o tempo de carregamento das páginas web e o status de retorno HTTP. A inclusão da URL `youtube.com` demonstra a capacidade do sistema de registrar e exibir cenários de falha, onde um código de status não-200 (ou 0 para falha de conexão) é esperado.

---

## 5. Considerações Finais

Esta solução demonstra a capacidade de construir uma pipeline de monitoramento completa e conteinerizada, desde a coleta de dados de rede até a visualização interativa. As escolhas de tecnologia visam robustez, escalabilidade e alinhamento com as melhores práticas de DevOps em ambientes de produção.

---