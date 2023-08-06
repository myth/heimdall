"""Heimdall utils"""

from datetime import date, datetime
from enum import Enum
from typing import Any

from heimdall.cfg import TZ


def default_encoder(o: Any):
    if isinstance(o, datetime):
        return o.astimezone(TZ).isoformat()
    elif isinstance(o, date):
        return o.isoformat()
    elif isinstance(o, Enum):
        return o.value
    else:
        raise TypeError(f"Unserializable type: {type(o)}")
