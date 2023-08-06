Heimdall
====

*- The monitoring suite*

## Development

1. Install `poetry`
2. Run `poetry install`
3. Start with `poetry run python main.py`

## Configuration

Configured with environment variables and a config file for component/service definitions.

### Environment variables

- `HD_DEBUG` true/false - default `True` - enable uvicorn debug mode and debug logs.
- `HD_TZ` default `Europe/Oslo` - which timezone to use - 
- `HD_DB_FILE` default `db.sqlite3` - path to the db file (inside container if Docker) 
- `HD_POLL_INTERVAL` default `60 * 10` - time in seconds between each polling cycle
- `HD_POLL_TIMEOUT` default `10` - time in seconds before poll timeout
- `HD_LOG_LEVEL` default `debug` - what log level to use

### Component definitions

JSON file (in root dir of app, mounted at `/app/config.json` in container) in following layout.

```
{
  "components": [
    {
      "name": "unique component name",
      "class": "web_server" | "host" | "node_exporter",
      "display_name": "human friendly name",
      "group": "group name",
      "url": "http://some.host:9001/path", // Only for class 'web_server' | 'node_exporter'
      "host": "some.host.com", // Only for class "host"
    }
  ]
}
```

## Build and run

Build it

```
docker compose build
```

Run it

```
touch .env
# Fill in env vars from config section
touch db.sqlite3
docker compose up -d
```
