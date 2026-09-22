FROM python:3.12-slim

WORKDIR /srv
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "pydantic>=2.6"

COPY app ./app
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
