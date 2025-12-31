FROM python:3.10-slim
WORKDIR /worker
COPY . .
RUN pip install --no-cache-dir pymongo requests
CMD ["python", "main.py"]
