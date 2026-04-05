FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
COPY keyguard/ keyguard/

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["keyguard"]
CMD ["--help"]
