#include <Wire.h>
#include <BH1750.h>

BH1750 lightSensor;

// Time between readings in milliseconds.
const unsigned long SAMPLE_INTERVAL_MS = 10000;

// Stores the millis() value from the last reading so the loop can time
// itself without using the blocking delay() function 
unsigned long lastSampleTime = 0;

void setup() {
  // Starts the serial connection on baud 9600
  Serial.begin(9600);
  while (!Serial); // blocks the port until the python script opens it

  // Start the I2C bus
  Wire.begin();

  // Attempt to initialise the light sensor. Program will not begin if there is an error connecting
  // Serial prints with # will be ignored in the python script
  while(!lightSensor.begin()) {
    Serial.println("[ ERROR ] BH1750 not found. Check sensor connections");
    delay(1000);
  }

  Serial.println("[ STATE ] BH1750 connected");
}

void loop() {
  // set now to current uptime of the board to assist in tracking the next sample
  unsigned long now = millis(); 

  // Gates the light reading to only sample the set interval
  if (now - lastSampleTime >= SAMPLE_INTERVAL_MS) {
    lastSampleTime = now; // Reset the sample timer

    // Read and print value to serial for python script. Python script handles data
    float lux = lightSensor.readLightLevel();
    Serial.println(lux);
  }
}