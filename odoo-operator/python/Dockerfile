FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY operator.py .
RUN chmod +x operator.py

CMD ["kopf", "run", "/app/operator.py", "--verbose"]
