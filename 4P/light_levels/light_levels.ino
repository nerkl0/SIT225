#include <Wire.h>
#include <BH1750.h>

#define LED1 (1ul << 11) // PB11 / D3
#define PIR_SENSOR (1ul << 10) // PB10 / D2

BH1750 lightSensor;

const unsigned long SAMPLE_INTERVAL = 120000; // 2 minutes
const unsigned long MOTION_COOLDOWN = 300000; // 5 minutes

void configurePins(){
  PORT->Group[1].DIRSET.reg = LED1;
  PORT->Group[1].DIRCLR.reg = PIR_SENSOR;
  PORT->Group[1].PINCFG[10].reg = PORT_PINCFG_INEN; // enable input buffer
}

bool motionDetected(){
  return (PORT->Group[1].IN.reg & PIR_SENSOR) != 0;
}

void powerLed(bool power){ 
  if (power)
    PORT->Group[1].OUTSET.reg = LED1; // on
  else 
    PORT->Group[1].OUTCLR.reg = LED1; // off
}

void sample() {
  float lux = lightSensor.readLightLevel();
  if (lux < 0) 
    Serial.println("[ ERROR ] BH1750 read failed");
  else { 
    Serial.print(lux); Serial.println(",1"); 
  }
}

void setup() {
  // Starts the serial connection on baud 9600
  Serial.begin(9600);
  while (!Serial); // blocks the port until the python script opens it

  configurePins();
  Wire.begin();  // Start the I2C bus

  // Attempt to initialise the light sensor. Program will not begin if there is an error connecting
  while(!lightSensor.begin()) {
    Serial.println("[ ERROR ] BH1750 not found. Check sensor connections");
    delay(1000);
  }
  Serial.println("[ STATE ] BH1750 connected");

  // give PIR sensor time to warm up
  //delay(6000);
}

void loop() {
  static unsigned long lastMotion; 
  static unsigned long lastSample;
  static bool motion = false;
  unsigned long now = millis();

  if (motionDetected()) {
    lastMotion = now;
    motion = true;
  }

  bool occupied = motion && now - lastMotion < MOTION_COOLDOWN;
  powerLed(occupied);

  if (now - lastSample >= SAMPLE_INTERVAL){
    lastSample = now;
    if (occupied) 
      sample();
    else 
      Serial.println("-,0");
  }
}