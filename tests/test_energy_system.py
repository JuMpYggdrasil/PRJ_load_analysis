import unittest

import pandas as pd

from battery_controllers import ScheduleController, SelfConsumptionController
from energy_system import (
    BatterySpec,
    calculate_bill,
    calculate_metrics,
    simulate_system,
    suggested_battery_capacity_kwh,
)


def hourly_index(periods=24, start="2024-01-01"):
    return pd.date_range(start, periods=periods, freq="h")


def constant_series(value, index):
    return pd.Series(float(value), index=index)


class EnergySystemTests(unittest.TestCase):
    def test_no_battery_curtails_surplus_without_export(self):
        index = hourly_index()
        load = constant_series(1.0, index)
        pv = constant_series(0.0, index)
        pv.iloc[6:18] = 2.0

        result = simulate_system(load, pv, None, None, allow_export=False)
        metrics = calculate_metrics(result)

        self.assertAlmostEqual(metrics["pv_produced_kwh"], 24.0)
        self.assertAlmostEqual(metrics["pv_to_load_kwh"], 12.0)
        self.assertAlmostEqual(metrics["pv_curtailed_kwh"], 12.0)
        self.assertAlmostEqual(metrics["pv_export_kwh"], 0.0)
        self.assertAlmostEqual(metrics["grid_import_kwh"], 12.0)
        self.assertAlmostEqual(metrics["grid_export_kwh"], 0.0)
        self.assertLess(metrics["energy_balance_gap"], 1e-9)

    def test_no_battery_exports_surplus(self):
        index = hourly_index()
        load = constant_series(1.0, index)
        pv = constant_series(0.0, index)
        pv.iloc[6:18] = 2.0

        result = simulate_system(load, pv, None, None, allow_export=True)
        metrics = calculate_metrics(result)

        self.assertAlmostEqual(metrics["pv_curtailed_kwh"], 0.0)
        self.assertAlmostEqual(metrics["pv_export_kwh"], 12.0)
        self.assertAlmostEqual(metrics["grid_export_kwh"], 12.0)
        self.assertAlmostEqual(metrics["grid_import_kwh"], 12.0)
        self.assertAlmostEqual(metrics["self_consumption_percent"], 50.0)

    def test_battery_respects_charge_power_limit(self):
        index = hourly_index(periods=1)
        load = constant_series(0.0, index)
        pv = constant_series(10.0, index)
        battery = BatterySpec(
            capacity_kwh=100,
            power_limit_kw=2,
            depth_of_discharge=1.0,
            charge_efficiency=1.0,
            discharge_efficiency=1.0,
            initial_soc_percent=0,
        )

        result = simulate_system(
            load,
            pv,
            battery,
            SelfConsumptionController(),
            allow_export=False,
        )
        metrics = calculate_metrics(result)

        self.assertAlmostEqual(metrics["batt_charge_kwh"], 2.0)
        self.assertAlmostEqual(result.data["batt_soc_kwh"].iloc[-1], 2.0)
        self.assertAlmostEqual(metrics["pv_curtailed_kwh"], 8.0)

    def test_battery_soc_never_exceeds_capacity(self):
        index = hourly_index(periods=12)
        load = constant_series(0.0, index)
        pv = constant_series(5.0, index)
        battery = BatterySpec(
            capacity_kwh=10,
            power_limit_kw=5,
            depth_of_discharge=1.0,
            charge_efficiency=1.0,
            discharge_efficiency=1.0,
            initial_soc_percent=0,
        )

        result = simulate_system(
            load,
            pv,
            battery,
            SelfConsumptionController(),
            allow_export=False,
        )
        metrics = calculate_metrics(result)

        self.assertLessEqual(metrics["soc_max_kwh"], 10.0 + 1e-9)
        self.assertGreaterEqual(metrics["soc_min_kwh"], -1e-9)
        self.assertAlmostEqual(metrics["batt_charge_kwh"], 10.0)
        self.assertAlmostEqual(metrics["pv_curtailed_kwh"], 50.0)

    def test_battery_efficiency_round_trip(self):
        index = hourly_index(periods=2)
        load = pd.Series([0.0, 10.0], index=index)
        pv = pd.Series([10.0, 0.0], index=index)
        battery = BatterySpec(
            capacity_kwh=10,
            power_limit_kw=10,
            depth_of_discharge=1.0,
            charge_efficiency=0.8,
            discharge_efficiency=0.8,
            initial_soc_percent=0,
        )

        result = simulate_system(
            load,
            pv,
            battery,
            SelfConsumptionController(),
            allow_export=False,
        )
        metrics = calculate_metrics(result)

        self.assertAlmostEqual(result.data["batt_soc_kwh"].iloc[0], 8.0)
        self.assertAlmostEqual(metrics["batt_discharge_kwh"], 6.4)
        self.assertAlmostEqual(metrics["grid_import_kwh"], 3.6)
        self.assertAlmostEqual(result.data["batt_soc_kwh"].iloc[-1], 0.0)
        self.assertLess(metrics["energy_balance_gap"], 1e-9)

    def test_weekday_schedule_only_discharges_on_weekdays(self):
        index = hourly_index(periods=7 * 24)
        load = constant_series(1.0, index)
        pv = constant_series(0.0, index)
        battery = BatterySpec(
            capacity_kwh=10,
            power_limit_kw=1,
            depth_of_discharge=1.0,
            charge_efficiency=1.0,
            discharge_efficiency=1.0,
            initial_soc_percent=100,
        )
        controller = ScheduleController(
            rules=[
                {
                    "days": ["mon", "tue", "wed", "thu", "fri"],
                    "start": "09:00",
                    "end": "10:00",
                    "action": "discharge",
                    "target_soc_percent": 0,
                }
            ],
            default_action="idle",
        )

        result = simulate_system(
            load,
            pv,
            battery,
            controller,
            allow_export=False,
        )
        metrics = calculate_metrics(result)
        weekend = result.data[~result.data["is_weekday"]]

        self.assertAlmostEqual(metrics["batt_discharge_kwh"], 5.0)
        self.assertAlmostEqual(metrics["grid_import_kwh"], 163.0)
        self.assertAlmostEqual(weekend["batt_discharge_kw"].sum(), 0.0)

    def test_bill_uses_grid_import_and_baseline(self):
        index = hourly_index()
        load = constant_series(1.0, index)
        pv = constant_series(0.0, index)
        pv.iloc[6:18] = 2.0
        tariff_cfg = {
            "on_peak_thb_per_kwh": 1.0,
            "off_peak_thb_per_kwh": 1.0,
            "demand_charge_thb_per_kw": 0.0,
            "service_charge_thb_per_month": 0.0,
            "export_thb_per_kwh": 0.0,
            "on_peak_start_hour": 9,
            "on_peak_end_hour_exclusive": 22,
            "holidays": [],
        }

        result = simulate_system(load, pv, None, None, allow_export=True)
        bill = calculate_bill(result, tariff_cfg)

        self.assertAlmostEqual(bill["baseline_total"], 24.0)
        self.assertAlmostEqual(bill["system_total"], 12.0)
        self.assertAlmostEqual(bill["savings"], 12.0)

    def test_suggested_capacity_uses_daily_surplus(self):
        index = hourly_index(periods=48)
        load = constant_series(1.0, index)
        pv = constant_series(0.0, index)
        pv.iloc[6:18] = 3.0
        pv.iloc[30:42] = 3.0

        capacity = suggested_battery_capacity_kwh(load, pv, 0.6, 1.0)

        self.assertAlmostEqual(capacity, 24.0)


if __name__ == "__main__":
    unittest.main()
