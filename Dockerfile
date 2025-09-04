FROM python:3.12-alpine

WORKDIR /app
RUN pip install uv

ADD uv.lock pyproject.toml /app/
RUN uv sync --frozen

COPY heimdall/ /app/heimdall
COPY main.py /app/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT [ "uv", "run", "python", "main.py" ]
