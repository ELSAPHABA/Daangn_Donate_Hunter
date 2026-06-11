FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    USER_ACTIVITY_LOG=/data/user_activity.log \
    ERROR_LOG=/data/error.log

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY main.py ./
COPY bot ./bot
COPY core ./core
COPY monitoring ./monitoring
COPY notifications ./notifications
COPY resources ./resources
COPY scraping ./scraping
COPY storage ./storage
COPY utils ./utils
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

VOLUME ["/data"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["bot"]
