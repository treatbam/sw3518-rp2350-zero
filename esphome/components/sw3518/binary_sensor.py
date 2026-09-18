import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_POWER,
)

from . import SW3518Component

CONF_SW3518_ID = "sw3518_id"
CONF_LINKED = "linked"
CONF_CHARGING = "charging"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_SW3518_ID): cv.use_id(SW3518Component),
        cv.Optional(CONF_LINKED): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_CONNECTIVITY,
        ),
        cv.Optional(CONF_CHARGING): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_POWER,
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_SW3518_ID])
    if CONF_LINKED in config:
        sens = await binary_sensor.new_binary_sensor(config[CONF_LINKED])
        cg.add(hub.set_linked_sensor(sens))
    if CONF_CHARGING in config:
        sens = await binary_sensor.new_binary_sensor(config[CONF_CHARGING])
        cg.add(hub.set_charging_sensor(sens))
