FROM python:3.9-slim-buster

WORKDIR /app

# Instala o ping e outras dependências do sistema necessárias
RUN apt-get update && \
    apt-get install -y iputils-ping && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .

EXPOSE 8000

CMD ["python", "agent.py"]