/*
 * EPDM Vacuum Test LCD Display Controller
 * 
 * Arduino Nano connected to Raspberry Pi via USB serial.
 * Displays status messages on I2C LCD 1602 (16x2 character display).
 * Supports scrolling for long text (jokes, etc.)
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
 *   - "SCROLL:text1|text2" - Display with auto-scrolling for long text
 *   - "NOSCROLL" - Stop scrolling, return to static display
 *   
 * Author: EPDM Vacuum Test System
 * License: MIT
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// LCD Configuration
#define LCD_ADDRESS 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

// Serial Configuration
#define SERIAL_BAUD 115200
#define MAX_MESSAGE_LENGTH 200  // Increased for longer jokes

// Scroll Configuration
#define SCROLL_DELAY_MS 400      // Time between scroll steps
#define SCROLL_PAUSE_START 2000  // Pause at start before scrolling
#define SCROLL_PAUSE_END 1500    // Pause at end before restarting

// Initialize LCD
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// Buffer for incoming serial data
char inputBuffer[MAX_MESSAGE_LENGTH];
int bufferIndex = 0;

// Current static display state
char line1[LCD_COLS + 1] = "";
char line2[LCD_COLS + 1] = "";
bool backlightOn = true;

// Scrolling state
bool scrollMode = false;
char scrollText1[MAX_MESSAGE_LENGTH] = "";
char scrollText2[MAX_MESSAGE_LENGTH] = "";
int scrollPos1 = 0;
int scrollPos2 = 0;
int scrollLen1 = 0;
int scrollLen2 = 0;
unsigned long lastScrollTime = 0;
bool scrollPauseStart = true;
bool scrollPauseEnd = false;
unsigned long scrollPauseTime = 0;

// Timing
unsigned long lastUpdate = 0;
const unsigned long heartbeatInterval = 30000;

void setup() {
  Serial.begin(SERIAL_BAUD);
  
  lcd.init();
  lcd.backlight();
  
  lcd.setCursor(0, 0);
  lcd.print("EPDM Vacuum Test");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  
  delay(1000);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ready");
  lcd.setCursor(0, 1);
  lcd.print("Awaiting data...");
  
  Serial.println("READY");
  lastUpdate = millis();
}

void loop() {
  // Read serial data
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
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
  
  // Handle scrolling animation
  if (scrollMode) {
    handleScrolling();
  }
  
  // Show "No Data" after timeout
  if (millis() - lastUpdate > heartbeatInterval) {
    scrollMode = false;
    lcd.setCursor(0, 1);
    lcd.print("No data...      ");
    lastUpdate = millis();
  }
}

void handleScrolling() {
  unsigned long now = millis();
  
  // Handle pause at start
  if (scrollPauseStart) {
    if (now - scrollPauseTime >= SCROLL_PAUSE_START) {
      scrollPauseStart = false;
      lastScrollTime = now;
    }
    return;
  }
  
  // Handle pause at end (before restart)
  if (scrollPauseEnd) {
    if (now - scrollPauseTime >= SCROLL_PAUSE_END) {
      scrollPauseEnd = false;
      scrollPos1 = 0;
      scrollPos2 = 0;
      scrollPauseStart = true;
      scrollPauseTime = now;
      displayScrollFrame();
    }
    return;
  }
  
  // Time to scroll?
  if (now - lastScrollTime >= SCROLL_DELAY_MS) {
    lastScrollTime = now;
    
    bool line1Done = (scrollLen1 <= LCD_COLS) || (scrollPos1 >= scrollLen1 - LCD_COLS);
    bool line2Done = (scrollLen2 <= LCD_COLS) || (scrollPos2 >= scrollLen2 - LCD_COLS);
    
    // Advance scroll positions
    if (!line1Done) scrollPos1++;
    if (!line2Done) scrollPos2++;
    
    displayScrollFrame();
    
    // Check if both lines are done scrolling
    if (line1Done && line2Done) {
      scrollPauseEnd = true;
      scrollPauseTime = now;
    }
  }
}

void displayScrollFrame() {
  // Display line 1
  lcd.setCursor(0, 0);
  for (int i = 0; i < LCD_COLS; i++) {
    int idx = scrollPos1 + i;
    if (idx < scrollLen1) {
      lcd.print(scrollText1[idx]);
    } else {
      lcd.print(' ');
    }
  }
  
  // Display line 2
  lcd.setCursor(0, 1);
  for (int i = 0; i < LCD_COLS; i++) {
    int idx = scrollPos2 + i;
    if (idx < scrollLen2) {
      lcd.print(scrollText2[idx]);
    } else {
      lcd.print(' ');
    }
  }
}

void startScrolling(const char* text1, const char* text2) {
  strncpy(scrollText1, text1, MAX_MESSAGE_LENGTH - 1);
  scrollText1[MAX_MESSAGE_LENGTH - 1] = '\0';
  strncpy(scrollText2, text2, MAX_MESSAGE_LENGTH - 1);
  scrollText2[MAX_MESSAGE_LENGTH - 1] = '\0';
  
  scrollLen1 = strlen(scrollText1);
  scrollLen2 = strlen(scrollText2);
  scrollPos1 = 0;
  scrollPos2 = 0;
  
  scrollMode = true;
  scrollPauseStart = true;
  scrollPauseEnd = false;
  scrollPauseTime = millis();
  
  // Display initial frame
  displayScrollFrame();
}

void processMessage(const char* message) {
  // Handle special commands
  if (strcmp(message, "CLEAR") == 0) {
    scrollMode = false;
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
  
  if (strcmp(message, "NOSCROLL") == 0) {
    scrollMode = false;
    Serial.println("OK:NOSCROLL");
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
  
  // SCROLL command - enable scrolling mode
  if (strncmp(message, "SCROLL:", 7) == 0) {
    const char* content = message + 7;
    char* pipePos = strchr(content, '|');
    
    if (pipePos != NULL) {
      *pipePos = '\0';
      startScrolling(content, pipePos + 1);
    } else {
      startScrolling(content, "");
    }
    Serial.println("OK:SCROLL");
    return;
  }
  
  if (strncmp(message, "LINE1:", 6) == 0) {
    scrollMode = false;
    updateLine(0, message + 6);
    Serial.println("OK:LINE1");
    return;
  }
  
  if (strncmp(message, "LINE2:", 6) == 0) {
    scrollMode = false;
    updateLine(1, message + 6);
    Serial.println("OK:LINE2");
    return;
  }
  
  // Standard message format: "LINE1|LINE2" (static, no scroll)
  scrollMode = false;
  char* pipePos = strchr(message, '|');
  if (pipePos != NULL) {
    *pipePos = '\0';
    const char* newLine1 = message;
    const char* newLine2 = pipePos + 1;
    
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
    if (strcmp(line1, message) != 0) {
      updateLine(0, message);
      updateLine(1, "");
    }
    Serial.println("OK:DISPLAY");
  }
}

void updateLine(int lineNum, const char* text) {
  char* lineBuffer = (lineNum == 0) ? line1 : line2;
  
  int len = strlen(text);
  if (len > LCD_COLS) len = LCD_COLS;
  
  strncpy(lineBuffer, text, len);
  lineBuffer[len] = '\0';
  
  lcd.setCursor(0, lineNum);
  lcd.print(lineBuffer);
  
  for (int i = len; i < LCD_COLS; i++) {
    lcd.print(' ');
  }
}
