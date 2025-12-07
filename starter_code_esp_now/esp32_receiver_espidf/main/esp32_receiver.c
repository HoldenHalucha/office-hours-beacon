#include <stdio.h>
#include "driver/gpio.h"
#include "driver/adc.h"
#include "esp_adc_cal.h"
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

#define ADC_CHANNEL ADC1_CHANNEL_0 
#define ADC_ATTEN ADC_ATTEN_DB_12
#define ADC_UNIT ADC_UNIT_1
#define ADC_WIDTH ADC_WIDTH_BIT_12

//to avoid long delays between position switches I am changing to have a struct for RTOS stuff
typedef struct {
    int red;
    int green;
    int blue;
    int position;
    bool new_command;
} command_t;

command_t command = {0,0,0,99,0};
SemaphoreHandle_t command_semaphore;

bool message_received_ignore_main = false;

tNeopixelContext neopixel;

tNeopixel pixels[PIXEL_COUNT]; //array of neopixel objects

float get_battery_volts() {
    esp_adc_cal_characteristics_t adc_chars;

    adc1_config_width(ADC_WIDTH);
    adc1_config_channel_atten(ADC_CHANNEL, ADC_ATTEN);

    esp_adc_cal_value_t val_type = esp_adc_cal_characterize(
        ADC_UNIT, ADC_ATTEN, ADC_WIDTH_BIT_12, 1100, &adc_chars);

    //used https://docs.espressif.com/projects/esp-idf/en/release-v3.3/api-reference/peripherals/adc.html
    //and
    //https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/adc/index.html

    int adc_raw = adc1_get_raw(ADC_CHANNEL);

    uint32_t voltage_mv = esp_adc_cal_raw_to_voltage(adc_raw, &adc_chars);
    float v_adc = voltage_mv / 1000.0; // in Volts

    // Battery calculation: Vadc = (2/3) * Vbatt => Vbatt = Vadc * (3/2)
    float v_batt = v_adc * 1.5;

    printf("Raw ADC: %d | ADC Voltage: %.3f V | Battery Voltage: %.3f V\n",
            adc_raw, v_adc, v_batt);

    printf("Battery Voltage: %.2f V\n", v_batt + 0.2);

    return v_batt + 0.2;
}

//for deep sleep
#include "esp_sleep.h"
#define MICROSEC_TO_sEC 1000000ULL
float deep_sleep_seconds = 6.7;

// ESP-NOW/WiFi frequency and listening window
uint16_t LISTEN_INTERVAL = 5000; //ms
uint16_t LISTEN_WINDOW = 200; //ms

void poweroff_neopixels() {
    for(int i = 0; i < PIXEL_COUNT; ++i) {
        pixels[i].index = i;
        pixels[i].rgb = NP_RGB(0, 0, 0);
    }
    neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
    gpio_set_level(NEOPIXEL_EN, 0);
}

void setColor(int red, int green, int blue, int position) {
    //POSITION MEANING
    // -1 = PINNED
    // -2 = BEING HELPED
    // 1 thru inf = ACTUAL POSITION VALUE

    //just a battery check
    float battery_life = get_battery_volts();

    if(battery_life < 3.3) {
        esp_sleep_enable_timer_wakeup(20 * MICROSEC_TO_sEC);
        esp_deep_sleep_start();
    }

    gpio_set_level(NEOPIXEL_EN, 1);

    int blink_pos_val = 0;
    //logic to decide how much to blink
    if(position >= 4) {
        blink_pos_val = 2;
    }
    else if(position < 4 && position > 1) {
        blink_pos_val = 2;
    }
    else if(position == 1) {
        blink_pos_val = 10;
    }
    else if(position == -2 || position == -1) {
        blink_pos_val = 0;
    }
    

    if(position == -1) {
        for(float brightness = 0.0; brightness <= 1.0; brightness+=0.05) {
            for(int i = 0; i < PIXEL_COUNT; ++i) {
                pixels[i].index = i;
                int actual_red = red * brightness;
                int actual_green = green * brightness;
                int actual_blue = blue * brightness;
                pixels[i].rgb = NP_RGB(actual_red, actual_blue, actual_green);
            }

            neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
            vTaskDelay(pdMS_TO_TICKS(70));
        }
        for(float brightness = 1.0; brightness >= 0.0; brightness-=0.05) {
            for(int i = 0; i < PIXEL_COUNT; ++i) {
                pixels[i].index = i;
                int actual_red = red * brightness;
                int actual_green = green * brightness;
                int actual_blue = blue * brightness;
                pixels[i].rgb = NP_RGB(actual_red, actual_blue, actual_green);
            }

            neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
            vTaskDelay(pdMS_TO_TICKS(70));
        }
    }


    else if(position == 2 || position == 3) {
        for(int i = 0; i < PIXEL_COUNT; ++i) {
            pixels[i].index = i;
            pixels[i].rgb = NP_RGB(red*0.30, blue*0.30, green*0.30);
        }
        neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
        //gpio_set_level(NEOPIXEL_EN, 0);
    }


    else if(position >= 4) {
        for(int i = 0; i < PIXEL_COUNT; ++i) {
            pixels[i].index = i;
            pixels[i].rgb = NP_RGB(red*0.05, blue*0.05, green*0.05);
        }
        neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
        //gpio_set_level(NEOPIXEL_EN, 0);
    }


    else if(position == 1) {
        //for(int blink = 0; blink < 10; ++blink) {
        for(int i = 0; i < PIXEL_COUNT; ++i) {
            pixels[i].index = i;
            pixels[i].rgb = NP_RGB(red, blue, green);
        }

        neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
        vTaskDelay(pdMS_TO_TICKS(200));

        //turn everything off
        for(int i = 0; i < PIXEL_COUNT; ++i) {
            pixels[i].index = i;
            pixels[i].rgb = NP_RGB(0, 0, 0);
        }
        neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
        vTaskDelay(pdMS_TO_TICKS(200));
        //gpio_set_level(NEOPIXEL_EN, 0);
        //}
    }

    else {
        for(int i = 0; i < PIXEL_COUNT; ++i) {
            pixels[i].index = i;
            pixels[i].rgb = NP_RGB(0, 0, 0);
        }
        neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
        gpio_set_level(NEOPIXEL_EN, 0);

    }

    /*
    for(int blink = 0; blink < blink_pos_val; ++blink) {
        for(int i = 0; i < PIXEL_COUNT; ++i) {
            pixels[i].index = i;
            pixels[i].rgb = NP_RGB(red, green, blue);
        }

        neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
        vTaskDelay(pdMS_TO_TICKS(200));

        //turn everything off
        for(int i = 0; i < PIXEL_COUNT; ++i) {
            pixels[i].index = i;
            pixels[i].rgb = NP_RGB(0, 0, 0);
        }
        neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
        vTaskDelay(pdMS_TO_TICKS(200));
    }
    

    //turn everything off
    for(int i = 0; i < PIXEL_COUNT; ++i) {
        pixels[i].index = i;
        pixels[i].rgb = NP_RGB(0, 0, 0);
    }
    neopixel_SetPixel(neopixel, pixels, PIXEL_COUNT);
    gpio_set_level(NEOPIXEL_EN, 0);
    */
}

// should hopefully call this when a message is received
void esp_now_received(const esp_now_recv_info_t *message_received, const uint8_t *data, int len) {
    message_received_ignore_main = true;

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

        //setColor(red_val, green_val, blue_val, position);

        //changing the actual global command struct to avoid delays 
        if(xSemaphoreTake(command_semaphore, 0) == pdTRUE) {
            command.red = red_val;
            command.blue = blue_val;
            command.green = green_val;
            command.position = position;
            command.new_command = 1; //latest command
            xSemaphoreGive(command_semaphore);
        }
    }

    //message received but it is the wrong size, print error message
    else {
        printf("ERROR: Invalid message length or format. Possible loss of packets!!!\n");
    }

    //poweroff_neopixels();
    /*

    printf("Goodbye\n");
    
    if(position >= 4) {
        deep_sleep_seconds = 10;
    }
    else if(position > 1 && position < 4) {
        deep_sleep_seconds = 5;
    }
    else {
        deep_sleep_seconds = 0.8;
    }
    */

    if(position == -3) {
        esp_sleep_enable_timer_wakeup(deep_sleep_seconds * MICROSEC_TO_sEC);
        esp_deep_sleep_start();
    }

}

void setting_command_task(void *pvParameters) {
    while (1) {
        bool update = 0;
        command_t command_copy;

        if (xSemaphoreTake(command_semaphore, 10 / portTICK_PERIOD_MS) == pdTRUE) {
            if (command.new_command) {
                update = 1;
                command_copy = command;
                command.new_command = 0;  //this is no longer new
            }
            xSemaphoreGive(command_semaphore);
        }

        if (update) {
            setColor(command_copy.red, command_copy.green, command_copy.blue, command_copy.position);
        }

        // Small delay so task isn't busy-waiting
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void app_init(void) {
    vTaskDelay(500 / portTICK_PERIOD_MS);
    printf("Hello\n");

    neopixel = neopixel_Init(PIXEL_COUNT, NEOPIXEL_PIN);

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

    command_semaphore = xSemaphoreCreateMutex(); //correct syntax?
    xTaskCreate(setting_command_task, "command_task", 4096, NULL, 5, NULL);
}


void app_main(void)
{
    
    //TickType_t start = xTaskGetTickCount();
    float battery_life = get_battery_volts();

    if(battery_life < 3.3) {
        esp_sleep_enable_timer_wakeup(20 * MICROSEC_TO_sEC);
        esp_deep_sleep_start();
    }

    else {
        app_init();
    }

    
    //while(((xTaskGetTickCount() - start) * portTICK_PERIOD_MS) < 5000);
    vTaskDelay(pdMS_TO_TICKS(2000));

    if(!message_received_ignore_main) {
        printf("No message, finna timeout\n");
        esp_sleep_enable_timer_wakeup(deep_sleep_seconds * MICROSEC_TO_sEC);
        esp_deep_sleep_start();
    }
    
}
