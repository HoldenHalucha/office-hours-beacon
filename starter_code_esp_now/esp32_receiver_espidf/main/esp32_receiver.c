#include <stdio.h>
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "esp_wifi.h"
#include "esp_now.h"
#include "esp_event.h"
#include "esp_log.h"

//for deep sleep
#include "esp_sleep.h"
#define MICROSEC_TO_sEC 1000000ULL
#define DEEP_SLEEP_SECONDS 10

#define LED_PIN 8

// logic is inverted for super-mini boards for low power (probably)
#define LED_LOW 1
#define LED_HIGH 0

// ESP-NOW/WiFi frequency and listening window
uint16_t LISTEN_INTERVAL = 5000; //ms
uint16_t LISTEN_WINDOW = 200; //ms


// should hopefully call this when a message is received
void esp_now_received(const esp_now_recv_info_t *message_received, const uint8_t *data, int len) {
    gpio_set_level(LED_PIN, LED_HIGH);
    printf("Received stuff from MAC: ");
    for (int i = 0; i < 6; i++) printf("%02X", message_received->src_addr[i]);
    printf(" | Length: %d | RSSI: %d\n", len, message_received->rx_ctrl->rssi);

    //pretending to do something
    vTaskDelay(20 / portTICK_PERIOD_MS);

    gpio_set_level(LED_PIN, LED_LOW);

    for(int i = 0; i < len-1; ++i) {
        printf("%c", data[i]);
    }
    //printf("this is the last character: %c\n", data[len-1]);
    printf("\n");

    //message received and is the right size
    //idk why the message length shows up as 15 instead of 14
    int red_val;
    int green_val;
    int blue_val;
    int blink_mode;
    int position;
    if((len == 15) && (data[0] == 'S') && (data[13] == 'Z')) {
        sscanf((char*)data + 1, "%3d", &red_val);
        sscanf((char*)data + 4, "%3d", &green_val);
        sscanf((char*)data + 7, "%3d", &blue_val);
        sscanf((char*)data + 10, "%1d", &blink_mode);
        sscanf((char*)data + 11, "%2d", &position);

        printf("red: %d\n", red_val);
        printf("green: %d\n", green_val);
        printf("blue: %d\n", blue_val);
        printf("blink_mode: %d\n", blink_mode);
        printf("position: %d\n", position);
    }

    //message received but it is the wrong size, print error message
    else {
        printf("ERROR: Invalid message length or format. Possible loss of packets!!!\n");
    }

    printf("Goodbye\n");
    esp_sleep_enable_timer_wakeup(DEEP_SLEEP_SECONDS * MICROSEC_TO_sEC);
    esp_deep_sleep_start();

}


void app_init(void) {
    vTaskDelay(500 / portTICK_PERIOD_MS);
    printf("Hello\n");

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
    //esp_wifi_connectionless_module_set_wake_interval(LISTEN_INTERVAL); // how frequently to check
    //esp_now_set_wake_window(LISTEN_WINDOW); // how long to check
    

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
