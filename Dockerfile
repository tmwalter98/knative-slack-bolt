FROM python:3.10-slim-bullseye AS builder

WORKDIR /app
COPY . .

RUN apt update -y && apt upgrade -y && apt install curl -y

ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.4.2 python3 -
RUN $POETRY_HOME/bin/poetry config virtualenvs.create false 
RUN $POETRY_HOME/bin/poetry install --only main
RUN $POETRY_HOME/bin/poetry export -f requirements.txt >> requirements.txt


FROM python:3.10-slim-bullseye AS runtime

RUN mkdir /app
WORKDIR /app

COPY src /app
COPY --from=builder /app/requirements.txt /app

RUN pip install --no-cache-dir -r /app/requirements.txt

ENTRYPOINT ["python3", "-u", "app.py"]
