#include <esp_now.h>
#include <WiFi.h>

#define uart_select_pin 36
#define MAX_BEACONS 40

#define RXD2 16
#define TXD2 17

struct Beacon{
  char name[4];
  uint8_t address[6];
};

int beacons_read = 0;

Beacon beacons[MAX_BEACONS];

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3],
           mac_addr[4], mac_addr[5]);
  Serial.print("Sent to ");
  Serial.print(macStr);
  Serial.print(" -> ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
}

void setup() {
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);
  Serial.begin(115200);
  
  //for testing
  Serial.println("HELLO THERE");

  pinMode(uart_select_pin, INPUT);

  while(!digitalRead(uart_select_pin));

  uint8_t mac[6];
  uint8_t text[18];
  char name[5];

  Beacon temp;

  while(digitalRead(uart_select_pin)) {
    //Serial.println("made it here first");
    //Serial.println(Serial.available());

    if(Serial2.available() >= 18) {
      ++beacons_read;
      Serial.print("Beacon Number ");
      Serial.println(beacons_read);
      
      Serial2.readBytes(text, 18);

      for(int i = 0; i < 4; ++i) {
        name[i] = text[i];
      }
      name[4] = '\0';

      int mac_ind = 0;
      for (int i = 5; i < 17; i += 2) {
          char hexPair[3] = { text[i], text[i + 1], '\0' };
          mac[mac_ind++] = (uint8_t)strtoul(hexPair, NULL, 16);
      }

      
      Serial.printf("Name: %s\n", name);

      Serial.print("MAC: ");
      for (int i = 0; i < 6; ++i) {
        Serial.printf("0x%02X", mac[i]);
        if (i < 5) Serial.print(", ");
      }
      Serial.print("\n\n");

      
      // Add to the array of beacons
      for(int i = 0; i < 4; ++i) {
        temp.name[i] = name[i];
      }     

      for(int i = 0; i < 6; ++i) {
        temp.address[i] = mac[i];
      }

      beacons[beacons_read - 1] = temp;
      
    }
  }

  delay(500);

  WiFi.mode(WIFI_STA);
  Serial.println("ESP-NOW Multi-Address Sender Initialized");

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);

  for (int i = 0; i < beacons_read; i++) {
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, beacons[i].address, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;
    
    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
      Serial.print("Failed to add peer ");
      Serial.println(i + 1);
    }
  }

}

void loop() {
  
  const char *message = "hello receivers";
  for (int i = 0; i < beacons_read; i++) {
    esp_err_t result = esp_now_send(beacons[i].address, (uint8_t *)message, strlen(message) + 1);
    if (result == ESP_OK) {
      Serial.printf("Message sent to receiver %d\n", i + 1);
    } else {
      Serial.printf("Error sending to receiver %d\n", i + 1);
    }
  }
  
  delay(50);
  
  /*/
  for(int i = 0; i < beacons_read; ++i) {
    Serial.println(beacons[i].name);

    delay(3000);
  }
  */
}
