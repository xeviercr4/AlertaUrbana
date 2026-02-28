FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY backend/ backend/
COPY frondend/ frondend/

# Crear archivo de tickets vacío
RUN echo "[]" > backend/tickets.json

# Railway inyecta PORT automáticamente
ENV PORT=8000

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
