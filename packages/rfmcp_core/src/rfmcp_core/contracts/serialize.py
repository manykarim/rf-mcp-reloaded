from __future__ import annotations

from pydantic import BaseModel


def dump_json(model: BaseModel) -> str:
    return model.model_dump_json(indent=2)
