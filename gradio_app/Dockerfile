FROM python:3.10-slim
WORKDIR /gradio_app
RUN pip install --no-cache-dir gradio==5.38 pymongo requests yattag jsonyx libsass
COPY . .
CMD ["python", "main.py"]
