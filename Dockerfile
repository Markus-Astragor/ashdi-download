FROM mcr.microsoft.com/playwright/python:latest

RUN apt-get update && apt-get install -y wget ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY download_survey.py .
COPY ashdi_download.py .
COPY utils.py .

ENTRYPOINT ["python", "ashdi_download.py"]
