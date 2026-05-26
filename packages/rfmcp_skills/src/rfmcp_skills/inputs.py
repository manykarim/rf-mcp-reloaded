from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GenerationSkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1)
    tasks: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)
    suite_name: str | None = None
    test_case_name: str = Field(default="Generated Test", min_length=1)
    libraries: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    documentation: str | None = None
    force: bool = False

    @model_validator(mode="after")
    def validate_body_requests(self) -> "GenerationSkillInput":
        if not any(item.strip() for item in [*self.steps, *self.assertions]):
            raise ValueError("Generation skill input requires at least one non-empty step or assertion.")
        return self


class RefactorSkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1)
    mode: Literal["refactor", "regenerate"] = "refactor"
    rename_to: str | None = None
    documentation: str | None = None
    replace: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_requested_changes(self) -> "RefactorSkillInput":
        has_body_lines = any(item.strip() for item in [*self.steps, *self.assertions])
        if self.mode == "regenerate" and not has_body_lines:
            raise ValueError("Refactor skill input in regenerate mode requires at least one non-empty step or assertion.")
        if self.mode == "refactor":
            has_replace = bool(self.replace)
            has_non_body_change = bool(self.rename_to or self.documentation or has_replace)
            if not has_non_body_change and not has_body_lines:
                raise ValueError("Refactor skill input requires at least one rename, documentation change, replacement, step, or assertion.")
        return self
