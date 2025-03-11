FROM python:3.11-slim

WORKDIR /app

COPY python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY python/operator.py python/types.py ./

# Make the operator executable
RUN chmod +x operator.py

# Run the operator
CMD ["kopf", "run", "/app/operator.py", "--verbose"]
