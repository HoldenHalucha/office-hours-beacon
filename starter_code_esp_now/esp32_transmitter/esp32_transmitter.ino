#include <esp_now.h>
#include <WiFi.h>

#define uart_select_pin 36
#define MAX_BEACONS 40

#define RXD2 16
#define TXD2 17

#define NAME_LEN 4
#define NAME_SENTINEL '_'

struct Beacon{
  char name[NAME_LEN];
  uint8_t address[6];
};

int beacons_read = 0;

Beacon beacons[MAX_BEACONS];

// Normalize a raw 1-4 char name into fixed 4 chars padded with sentinel
static void packNameWithSentinel(const char *src4, char *dest4) {
  // Determine effective length (contiguous alnum prefix up to 4)
  int effectiveLen = 0;
  for (int i = 0; i < NAME_LEN; ++i) {
    char c = src4[i];
    if ((c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')) {
      effectiveLen++;
    } else {
      break;
    }
  }
  for (int i = 0; i < NAME_LEN; ++i) {
    if (i < effectiveLen) dest4[i] = src4[i]; else dest4[i] = NAME_SENTINEL;
  }
}

// Find index of beacon by 4-char device name, returns -1 if not found
int findBeaconIndexByName(const char *deviceName) {
  for (int i = 0; i < beacons_read; ++i) {
    bool match = true;
    for (int j = 0; j < NAME_LEN; ++j) {
      if (beacons[i].name[j] != deviceName[j]) { match = false; break; }
    }
    if (match)
      return i;
  }
  return -1;
}

// Parse command of format: S{device_name}%{position}%{[r,g,b]}Z
// On success, fills deviceName(4 chars, not null-terminated), position, r,g,b and returns true
bool parseCommand(const char *cmd, size_t len, char *deviceNameOut, int &positionOut, int &rOut, int &gOut, int &bOut) {
  if (len < 10) return false; // minimal sanity
  if (cmd[0] != 'S' || cmd[len - 1] != 'Z') return false;

  // Extract inside without S ... Z
  String body;
  body.reserve(len);
  for (size_t i = 1; i + 1 < len; ++i) body += cmd[i];

  // Expected: NAME%POS%[r,g,b]
  int firstPct = body.indexOf('%');
  int secondPct = body.indexOf('%', firstPct + 1);
  if (firstPct <= 0 || secondPct <= firstPct + 1) return false;

  String name = body.substring(0, firstPct);
  String posStr = body.substring(firstPct + 1, secondPct);
  String colorStr = body.substring(secondPct + 1);

  if (name.length() < 1 || name.length() > 4) return false;
  // pack into fixed length with sentinel padding
  char raw4[NAME_LEN] = { NAME_SENTINEL, NAME_SENTINEL, NAME_SENTINEL, NAME_SENTINEL };
  for (int i = 0; i < name.length(); ++i) raw4[i] = name[i];
  packNameWithSentinel(raw4, deviceNameOut);

  positionOut = posStr.toInt();

  // colorStr like [r,g,b]
  int lb = colorStr.indexOf('[');
  int rb = colorStr.indexOf(']');
  if (lb == -1 || rb == -1 || rb <= lb + 1) return false;
  String inside = colorStr.substring(lb + 1, rb);

  // split by commas
  int c1 = inside.indexOf(',');
  int c2 = inside.indexOf(',', c1 + 1);
  if (c1 == -1 || c2 == -1) return false;
  String rStr = inside.substring(0, c1);
  String gStr = inside.substring(c1 + 1, c2);
  String bStr = inside.substring(c2 + 1);

  rOut = rStr.toInt();
  gOut = gStr.toInt();
  bOut = bStr.toInt();

  // clamp to 0-255
  rOut = constrain(rOut, 0, 255);
  gOut = constrain(gOut, 0, 255);
  bOut = constrain(bOut, 0, 255);

  return true;
}

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

  //while(!digitalRead(uart_select_pin));

  uint8_t mac[6];
  uint8_t text[18];
  char name[5];

  Beacon temp;

  while(!Serial2.available()){
    //do nothing
  }
  
  while(Serial2.available()) {
    Serial.println("made it here first");
    Serial.println(Serial.available());

    if(Serial2.available() >= 18) {
      ++beacons_read;
      Serial.print("Beacon Number ");
      Serial.println(beacons_read);
      
      Serial2.readBytes(text, 18);

      for(int i = 0; i < NAME_LEN; ++i) {
        name[i] = text[i];
      }
      name[NAME_LEN] = '\0';

      int mac_ind = 0;
      for (int i = 5; i < 17; i += 2) {
          char hexPair[3] = { text[i], text[i + 1], '\0' };
          mac[mac_ind++] = (uint8_t)strtoul(hexPair, NULL, 16);
      }

      
      Serial.printf("Name (raw): %s\n", name);

      Serial.print("MAC: ");
      for (int i = 0; i < 6; ++i) {
        Serial.printf("0x%02X", mac[i]);
        if (i < 5) Serial.print(", ");
      }
      Serial.print("\n\n");

      
      // Add to the array of beacons (normalize to sentinel-padded)
      packNameWithSentinel(name, temp.name);

      for(int i = 0; i < 6; ++i) {
        temp.address[i] = mac[i];
      }

      beacons[beacons_read - 1] = temp;

      delay(250);
      
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
  // Read UART for commands: S{name}%{position}%{[r,g,b]}Z
  static char buffer[128];
  static size_t idx = 0;

  while (Serial2.available() > 0) {
    char c = (char)Serial2.read();
    if (idx == 0) {
      if (c != 'S') continue; // wait for start
      buffer[idx++] = c;
    } else {
      buffer[idx++] = c;
      if (idx >= sizeof(buffer)) idx = 0; // overflow guard
      if (c == 'Z') {
        // process command in buffer[0..idx-1]
        char deviceName[4];
        int position, r, g, b;
        if (parseCommand(buffer, idx, deviceName, position, r, g, b)) {
          int beaconIndex = findBeaconIndexByName(deviceName);
          if (beaconIndex >= 0) {
            // Format payload: "SRRRGGGBBBPPZ"
            char payload[] = "S00000024516Z";
            int n = sprintf(payload, "S%03d%03d%03d%02dZ", r, g, b, position);
            if (n > 0) {
              esp_err_t result = esp_now_send(beacons[beaconIndex].address, (uint8_t *)payload, strlen(payload)+1);
              if (result == ESP_OK) {
                Serial.print("Sent payload to ");
                for (int i = 0; i < 4; ++i) Serial.print(beacons[beaconIndex].name[i]);
                Serial.print(": ");
                Serial.println(payload);
              } else {
                Serial.println("ESP-NOW send error");
              }
            }
          } else {
            Serial.print("Unknown device name: ");
            for (int i = 0; i < 4; ++i) Serial.print(deviceName[i]);
            Serial.println();
          }
        } else {
          Serial.println("Invalid command format");
        }
        idx = 0; // reset for next command
      }
    }
  }

  delay(1);
}
