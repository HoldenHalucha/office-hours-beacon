#include <esp_now.h>
#include <WiFi.h>

uint8_t receiverAddress[] = {0xA0, 0xB7, 0x65, 0x49, 0xB6, 0x10};
int i = 0;

typedef struct struct_message {
  char a[32];
} struct_message;

struct_message myData;

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, receiverAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    Serial.println("Failed to add peer");
    return;
  }
}

void loop() {
  ++i;
  if(i > 1310718) {
    i = 0;
  }

  snprintf(myData.a, sizeof(myData.a), "%d", i);  // convert i to string safely
  esp_err_t result = esp_now_send(receiverAddress, (uint8_t *) &myData, sizeof(myData));

  if (result == ESP_OK) {
    Serial.print("Sent the message: ");
    Serial.println(myData.a);
  } else {
    Serial.println("Error sending the message");
  }
  delay(1000);
}
