FROM python:3.10-slim
WORKDIR /gradio_app
RUN apt-get update && apt-get install -y iputils-ping
RUN pip install --no-cache-dir gradio==6.5.1 pymongo requests yattag jsonyx libsass 
COPY . .
CMD ["python", "main.py"]
