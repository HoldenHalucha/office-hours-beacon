#include <stdio.h>
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "esp_wifi.h"
#include "esp_now.h"
#include "esp_event.h"
#include "esp_log.h"

#define LED_PIN 8

// logic is inverted for super-mini boards for low power (probably)
#define LED_LOW 1
#define LED_HIGH 0

// ESP-NOW/WiFi frequency and listening window
uint16_t LISTEN_INTERVAL = 10000; //ms
uint16_t LISTEN_WINDOW = 500; //ms

// Global state for latest command
typedef struct {
    int position;
    uint8_t r;
    uint8_t g;
    uint8_t b;
} receiver_state_t;

static receiver_state_t g_state = {0, 0, 0, 0};

// should hopefully call this when a message is received
void esp_now_received(const esp_now_recv_info_t *message_received, const uint8_t *data, int len) {
    gpio_set_level(LED_PIN, LED_HIGH);
    printf("From MAC: ");
    for (int i = 0; i < 6; i++) printf("%02X", message_received->src_addr[i]);
    printf(" | Length: %d | RSSI: %d\n", len, message_received->rx_ctrl->rssi);

    // Expect payload like: "pos|r,g,b"
    int pos = 0, r = 0, g = 0, b = 0;
    if (len > 0) {
        // Ensure null-terminated temporary buffer for parsing
        char buf[64];
        int copyLen = len < (int)sizeof(buf) - 1 ? len : (int)sizeof(buf) - 1;
        for (int i = 0; i < copyLen; ++i) buf[i] = (char)data[i];
        buf[copyLen] = '\0';

        int matched = sscanf(buf, "%d|%d,%d,%d", &pos, &r, &g, &b);
        if (matched == 4) {
            if (r < 0) r = 0; if (r > 255) r = 255;
            if (g < 0) g = 0; if (g > 255) g = 255;
            if (b < 0) b = 0; if (b > 255) b = 255;
            g_state.position = pos;
            g_state.r = (uint8_t)r;
            g_state.g = (uint8_t)g;
            g_state.b = (uint8_t)b;
            printf("Saved state -> pos:%d rgb:[%u,%u,%u]\n", g_state.position, g_state.r, g_state.g, g_state.b);
        } else {
            printf("Unexpected payload format: %s\n", buf);
        }
    }

    gpio_set_level(LED_PIN, LED_LOW);
}


void app_init(void) {
    // need this for esp-now
    ESP_ERROR_CHECK(nvs_flash_init());

    // intialize stuff (straight out of an example)
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    // intialize stuff (straight out of an example)
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());

    // initialize ESP-NOW
    ESP_ERROR_CHECK(esp_now_init());

    // power saving test 
    esp_wifi_connectionless_module_set_wake_interval(LISTEN_INTERVAL); // how frequently to check
    esp_now_set_wake_window(LISTEN_WINDOW); // how long to check

    //sanity for me
    printf("LET'S GET STARTED BOSS!\n");

    gpio_reset_pin(LED_PIN);
    gpio_set_direction(LED_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(LED_PIN, LED_LOW);

    // Register the receive callback
    ESP_ERROR_CHECK(esp_now_register_recv_cb(esp_now_received));
}


void app_main(void)
{
    app_init();

}
