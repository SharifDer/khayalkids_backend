FROM python:3.12-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# Enable contrib repository
RUN echo "deb http://deb.debian.org/debian trixie main contrib" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian trixie-updates main contrib" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security trixie-security main contrib" >> /etc/apt/sources.list && \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections && \
    apt-get update && apt-get install -y \
    libreoffice \
    poppler-utils \
    fontconfig \
    ttf-mscorefonts-installer \
    fonts-wine \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

# VERIFY fonts installed
RUN fc-list | grep -q -i "times new roman" && \
    fc-list | grep -q -i "tahoma" || \
    (echo "ERROR: Required fonts missing!" && exit 1)

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
