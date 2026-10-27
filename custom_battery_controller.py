from __future__ import annotations

from battery_controllers import SelfConsumptionController
from energy_system import BatteryCommand, BatteryContext


class CustomController(SelfConsumptionController):
    """Editable battery controller.

    Set battery.controller.name to "custom" in config.json to use this class.
    The default behavior is self-consumption. Add your own rules in decide().
    """

    name = "custom"

    def decide(self, context: BatteryContext) -> BatteryCommand:
        if (
            context.is_weekday
            and 9 <= context.timestamp.hour < 11
            and context.soc_percent > 20
        ):
            return BatteryCommand(
                mode="discharge",
                source="battery",
                target_soc_percent=20,
            )
        if (
            context.is_weekday
            and 11 <= context.timestamp.hour < 13
            and context.surplus_kw > 0
        ):
            return BatteryCommand(
                mode="charge",
                source="pv",
                target_soc_percent=90,
            )
        return super().decide(context)
