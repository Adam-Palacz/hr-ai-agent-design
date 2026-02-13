# Multi-stage build dla optymalizacji rozmiaru
FROM python:3.11-slim as builder

# Instalacja zależności systemowych do budowania
# Retry logic dla problemów z siecią (czasami repozytoria Debian są niedostępne)
RUN set -eux; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends build-essential && \
        break || \
        (echo "Attempt $i failed, retrying..." && sleep 5); \
    done && \
    rm -rf /var/lib/apt/lists/*

# Kopia requirements i instalacja zależności Python (globalnie, nie --user)
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Finalny obraz
FROM python:3.11-slim

# Instalacja zależności runtime (dla PDF processing)
# Retry logic dla problemów z siecią
RUN set -eux; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends poppler-utils && \
        break || \
        (echo "Attempt $i failed, retrying..." && sleep 5); \
    done && \
    rm -rf /var/lib/apt/lists/*

# Kopia zainstalowanych pakietów z buildera (globalne instalacje)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Utworzenie użytkownika nie-root
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/uploads /app/qdrant_db && \
    chown -R appuser:appuser /app

# Ustawienie katalogu roboczego
WORKDIR /app

# Kopia kodu aplikacji
COPY --chown=appuser:appuser . .

# Przełączenie na użytkownika nie-root
USER appuser

# Expose port Flask
EXPOSE 5000

# Zmienne środowiskowe
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# Health check (używa curl zamiast requests, żeby uniknąć dodatkowej zależności)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=5)" || exit 1

# Uruchomienie aplikacji
# Dla MVP: wszystko w jednym kontenerze (web + email monitor w threads)
# Dla produkcji: użyj Dockerfile.web + Dockerfile.worker z docker-compose.prod.yml
CMD ["python", "app.py"]
