FROM python:3.11-alpine

WORKDIR /app
RUN pip install poetry

ADD poetry.lock pyproject.toml /app/
RUN poetry install

COPY heimdall/ /app/heimdall
COPY main.py /app/

ENV PYTHONUNBUFFERED 1
EXPOSE 8000

ENTRYPOINT [ "poetry", "run", "python", "main.py" ]
