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
int rainIntensity = 0;

int rainState = 0;   // digital
int rainValue = 0;   // analog

bool rainDetected = false;
bool switchOn = false;
bool servoIsClosingNow = false;
bool allowOpen = true;
bool forceOpenCmd = false;

Servo myServo;

unsigned long lastServoStep = 0;
const unsigned long servoStepInterval = 15; // ms per 1° step

unsigned long lastRainTime = 0;
const unsigned long reopenDelay = 5000; 

void serialPrints();
void buzzerAlert();
void servoControl();
void checkSerialCommand();

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);   // faster readStringUntil
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

  checkSerialCommand();

  rainDetected = (rainState == LOW);   // MH-RD (active LOW)
  switchOn     = (switchState == HIGH);
  rainIntensity = map(rainValue, 900, 200, 0, 100);
  rainIntensity = constrain(rainIntensity, 0, 100);
  

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
  if (forceOpenCmd) {
    targetPosition = 0;   // keep open
    buzzerVolume = 0;     // keep silent

    buzzerAlert();
    servoControl();
    delay(50);
    return;   
  } 

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

void printFixed3(int value) {
  char buffer[5];                
  snprintf(buffer, sizeof(buffer), "%3d", value);
  Serial.print(buffer);
}

void serialPrints() {
  printFixed3(rainIntensity);     Serial.print(",");
  printFixed3(rainDetected);  Serial.print(",");
  printFixed3(switchOn);      Serial.print(",");
  printFixed3(servoPosition); Serial.print(",");
  printFixed3(buzzerVolume); Serial.print(",");
  printFixed3(forceOpenCmd);
  Serial.println();
}

void checkSerialCommand() {
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "forceOpen") {
      forceOpenCmd = true;        // latch ON
      // reset auto-close logic so it won't immediately re-close after release
      lastRainTime = 0;
      allowOpen = true;
    }
    else if (cmd == "forceOpenOff") {
      forceOpenCmd = false;       // latch OFF (deselected)
    }
  }
}