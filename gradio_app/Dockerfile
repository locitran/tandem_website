FROM python:3.10-slim
WORKDIR /gradio_app
RUN pip install --no-cache-dir gradio==6.2 pymongo requests yattag
COPY . .
CMD ["python", "main.py"]
