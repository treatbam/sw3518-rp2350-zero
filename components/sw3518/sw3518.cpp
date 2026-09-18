#include "sw3518.h"
#include "esphome/core/log.h"
#include "esphome/core/hal.h"

namespace esphome {
namespace sw3518 {

static const char *const TAG = "sw3518";
static const uint8_t REG_FCX_STATUS = 0x06;
static const uint8_t REG_I2C_CTRL = 0x13;
static const uint8_t REG_ADC_VIN_H = 0x30;
static const uint8_t REG_ADC_VIN_VOUT_L = 0x32;
static const uint8_t REG_ADC_TYPE = 0x3A;
static const uint8_t REG_ADC_H = 0x3B;
static const uint8_t REG_ADC_L = 0x3C;
static const uint8_t ADC_VIN = 1;
static const uint8_t ADC_VOUT = 2;
// Same A/C swap as the Arduino driver (types 3/4).
static const uint8_t ADC_IOUT_C = 3;
static const uint8_t ADC_IOUT_A = 4;
static const uint8_t I2C_CTRL_VIN_ADC_EN = 0x02;

void SW3518Component::setup() {
  if (!this->enable_vin_adc_()) {
    ESP_LOGW(TAG, "VIN ADC enable failed (chip missing?)");
  }
}

void SW3518Component::dump_config() {
  ESP_LOGCONFIG(TAG, "SW3518");
  LOG_I2C_DEVICE(this);
  LOG_UPDATE_INTERVAL(this);
}

bool SW3518Component::write_reg_(uint8_t reg, uint8_t val) {
  return this->write_byte(reg, val);
}

bool SW3518Component::read_reg_(uint8_t reg, uint8_t &val) {
  return this->read_byte(reg, &val);
}

bool SW3518Component::enable_vin_adc_() { return this->write_reg_(REG_I2C_CTRL, I2C_CTRL_VIN_ADC_EN); }

bool SW3518Component::read_adc_(uint8_t type, uint16_t &raw) {
  if (!this->write_reg_(REG_ADC_TYPE, type))
    return false;
  delay(2);
  uint8_t hi = 0, lo = 0;
  if (!this->read_reg_(REG_ADC_H, hi) || !this->read_reg_(REG_ADC_L, lo))
    return false;
  raw = (static_cast<uint16_t>(hi) << 4) | static_cast<uint16_t>(lo & 0x0F);
  return true;
}

bool SW3518Component::read_vin_mv_(uint16_t &out) {
  uint8_t vin_h = 0, vin_vout_l = 0;
  if (this->read_reg_(REG_ADC_VIN_H, vin_h) && this->read_reg_(REG_ADC_VIN_VOUT_L, vin_vout_l)) {
    const uint16_t packed =
        (static_cast<uint16_t>(vin_h) << 4) | static_cast<uint16_t>(vin_vout_l >> 4);
    if (packed != 0) {
      out = packed * 10;
      return true;
    }
  }
  uint16_t raw = 0;
  if (!this->read_adc_(ADC_VIN, raw))
    return false;
  out = raw * 10;
  return true;
}

bool SW3518Component::read_vout_mv_(uint16_t &out) {
  uint16_t raw = 0;
  if (!this->read_adc_(ADC_VOUT, raw))
    return false;
  out = raw * 6;
  return true;
}

bool SW3518Component::read_ia_ma_(uint16_t &out) {
  uint16_t raw = 0;
  if (!this->read_adc_(ADC_IOUT_A, raw))
    return false;
  out = (raw * 25) / 10;
  return true;
}

bool SW3518Component::read_ic_ma_(uint16_t &out) {
  uint16_t raw = 0;
  if (!this->read_adc_(ADC_IOUT_C, raw))
    return false;
  out = (raw * 25) / 10;
  return true;
}

const char *SW3518Component::protocol_name_(uint8_t ind) {
  switch (ind) {
    case 0:
      return "5V/DCP";
    case 1:
      return "QC2.0";
    case 2:
      return "QC3.0";
    case 3:
      return "FCP";
    case 4:
      return "SCP";
    case 5:
      return "PD FIX";
    case 6:
      return "PD PPS";
    case 7:
      return "PE1.1";
    case 8:
      return "PE2.0";
    case 9:
      return "LVDC";
    case 10:
      return "SFCP";
    case 11:
      return "AFC";
    default:
      return "?";
  }
}

void SW3518Component::update() {
  uint16_t vin = 0, vout = 0, ia = 0, ic = 0;
  if (!this->read_vin_mv_(vin) || !this->read_vout_mv_(vout) || !this->read_ia_ma_(ia) ||
      !this->read_ic_ma_(ic)) {
    ESP_LOGW(TAG, "I2C read failed");
    if (this->linked_ != nullptr)
      this->linked_->publish_state(false);
    if (this->charging_ != nullptr)
      this->charging_->publish_state(false);
    this->status_set_warning();
    return;
  }
  this->status_clear_warning();
  if (this->linked_ != nullptr)
    this->linked_->publish_state(true);

  const float vout_v = vout / 1000.0f;
  const float ia_a = ia / 1000.0f;
  const float ic_a = ic / 1000.0f;
  const float pa = vout_v * ia_a;
  const float pc = vout_v * ic_a;
  const float pt = pa + pc;
  const bool charging = ia > 50 || ic > 50;

  if (this->vin_ != nullptr)
    this->vin_->publish_state(vin / 1000.0f);
  if (this->vout_ != nullptr)
    this->vout_->publish_state(vout_v);
  if (this->ia_ != nullptr)
    this->ia_->publish_state(ia_a);
  if (this->ic_ != nullptr)
    this->ic_->publish_state(ic_a);
  if (this->power_a_ != nullptr)
    this->power_a_->publish_state(pa);
  if (this->power_c_ != nullptr)
    this->power_c_->publish_state(pc);
  if (this->power_ != nullptr)
    this->power_->publish_state(pt);
  if (this->charging_ != nullptr)
    this->charging_->publish_state(charging);

  uint8_t st = 0;
  if (this->protocol_ != nullptr && this->read_reg_(REG_FCX_STATUS, st)) {
    this->protocol_->publish_state(this->protocol_name_(st & 0x0F));
  }
}

}  // namespace sw3518
}  // namespace esphome
