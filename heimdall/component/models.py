"""Heimdal service models"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum, auto
from logging import getLogger

from pydantic import BaseModel, Field
import sqlalchemy as sa

from heimdall.db import database, metadata
from heimdall.component.checks import ComponentState, check_url, ping_host, tcp_connect
from heimdall.util import default_encoder

LOG = getLogger(__name__)


class ComponentType(StrEnum):
    WEB_SERVER = auto()
    PROCESS = auto()
    DATABASE = auto()
    INTERNAL = auto()
    SERVICE = auto()
    HOST = auto()
    PROXY = auto()


component_table = sa.Table(
    "component",
    metadata,
    sa.Column("name", sa.String(32), primary_key=True),
    sa.Column("component_type", sa.Enum(ComponentType), nullable=False),
    sa.Column("display_name", sa.String(64)),
    sa.Column("group", sa.String(32)),
)
component_state_table = sa.Table(
    "state",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("component", sa.ForeignKey("component.name"), index=True, nullable=False),
    sa.Column("timestamp", sa.DateTime, index=True, nullable=False),
    sa.Column("state", sa.Enum(ComponentState), nullable=False),
)


class ComponentStateModel(BaseModel):
    id: int
    component: str = Field(None, exclude=True)
    timestamp: datetime
    state: ComponentState

    class Config:
        json_encoders = {ComponentState: default_encoder}

    def __eq__(self, other: ComponentStateModel) -> bool:
        return self.component == other.component and self.state == other.state

    def __str__(self) -> str:
        return f"State<{self.component}>[state={self.state.name} ts={self.timestamp}]"


class ComponentModel(BaseModel):
    name: str
    display_name: str
    component_type: ComponentType
    state: ComponentState
    timestamp: datetime
    group: str | None = None
    history: list[ComponentStateModel]

    class Config:
        json_encoders = {ComponentState: default_encoder, ComponentType: default_encoder}


class Component:
    def __init__(self, *, name: str, display_name: str, component_type: ComponentType, group: str | None = None):
        self.name = name
        self.display_name = display_name
        self.component_type = component_type
        self.group = group
        self.history: list[ComponentStateModel] = []
        self.current = ComponentStateModel(id=0, component=name, timestamp=datetime.utcnow(), state=ComponentState.OK)

    async def init(self):
        LOG.info("Initializing component '%s'", self.name)

        found = await database.fetch_one(component_table.select().where(component_table.c.name == self.name))
        if not found:
            await database.execute(
                component_table.insert().values(
                    name=self.name, display_name=self.display_name, component_type=self.component_type, group=self.group
                )
            )
            LOG.info("Created new component '%s' in database", self.name)
        else:
            LOG.debug("Component '%s' already present in database", self.name)

        state = await database.fetch_all(
            sa.select(component_state_table)
            .where(component_state_table.c.component == self.name)
            .order_by(component_state_table.c.timestamp.desc())
            .limit(10)
        )
        if state:
            self.history = [ComponentStateModel(**s._mapping) for s in state]
            self.current = self.history.pop(0)
            LOG.debug("Last known component state for '%s': %s", self.name, self.current)
        else:
            now = datetime.utcnow()
            id = await database.execute(
                component_state_table.insert().values(
                    component=self.name,
                    timestamp=now,
                    state=ComponentState.OK,
                )
            )
            self.current = ComponentStateModel(id=id, component=self.name, timestamp=now, state=ComponentState.OK)
            self.history = []
            LOG.info("Created initial component state for '%s'", self.name)

    async def poll(self):
        try:
            state = await self.check()
        except Exception as e:
            state = ComponentState.DEGRADED
            LOG.error("Failed to check component '%s': %s", self.name, e)

        if state != self.current.state:
            id = await database.execute(
                component_state_table.insert().values(
                    component=self.name,
                    timestamp=datetime.utcnow(),
                    state=state,
                )
            )
            self.history = [self.current] + self.history[:9]
            self.current = ComponentStateModel(id=id, component=self.name, timestamp=datetime.utcnow(), state=state)
            LOG.info("Component '%s' changed state: %s", self.name, self.current)
            return self

    async def check(self) -> ComponentState:
        LOG.debug("Dummy check of %s", self)
        return ComponentState.OK

    def as_model(self) -> ComponentModel:
        return ComponentModel(
            name=self.name,
            display_name=self.display_name,
            component_type=self.component_type,
            state=self.current.state,
            timestamp=self.current.timestamp,
            group=self.group,
            history=self.history,
        )

    @property
    def healthy(self) -> bool:
        return self.current.state == ComponentState.OK

    def __repr__(self) -> str:
        return f"Component<{self.name}@{self.group}|{self.current.state.name}>"


class WebServer(Component):
    def __init__(
        self,
        *,
        url: str,
        component_type: ComponentType = ComponentType.WEB_SERVER,
        ignore_unauthorized: bool = False,
        **kwargs,
    ):
        super().__init__(component_type=component_type, **kwargs)
        self.url = url
        self.ignore_unauthorized = ignore_unauthorized

    async def check(self) -> ComponentState:
        return await check_url(self.url, ignore_unauthorized=self.ignore_unauthorized)

    def __repr__(self) -> str:
        return "WebServer" + super().__repr__() + f"[url={self.url}]"


class Host(Component):
    def __init__(self, *, host: str, **kwargs):
        super().__init__(component_type=ComponentType.HOST, **kwargs)
        self.host = host

    async def check(self) -> ComponentState:
        return await ping_host(self.host)

    def __repr__(self) -> str:
        return "Host" + super().__repr__() + f"[host={self.host}]"


class NodeExporter(WebServer):
    def __init__(self, **kwargs):
        super().__init__(component_type=ComponentType.PROCESS, group="metrics", **kwargs)

    def __repr__(self) -> str:
        return "NodeExporter" + super().__repr__() + f"[url={self.url}]"


class TCPServer(Component):
    def __init__(self, *, host: str, port: int, component_type=ComponentType.SERVICE, **kwargs):
        super().__init__(component_type=component_type, **kwargs)
        self.host = host
        self.port = port

    async def check(self) -> ComponentState:
        return await tcp_connect(self.host, self.port)

    def __repr__(self) -> str:
        return "TCPServer" + super().__repr__() + f"[target={self.host}:{self.port}]"


class Proxy(WebServer):
    def __init__(self, **kwargs):
        super().__init__(component_type=ComponentType.PROXY, ignore_unauthorized=True, group="proxies", **kwargs)

    def __repr__(self) -> str:
        return "Proxy" + super().__repr__() + f"[url={self.url}]"
