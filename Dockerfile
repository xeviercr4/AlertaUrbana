FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema para faiss-cpu (OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código (lazy OpenAI init fix)
COPY backend/ backend/
COPY frondend/ frondend/

# Crear archivo de tickets vacío
RUN echo "[]" > backend/tickets.json

# Railway inyecta PORT automáticamente
ENV PORT=8000

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
