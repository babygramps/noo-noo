/*
 * EPDM Vacuum Test LCD Display Controller
 * 
 * Arduino Nano connected to Raspberry Pi via USB serial.
 * Displays status messages on I2C LCD 1602 (16x2 character display).
 * 
 * Wiring:
 *   LCD VCC -> Arduino 5V
 *   LCD GND -> Arduino GND
 *   LCD SDA -> Arduino A4
 *   LCD SCL -> Arduino A5
 * 
 * Serial Protocol:
 *   Messages are newline-terminated strings.
 *   Format: "LINE1|LINE2" (pipe separates lines)
 *   Example: "Vacuum: 0.3 bar|Stage: Evacuate"
 *   
 *   Special commands:
 *   - "CLEAR" - Clear the display
 *   - "BACKLIGHT:ON" / "BACKLIGHT:OFF" - Control backlight
 *   - "PING" - Returns "PONG" (for connection testing)
 *   
 * Author: EPDM Vacuum Test System
 * License: MIT
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// LCD Configuration
// Default I2C address for PCF8574T is 0x27, for PCF8574AT it's 0x3F
// If display doesn't work, try the other address
#define LCD_ADDRESS 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

// Serial Configuration
#define SERIAL_BAUD 115200
#define MAX_MESSAGE_LENGTH 64

// Initialize LCD (address, columns, rows)
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// Buffer for incoming serial data
char inputBuffer[MAX_MESSAGE_LENGTH];
int bufferIndex = 0;

// Current display state
char line1[LCD_COLS + 1] = "";
char line2[LCD_COLS + 1] = "";
bool backlightOn = true;

// Timing for status display
unsigned long lastUpdate = 0;
const unsigned long heartbeatInterval = 30000; // 30 seconds

void setup() {
  // Initialize serial communication
  Serial.begin(SERIAL_BAUD);
  
  // Initialize LCD
  lcd.init();
  lcd.backlight();
  
  // Show startup message
  lcd.setCursor(0, 0);
  lcd.print("EPDM Vacuum Test");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  
  delay(1000);
  
  // Ready message
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ready");
  lcd.setCursor(0, 1);
  lcd.print("Awaiting data...");
  
  // Send ready signal to Pi
  Serial.println("READY");
  
  lastUpdate = millis();
}

void loop() {
  // Read serial data
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      // End of message
      if (bufferIndex > 0) {
        inputBuffer[bufferIndex] = '\0';
        processMessage(inputBuffer);
        bufferIndex = 0;
      }
    } else if (bufferIndex < MAX_MESSAGE_LENGTH - 1) {
      inputBuffer[bufferIndex++] = c;
    }
    
    lastUpdate = millis();
  }
  
  // Show "No Data" after timeout (indicates connection lost)
  if (millis() - lastUpdate > heartbeatInterval) {
    lcd.setCursor(0, 1);
    lcd.print("No data...      ");
    lastUpdate = millis();
  }
}

void processMessage(const char* message) {
  // Handle special commands
  if (strcmp(message, "CLEAR") == 0) {
    lcd.clear();
    strcpy(line1, "");
    strcpy(line2, "");
    Serial.println("OK:CLEAR");
    return;
  }
  
  if (strcmp(message, "PING") == 0) {
    Serial.println("PONG");
    return;
  }
  
  if (strcmp(message, "BACKLIGHT:ON") == 0) {
    lcd.backlight();
    backlightOn = true;
    Serial.println("OK:BACKLIGHT:ON");
    return;
  }
  
  if (strcmp(message, "BACKLIGHT:OFF") == 0) {
    lcd.noBacklight();
    backlightOn = false;
    Serial.println("OK:BACKLIGHT:OFF");
    return;
  }
  
  if (strncmp(message, "LINE1:", 6) == 0) {
    // Update only line 1
    updateLine(0, message + 6);
    Serial.println("OK:LINE1");
    return;
  }
  
  if (strncmp(message, "LINE2:", 6) == 0) {
    // Update only line 2
    updateLine(1, message + 6);
    Serial.println("OK:LINE2");
    return;
  }
  
  // Standard message format: "LINE1|LINE2"
  char* pipePos = strchr(message, '|');
  if (pipePos != NULL) {
    // Split message at pipe
    *pipePos = '\0';
    const char* newLine1 = message;
    const char* newLine2 = pipePos + 1;
    
    // Only update if content changed (reduces LCD flicker)
    bool changed = false;
    if (strcmp(line1, newLine1) != 0) {
      updateLine(0, newLine1);
      changed = true;
    }
    if (strcmp(line2, newLine2) != 0) {
      updateLine(1, newLine2);
      changed = true;
    }
    
    if (changed) {
      Serial.println("OK:DISPLAY");
    }
  } else {
    // Single line - display on line 1, clear line 2
    if (strcmp(line1, message) != 0) {
      updateLine(0, message);
      updateLine(1, "");
    }
    Serial.println("OK:DISPLAY");
  }
}

void updateLine(int lineNum, const char* text) {
  char* lineBuffer = (lineNum == 0) ? line1 : line2;
  
  // Copy and pad with spaces to clear old content
  int len = strlen(text);
  if (len > LCD_COLS) len = LCD_COLS;
  
  strncpy(lineBuffer, text, len);
  lineBuffer[len] = '\0';
  
  // Display on LCD
  lcd.setCursor(0, lineNum);
  lcd.print(lineBuffer);
  
  // Pad with spaces to clear remaining characters
  for (int i = len; i < LCD_COLS; i++) {
    lcd.print(' ');
  }
}
