#include <dummy.h>

#include <esp_now.h>
#include <WiFi.h>

const int rx_pin = 16;
const int tx_pin = 17;

uint8_t receiverAddress[] = {0xA0, 0xB7, 0x65, 0x49, 0xB6, 0x10};
int i = 0;

char data_buf = 1;

void setup() {
  Serial2.begin(9600, SERIAL_8N1, rx_pin, tx_pin);
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



  
  //configure to send with whatever the queue is saying
  if (Serial2.available()) {
    data_buf = Serial2.read();
  }
  

  esp_err_t result = esp_now_send(receiverAddress, (uint8_t *) &data_buf, sizeof(data_buf));

  if (result == ESP_OK) {
    Serial.print("Sent the message: ");
    Serial.println((int)data_buf);
  } else {
    Serial.println("Error sending the message");
  }
  delay(1000);
}