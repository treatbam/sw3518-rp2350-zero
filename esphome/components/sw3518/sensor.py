import esphome.codegen as cg
from esphome.components import sensor
import esphome.config_validation as cv
from esphome.const import (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_VOLTAGE,
    STATE_CLASS_MEASUREMENT,
    UNIT_AMPERE,
    UNIT_VOLT,
    UNIT_WATT,
)

from . import SW3518Component

CONF_SW3518_ID = "sw3518_id"
CONF_VIN = "vin"
CONF_VOUT = "vout"
CONF_CURRENT_A = "current_a"
CONF_CURRENT_C = "current_c"
CONF_POWER = "power"
CONF_POWER_A = "power_a"
CONF_POWER_C = "power_c"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_SW3518_ID): cv.use_id(SW3518Component),
        cv.Optional(CONF_VIN): sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_VOLTAGE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_VOUT): sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_VOLTAGE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_CURRENT_A): sensor.sensor_schema(
            unit_of_measurement=UNIT_AMPERE,
            accuracy_decimals=3,
            device_class=DEVICE_CLASS_CURRENT,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_CURRENT_C): sensor.sensor_schema(
            unit_of_measurement=UNIT_AMPERE,
            accuracy_decimals=3,
            device_class=DEVICE_CLASS_CURRENT,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_POWER): sensor.sensor_schema(
            unit_of_measurement=UNIT_WATT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_POWER,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_POWER_A): sensor.sensor_schema(
            unit_of_measurement=UNIT_WATT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_POWER,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_POWER_C): sensor.sensor_schema(
            unit_of_measurement=UNIT_WATT,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_POWER,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_SW3518_ID])
    for key, setter in (
        (CONF_VIN, "set_vin_sensor"),
        (CONF_VOUT, "set_vout_sensor"),
        (CONF_CURRENT_A, "set_ia_sensor"),
        (CONF_CURRENT_C, "set_ic_sensor"),
        (CONF_POWER, "set_power_sensor"),
        (CONF_POWER_A, "set_power_a_sensor"),
        (CONF_POWER_C, "set_power_c_sensor"),
    ):
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(getattr(hub, setter)(sens))
