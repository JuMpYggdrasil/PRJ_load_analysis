from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BatterySpec:
    capacity_kwh: float
    power_limit_kw: float
    depth_of_discharge: float = 0.8
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    initial_soc_percent: float = 50.0
    charge_power_kw: Optional[float] = None
    discharge_power_kw: Optional[float] = None

    def __post_init__(self):
        if self.capacity_kwh <= 0:
            raise ValueError("Battery capacity must be greater than 0")
        if self.power_limit_kw <= 0:
            raise ValueError("Battery power_limit_kw must be greater than 0")
        if not 0 < self.depth_of_discharge <= 1:
            raise ValueError("Battery depth_of_discharge must be in (0, 1]")
        if not 0 < self.charge_efficiency <= 1:
            raise ValueError("Battery charge_efficiency must be in (0, 1]")
        if not 0 < self.discharge_efficiency <= 1:
            raise ValueError("Battery discharge_efficiency must be in (0, 1]")
        if not 0 <= self.initial_soc_percent <= 100:
            raise ValueError("Battery initial_soc_percent must be in [0, 100]")
        if self.charge_power_kw is not None and self.charge_power_kw <= 0:
            raise ValueError("Battery charge_power_kw must be greater than 0")
        if self.discharge_power_kw is not None and self.discharge_power_kw <= 0:
            raise ValueError("Battery discharge_power_kw must be greater than 0")

    @property
    def soc_min_kwh(self) -> float:
        return self.capacity_kwh * (1.0 - self.depth_of_discharge)

    @property
    def soc_max_kwh(self) -> float:
        return self.capacity_kwh

    @property
    def usable_capacity_kwh(self) -> float:
        return self.soc_max_kwh - self.soc_min_kwh

    @property
    def max_charge_power_kw(self) -> float:
        if self.charge_power_kw is None:
            return self.power_limit_kw
        return self.charge_power_kw

    @property
    def max_discharge_power_kw(self) -> float:
        if self.discharge_power_kw is None:
            return self.power_limit_kw
        return self.discharge_power_kw

    def initial_soc_kwh(self) -> float:
        soc = self.capacity_kwh * self.initial_soc_percent / 100.0
        return float(np.clip(soc, self.soc_min_kwh, self.soc_max_kwh))

    def soc_percent(self, soc_kwh: float) -> float:
        return float(soc_kwh / self.capacity_kwh * 100.0)


@dataclass(frozen=True)
class BatteryContext:
    step: int
    timestamp: pd.Timestamp
    load_kw: float
    pv_kw: float
    net_load_kw: float
    surplus_kw: float
    deficit_kw: float
    soc_kwh: float
    soc_percent: float
    battery: BatterySpec
    dt_hours: float
    is_weekday: bool
    is_holiday: bool
    is_on_peak: bool
    tariff_period: str


@dataclass(frozen=True)
class BatteryCommand:
    mode: str = "idle"
    power_kw: Optional[float] = None
    source: str = "any"
    target_soc_percent: Optional[float] = None
    allow_export: bool = False

    def __post_init__(self):
        if self.mode not in {"idle", "charge", "discharge"}:
            raise ValueError(f"Unknown battery mode: {self.mode}")
        if self.source not in {"pv", "grid", "any", "battery"}:
            raise ValueError(f"Unknown battery source: {self.source}")
        if self.power_kw is not None and self.power_kw < 0:
            raise ValueError("Battery command power_kw must be non-negative")
        if self.target_soc_percent is not None and not 0 <= self.target_soc_percent <= 100:
            raise ValueError("Battery target_soc_percent must be in [0, 100]")


class BatteryControllerProtocol(Protocol):
    def reset(self) -> None:
        ...

    def decide(self, context: BatteryContext) -> BatteryCommand:
        ...


@dataclass
class SystemResult:
    data: pd.DataFrame
    battery: Optional[BatterySpec]
    controller_name: str
    dt_hours: float
    allow_export: bool


def infer_dt_hours(index: pd.Index) -> float:
    if len(index) < 2:
        return 1.0

    timestamps = pd.Series(pd.to_datetime(index))
    differences = timestamps.diff().dropna().dt.total_seconds() / 3600.0
    if differences.empty:
        return 1.0

    dt_hours = float(differences.iloc[0])
    if dt_hours <= 0:
        raise ValueError("Timestamps must be increasing")
    if not np.allclose(differences.to_numpy(), dt_hours):
        raise ValueError("Timestamps must have a uniform interval")
    return dt_hours


def _holiday_dates(holidays: Sequence) -> set[pd.Timestamp]:
    return {pd.Timestamp(day).normalize() for day in holidays}


def daily_pv_surplus_kwh(
    load_kw: pd.Series,
    pv_kw: pd.Series,
    dt_hours: Optional[float] = None,
) -> pd.Series:
    if dt_hours is None:
        dt_hours = infer_dt_hours(load_kw.index)

    data = pd.concat(
        [load_kw.rename("load_kw"), pv_kw.rename("pv_kw")],
        axis=1,
        join="inner",
    ).fillna(0.0)
    surplus = (data["pv_kw"] - data["load_kw"]).clip(lower=0.0)
    return (surplus * dt_hours).resample("D").sum()


def suggested_battery_capacity_kwh(
    load_kw: pd.Series,
    pv_kw: pd.Series,
    percentile: float,
    dt_hours: Optional[float] = None,
) -> float:
    daily_surplus = daily_pv_surplus_kwh(load_kw, pv_kw, dt_hours)
    daily_surplus = daily_surplus[daily_surplus > 1.0]
    if daily_surplus.empty:
        return 0.0
    return float(daily_surplus.quantile(percentile))


def resolve_battery_spec(
    battery_cfg: dict,
    capacity_kwh: Optional[float] = None,
) -> Optional[BatterySpec]:
    if not battery_cfg.get("enabled", True):
        return None

    capacity = battery_cfg.get("capacity_kwh")
    if capacity is None:
        capacity = capacity_kwh
    if capacity is None:
        raise ValueError(
            "battery.capacity_kwh is null and no heuristic capacity was provided"
        )

    power_limit = battery_cfg.get("power_limit_kw")
    if power_limit is None:
        raise ValueError("battery.power_limit_kw must be set when battery is enabled")

    return BatterySpec(
        capacity_kwh=float(capacity),
        power_limit_kw=float(power_limit),
        depth_of_discharge=float(battery_cfg.get("depth_of_discharge", 0.8)),
        charge_efficiency=float(battery_cfg.get("charge_efficiency", 0.95)),
        discharge_efficiency=float(battery_cfg.get("discharge_efficiency", 0.95)),
        initial_soc_percent=float(battery_cfg.get("initial_soc_percent", 50.0)),
        charge_power_kw=battery_cfg.get("charge_power_kw"),
        discharge_power_kw=battery_cfg.get("discharge_power_kw"),
    )


def _command_target_soc(
    command: BatteryCommand,
    battery: BatterySpec,
    default_soc_kwh: float,
) -> float:
    if command.target_soc_percent is None:
        return default_soc_kwh
    target = battery.capacity_kwh * command.target_soc_percent / 100.0
    return float(np.clip(target, battery.soc_min_kwh, battery.soc_max_kwh))


def simulate_system(
    load_kw: pd.Series,
    pv_kw: pd.Series,
    battery: Optional[BatterySpec],
    controller: Optional[BatteryControllerProtocol] = None,
    *,
    allow_grid_charge: bool = False,
    allow_export: bool = True,
    export_limit_kw: Optional[float] = None,
    holidays: Sequence = (),
    on_peak_start_hour: int = 9,
    on_peak_end_hour_exclusive: int = 22,
    controller_name: str = "",
) -> SystemResult:
    data = pd.concat(
        [load_kw.rename("load_kw"), pv_kw.rename("pv_kw")],
        axis=1,
        join="inner",
    ).sort_index()
    if data.empty:
        raise ValueError("Load and PV series have no overlapping timestamps")
    data = data.fillna(0.0).clip(lower=0.0)

    dt_hours = infer_dt_hours(data.index)
    holiday_dates = _holiday_dates(holidays)
    export_limit_energy = (
        None if export_limit_kw is None else max(0.0, float(export_limit_kw)) * dt_hours
    )

    if battery is not None:
        initial_soc = battery.initial_soc_kwh()
        soc_kwh = initial_soc
    else:
        initial_soc = 0.0
        soc_kwh = 0.0

    if controller is not None:
        controller.reset()

    rows = []
    load_values = data["load_kw"].to_numpy(dtype=float)
    pv_values = data["pv_kw"].to_numpy(dtype=float)

    for step, timestamp in enumerate(data.index):
        load = max(0.0, float(load_values[step]))
        pv = max(0.0, float(pv_values[step]))

        pv_to_load_kw = min(load, pv)
        surplus_kw = max(0.0, pv - pv_to_load_kw)
        deficit_kw = max(0.0, load - pv_to_load_kw)

        is_weekday = timestamp.dayofweek < 5
        is_holiday = timestamp.normalize() in holiday_dates
        is_on_peak = (
            is_weekday
            and not is_holiday
            and on_peak_start_hour <= timestamp.hour < on_peak_end_hour_exclusive
        )

        command = BatteryCommand()
        if battery is not None and controller is not None:
            context = BatteryContext(
                step=step,
                timestamp=timestamp,
                load_kw=load,
                pv_kw=pv,
                net_load_kw=load - pv,
                surplus_kw=surplus_kw,
                deficit_kw=deficit_kw,
                soc_kwh=soc_kwh,
                soc_percent=battery.soc_percent(soc_kwh),
                battery=battery,
                dt_hours=dt_hours,
                is_weekday=is_weekday,
                is_holiday=is_holiday,
                is_on_peak=is_on_peak,
                tariff_period="on_peak" if is_on_peak else "off_peak",
            )
            command = controller.decide(context)
            if not isinstance(command, BatteryCommand):
                raise TypeError("Battery controller must return a BatteryCommand")

        charge_from_pv_kwh = 0.0
        charge_from_grid_kwh = 0.0
        batt_to_load_kwh = 0.0
        batt_export_request_kwh = 0.0

        if battery is not None and command.mode == "charge":
            target_soc = _command_target_soc(
                command, battery, battery.soc_max_kwh
            )
            if command.power_kw is None:
                charge_power_kw = battery.max_charge_power_kw
            else:
                charge_power_kw = min(command.power_kw, battery.max_charge_power_kw)

            max_charge_kwh = min(
                max(0.0, charge_power_kw) * dt_hours,
                max(0.0, target_soc - soc_kwh) / battery.charge_efficiency,
            )

            if command.source in {"pv", "any"}:
                charge_from_pv_kwh = min(max_charge_kwh, surplus_kw * dt_hours)

            if command.source in {"grid", "any"} and allow_grid_charge:
                remaining_charge = max_charge_kwh - charge_from_pv_kwh
                charge_from_grid_kwh = max(0.0, remaining_charge)

        elif battery is not None and command.mode == "discharge":
            target_soc = _command_target_soc(
                command, battery, battery.soc_min_kwh
            )
            if command.power_kw is None:
                discharge_power_kw = battery.max_discharge_power_kw
            else:
                discharge_power_kw = min(command.power_kw, battery.max_discharge_power_kw)

            max_discharge_kwh = min(
                max(0.0, discharge_power_kw) * dt_hours,
                max(0.0, soc_kwh - target_soc) * battery.discharge_efficiency,
            )

            batt_to_load_kwh = min(max_discharge_kwh, deficit_kw * dt_hours)
            batt_export_request_kwh = max(0.0, max_discharge_kwh - batt_to_load_kwh)

        pv_export_kwh = 0.0
        batt_export_kwh = 0.0
        if allow_export:
            export_remaining = (
                float("inf") if export_limit_energy is None else export_limit_energy
            )
            pv_export_kwh = min(
                max(0.0, surplus_kw * dt_hours - charge_from_pv_kwh),
                export_remaining,
            )
            export_remaining -= pv_export_kwh
            if command.allow_export:
                batt_export_kwh = min(batt_export_request_kwh, export_remaining)

        pv_curtailed_kwh = max(
            0.0,
            surplus_kw * dt_hours - charge_from_pv_kwh - pv_export_kwh,
        )
        load_from_grid_kwh = max(0.0, deficit_kw * dt_hours - batt_to_load_kwh)
        grid_import_kwh = load_from_grid_kwh + charge_from_grid_kwh
        grid_export_kwh = pv_export_kwh + batt_export_kwh
        grid_net_kwh = grid_import_kwh - grid_export_kwh

        batt_charge_kwh = charge_from_pv_kwh + charge_from_grid_kwh
        batt_discharge_kwh = batt_to_load_kwh + batt_export_kwh
        previous_soc = soc_kwh
        if battery is not None:
            soc_kwh += (
                battery.charge_efficiency * batt_charge_kwh
                - batt_discharge_kwh / battery.discharge_efficiency
            )
            soc_kwh = float(
                np.clip(soc_kwh, battery.soc_min_kwh, battery.soc_max_kwh)
            )
        soc_delta = soc_kwh - previous_soc
        batt_loss_kwh = max(
            0.0, batt_charge_kwh - batt_discharge_kwh - soc_delta
        )

        rows.append(
            {
                "load_kw": load,
                "pv_kw": pv,
                "pv_surplus_kw": surplus_kw,
                "pv_to_load_kw": pv_to_load_kw,
                "pv_to_batt_kw": charge_from_pv_kwh / dt_hours,
                "pv_export_kw": pv_export_kwh / dt_hours,
                "pv_curtailed_kw": pv_curtailed_kwh / dt_hours,
                "batt_charge_kw": batt_charge_kwh / dt_hours,
                "batt_discharge_kw": batt_discharge_kwh / dt_hours,
                "batt_to_load_kw": batt_to_load_kwh / dt_hours,
                "batt_export_kw": batt_export_kwh / dt_hours,
                "batt_loss_kw": batt_loss_kwh / dt_hours,
                "batt_soc_kwh": soc_kwh,
                "batt_soc_percent": (
                    battery.soc_percent(soc_kwh) if battery is not None else 0.0
                ),
                "grid_to_batt_kw": charge_from_grid_kwh / dt_hours,
                "grid_import_kw": grid_import_kwh / dt_hours,
                "grid_export_kw": grid_export_kwh / dt_hours,
                "grid_net_kw": grid_net_kwh / dt_hours,
                "load_from_grid_kw": load_from_grid_kwh / dt_hours,
                "is_weekday": is_weekday,
                "is_holiday": is_holiday,
                "is_on_peak": is_on_peak,
                "tariff_period": "on_peak" if is_on_peak else "off_peak",
            }
        )

    result_data = pd.DataFrame(rows, index=data.index)
    return SystemResult(
        data=result_data,
        battery=battery,
        controller_name=controller_name,
        dt_hours=dt_hours,
        allow_export=allow_export,
    )


def calculate_metrics(result: SystemResult) -> dict:
    data = result.data
    dt_hours = result.dt_hours

    def energy(column: str) -> float:
        return float(data[column].sum() * dt_hours)

    pv_produced_kwh = energy("pv_kw")
    pv_to_load_kwh = energy("pv_to_load_kw")
    pv_to_batt_kwh = energy("pv_to_batt_kw")
    pv_export_kwh = energy("pv_export_kw")
    pv_curtailed_kwh = energy("pv_curtailed_kw")
    pv_surplus_kwh = energy("pv_surplus_kw")
    load_kwh = energy("load_kw")
    batt_charge_kwh = energy("batt_charge_kw")
    batt_discharge_kwh = energy("batt_discharge_kw")
    batt_to_load_kwh = energy("batt_to_load_kw")
    batt_export_kwh = energy("batt_export_kw")
    batt_loss_kwh = energy("batt_loss_kw")
    grid_import_kwh = energy("grid_import_kw")
    grid_export_kwh = energy("grid_export_kw")
    grid_to_batt_kwh = energy("grid_to_batt_kw")
    load_from_grid_kwh = energy("load_from_grid_kw")

    if result.battery is not None:
        initial_soc_kwh = result.battery.initial_soc_kwh()
        soc_end_kwh = float(data["batt_soc_kwh"].iloc[-1])
        soc_min_kwh = float(data["batt_soc_kwh"].min())
        soc_max_kwh = float(data["batt_soc_kwh"].max())
        equivalent_cycles = (
            batt_discharge_kwh / result.battery.usable_capacity_kwh
            if result.battery.usable_capacity_kwh > 0
            else 0.0
        )
    else:
        initial_soc_kwh = 0.0
        soc_end_kwh = 0.0
        soc_min_kwh = 0.0
        soc_max_kwh = 0.0
        equivalent_cycles = 0.0

    self_consumed_kwh = pv_to_load_kwh + pv_to_batt_kwh
    energy_balance_gap = max(
        abs(pv_produced_kwh - (pv_to_load_kwh + pv_to_batt_kwh + pv_export_kwh + pv_curtailed_kwh)),
        abs(load_kwh - (pv_to_load_kwh + batt_to_load_kwh + load_from_grid_kwh)),
        abs(grid_import_kwh - (load_from_grid_kwh + grid_to_batt_kwh)),
        abs(grid_export_kwh - (pv_export_kwh + batt_export_kwh)),
        abs(
            (soc_end_kwh - initial_soc_kwh)
            - (batt_charge_kwh - batt_discharge_kwh - batt_loss_kwh)
        ),
    )

    return {
        "load_kwh": load_kwh,
        "pv_produced_kwh": pv_produced_kwh,
        "pv_to_load_kwh": pv_to_load_kwh,
        "pv_to_batt_kwh": pv_to_batt_kwh,
        "pv_export_kwh": pv_export_kwh,
        "pv_curtailed_kwh": pv_curtailed_kwh,
        "pv_surplus_kwh": pv_surplus_kwh,
        "pv_serve_load_kwh": pv_to_load_kwh,
        "self_consumed_kwh": self_consumed_kwh,
        "self_consumption_percent": (
            self_consumed_kwh / pv_produced_kwh * 100.0 if pv_produced_kwh > 0 else 0.0
        ),
        "curtailment_percent": (
            pv_curtailed_kwh / pv_produced_kwh * 100.0 if pv_produced_kwh > 0 else 0.0
        ),
        "export_percent": (
            pv_export_kwh / pv_produced_kwh * 100.0 if pv_produced_kwh > 0 else 0.0
        ),
        "batt_charge_kwh": batt_charge_kwh,
        "batt_discharge_kwh": batt_discharge_kwh,
        "batt_to_load_kwh": batt_to_load_kwh,
        "batt_export_kwh": batt_export_kwh,
        "batt_loss_kwh": batt_loss_kwh,
        "equivalent_cycles": equivalent_cycles,
        "grid_import_kwh": grid_import_kwh,
        "grid_export_kwh": grid_export_kwh,
        "grid_net_kwh": grid_import_kwh - grid_export_kwh,
        "grid_to_batt_kwh": grid_to_batt_kwh,
        "load_from_grid_kwh": load_from_grid_kwh,
        "grid_import_reduction_kwh": load_kwh - grid_import_kwh,
        "soc_initial_kwh": initial_soc_kwh,
        "soc_end_kwh": soc_end_kwh,
        "soc_min_kwh": soc_min_kwh,
        "soc_max_kwh": soc_max_kwh,
        "peak_load_kw": float(data["load_kw"].max()),
        "peak_grid_import_kw": float(data["grid_import_kw"].max()),
        "energy_balance_gap": energy_balance_gap,
    }


def calculate_bill(result: SystemResult, tariff_cfg: dict) -> dict:
    data = result.data
    dt_hours = result.dt_hours

    load_energy_kwh = data["load_kw"] * dt_hours
    grid_import_energy_kwh = data["grid_import_kw"] * dt_hours
    grid_export_energy_kwh = data["grid_export_kw"] * dt_hours

    on_peak = data["is_on_peak"].astype(bool)
    off_peak = ~on_peak

    baseline_on_peak_kwh = float(load_energy_kwh[on_peak].sum())
    baseline_off_peak_kwh = float(load_energy_kwh[off_peak].sum())
    system_on_peak_kwh = float(grid_import_energy_kwh[on_peak].sum())
    system_off_peak_kwh = float(grid_import_energy_kwh[off_peak].sum())

    baseline_demand_kw = float(data["load_kw"].resample("M").max().sum())
    system_demand_kw = float(data["grid_import_kw"].resample("M").max().sum())
    months = int(data.index.to_period("M").nunique())

    on_peak_rate = float(tariff_cfg["on_peak_thb_per_kwh"])
    off_peak_rate = float(tariff_cfg["off_peak_thb_per_kwh"])
    demand_rate = float(tariff_cfg["demand_charge_thb_per_kw"])
    service_rate = float(tariff_cfg["service_charge_thb_per_month"])
    export_rate = float(tariff_cfg.get("export_thb_per_kwh", 0.0))

    baseline_energy_cost = (
        baseline_on_peak_kwh * on_peak_rate
        + baseline_off_peak_kwh * off_peak_rate
    )
    baseline_demand_cost = baseline_demand_kw * demand_rate
    baseline_service_cost = service_rate * months
    baseline_total = baseline_energy_cost + baseline_demand_cost + baseline_service_cost

    system_energy_cost = (
        system_on_peak_kwh * on_peak_rate
        + system_off_peak_kwh * off_peak_rate
    )
    system_demand_cost = system_demand_kw * demand_rate
    system_service_cost = service_rate * months
    export_credit = float(grid_export_energy_kwh.sum()) * export_rate
    system_total = (
        system_energy_cost
        + system_demand_cost
        + system_service_cost
        - export_credit
    )

    savings = baseline_total - system_total

    return {
        "months": months,
        "baseline_on_peak_kwh": baseline_on_peak_kwh,
        "baseline_off_peak_kwh": baseline_off_peak_kwh,
        "baseline_energy_cost": baseline_energy_cost,
        "baseline_demand_kw": baseline_demand_kw,
        "baseline_demand_cost": baseline_demand_cost,
        "baseline_service_cost": baseline_service_cost,
        "baseline_total": baseline_total,
        "system_on_peak_kwh": system_on_peak_kwh,
        "system_off_peak_kwh": system_off_peak_kwh,
        "system_energy_cost": system_energy_cost,
        "system_demand_kw": system_demand_kw,
        "system_demand_cost": system_demand_cost,
        "system_service_cost": system_service_cost,
        "export_credit": export_credit,
        "system_total": system_total,
        "savings": savings,
        "savings_percent": (
            savings / baseline_total * 100.0 if baseline_total > 0 else 0.0
        ),
        "export_thb_per_kwh": export_rate,
    }
