FROM python:3.10-slim
WORKDIR /app
RUN pip install --no-cache-dir gradio pymongo requests
COPY . .
CMD ["python", "app.py"]
