import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv


from . import SW3518Component

CONF_SW3518_ID = "sw3518_id"
CONF_PROTOCOL = "protocol"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_SW3518_ID): cv.use_id(SW3518Component),
        cv.Optional(CONF_PROTOCOL): text_sensor.text_sensor_schema(),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_SW3518_ID])
    if CONF_PROTOCOL in config:
        sens = await text_sensor.new_text_sensor(config[CONF_PROTOCOL])
        cg.add(hub.set_protocol_sensor(sens))
