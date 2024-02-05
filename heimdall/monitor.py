"""Monitoring agent"""

from asyncio import CancelledError, Task, create_task, sleep
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from logging import getLogger
from pathlib import Path

from pydantic import BaseModel

from heimdall import cfg
from heimdall.component.models import Component, ComponentModel, Host, NodeExporter, Proxy, TCPServer, WebServer
from heimdall.util import send_email

LOG = getLogger(__name__)


class MonitorModel(BaseModel):
    monitor: str
    healthy: bool
    components: list[ComponentModel]


def create_state_change_email(monitor: MonitorModel, changeset: list[Component]):
    return (
        f"{len(changeset)} component(s) changed state:{chr(10)}{chr(10)}"
        f"{chr(10).join(f' {c}' for c in changeset)}{chr(10)}{chr(10)}"
        f"{monitor}"
    )


class Monitor:
    def __init__(self):
        self._task: Task | None = None
        self.components: list[Component] = []

    def load_from_config(self, config_file: Path):
        LOG.info("Loading components from %s", config_file)
        if not config_file.exists():
            raise FileNotFoundError(f"The config file {config_file} does not exist")

        with open(config_file) as f:
            data = json.load(f)

        components = data.get("components", [])
        component_names = set()

        for c in components:
            component_name = c.get("nam")
            if component_name in component_names:
                raise ValueError(f"Duplicate component name '{component_name}'")

            component_class = c.pop("class", None)

            try:
                match component_class:
                    case "host":
                        self.components.append(Host(**c))
                    case "node_exporter":
                        self.components.append(NodeExporter(**c))
                    case "web_server":
                        self.components.append(WebServer(**c))
                    case "tcp_server":
                        self.components.append(TCPServer(**c))
                    case "proxy":
                        self.components.append(Proxy(**c))
                    case _:
                        LOG.error("Could not load unsupported component class: '%s'", component_class)
                component_names.add(c["name"])
            except TypeError as e:
                LOG.error("Could not load '%s' due to: %s", component_name, e)

        LOG.info("Loaded %d/%d configured components", len(self.components), len(components))

    def start(self):
        self._task = create_task(self.run())

    async def stop(self):
        if self._task:
            self._task.cancel()
            await self._task
            self._task = None
            LOG.info("Monitoring stopped")
        else:
            LOG.warning("Attempt to stop when not running")

    async def run(self):
        LOG.info("Initializing components")
        for s in self.components:
            try:
                await s.init()
            except Exception as e:
                LOG.exception(e)

        LOG.info("Monitoring started on %s", self)
        LOG.info("Polling cycles will start in 5s")
        await sleep(5)
        try:
            while True:
                start = datetime.now()
                LOG.debug("Starting polling cycle")

                changed = []
                for c in self.components:
                    try:
                        change = await c.poll()
                        if change:
                            changed.append(c)
                        await sleep(cfg.POLL_STAGGER_TIME)
                    except Exception as e:
                        LOG.error("Caught error during poll of %s", c)

                if changed:
                    message = create_state_change_email(self, changed)
                    subject = "Ulv.io services resumed normal operation" if self.healthy else "Ongoing component outage"
                    create_task(send_email(message, subject=subject), name="email")

                wait = start + relativedelta(seconds=cfg.POLL_INTERVAL) - datetime.now()
                LOG.debug("Polling finished for %s, waiting %ss until next poll", self, round(wait.total_seconds(), 1))
                await sleep(max(1.0, wait.total_seconds()))
        except CancelledError:
            LOG.debug("Monitor task was cancelled")

    def as_model(self) -> MonitorModel:
        return MonitorModel(
            monitor=self.state, healthy=self.healthy, components=[c.as_model() for c in self.components]
        )

    @property
    def state(self) -> str:
        return "RUNNING" if self._task else "STOPPED"

    @property
    def healthy(self) -> bool:
        return all(c.healthy for c in self.components)

    @property
    def num_healthy(self) -> int:
        return sum(c.healthy for c in self.components)

    @property
    def num_unhealthy(self) -> int:
        return len(self.components) - self.num_healthy

    def __repr__(self) -> str:
        return f"Monitor<{self.state}>[healthy={self.num_healthy}/{len(self.components)}]"

    def __str__(self) -> str:
        return f"Monitor is {self.state} with {self.num_healthy} of {len(self.components)} healthy components."
