from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from energy_system import BatteryCommand, BatteryContext


DAY_NAMES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


def _parse_minute(value) -> int:
    if isinstance(value, int):
        if 0 <= value <= 24:
            return value * 60
        raise ValueError(f"Invalid hour: {value}")
    if isinstance(value, str):
        text = value.strip()
        if ":" in text:
            hour_text, minute_text = text.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
        else:
            hour = int(text)
            minute = 0
        if not 0 <= hour <= 24 or not 0 <= minute < 60:
            raise ValueError(f"Invalid time: {value}")
        return hour * 60 + minute
    raise ValueError(f"Invalid time: {value}")


def _parse_days(days: Optional[Sequence]) -> set[int]:
    if days is None:
        return set(range(7))
    parsed = set()
    for day in days:
        if isinstance(day, int):
            if not 0 <= day <= 6:
                raise ValueError(f"Invalid day index: {day}")
            parsed.add(day)
            continue
        key = str(day).strip().lower()
        if key not in DAY_NAMES:
            raise ValueError(f"Invalid day name: {day}")
        parsed.add(DAY_NAMES[key])
    if not parsed:
        raise ValueError("Schedule rule must include at least one day")
    return parsed


@dataclass(frozen=True)
class ScheduleRule:
    days: set[int]
    start_minute: int
    end_minute: int
    action: str
    source: str = "any"
    power_kw: Optional[float] = None
    target_soc_percent: Optional[float] = None
    allow_export: bool = False
    enabled: bool = True

    def __post_init__(self):
        if self.action not in {"charge", "discharge", "idle", "self_consumption"}:
            raise ValueError(f"Unknown schedule action: {self.action}")
        if self.start_minute < 0 or self.end_minute > 24 * 60:
            raise ValueError("Schedule time must be within one day")
        if self.end_minute <= self.start_minute:
            raise ValueError("Schedule end must be after start")
        if self.power_kw is not None and self.power_kw < 0:
            raise ValueError("Schedule power_kw must be non-negative")
        if self.target_soc_percent is not None and not 0 <= self.target_soc_percent <= 100:
            raise ValueError("Schedule target_soc_percent must be in [0, 100]")

    def matches(self, context: BatteryContext) -> bool:
        if not self.enabled or context.timestamp.dayofweek not in self.days:
            return False
        minute = context.timestamp.hour * 60 + context.timestamp.minute
        return self.start_minute <= minute < self.end_minute


class BatteryController:
    name = "base"

    def reset(self) -> None:
        pass

    def decide(self, context: BatteryContext) -> BatteryCommand:
        return BatteryCommand()


class SelfConsumptionController(BatteryController):
    name = "self_consumption"

    def decide(self, context: BatteryContext) -> BatteryCommand:
        battery = context.battery
        if (
            context.surplus_kw > 0
            and context.soc_kwh < battery.soc_max_kwh - 1e-9
        ):
            return BatteryCommand(
                mode="charge",
                source="pv",
                target_soc_percent=100.0,
            )
        if (
            context.deficit_kw > 0
            and context.soc_kwh > battery.soc_min_kwh + 1e-9
        ):
            return BatteryCommand(
                mode="discharge",
                source="battery",
                target_soc_percent=battery.soc_percent(battery.soc_min_kwh),
            )
        return BatteryCommand()


class ScheduleController(BatteryController):
    name = "schedule"

    def __init__(
        self,
        rules: Sequence[dict],
        default_action: str = "self_consumption",
    ):
        if default_action not in {"self_consumption", "idle"}:
            raise ValueError(f"Unknown default_action: {default_action}")
        self.default_action = default_action
        self.rules = [
            ScheduleRule(
                days=_parse_days(rule.get("days")),
                start_minute=_parse_minute(rule["start"]),
                end_minute=_parse_minute(rule["end"]),
                action=str(rule["action"]).strip().lower(),
                source=str(rule.get("source", "any")).strip().lower(),
                power_kw=rule.get("power_kw"),
                target_soc_percent=rule.get("target_soc_percent"),
                allow_export=bool(rule.get("allow_export", False)),
                enabled=bool(rule.get("enabled", True)),
            )
            for rule in rules
        ]
        self.default_controller = SelfConsumptionController()

    def reset(self) -> None:
        self.default_controller.reset()

    def decide(self, context: BatteryContext) -> BatteryCommand:
        for rule in reversed(self.rules):
            if rule.matches(context):
                return self._command_from_rule(rule, context)
        if self.default_action == "self_consumption":
            return self.default_controller.decide(context)
        return BatteryCommand()

    def _command_from_rule(
        self,
        rule: ScheduleRule,
        context: BatteryContext,
    ) -> BatteryCommand:
        if rule.action == "idle":
            return BatteryCommand()
        if rule.action == "self_consumption":
            return self.default_controller.decide(context)
        if rule.action == "charge":
            return BatteryCommand(
                mode="charge",
                power_kw=rule.power_kw,
                source=rule.source,
                target_soc_percent=rule.target_soc_percent,
                allow_export=rule.allow_export,
            )
        return BatteryCommand(
            mode="discharge",
            power_kw=rule.power_kw,
            source="battery",
            target_soc_percent=rule.target_soc_percent,
            allow_export=rule.allow_export,
        )


def build_controller(controller_cfg: Optional[dict]) -> BatteryController:
    config = controller_cfg or {}
    name = str(config.get("name", "self_consumption")).strip().lower()

    if name in {"self", "self_consumption", "self-consumption"}:
        return SelfConsumptionController()
    if name == "schedule":
        return ScheduleController(
            rules=config.get("rules", []),
            default_action=config.get("default_action", "self_consumption"),
        )
    if name == "custom":
        from custom_battery_controller import CustomController

        return CustomController()

    raise ValueError(f"Unknown battery controller: {name}")
