#include "net.h"

#if defined(CHARGER_PICOW)

#include <WiFi.h>
#include <PubSubClient.h>

#if __has_include("secrets.h")
#include "secrets.h"
#endif

#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif
#ifndef MQTT_HOST
#define MQTT_HOST ""
#endif
#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif
#ifndef MQTT_USER
#define MQTT_USER ""
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD ""
#endif
#ifndef MQTT_BASE
#define MQTT_BASE "picow/sw3518"
#endif
#ifndef MQTT_DISCOVERY_PREFIX
#define MQTT_DISCOVERY_PREFIX "homeassistant"
#endif

static constexpr bool kWifiOn = (WIFI_SSID[0] != '\0');
static constexpr bool kMqttOn = kWifiOn && (MQTT_HOST[0] != '\0');

static WiFiClient wifiClient;
static PubSubClient mqtt(wifiClient);
static bool mqttDiscoverySent = false;
static char mqttDevId[24];
static char mqttAvailTopic[64];
static uint32_t lastWifiTryMs = 0;

bool netWifiConfigured() { return kWifiOn; }
bool netWifiUp() { return kWifiOn && WiFi.status() == WL_CONNECTED; }
bool netMqttOk() { return kMqttOn && mqtt.connected(); }

void netIpText(char* out, size_t n) {
  if (!kWifiOn) {
    snprintf(out, n, "no-wifi");
    return;
  }
  if (WiFi.status() == WL_CONNECTED) {
    const IPAddress ip = WiFi.localIP();
    snprintf(out, n, "%u.%u.%u.%u", ip[0], ip[1], ip[2], ip[3]);
  } else {
    snprintf(out, n, "wifi...");
  }
}

static void mqttBuildIds() {
  uint8_t mac[6] = {0};
  WiFi.macAddress(mac);
  snprintf(mqttDevId, sizeof(mqttDevId), "sw3518pw_%02x%02x", mac[4], mac[5]);
  snprintf(mqttAvailTopic, sizeof(mqttAvailTopic), "%s/status", MQTT_BASE);
}

static void publishHaDiscovery() {
  char topic[128];
  char payload[768];
  char state[64];

  auto discSensor = [&](const char* objectId, const char* name, const char* leaf, const char* unit,
                        const char* deviceClass, const char* stateClass) {
    snprintf(state, sizeof(state), "%s/%s", MQTT_BASE, leaf);
    snprintf(topic, sizeof(topic), "%s/sensor/%s/%s/config", MQTT_DISCOVERY_PREFIX, mqttDevId,
             objectId);
    if (deviceClass && deviceClass[0]) {
      snprintf(payload, sizeof(payload),
               "{\"name\":\"%s\",\"uniq_id\":\"%s_%s\",\"stat_t\":\"%s\",\"avty_t\":\"%s\","
               "\"pl_avail\":\"online\",\"pl_not_avail\":\"offline\",\"unit_of_meas\":\"%s\","
               "\"dev_cla\":\"%s\",\"stat_cla\":\"%s\","
               "\"dev\":{\"ids\":[\"%s\"],\"name\":\"SW3518 Pico W\",\"mdl\":\"PicoW+SW3518\","
               "\"mf\":\"DIY\"}}",
               name, mqttDevId, objectId, state, mqttAvailTopic, unit, deviceClass, stateClass,
               mqttDevId);
    } else {
      snprintf(payload, sizeof(payload),
               "{\"name\":\"%s\",\"uniq_id\":\"%s_%s\",\"stat_t\":\"%s\",\"avty_t\":\"%s\","
               "\"pl_avail\":\"online\",\"pl_not_avail\":\"offline\",\"unit_of_meas\":\"%s\","
               "\"stat_cla\":\"%s\","
               "\"dev\":{\"ids\":[\"%s\"],\"name\":\"SW3518 Pico W\",\"mdl\":\"PicoW+SW3518\","
               "\"mf\":\"DIY\"}}",
               name, mqttDevId, objectId, state, mqttAvailTopic, unit, stateClass, mqttDevId);
    }
    mqtt.publish(topic, payload, true);
  };

  auto discText = [&](const char* objectId, const char* name, const char* leaf) {
    snprintf(state, sizeof(state), "%s/%s", MQTT_BASE, leaf);
    snprintf(topic, sizeof(topic), "%s/sensor/%s/%s/config", MQTT_DISCOVERY_PREFIX, mqttDevId,
             objectId);
    snprintf(payload, sizeof(payload),
             "{\"name\":\"%s\",\"uniq_id\":\"%s_%s\",\"stat_t\":\"%s\",\"avty_t\":\"%s\","
             "\"pl_avail\":\"online\",\"pl_not_avail\":\"offline\","
             "\"dev\":{\"ids\":[\"%s\"],\"name\":\"SW3518 Pico W\",\"mdl\":\"PicoW+SW3518\","
             "\"mf\":\"DIY\"}}",
             name, mqttDevId, objectId, state, mqttAvailTopic, mqttDevId);
    mqtt.publish(topic, payload, true);
  };

  auto discBinary = [&](const char* objectId, const char* name, const char* leaf) {
    snprintf(state, sizeof(state), "%s/%s", MQTT_BASE, leaf);
    snprintf(topic, sizeof(topic), "%s/binary_sensor/%s/%s/config", MQTT_DISCOVERY_PREFIX, mqttDevId,
             objectId);
    snprintf(payload, sizeof(payload),
             "{\"name\":\"%s\",\"uniq_id\":\"%s_%s\",\"stat_t\":\"%s\",\"avty_t\":\"%s\","
             "\"pl_avail\":\"online\",\"pl_not_avail\":\"offline\","
             "\"pl_on\":\"ON\",\"pl_off\":\"OFF\",\"dev_cla\":\"power\","
             "\"dev\":{\"ids\":[\"%s\"],\"name\":\"SW3518 Pico W\",\"mdl\":\"PicoW+SW3518\","
             "\"mf\":\"DIY\"}}",
             name, mqttDevId, objectId, state, mqttAvailTopic, mqttDevId);
    mqtt.publish(topic, payload, true);
  };

  discSensor("vin", "Input voltage", "vin", "V", "voltage", "measurement");
  discSensor("vout", "Output voltage", "vout", "V", "voltage", "measurement");
  discSensor("i_c", "USB-C current", "i_c", "A", "current", "measurement");
  discSensor("i_a", "USB-A current", "i_a", "A", "current", "measurement");
  discSensor("power", "Total power", "power", "W", "power", "measurement");
  discSensor("power_c", "USB-C power", "power_c", "W", "power", "measurement");
  discSensor("power_a", "USB-A power", "power_a", "W", "power", "measurement");
  discSensor("session_wh", "Session energy", "session_wh", "Wh", "", "measurement");
  discSensor("session_peak_w", "Session peak power", "session_peak_w", "W", "power", "measurement");
  discText("protocol", "Charge protocol", "protocol");
  discBinary("charging", "Charging", "charging");
  discBinary("linked", "SW3518 linked", "linked");
  Serial.println("HA MQTT discovery published");
}

static void ensureMqtt() {
  if (!kMqttOn) return;
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) return;

  mqttBuildIds();
  mqtt.setBufferSize(1024);
  mqtt.setKeepAlive(30);

  bool ok = false;
  if (MQTT_USER[0]) {
    ok = mqtt.connect(mqttDevId, MQTT_USER, MQTT_PASSWORD, mqttAvailTopic, 1, true, "offline");
  } else {
    ok = mqtt.connect(mqttDevId, mqttAvailTopic, 1, true, "offline");
  }
  if (!ok) {
    Serial.println("MQTT connect failed");
    mqttDiscoverySent = false;
    return;
  }
  mqtt.publish(mqttAvailTopic, "online", true);
  mqttDiscoverySent = false;
  Serial.println("MQTT connected");
}

void netSetup() {
  if (!kWifiOn) {
    Serial.println("WiFi/MQTT off (empty WIFI_SSID — copy secrets.h.example to secrets.h)");
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiTryMs = millis();
  Serial.printf("WiFi connecting to %s\n", WIFI_SSID);
  if (kMqttOn) mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void netTick() {
  if (!kWifiOn) return;
  const uint32_t now = millis();
  const wl_status_t st = WiFi.status();
  if (st != WL_CONNECTED) {
    if (now - lastWifiTryMs >= 10000) {
      lastWifiTryMs = now;
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      Serial.println("WiFi retry");
    }
    return;
  }
  ensureMqtt();
  if (kMqttOn) mqtt.loop();
}

void netPublish(const SW3518::Snapshot& snap, const Session& session, bool linked) {
  if (!kMqttOn || !mqtt.connected()) return;
  if (!mqttDiscoverySent) {
    publishHaDiscovery();
    mqttDiscoverySent = true;
  }

  char topic[64], val[48];
  auto pub = [&](const char* leaf, const char* v) {
    snprintf(topic, sizeof(topic), "%s/%s", MQTT_BASE, leaf);
    mqtt.publish(topic, v, true);
  };

  snprintf(val, sizeof(val), "%.3f", snap.vin_mv / 1000.0f);
  pub("vin", val);
  snprintf(val, sizeof(val), "%.3f", snap.vout_mv / 1000.0f);
  pub("vout", val);
  snprintf(val, sizeof(val), "%.3f", snap.ic_ma / 1000.0f);
  pub("i_c", val);
  snprintf(val, sizeof(val), "%.3f", snap.ia_ma / 1000.0f);
  pub("i_a", val);
  snprintf(val, sizeof(val), "%.3f", snap.power_total_w);
  pub("power", val);
  snprintf(val, sizeof(val), "%.3f", snap.power_c_w);
  pub("power_c", val);
  snprintf(val, sizeof(val), "%.3f", snap.power_a_w);
  pub("power_a", val);
  pub("protocol", SW3518::protocolName(snap.protocol));
  snprintf(val, sizeof(val), "%.4f", session.mwh / 1000.0f);
  pub("session_wh", val);
  snprintf(val, sizeof(val), "%.2f", session.peakW);
  pub("session_peak_w", val);
  const bool charging = snap.ia_ma > Session::kLoadMa || snap.ic_ma > Session::kLoadMa;
  pub("charging", charging ? "ON" : "OFF");
  pub("linked", linked ? "ON" : "OFF");
  mqtt.publish(mqttAvailTopic, "online", true);
}

#else  // not Pico W — Zero / Wokwi: no Wi-Fi

void netSetup() {}
void netTick() {}
void netPublish(const SW3518::Snapshot&, const Session&, bool) {}
bool netWifiConfigured() { return false; }
bool netWifiUp() { return false; }
bool netMqttOk() { return false; }
void netIpText(char* out, size_t n) { snprintf(out, n, "no-wifi"); }

#endif
