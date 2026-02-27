#include <Arduino.h>
#include <Servo.h>

// Global Variables
const int switchPin  = 7;
const int buzzerPin  = 5;
const int servoPin   = 3;
const int rainDigPin = 4;
const int rainAnaPin = A0;
const int closePosition = 90;

int switchState = 0;
int buzzerVolume = 0;
int servoPosition = 0;
int targetPosition = 0;

int rainState = 0;   // digital
int rainValue = 0;   // analog

bool rainDetected = false;
bool switchOn = false;
bool servoIsClosingNow = false;
bool allowOpen = true;

Servo myServo;

unsigned long lastServoStep = 0;
const unsigned long servoStepInterval = 15; // ms per 1° step

unsigned long lastRainTime = 0;
const unsigned long reopenDelay = 5000; 

void serialPrints();
void buzzerAlert();
void servoControl();
void serialPrints();

void setup() {
  Serial.begin(9600);
  myServo.attach(servoPin);

  pinMode(switchPin, INPUT);
  pinMode(buzzerPin, OUTPUT);
  pinMode(rainDigPin, INPUT);

  myServo.write(servoPosition);
}

void loop() {
  switchState = digitalRead(switchPin);
  rainState   = digitalRead(rainDigPin);
  rainValue   = analogRead(rainAnaPin);

  rainDetected = (rainState == LOW);   // MH-RD (active LOW)
  switchOn     = (switchState == HIGH);

  serialPrints();

  
  // Allow open only when rain has been absent for {reopenDelay}
  if (rainDetected) {
    lastRainTime = millis();
  }
  
  allowOpen = (millis() - lastRainTime) > reopenDelay;

  // Close when:
  //  - switch ON
  //  - rain detected
  //  - OR still inside delay window after rain stopped
  targetPosition = (switchOn || rainDetected || !allowOpen)
                   ? closePosition
                   : 0;

  // Only ON while servo is moving to CLOSE
  servoIsClosingNow = (targetPosition == closePosition) 
                      && (servoPosition != closePosition);

  if (servoIsClosingNow) {
    // Adjust 900 (dry) and 200 (wet) after calibration
    buzzerVolume = map(rainValue, 900, 200, 0, 255);
    buzzerVolume = constrain(buzzerVolume, 0, 255);
  } else {
    buzzerVolume = 0;
  }

  buzzerAlert();
  servoControl();
  
  delay(50);
}

void buzzerAlert() {
  analogWrite(buzzerPin, buzzerVolume);
}

void servoControl() {
  if (servoPosition == targetPosition) return;
  
  // Non-blocking servo stepper
  unsigned long now = millis();
  if (now - lastServoStep < servoStepInterval) return;
  lastServoStep = now;

  int step = (targetPosition > servoPosition) ? +1 : -1;
  servoPosition += step;

  myServo.write(servoPosition);
}

void serialPrints() {
  Serial.print(rainValue);      Serial.print(",");
  Serial.print(rainDetected);   Serial.print(",");
  Serial.print(switchOn);       Serial.print(",");
  Serial.print(servoPosition);  Serial.print(",");
  Serial.println(buzzerVolume);
}