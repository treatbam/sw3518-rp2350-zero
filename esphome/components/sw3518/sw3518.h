#pragma once

#include "esphome/core/component.h"
#include "esphome/components/i2c/i2c.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/binary_sensor/binary_sensor.h"

namespace esphome {
namespace sw3518 {

class SW3518Component : public PollingComponent, public i2c::I2CDevice {
 public:
  void set_vin_sensor(sensor::Sensor *s) { vin_ = s; }
  void set_vout_sensor(sensor::Sensor *s) { vout_ = s; }
  void set_ia_sensor(sensor::Sensor *s) { ia_ = s; }
  void set_ic_sensor(sensor::Sensor *s) { ic_ = s; }
  void set_power_sensor(sensor::Sensor *s) { power_ = s; }
  void set_power_a_sensor(sensor::Sensor *s) { power_a_ = s; }
  void set_power_c_sensor(sensor::Sensor *s) { power_c_ = s; }
  void set_protocol_sensor(text_sensor::TextSensor *s) { protocol_ = s; }
  void set_linked_sensor(binary_sensor::BinarySensor *s) { linked_ = s; }
  void set_charging_sensor(binary_sensor::BinarySensor *s) { charging_ = s; }

  void setup() override;
  void update() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

 protected:
  bool write_reg_(uint8_t reg, uint8_t val);
  bool read_reg_(uint8_t reg, uint8_t &val);
  bool read_adc_(uint8_t type, uint16_t &raw);
  bool enable_vin_adc_();
  bool read_vin_mv_(uint16_t &out);
  bool read_vout_mv_(uint16_t &out);
  bool read_ia_ma_(uint16_t &out);
  bool read_ic_ma_(uint16_t &out);
  const char *protocol_name_(uint8_t ind);

  sensor::Sensor *vin_{nullptr};
  sensor::Sensor *vout_{nullptr};
  sensor::Sensor *ia_{nullptr};
  sensor::Sensor *ic_{nullptr};
  sensor::Sensor *power_{nullptr};
  sensor::Sensor *power_a_{nullptr};
  sensor::Sensor *power_c_{nullptr};
  text_sensor::TextSensor *protocol_{nullptr};
  binary_sensor::BinarySensor *linked_{nullptr};
  binary_sensor::BinarySensor *charging_{nullptr};
};

}  // namespace sw3518
}  // namespace esphome
