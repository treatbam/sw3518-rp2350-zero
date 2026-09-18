#pragma once

#include "session.h"
#include "sw3518.h"

void netSetup();
void netTick();
void netPublish(const SW3518::Snapshot& snap, const Session& session, bool linked);

bool netWifiConfigured();
bool netWifiUp();
bool netMqttOk();
void netIpText(char* out, size_t n);
