#include <esp_now.h>
#include <WiFi.h>

char receivedData;

void OnDataRecv(const uint8_t * mac, const uint8_t * incomingData, int len) {
  if(len == sizeof(receivedData)) {
    memcpy(&receivedData, incomingData, sizeof(receivedData));
    Serial.print("Received: ");
    Serial.println((int)receivedData);

    int led_status = receivedData;
    if(led_status == 1) {
      digitalWrite(25, HIGH); 
    }
    else {
      digitalWrite(25, LOW); 
    }
  } else {
    Serial.print("Incorrect data length received: ");
    Serial.println(len);
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_recv_cb(OnDataRecv);

  pinMode(25, OUTPUT);
}

void loop() {
}
