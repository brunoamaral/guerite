FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY guerite ./guerite

RUN apk add --no-cache ca-certificates

RUN pip install --no-cache-dir .

CMD ["python", "-m", "guerite"]
