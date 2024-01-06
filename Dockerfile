FROM python:3.11.3-slim

RUN pip install poetry==1.7.1

WORKDIR /app

COPY . .

RUN poetry install --without dev

EXPOSE 8888
ENTRYPOINT ["poetry", "run", "uvicorn", "main:app",  "--host", "0.0.0.0", "--port", "8888"]
