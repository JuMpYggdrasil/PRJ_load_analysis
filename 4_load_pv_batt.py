import json
import os
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from battery_controllers import build_controller
from energy_system import (
    build_reopt_dispatch_table,
    calculate_bill,
    calculate_metrics,
    daily_pv_surplus_kwh,
    infer_dt_hours,
    resolve_battery_spec,
    simulate_system,
    suggested_battery_capacity_kwh,
)

CONFIG_PATH = "config.json"


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as config_file:
        config = json.load(config_file)

    required_sections = ["solar_pv", "grid", "battery", "tariff", "analysis"]
    missing_sections = [section for section in required_sections if section not in config]
    if missing_sections:
        raise KeyError(f"Missing config sections: {', '.join(missing_sections)}")

    solar_cfg = config["solar_pv"]
    if len(solar_cfg["install_capacities_kwp"]) != len(
        solar_cfg["pvsyst_yield_kwh_per_kwp_year"]
    ):
        raise ValueError(
            "solar_pv.install_capacities_kwp and solar_pv.pvsyst_yield_kwh_per_kwp_year "
            "must have the same length"
        )

    grid_cfg = config["grid"]
    if grid_cfg.get("export_limit_kw") is not None and float(
        grid_cfg["export_limit_kw"]
    ) < 0:
        raise ValueError("grid.export_limit_kw must be non-negative or null")

    battery_cfg = config["battery"]
    if battery_cfg.get("enabled", True):
        power_limit = battery_cfg.get("power_limit_kw")
        if power_limit is None or float(power_limit) <= 0:
            raise ValueError("battery.power_limit_kw must be greater than 0")
        capacity = battery_cfg.get("capacity_kwh")
        if capacity is not None and float(capacity) <= 0:
            raise ValueError("battery.capacity_kwh must be greater than 0 or null")
        if not 0 < float(battery_cfg.get("depth_of_discharge", 0.8)) <= 1:
            raise ValueError("battery.depth_of_discharge must be in (0, 1]")
        if not 0 < float(battery_cfg.get("charge_efficiency", 0.95)) <= 1:
            raise ValueError("battery.charge_efficiency must be in (0, 1]")
        if not 0 < float(battery_cfg.get("discharge_efficiency", 0.95)) <= 1:
            raise ValueError("battery.discharge_efficiency must be in (0, 1]")
        if not 0 <= float(battery_cfg.get("initial_soc_percent", 50)) <= 100:
            raise ValueError("battery.initial_soc_percent must be in [0, 100]")
        for key in ("charge_power_kw", "discharge_power_kw"):
            value = battery_cfg.get(key)
            if value is not None and float(value) <= 0:
                raise ValueError(f"battery.{key} must be greater than 0 or null")
        build_controller(battery_cfg.get("controller"))

    tariff_cfg = config["tariff"]
    required_tariff_keys = [
        "on_peak_thb_per_kwh",
        "off_peak_thb_per_kwh",
        "demand_charge_thb_per_kw",
        "service_charge_thb_per_month",
        "on_peak_start_hour",
        "on_peak_end_hour_exclusive",
        "holidays",
    ]
    missing_tariff_keys = [key for key in required_tariff_keys if key not in tariff_cfg]
    if missing_tariff_keys:
        raise KeyError(f"Missing tariff keys: {', '.join(missing_tariff_keys)}")
    if float(tariff_cfg.get("export_thb_per_kwh", 0.0)) < 0:
        raise ValueError("tariff.export_thb_per_kwh must be non-negative")

    return config


config = load_config()
solar_cfg = config["solar_pv"]
grid_cfg = config["grid"]
battery_cfg = config["battery"]
tariff_cfg = config["tariff"]
analysis_cfg = config["analysis"]

PV_Install_Capacity = solar_cfg["install_capacities_kwp"]
PVSyst_GlobInc = solar_cfg["pvsyst_globinc_kwh_per_m2_year"]
PVSyst_Energy_per_year_per_kWp = solar_cfg["pvsyst_yield_kwh_per_kwp_year"]
SOLAR_REFERENCE_YIELD = solar_cfg["reference_yield_kwh_per_kwp_year"]
PV_Energy_Adjust_Factor = [
    value / SOLAR_REFERENCE_YIELD for value in PVSyst_Energy_per_year_per_kWp
]
print(PV_Energy_Adjust_Factor)

unit_price_on_peak = tariff_cfg["on_peak_thb_per_kwh"]
unit_price_off_peak = tariff_cfg["off_peak_thb_per_kwh"]
unit_price_demand_charge = tariff_cfg["demand_charge_thb_per_kw"]
unit_price_service_charge = tariff_cfg["service_charge_thb_per_month"]
kg_CO2_per_kWh = solar_cfg["co2_kg_per_kwh"]
hours_per_year = analysis_cfg["hours_per_year"]

df_load = pd.read_csv("temporary/analyse_electric_load_data.csv", parse_dates=["timestamp"])
df_load.set_index("timestamp", inplace=True)

year_of_first_row = df_load.index[0].year
folder_name = f"result_{year_of_first_row}"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")

solar_profile_template = (
    solar_cfg["tracking_profile_template"]
    if solar_cfg["use_tracking"]
    else solar_cfg["profile_template"]
)
solar_profile_path = solar_profile_template.format(year=year_of_first_row)
df_pv = pd.read_csv(
    solar_profile_path,
    parse_dates=["timestamp"],
    date_format=solar_cfg["timestamp_format"],
)
df_pv.set_index("timestamp", inplace=True)

solar_pattern = []
for hour in range(24):
    solar_pattern.append(df_pv["pv"][df_pv.index.hour == hour].mean())

print(solar_pattern)
pd.DataFrame(solar_pattern).to_csv("solar_pattern.csv")

df_pv_day = df_pv.resample("D").max()
df_pv_data = pd.DataFrame(index=df_pv_day.index)
df_pv_data["pv_max"] = df_pv_day["pv"]
df_pv_data["pv_5"] = df_pv[df_pv.index.hour == 5].resample("D").mean()["pv"]
df_pv_data["pv_6"] = df_pv[df_pv.index.hour == 6].resample("D").mean()["pv"]
df_pv_data["pv_7"] = df_pv[df_pv.index.hour == 7].resample("D").mean()["pv"]
df_pv_data.to_csv("temporary/pv_data_for_train_model.csv")

hours = list(range(24))
month_name = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "None",
]
file_path = "temporary/param_for_economic.json"
if os.path.exists(file_path):
    os.remove(file_path)


def safe_index(values, item):
    try:
        return values.index(item)
    except ValueError:
        return -1


def pv_adjustment_factor(pv_install_capacity):
    index = safe_index(PV_Install_Capacity, pv_install_capacity)
    if index != -1:
        return PV_Energy_Adjust_Factor[index]
    return sum(PV_Energy_Adjust_Factor) / len(PV_Energy_Adjust_Factor)


def build_average_profile(result):
    data = result.data
    columns = {
        "average_load_kW": "load_kw",
        "average_pv_kW": "pv_kw",
        "average_pv_to_load_kW": "pv_to_load_kw",
        "average_batt_charge_kW": "batt_charge_kw",
        "average_batt_discharge_kW": "batt_discharge_kw",
        "average_grid_import_kW": "grid_import_kw",
        "average_grid_export_kW": "grid_export_kw",
        "average_grid_net_kW": "grid_net_kw",
        "average_soc_percent": "batt_soc_percent",
    }
    hourly = data.groupby(data.index.hour)[list(columns.values())].mean()
    hourly = hourly.reindex(range(24)).fillna(0.0)
    average_profile = pd.DataFrame({"hour": hours})
    for output_column, source_column in columns.items():
        average_profile[output_column] = hourly[source_column].to_numpy()
    return average_profile


def print_report(
    pv_install_capacity,
    adjustment_factor,
    result,
    metrics,
    bill,
    suggested_capacity,
):
    data = result.data
    dt_hours = result.dt_hours
    battery = result.battery

    print(f"\nPV Install_cap: {pv_install_capacity:,.2f} kW")
    print(f"PV adjustment factor: {adjustment_factor:.6f}")
    print(f"Energy of pv_produce: {metrics['pv_produced_kwh']:,.2f} kWh/year")
    monthly_pv = (data["pv_kw"] * dt_hours).groupby(data.index.month).sum()
    formatted_monthly_pv = ",".join(
        f"{monthly_pv.get(month, 0.0):,.0f}" for month in range(1, 13)
    )
    print(f"  Monthly PV energy production (kWh/month): {formatted_monthly_pv}")
    print(
        f"Energy of pv_produce: "
        f"{metrics['pv_produced_kwh'] / pv_install_capacity:,.2f} kWh/kWp/year"
    )
    print(
        f"Energy of pv_produce: "
        f"{metrics['pv_produced_kwh'] / pv_install_capacity / 365:,.2f} kWh/kWp/day"
    )
    capacity_factor = (
        metrics["pv_produced_kwh"] / pv_install_capacity / hours_per_year * 100
    )
    print(f"Capacity Factor: {capacity_factor:,.2f} %")
    print(f"PR ratio (PV): {metrics['pv_produced_kwh'] / PVSyst_GlobInc / pv_install_capacity:,.2f}")
    print(f"PR ratio (Load/PV direct): {metrics['pv_to_load_kwh'] / PVSyst_GlobInc / pv_install_capacity:,.2f}")

    on_peak_mask = data["is_on_peak"]
    holiday_mask = data["is_holiday"] | ~data["is_weekday"]
    off_peak_weekday_mask = data["is_weekday"] & ~data["is_holiday"] & ~data["is_on_peak"]
    pv_to_load_on_peak = data.loc[on_peak_mask, "pv_to_load_kw"].sum() * dt_hours
    pv_to_load_off_peak = (
        data.loc[off_peak_weekday_mask, "pv_to_load_kw"].sum() * dt_hours
    )
    pv_to_load_holiday = data.loc[holiday_mask, "pv_to_load_kw"].sum() * dt_hours
    print(f"  pv_serve_load -- On Peak: {pv_to_load_on_peak:,.2f} kWh")
    print(f"  pv_serve_load -- Off Peak: {pv_to_load_off_peak:,.2f} kWh")
    print(f"  pv_serve_load -- holiday: {pv_to_load_holiday:,.2f} kWh")
    print(f"Energy of pv_serve_load: {metrics['pv_to_load_kwh']:,.2f} kWh")
    print(f"Energy of pv_export: {metrics['pv_export_kwh']:,.2f} kWh")
    print(f"Energy of pv_surplus: {metrics['pv_surplus_kwh']:,.2f} kWh")
    print(
        f"Energy of pv_curtailed: {metrics['pv_curtailed_kwh']:,.2f} kWh "
        f"({metrics['curtailment_percent']:.2f} %)"
    )
    print(
        f"PV self-consumption: {metrics['self_consumed_kwh']:,.2f} kWh "
        f"({metrics['self_consumption_percent']:.2f} %)"
    )

    if battery is None:
        print("Battery: disabled")
    else:
        print(f"Battery controller: {result.controller_name}")
        print(f"Battery capacity: {battery.capacity_kwh:,.2f} kWh")
        if suggested_capacity is not None:
            print(
                f"  heuristic capacity: {suggested_capacity:,.2f} kWh "
                f"({battery_cfg['sizing_percentile'] * 100:.0f}th percentile)"
            )
        print(
            f"Battery power limit: {battery.max_charge_power_kw:,.2f} kW charge / "
            f"{battery.max_discharge_power_kw:,.2f} kW discharge"
        )
        print(
            f"Battery SOC initial/min/max/end: "
            f"{metrics['soc_initial_kwh']:,.2f} / {metrics['soc_min_kwh']:,.2f} / "
            f"{metrics['soc_max_kwh']:,.2f} / {metrics['soc_end_kwh']:,.2f} kWh"
        )
        print(f"Battery charge: {metrics['batt_charge_kwh']:,.2f} kWh")
        print(f"Battery discharge: {metrics['batt_discharge_kwh']:,.2f} kWh")
        print(f"Battery losses: {metrics['batt_loss_kwh']:,.2f} kWh")
        print(f"Equivalent full cycles: {metrics['equivalent_cycles']:,.2f}")

    print(f"Grid import: {metrics['grid_import_kwh']:,.2f} kWh")
    print(f"Grid export: {metrics['grid_export_kwh']:,.2f} kWh")
    print(f"Grid net: {metrics['grid_net_kwh']:,.2f} kWh")
    print(f"Load from grid: {metrics['load_from_grid_kwh']:,.2f} kWh")
    print(f"Peak grid import: {metrics['peak_grid_import_kw']:,.2f} kW")
    print(
        f"CO2 Emission Reduction: "
        f"{metrics['grid_import_reduction_kwh'] * kg_CO2_per_kWh:,.0f} kg-CO2"
    )

    print(f"Baseline on-peak: {bill['baseline_on_peak_kwh']:,.2f} kWh")
    print(f"Baseline off-peak: {bill['baseline_off_peak_kwh']:,.2f} kWh")
    print(f"Baseline energy cost: {bill['baseline_energy_cost']:,.2f} THB")
    print(f"Baseline demand: {bill['baseline_demand_kw']:,.2f} kW")
    print(f"Baseline demand cost: {bill['baseline_demand_cost']:,.2f} THB")
    print(f"Baseline service cost: {bill['baseline_service_cost']:,.2f} THB")
    print(f"Baseline bill: {bill['baseline_total']:,.2f} THB")
    print(f"System on-peak: {bill['system_on_peak_kwh']:,.2f} kWh")
    print(f"System off-peak: {bill['system_off_peak_kwh']:,.2f} kWh")
    print(f"System energy cost: {bill['system_energy_cost']:,.2f} THB")
    print(f"System demand: {bill['system_demand_kw']:,.2f} kW")
    print(f"System demand cost: {bill['system_demand_cost']:,.2f} THB")
    print(f"System service cost: {bill['system_service_cost']:,.2f} THB")
    print(f"Export credit: {bill['export_credit']:,.2f} THB")
    print(f"System bill: {bill['system_total']:,.2f} THB")
    print(f"Savings: {bill['savings']:,.2f} THB ({bill['savings_percent']:.2f} %)")
    print("\tignore FT & vat\n\r")


def plot_monthly_profiles(result, pv_install_capacity):
    data = result.data
    target_month_show = [3, 8]
    start_date = data.index[0]
    for month in range(1, 13):
        figure, axis = plt.subplots(figsize=(14, 6))
        axis.plot(data.index, data["load_kw"], label="Load")
        axis.plot(data.index, data["pv_kw"], label="PV Produce")
        axis.set_xlabel("Timestamp")
        axis.set_ylabel("Power (kW)")
        axis.set_title(
            f"Load and PV({pv_install_capacity:,.0f} kWp) {month_name[month]}"
        )
        axis.legend()
        start_of_target_month = start_date.replace(month=month, day=1)
        start_of_next_month = (
            start_of_target_month + pd.DateOffset(months=1)
        ).replace(day=1)
        axis.set_xlim((start_of_target_month, start_of_next_month))
        figure.savefig(
            f"result_{year_of_first_row}/"
            f"Load_and_PV({pv_install_capacity:,.0f}_kWp)_{month}_{month_name[month]}.png",
            format="png",
        )
        if month in target_month_show:
            plt.show()
        plt.close(figure)


def plot_monthly_dispatch(result, pv_install_capacity):
    data = result.data
    for month in range(1, 13):
        month_data = data[data.index.month == month]
        if month_data.empty:
            continue

        figure, axis = plt.subplots(figsize=(14, 6))
        soc_axis = axis.twinx()
        timestamps = month_data.index

        axis.stackplot(
            timestamps,
            month_data["load_from_grid_kw"],
            month_data["pv_to_load_kw"],
            month_data["batt_to_load_kw"],
            labels=[
                "Grid serving load",
                "PV serving load",
                "Battery discharging",
            ],
            colors=["#9e9e9e", "#f2c14e", "#4c78a8"],
            alpha=0.75,
        )
        axis.stackplot(
            timestamps,
            -(month_data["pv_to_batt_kw"] + month_data["grid_to_batt_kw"]),
            -month_data["pv_export_kw"],
            -month_data["batt_export_kw"],
            -month_data["pv_curtailed_kw"],
            labels=[
                "Battery charging (PV + grid)",
                "PV export",
                "Battery export",
                "PV curtailed",
            ],
            colors=["#8ecae6", "#90be6d", "#577590", "#bdbdbd"],
            alpha=0.65,
        )
        axis.plot(
            timestamps,
            month_data["load_kw"],
            color="black",
            linewidth=1.6,
            label="Load",
        )
        axis.axhline(0, color="black", linewidth=0.8)
        axis.set_xlabel("Timestamp")
        axis.set_ylabel("Power (kW)")
        axis.set_title(
            f"System Dispatch ({pv_install_capacity:,.0f} kWp) "
            f"{month_name[month]}"
        )
        axis.grid(True, alpha=0.3)
        axis.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        axis.set_xlim(month_data.index[0], month_data.index[-1])

        handles, labels = axis.get_legend_handles_labels()
        if result.battery is not None:
            soc_axis.plot(
                timestamps,
                month_data["batt_soc_percent"],
                color="#e45756",
                linestyle="--",
                linewidth=1.2,
                label="Battery SOC",
            )
            soc_axis.set_ylabel("Battery SOC (%)")
            soc_axis.set_ylim(0, 100)
            soc_axis.set_zorder(axis.get_zorder() + 1)
            soc_axis.patch.set_visible(False)
            soc_handles, soc_labels = soc_axis.get_legend_handles_labels()
            handles += soc_handles
            labels += soc_labels
        else:
            soc_axis.set_visible(False)

        axis.legend(
            handles,
            labels,
            loc="upper left",
            fontsize=7,
            ncol=2,
            framealpha=0.85,
        )
        figure.tight_layout()
        figure.savefig(
            f"result_{year_of_first_row}/"
            f"system_dispatch_{pv_install_capacity:,.0f}kWp_"
            f"{month}_{month_name[month]}.png",
            format="png",
        )
        plt.close(figure)


def plot_average_profile(result, average_profile, pv_install_capacity):
    figure, axis = plt.subplots(figsize=(12, 6))
    axis.plot(
        average_profile["hour"],
        average_profile["average_load_kW"],
        label="average_load_patterns",
        marker="o",
    )
    axis.plot(
        average_profile["hour"],
        average_profile["average_pv_kW"],
        label="average_pv_patterns",
        marker="o",
    )
    axis.plot(
        average_profile["hour"],
        average_profile["average_grid_net_kW"],
        label="average_grid_net_kW",
        marker="o",
    )
    pv_above_load = (
        average_profile["average_pv_kW"] > average_profile["average_load_kW"]
    )
    axis.fill_between(
        average_profile["hour"],
        average_profile["average_load_kW"],
        average_profile["average_pv_kW"],
        where=pv_above_load,
        color="darkviolet",
        alpha=0.5,
    )
    axis.fill_between(
        average_profile["hour"],
        average_profile["average_load_kW"],
        average_profile["average_pv_kW"],
        where=pv_above_load,
        color="none",
        hatch="///",
        edgecolor="purple",
    )
    axis.set_title(f"Hourly Electrical Load & PV Profile({pv_install_capacity:,.0f}_kWp)")
    axis.set_xlabel("Hour of the Day")
    axis.set_ylabel("Average Load & PV (kW)")
    axis.legend()
    axis.grid(True)
    axis.set_xticks(hours)
    figure.savefig(
        f"result_{year_of_first_row}/load_pv({pv_install_capacity:,.0f}_kWp).png",
        format="png",
    )
    plt.close(figure)


def plot_battery_profiles(result, pv_install_capacity):
    if result.battery is None:
        return

    data = result.data
    dt_hours = result.dt_hours

    daily_soc = data["batt_soc_percent"].resample("D").agg(["min", "mean", "max"])
    figure, axis = plt.subplots(figsize=(14, 6))
    axis.plot(daily_soc.index, daily_soc["min"], label="SOC min")
    axis.plot(daily_soc.index, daily_soc["mean"], label="SOC mean")
    axis.plot(daily_soc.index, daily_soc["max"], label="SOC max")
    axis.set_title(f"Battery SOC ({pv_install_capacity:,.0f} kWp)")
    axis.set_xlabel("Date")
    axis.set_ylabel("SOC (%)")
    axis.legend()
    axis.grid(True)
    figure.savefig(
        f"result_{year_of_first_row}/battery_soc_{pv_install_capacity:,.0f}kWp.png",
        format="png",
    )
    plt.close(figure)

    daily_battery = pd.DataFrame(
        {
            "charge_kwh": data["batt_charge_kw"].resample("D").sum() * dt_hours,
            "discharge_kwh": data["batt_discharge_kw"].resample("D").sum() * dt_hours,
        }
    )
    figure, axis = plt.subplots(figsize=(14, 6))
    axis.plot(daily_battery.index, daily_battery["charge_kwh"], label="Charge")
    axis.plot(daily_battery.index, daily_battery["discharge_kwh"], label="Discharge")
    axis.set_title(f"Battery Energy ({pv_install_capacity:,.0f} kWp)")
    axis.set_xlabel("Date")
    axis.set_ylabel("Energy (kWh/day)")
    axis.legend()
    axis.grid(True)
    figure.savefig(
        f"result_{year_of_first_row}/battery_power_{pv_install_capacity:,.0f}kWp.png",
        format="png",
    )
    plt.close(figure)


def plot_grid_profile(result, pv_install_capacity):
    data = result.data
    dt_hours = result.dt_hours
    daily_grid = pd.DataFrame(
        {
            "import_kwh": data["grid_import_kw"].resample("D").sum() * dt_hours,
            "export_kwh": data["grid_export_kw"].resample("D").sum() * dt_hours,
        }
    )
    figure, axis = plt.subplots(figsize=(14, 6))
    axis.plot(daily_grid.index, daily_grid["import_kwh"], label="Grid import")
    axis.plot(
        daily_grid.index,
        -daily_grid["export_kwh"],
        label="Grid export (negative)",
    )
    axis.set_title(f"Grid Energy ({pv_install_capacity:,.0f} kWp)")
    axis.set_xlabel("Date")
    axis.set_ylabel("Energy (kWh/day)")
    axis.legend()
    axis.grid(True)
    figure.savefig(
        f"result_{year_of_first_row}/grid_profile_{pv_install_capacity:,.0f}kWp.png",
        format="png",
    )
    plt.close(figure)


def plot_surplus_percentiles(result, pv_install_capacity):
    data = result.data
    daily_surplus = daily_pv_surplus_kwh(
        data["load_kw"], data["pv_kw"], result.dt_hours
    )
    daily_surplus = daily_surplus[daily_surplus > 1.0]
    if daily_surplus.empty:
        return

    percentile_values = {
        percentile: daily_surplus.quantile(percentile)
        for percentile in battery_cfg["plot_percentiles"]
    }
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.plot(daily_surplus.index, daily_surplus, marker="o", label="PV surplus")
    plot_styles = ["lime", "g", "lightgreen"]
    for percentile, color in zip(
        sorted(battery_cfg["plot_percentiles"], reverse=True), plot_styles
    ):
        axis.axhline(
            y=percentile_values[percentile],
            color=color,
            linestyle="--"
            if percentile != battery_cfg["sizing_percentile"]
            else "-",
            label=(
                f"{percentile * 100:.0f}th Percentile "
                f"({percentile_values[percentile]:,.0f} kWh)"
            ),
        )
    axis.set_title(
        f"PV Surplus with {battery_cfg['sizing_percentile'] * 100:.0f}th Percentile "
        f"({pv_install_capacity:,.0f} kWp)"
    )
    axis.set_xlabel("Date")
    axis.set_ylabel("PV surplus (kWh/day)")
    axis.legend()
    axis.grid(True)
    figure.savefig(
        f"result_{year_of_first_row}/"
        f"pv_surplus_percentile_{pv_install_capacity:,.0f}kWp.png",
        format="png",
    )
    plt.close(figure)


def save_case_outputs(
    pv_install_capacity,
    result,
    average_profile,
    metrics,
    bill,
):
    result.data.to_csv(
        f"temporary/load_pv_profile_{pv_install_capacity:,.0f}kWp.csv",
        index_label="timestamp",
    )
    result.data.to_csv("temporary/load_pv_profile.csv", index_label="timestamp")
    average_profile.to_csv(
        f"result_{year_of_first_row}/"
        f"average_load_pv_profile_{pv_install_capacity:,.0f}kWp.csv",
        index=False,
    )
    print(
        f"Saved hourly averages -> result_{year_of_first_row}/"
        f"average_load_pv_profile_{pv_install_capacity:,.0f}kWp.csv"
    )
    dispatch_path = (
        f"result_{year_of_first_row}/"
        f"system_performance_dispatch_{pv_install_capacity:,.0f}kWp.csv"
    )
    build_reopt_dispatch_table(result).to_csv(dispatch_path, index=False)
    print(f"Saved system dispatch -> {dispatch_path}")

    param_econ = {
        "installed_capacity": pv_install_capacity,
        "capacity_factor": (
            metrics["pv_produced_kwh"]
            / pv_install_capacity
            / hours_per_year
            * 100
        ),
        "energy_of_pv_produce": metrics["pv_produced_kwh"],
        "energy_of_pv_serve_load": metrics["pv_to_load_kwh"],
        "battery_capacity_kwh": (
            result.battery.capacity_kwh if result.battery is not None else 0
        ),
        "battery_power_limit_kw": (
            result.battery.power_limit_kw if result.battery is not None else 0
        ),
        "grid_import_kwh": metrics["grid_import_kwh"],
        "grid_export_kwh": metrics["grid_export_kwh"],
        "baseline_bill_thb": bill["baseline_total"],
        "system_bill_thb": bill["system_total"],
        "savings_thb": bill["savings"],
    }
    with open(file_path, "a", encoding="utf-8") as json_file:
        json.dump(param_econ, json_file)
        json_file.write("\n")


def evaluate_case(df_pv, df_load, pv_install_capacity):
    adjustment_factor = pv_adjustment_factor(pv_install_capacity)
    pv_produce = df_pv["pv"] * pv_install_capacity * adjustment_factor
    aligned = pd.concat(
        [df_load["load"].rename("load_kw"), pv_produce.rename("pv_kw")],
        axis=1,
        join="inner",
    ).dropna()
    if aligned.empty:
        raise ValueError("Load and PV data have no overlapping timestamps")

    dt_hours = infer_dt_hours(aligned.index)
    battery_spec = None
    controller = None
    suggested_capacity = None

    if battery_cfg.get("enabled", True):
        if battery_cfg.get("capacity_kwh") is None:
            suggested_capacity = suggested_battery_capacity_kwh(
                aligned["load_kw"],
                aligned["pv_kw"],
                battery_cfg["sizing_percentile"],
                dt_hours,
            )
            if suggested_capacity > 0:
                battery_spec = resolve_battery_spec(battery_cfg, suggested_capacity)
        else:
            battery_spec = resolve_battery_spec(battery_cfg)

        if battery_spec is not None:
            controller = build_controller(battery_cfg.get("controller"))
        else:
            print("Battery skipped: no usable PV surplus for heuristic sizing")

    result = simulate_system(
        aligned["load_kw"],
        aligned["pv_kw"],
        battery_spec,
        controller,
        allow_grid_charge=bool(battery_cfg.get("allow_grid_charge", False)),
        allow_export=bool(grid_cfg.get("allow_export", True)),
        export_limit_kw=grid_cfg.get("export_limit_kw"),
        holidays=tariff_cfg["holidays"],
        on_peak_start_hour=tariff_cfg["on_peak_start_hour"],
        on_peak_end_hour_exclusive=tariff_cfg["on_peak_end_hour_exclusive"],
        controller_name=controller.name if controller is not None else "none",
    )
    metrics = calculate_metrics(result)
    bill = calculate_bill(result, tariff_cfg)
    average_profile = build_average_profile(result)

    print_report(
        pv_install_capacity,
        adjustment_factor,
        result,
        metrics,
        bill,
        suggested_capacity,
    )
    save_case_outputs(
        pv_install_capacity,
        result,
        average_profile,
        metrics,
        bill,
    )
    plot_monthly_profiles(result, pv_install_capacity)
    plot_monthly_dispatch(result, pv_install_capacity)
    plot_average_profile(result, average_profile, pv_install_capacity)
    plot_battery_profiles(result, pv_install_capacity)
    plot_grid_profile(result, pv_install_capacity)
    plot_surplus_percentiles(result, pv_install_capacity)

    return {
        "capacity": pv_install_capacity,
        "metrics": metrics,
        "bill": bill,
        "suggested_capacity": suggested_capacity,
    }


def main():
    summaries = []
    for install_cap in PV_Install_Capacity:
        report_path = (
            f"result_{year_of_first_row}/load_pv_batt_result_{install_cap}.txt"
        )
        original_stdout = sys.stdout
        with open(report_path, "w", encoding="utf-8") as report_file:
            sys.stdout = report_file
            try:
                summary = evaluate_case(df_pv, df_load, install_cap)
            finally:
                sys.stdout = original_stdout
        summaries.append(summary)
        print(
            f"Completed {install_cap:,.0f} kWp: "
            f"system bill {summary['bill']['system_total']:,.2f} THB, "
            f"savings {summary['bill']['savings']:,.2f} THB"
        )

    print("Done. Capacities loaded from solar_pv.install_capacities_kwp.")


if __name__ == "__main__":
    main()
