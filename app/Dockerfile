FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Запускаем streamlit на 8000 порту, как указано в нашем docker-compose
CMD ["streamlit", "run", "main.py", "--server.port=8000", "--server.address=0.0.0.0"]