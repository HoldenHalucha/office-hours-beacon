#include <stdio.h>
#include "driver/gpio.h"
#include "driver/adc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "esp_wifi.h"
#include "esp_now.h"
#include "esp_event.h"
#include "esp_log.h"

//get the neopixel functions
#include "neopixel.h"
#define NEOPIXEL_EN GPIO_NUM_7
#define NEOPIXEL_PIN GPIO_NUM_3
#define PIXEL_COUNT 8

#define ADC_CHANNEL ADC1_CHANNEL_1 
#define ADC_ATTEN ADC_ATTEN_DB_11
#define ADC_UNIT ADC_UNIT_1
#define ADC_WIDTH ADC_WIDTH_BIT_12

void get_battery_volts() {
    adc1_config_width(ADC_WIDTH);
    adc1_config_channel_atten(ADC_CHANNEL, ADC_ATTEN);

    //used https://docs.espressif.com/projects/esp-idf/en/release-v3.3/api-reference/peripherals/adc.html
    //and
    //https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/adc/index.html

    int adc_raw = adc1_get_raw(ADC_CHANNEL);

    float v_adc = ((float)adc_raw / 4095.0) * 3.3;

    float v_batt = v_adc * 1.5; //due to our voltage divider setup

    printf("Battery Voltage: %.2f V\n", v_batt);
}

//for deep sleep
#include "esp_sleep.h"
#define MICROSEC_TO_sEC 1000000ULL
int deep_sleep_seconds = 10;

// ESP-NOW/WiFi frequency and listening window
uint16_t LISTEN_INTERVAL = 5000; //ms
uint16_t LISTEN_WINDOW = 200; //ms

void setColor(int red, int green, int blue) {
    gpio_set_level(NEOPIXEL_EN, 1);
    tNeopixelContext neopixel = neopixel_Init(PIXEL_COUNT, NEOPIXEL_PIN);

    tNeopixel pixels[PIXEL_COUNT]; //array of neopixel objects
    for(int i = 0; i < PIXEL_COUNT; ++i) {
        pixels[i].index = i;
        pixels[i].rgb = NP_RGB(red, green, blue);
    }

    neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
    vTaskDelay(pdMS_TO_TICKS(500));


    //turn everything off
    for(int i = 0; i < PIXEL_COUNT; ++i) {
        pixels[i].index = i;
        pixels[i].rgb = NP_RGB(0, 0, 0);
    }
    neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
    gpio_set_level(NEOPIXEL_EN, 0);
}

// should hopefully call this when a message is received
void esp_now_received(const esp_now_recv_info_t *message_received, const uint8_t *data, int len) {
    printf("Received stuff from MAC: ");
    for (int i = 0; i < 6; i++) printf("%02X", message_received->src_addr[i]);
    printf(" | Length: %d | RSSI: %d\n", len, message_received->rx_ctrl->rssi);

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
    int position;
    if((len == 14) && (data[0] == 'S') && (data[12] == 'Z')) {
        sscanf((char*)data + 1, "%3d", &red_val);
        sscanf((char*)data + 4, "%3d", &blue_val);
        sscanf((char*)data + 7, "%3d", &green_val);
        sscanf((char*)data + 10, "%2d", &position);

        printf("red: %d\n", red_val);
        printf("green: %d\n", green_val);
        printf("blue: %d\n", blue_val);
        printf("position: %d\n", position);

        setColor(red_val, blue_val, green_val);
    }

    //message received but it is the wrong size, print error message
    else {
        printf("ERROR: Invalid message length or format. Possible loss of packets!!!\n");
    }

    printf("Goodbye\n");
    
    if(position < 4) {
        deep_sleep_seconds = 5;
    }
    else {
        deep_sleep_seconds = 10;
    }

    esp_sleep_enable_timer_wakeup(deep_sleep_seconds * MICROSEC_TO_sEC);
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

    gpio_reset_pin(NEOPIXEL_EN);
    gpio_set_direction(NEOPIXEL_EN, GPIO_MODE_OUTPUT);
    gpio_set_level(NEOPIXEL_EN, 1);

    // Register the receive callback
    ESP_ERROR_CHECK(esp_now_register_recv_cb(esp_now_received));
}


void app_main(void)
{
    TickType_t start = xTaskGetTickCount();
    get_battery_volts();
    app_init();

    
    while(((xTaskGetTickCount() - start) * portTICK_PERIOD_MS) < 4000);
    printf("No message, finna timeout\n");
    esp_sleep_enable_timer_wakeup(deep_sleep_seconds * MICROSEC_TO_sEC);
    esp_deep_sleep_start();
}
