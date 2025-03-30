// Arduino IDE: 
// File -> Examples -> 04.Communication -> PhysicalPixel


String command;      // variable stores  serial data

void setup() {
  // initialize serial communication:
  Serial.begin(9600);
  // initialize the LED pin as an output:
  for(int i = 2 ; i<=13 ; i++){
    pinMode(i, OUTPUT);
  }

  
}

void loop() {
  // see if there's incoming serial data:
  if (Serial.available() > 0) {
    
  
    // read the oldest byte in the serial buffer:
    command = Serial.readStringUntil('\n');
    command.trim();
    if (command.length() >= 2) {
      
      // Extract the first character as a new String
      String value = command.substring(0, 1);
      
      // Extract the left characters as a new String
      int pin = command.substring(1).toInt();


      if(value == "H"){
        // turn on the wanted pin
        digitalWrite(pin , HIGH);
      }
      else if(value == "L"){
        // turn off the wanted pin
        digitalWrite(pin, LOW);
      }
    }
    
    else{
    
    }
   
  }
}
