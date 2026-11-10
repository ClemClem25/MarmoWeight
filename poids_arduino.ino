#include <HX711.h>
#include <SoftwareSerial.h>

const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN  = 4;
const int buttonPin = 8;

// HC-05
const int BT_RX = 7; // HC05 TX
const int BT_TX = 13; // HC05 RX

SoftwareSerial bluetooth(BT_RX, BT_TX);

const float Calibration_Weight = 247.0;
HX711 scale; 
float scale_factor = 1.0;


void setup() {
  Serial.begin(9600);        // USB (debug)
  bluetooth.begin(9600);    // HC-05 (par défaut 9600)

  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);

  pinMode(buttonPin, INPUT_PULLUP);

  Serial.println("TARE...");
  while (digitalRead(buttonPin) == LOW) delay(10);
  scale.tare();

  Serial.println("CALIBRATION...");
  while (digitalRead(buttonPin) == LOW) delay(10);
  long reading = scale.get_value(10);
  scale_factor = (float)reading / Calibration_Weight;
  scale.set_scale(scale_factor);

  Serial.println("READY");
  bluetooth.println("READY");
}

void loop() {
  if (scale.is_ready()) {
    float weight = scale.get_units(5);

    Serial.println(weight, 3);
    bluetooth.println(weight, 3);  // envoi Bluetooth
  } else {
    bluetooth.println("0.000");
  }

  delay(100);
}
