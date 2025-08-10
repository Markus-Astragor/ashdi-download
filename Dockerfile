FROM mcr.microsoft.com/playwright/python:latest

RUN apt-get update && apt-get install -y wget ffmpeg xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ashdi-download.py .

ENTRYPOINT ["/bin/bash", "-c", "\
if [ \"${!#}\" = '--browser' ]; then \
  Xvfb :99 -screen 0 1280x800x24 & \
  export DISPLAY=:99; \
fi; \
exec python ashdi-download.py \"$@\" \
", "--"]
