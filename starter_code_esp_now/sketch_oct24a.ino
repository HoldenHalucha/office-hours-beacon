#include <esp_now.h>
#include <WiFi.h>

#define NUM_RECEIVERS 4

// List of receiver MAC addresses
uint8_t receivers[NUM_RECEIVERS][6] = {
  {0x0C, 0x4E, 0xA0, 0x4D, 0xAA, 0xF8},  // Receiver #1
  {0x0C, 0x4E, 0xA0, 0x4D, 0xAA, 0xA4},  // Receiver #2
  {0x0C, 0x4E, 0xA0, 0x4D, 0xAB, 0x08},  // Receiver #3
  {0x10, 0x20, 0xBA, 0xD1, 0xF4, 0x44}
};

// Callback function for send status
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
    mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3], mac_addr[4], mac_addr[5]);
  
  Serial.print("Sent to ");
  Serial.print(macStr);
  Serial.print(" -> ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
}

void setup() {
  Serial.begin(9600);
  WiFi.mode(WIFI_STA);
  Serial.println("ESP-NOW Multi-Address Sender Initialized");

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);

  // Add each receiver as ESP-NOW peer
  for (int i = 0; i < NUM_RECEIVERS; i++) {
    esp_now_peer_info_t peerInfo;
    memset(&peerInfo, 0, sizeof(peerInfo)); // Fill with zeroes
    memcpy(peerInfo.peer_addr, receivers[i], 6);
    peerInfo.channel = 0;       // 0 means current WiFi channel
    peerInfo.encrypt = false;   // no encryption
    peerInfo.ifidx = WIFI_IF_STA; // << IMPORTANT FIX

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
      Serial.print("Failed to add peer ");
      Serial.println(i + 1);
    }
  }
}

void loop() {
  const char *message = "S250235155967Z";

  // Send to each receiver
  for (int i = 0; i < NUM_RECEIVERS; i++) {
    esp_err_t result = esp_now_send(receivers[i], (uint8_t *)message, strlen(message) + 1);
    if (result == ESP_OK) {
      Serial.printf("Message sent to receiver %d\n", i + 1);
    } else {
      Serial.printf("Error sending to receiver %d\n", i + 1);
    }
    delay(10); // brief delay, helps serial output
  }
}