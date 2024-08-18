#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>
#include <ArduinoJson.h>
#include <time.h>
#include <OneWire.h>
#include <DallasTemperature.h>


// Konstan untuk UBIDOTS  
const char *UBIDOTS_TOKEN = "BBUS-xhl2VElj9gMEWA0aXyA9qnqkSd39Tp";
const char *DEVICE_LABEL = "sic";

// Konstan untuk WiFi credentials
const char *WIFI_SSID = "Cari Gratisan yaa";
const char *WIFI_PASS = "yaudahsambunginaja";

// Kalibrasi pH
const float PH4 = 1.7;  // Tegangan untuk pH 4.0
const float PH7 = 2.86;  // Tegangan untuk pH 7.0
const float PH_STEP = (PH4 - PH7) / 3;  // Langkah pH berdasarkan dua titik kalibrasi

// Pin assignments
int mq135 = 34;
#define ONE_WIRE_BUS 18
#define DHTPIN 27  // DHT22 sensor pin
#define DHTTYPE DHT11  // DHT sensor type
#define TDS_SENSOR_PIN 32
#define PH_pin 35

#define RELAY_KIPAS 26 
#define RELAY_LAMPU 33
#define RELAY_NUTRISI 14
#define RELAY_AIR 13


//DHT
DHT dht(DHTPIN, DHTTYPE);

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

const char* FLASK_URL = "http://192.168.18.172:5000/get_latest_temp_settings";
const char* FLASK_TIME_URL = "http://192.168.18.172:5000/get_latest_clock_settings";
const char* FLASK_MOTOR_URL = "http://192.168.18.172:5000/control_device";

// Konstan untuk NTP
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 6 * 3600;
const int daylightOffset_sec = 3600;

void printLocalTime()
{
    struct tm timeinfo;
    if(!getLocalTime(&timeinfo)){
        Serial.println("Failed to obtain time");
        return;
    }
    Serial.printf("%02d:%02d\n", timeinfo.tm_hour, timeinfo.tm_min);
}

// Fungsi untuk mendapatkan data suhu
float get_temperature_data() {
    float t = dht.readTemperature();
    if (isnan(t)) {
        Serial.println(F("Error reading temperature!"));
        return 0.0;  // Return default value on error
    } else {
        Serial.print(F("Temperature: "));
        Serial.print(t);
        Serial.println(F("°C"));
        return t;
    }
}

// Fungsi untuk mendapatkan data kelembaban
float get_humidity_data() {
    float h = dht.readHumidity();
    if (isnan(h)) {
        Serial.println(F("Error reading humidity!"));
        return 0.0;  // Return default value on error
    } else {
        Serial.print(F("Humidity: "));
        Serial.print(h);
        Serial.println(F("%"));
        return h;
    }
}

// Fungsi untuk membaca data analog dari air quality sensor
int get_air_quality_data() {
    int analog_data = analogRead(mq135);
    Serial.print("Air Quality: ");
    Serial.println(analog_data);
    delay(300);  // Allow sensor to stabilize
    return analog_data;
}

// Fungsi untuk menghitung pH dari data analog
float get_ph() {
    int nilai_analog_PH = analogRead(PH_pin);
    Serial.print("Nilai ADC pH: ");
    Serial.println(nilai_analog_PH);
    
    float voltage = nilai_analog_PH * (3.3 / 4095.0); // Konversi ke voltase
    Serial.print("Tegangan pH: ");
    Serial.println(voltage, 3);

    // Hitung pH dengan rumus berdasarkan kalibrasi
    float pH = 7.0 + ((voltage - PH7) / PH_STEP);
    Serial.print("pH: ");
    Serial.println(pH, 2);
    
    // Pastikan pH dalam rentang yang realistis
    if (pH < 0.0) pH = 0.0; // Minimum pH
    if (pH > 14.0) pH = 14.0; // Maksimum pH
    
    return pH;
}

float get_TDS() {
    int tdsValue = analogRead(TDS_SENSOR_PIN);
    Serial.print("Raw TDS Value: ");
    Serial.println(tdsValue);

    float tdsVoltage = (tdsValue * 3.3) / 4095.0; // Convert to voltage
    Serial.print("TDS Voltage: ");
    Serial.println(tdsVoltage, 3);

    float tdsPPM = (tdsVoltage * 133.42) / (1 + (tdsVoltage * 1.0094)); // Convert to ppm
    Serial.print("TDS PPM: ");
    Serial.println(tdsPPM, 2);

    return tdsPPM;
}

float get_ds18b20_temperature() {
    sensors.requestTemperatures(); // Mengambil suhu dari semua sensor DS18B20
    float temperature_air = sensors.getTempCByIndex(0); // Membaca suhu dari sensor pertama
    
    if (temperature_air == DEVICE_DISCONNECTED_C) {
        Serial.println("Error: No DS18B20 sensor detected.");
        return 0.0;
    } else {
        Serial.print("Temperature Water: ");
        Serial.print(temperature_air);
        Serial.println("°C");
        return temperature_air;
    }
}


// Fungsi untuk mendapatkan pengaturan suhu terbaru dari Flask
bool get_latest_temp_settings(float &min_temp, float &max_temp) {
    HTTPClient http;
    http.begin(FLASK_URL);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
        String payload = http.getString();
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, payload);
        if (error) {
            Serial.print("deserializeJson() failed: ");
            Serial.println(error.f_str());
            http.end();
            return false;
        }

        min_temp = doc["min_temp"];
        max_temp = doc["max_temp"];
        
        Serial.print("Min Temp from Flask: ");
        Serial.println(min_temp);
        Serial.print("Max Temp from Flask: ");
        Serial.println(max_temp);

        http.end();
        return true;
    } else {
        Serial.print("Failed to retrieve settings. HTTP Code: ");
        Serial.println(httpCode);
        http.end();
        return false;
    }
}

bool get_latest_clock_settings(String &alarm_time_1, String &alarm_time_2, String &alarm_time_3) {
    HTTPClient http;
    http.begin(FLASK_TIME_URL);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
        String payload = http.getString();
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, payload);
        if (error) {
            Serial.print("deserializeJson() failed: ");
            Serial.println(error.f_str());
            http.end();
            return false;
        }

        alarm_time_1 = doc["alarm_time_1"].as<String>();
        alarm_time_2 = doc["alarm_time_2"].as<String>();
        alarm_time_3 = doc["alarm_time_3"].as<String>();

        http.end();
        return true;
    } else {
        Serial.print("Failed to retrieve settings. HTTP Code: ");
        Serial.println(httpCode);
        http.end();
        return false;
    }
}

bool get_motor_status() {
    HTTPClient http;
    String url = String(FLASK_MOTOR_URL) + "?status=ON"; // Tambahkan parameter jika diperlukan
    http.begin(url);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
        String payload = http.getString();
        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, payload);
        if (error) {
            Serial.print("deserializeJson() failed: ");
            Serial.println(error.f_str());
            http.end();
            return false;
        }

        bool motor_status = doc["motor_status"];
        Serial.print("Motor status from Flask: ");
        Serial.println(motor_status ? "ON" : "OFF");
        http.end();
        return true;
    } else {
        Serial.print("Failed to retrieve motor status. HTTP Code: ");
        Serial.println(httpCode);
        http.end();
        return false;
    }
}


// Fungsi untuk mengirim data ke ubidots menggunakan HTTP POST
void send_data_to_ubidots(float temperature, float humidity, int air_quality, float PH, float TDS, float temperature_water) {
    HTTPClient http;
    String url = "https://industrial.api.ubidots.com/api/v1.6/devices/" + String(DEVICE_LABEL) + "/";
    String post_data = "{\"temperature\":" + String(temperature) + ",\"humidity\":" + String(humidity) +
                        ",\"air_quality\":" + String(air_quality) + ",\"pH\":" + String(PH) +
                        ",\"TDS\":" + String(TDS) + ",\"temperature_water\":" + String(temperature_water) + "}";
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Auth-Token", UBIDOTS_TOKEN);
    int httpResponseCode = http.POST(post_data);

    // Check response
    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("HTTP Response code: " + String(httpResponseCode));
        Serial.println("Response: " + response);
    } else {
        Serial.println("Error on sending POST: " + String(httpResponseCode));
        Serial.println("Payload: " + post_data);
    }

    // End HTTP request
    http.end();
}

void parse_alarm_time(const String &alarm_time, int &hour, int &minute) {
    int separatorIndex = alarm_time.indexOf(':');
    if (separatorIndex != -1) {
        hour = alarm_time.substring(0, separatorIndex).toInt();
        minute = alarm_time.substring(separatorIndex + 1).toInt();
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(RELAY_KIPAS, OUTPUT);
    pinMode(RELAY_LAMPU, OUTPUT);
    pinMode(RELAY_NUTRISI, OUTPUT);
    pinMode(RELAY_AIR, OUTPUT);
    pinMode(PH_pin, INPUT);
    pinMode(TDS_SENSOR_PIN, INPUT);

    digitalWrite(RELAY_AIR,LOW);
    digitalWrite(RELAY_KIPAS, LOW);
    digitalWrite(RELAY_LAMPU, LOW);
    digitalWrite(RELAY_NUTRISI, LOW); // Set default to HIGH to keep motor off

    WiFi.begin(WIFI_SSID, WIFI_PASS);

    // Wait for connection
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("Connected to WiFi");

    dht.begin();
    sensors.begin();

    // Setup time with NTP
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    Serial.println("Waiting for NTP time sync...");
    while (time(nullptr) < 8 * 3600 * 2) {
        delay(100);
        Serial.print(".");
    }
    Serial.println();
    Serial.println("Time synchronized.");
}

void loop() {
  //Motor 
    digitalWrite(RELAY_AIR,LOW);

    float min_temp = 20.0, max_temp = 30.0;
    if (!get_latest_temp_settings(min_temp, max_temp)) {
        Serial.println("Failed to retrieve temperature settings.");
    }

    String alarm_time_1, alarm_time_2, alarm_time_3;
    if (!get_latest_clock_settings( alarm_time_1, alarm_time_2, alarm_time_3)) {
        Serial.println("Failed to retrieve clock settings.");
    } else {
        Serial.print("Nutrisi Diberikan pada waktu: ");
        Serial.print(alarm_time_1);
        Serial.print(", ");
        Serial.print(alarm_time_2);
        Serial.print(", ");
        Serial.println(alarm_time_3);
    }

    delay(1000);

    int alarm_hour_1 = 0, alarm_minute_1 = 0;
    int alarm_hour_2 = 0, alarm_minute_2 = 0;
    int alarm_hour_3 = 0, alarm_minute_3 = 0;

    parse_alarm_time(alarm_time_1, alarm_hour_1, alarm_minute_1);
    parse_alarm_time(alarm_time_2, alarm_hour_2, alarm_minute_2);
    parse_alarm_time(alarm_time_3, alarm_hour_3, alarm_minute_3);

    // Mendapatkan waktu saat ini
    time_t now = time(nullptr);
    struct tm *current_time = localtime(&now);
    int current_hour = current_time->tm_hour;
    int current_minute = current_time->tm_min;

    Serial.print("Current Time: ");
    Serial.print(current_hour);
    Serial.print(":");
    Serial.println(current_minute);
  
    Serial.print("Alarm Time 1: ");
    Serial.println(alarm_time_1);
    Serial.print("Alarm Time 2: ");
    Serial.println(alarm_time_2);
    Serial.print("Alarm Time 3: ");
    Serial.println(alarm_time_3);

    if ((current_hour == alarm_hour_1 && current_minute == alarm_minute_1) ||
        (current_hour == alarm_hour_2 && current_minute == alarm_minute_2) ||
        (current_hour == alarm_hour_3 && current_minute == alarm_minute_3)) {
        Serial.println("Waktunya memberi nutrisi! Menyalakan motor.");
        digitalWrite(RELAY_NUTRISI, LOW); // Nyalakan motor
        delay(60000); //satu menit
        digitalWrite(RELAY_NUTRISI, HIGH);
          } 
    else {
        digitalWrite(RELAY_NUTRISI, HIGH); // Matikan motor jika tidak dalam waktu alarm
    }

    float temperature = get_temperature_data();
    float humidity = get_humidity_data();
    int air_quality = get_air_quality_data();
    float sensor_ph = get_ph();
    float tds = get_TDS(); // Retrieve TDS value
    float ds18b20_temp = get_ds18b20_temperature();

    Serial.print("Temperature: ");
    Serial.println(temperature);
    Serial.print("Humidity: ");
    Serial.println(humidity);
    Serial.print("Air Quality: ");
    Serial.println(air_quality);
    Serial.print("pH: ");
    Serial.println(sensor_ph);
    Serial.print("TDS : ");
    Serial.println(tds);
    Serial.print("Temperature Water: ");
    Serial.println(ds18b20_temp);

    if (temperature > max_temp) {
        Serial.println("Suhu diatas batas maksimum Kipas dinyalakan");
        digitalWrite(RELAY_KIPAS, LOW);  // Nyalakan kipas
        digitalWrite(RELAY_LAMPU,HIGH);
    } else if (temperature < min_temp) {
        Serial.println("Suhu dibawah batas minimum Lampu menyala");
        digitalWrite(RELAY_KIPAS, HIGH);   // Matikan kipas
        digitalWrite(RELAY_LAMPU,LOW);
    } else {
        Serial.println("Suhu dalam batas normal ");
        digitalWrite(RELAY_KIPAS, HIGH);
        digitalWrite(RELAY_LAMPU,HIGH);
    }


    if (air_quality < 200) {
        Serial.println("Kualitas Udara: Sangat Baik");
    } else if (air_quality >= 200 && air_quality < 400) {
        Serial.println("Kualitas Udara: Baik");
    } else if (air_quality >= 400 && air_quality < 800) {
        Serial.println("Kualitas Udara: Sedang");
    } else if (air_quality >= 800 && air_quality < 1000) {
        Serial.println("Kualitas Udara: Buruk");
    } else {
        Serial.println("Kualitas Udara: Sangat Buruk");
    }

    

    send_data_to_ubidots(temperature, humidity, air_quality, sensor_ph, tds, ds18b20_temp); // Send TDS data
    delay(5000);  // Delay between data sends
}
