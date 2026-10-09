"""Bounded daily-sales, forecasting and stock-planning API contracts."""

import re
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password", mode="before")
    @classmethod
    def preserve_password(cls, value):
        # Password whitespace is meaningful; reject it at the boundaries instead of silently changing it.
        if isinstance(value, str) and value != value.strip():
            raise ValueError("Password must not start or end with whitespace.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        value = value.lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class SeriesInput(StrictModel):
    sku: str = Field(min_length=1, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(default="Main store", min_length=1, max_length=120)
    unit: str = Field(default="unit", min_length=1, max_length=20)


class Observation(StrictModel):
    date: date
    quantity: float = Field(ge=0, le=1e9, allow_inf_nan=False)

    @field_validator("date")
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError("Sales observations cannot be in the future.")
        return value


class DatasetInput(StrictModel):
    source: str = Field(min_length=1, max_length=200)
    missing_policy: Literal["reject", "zero_fill"] = "reject"
    observations: list[Observation] = Field(min_length=14, max_length=1500)


class CsvInput(StrictModel):
    csv_text: str = Field(min_length=1, max_length=200000)


class Arrival(StrictModel):
    date: date
    quantity: float = Field(gt=0, le=1e9, allow_inf_nan=False)


class ForecastInput(StrictModel):
    dataset_id: str
    scenario_name: str = Field(default="Base forecast", min_length=1, max_length=120)
    horizon: int = Field(default=30, ge=1, le=90)
    model: Literal["auto", "moving_average", "weekday", "damped_trend"] = "auto"
    demand_multiplier: float = Field(default=1, ge=0, le=3, allow_inf_nan=False)
    starting_stock: float = Field(default=0, ge=0, le=1e9, allow_inf_nan=False)
    arrivals: list[Arrival] = Field(default_factory=list, max_length=90)

    @model_validator(mode="after")
    def distinct_arrivals(self):
        if len({x.date for x in self.arrivals}) != len(self.arrivals):
            raise ValueError("Combine arrivals on the same date.")
        return self


class ComparisonInput(StrictModel):
    analysis_ids: list[str] = Field(min_length=2, max_length=10)

    @field_validator("analysis_ids")
    @classmethod
    def unique_ids(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Select distinct analyses.")
        return values
