#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <string>

#undef DEBUG
char ssid[] = "Bapa ne keh Wi-Fi nakhave";  //  your network SSID (name)
char pass[] = "Aapu2minute";       // your network password
#define VERSIONNUMBER 28
#define LOGGERIPINC 20
#define SWARMSIZE 6
// 30 seconds is too old - it must be dead
#define SWARMTOOOLD 30000
int mySwarmID = 0;
// Packet Types
#define LIGHT_UPDATE_PACKET 0
#define RESET_SWARM_PACKET 1
#define CHANGE_TEST_PACKET 2
#define RESET_ME_PACKET 3
#define DEFINE_SERVER_LOGGER_PACKET 4
#define LOG_TO_SERVER_PACKET 5
#define MASTER_CHANGE_PACKET 6
#define BLINK_BRIGHT_LED 7
unsigned int localPort = 5006;      // local port to listen for UDP packets
// master variables
boolean masterState = true;   // True if master, False if not
int swarmClear[SWARMSIZE];
int swarmVersion[SWARMSIZE];
int swarmState[SWARMSIZE];
long swarmTimeStamp[SWARMSIZE];   // for aging
IPAddress serverAddress = IPAddress(0, 0, 0, 0); // default no IP Address
int swarmAddresses[SWARMSIZE];  // Swarm addresses
// variables for light sensor
int redColor;
int blueColor;
int greenColor;
uint16_t ldr = 0;
const int ldrPin = A0;
int ledPins[] = {D1, D2, D5, D6, D7, D8};
const int PACKET_SIZE = 14; // Light Update Packet
const int BUFFERSIZE = 1024;
byte packetBuffer[BUFFERSIZE]; //buffer to hold incoming and outgoing packets
// A UDP instance to let us send and receive packets over UDP
WiFiUDP udp;
IPAddress localIP;
int a = 16;
void setup()
{
  delay(200);
  Serial.begin(9600);
  Serial.println();
  Serial.println();

  Serial.println("");
  Serial.println("--------------------------");
  Serial.println("LightSwarm");
  Serial.print("Version ");
  Serial.println(VERSIONNUMBER);
  Serial.println("--------------------------");
  pinMode(D3, OUTPUT);
  pinMode(a, OUTPUT);
  digitalWrite(a, HIGH);  
  pinMode(ldrPin, INPUT);
  randomSeed(analogRead(A0));
  for (int i = 0; i < 6; i++){
    pinMode(ledPins[i], OUTPUT);
  }

  Serial.print("analogRead(A0)=");
  Serial.println(analogRead(A0));
  // everybody starts at 0 and changes from there
  mySwarmID = 0;
  // We start by connecting to a WiFi network
  Serial.print("LightSwarm Instance: ");
  Serial.println(mySwarmID);
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, pass);
  // initialize Swarm Address - we start out as swarmID of 0
  while (WiFi.status() != WL_CONNECTED) 
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.println("Starting UDP");
  udp.begin(localPort);
  Serial.print("Local port: ");
  Serial.println(udp.localPort());

  // initialize light sensor and arrays
  for (int i = 0; i < SWARMSIZE; i++)
  {
    swarmAddresses[i] = 0;
    swarmClear[i] = 0;
    swarmTimeStamp[i] = -1;
  }
  swarmClear[mySwarmID] = 0;
  swarmTimeStamp[mySwarmID] = 1;   // I am always in time to myself
  ldr = swarmClear[mySwarmID];
  swarmVersion[mySwarmID] = VERSIONNUMBER;
  swarmState[mySwarmID] = masterState;
  Serial.print("ldr =");
  Serial.println(ldr);
  // set SwarmID based on IP address 
  localIP = WiFi.localIP();
  swarmAddresses[0] =  localIP[3];
  mySwarmID = 0;
  Serial.print("MySwarmID=");
  Serial.println(mySwarmID);
}

void loop()
{
  ldr  = analogRead(ldrPin);
  Serial.print("LDR value: "); 
  Serial.println(ldr);
  int val = ldr/4.1;
  analogWrite(D3, val);  
  int map_ldr = map(ldr, 0, 1023, 0, 5);
  for(int i = 0; i < 6; i++){
    if (i <= map_ldr) digitalWrite(ledPins[i], HIGH);
    else digitalWrite(ledPins[i], LOW);
  }
  swarmClear[mySwarmID] = ldr;
  int cb = udp.parsePacket();
  if (!cb) {
    //  Serial.println("no packet yet");
    Serial.print(".");
  }
  else {
    // We've received a packet, read the data from it
    udp.read(packetBuffer, PACKET_SIZE); // read the packet into the buffer
    Serial.print("packetbuffer[1] =");
    Serial.println(packetBuffer[1]);
    if (packetBuffer[1] == LIGHT_UPDATE_PACKET)
    {
      Serial.print("LIGHT_UPDATE_PACKET received from LightSwarm #");
      Serial.println(packetBuffer[2]);
      setAndReturnMySwarmIndex(packetBuffer[2]);
      Serial.print("LS Packet Recieved from #");
      Serial.print(packetBuffer[2]);
      Serial.print(" SwarmState:");
      if (packetBuffer[3] == 0)
        Serial.print("SLAVE");
      else
        Serial.print("MASTER");
      Serial.print(" CC:");
      Serial.print(packetBuffer[5] * 256 + packetBuffer[6]);
      Serial.print(" RC:");
      Serial.print(packetBuffer[7] * 256 + packetBuffer[8]);
      Serial.print(" GC:");
      Serial.print(packetBuffer[9] * 256 + packetBuffer[10]);
      Serial.print(" BC:");
      Serial.print(packetBuffer[11] * 256 + packetBuffer[12]);
      Serial.print(" Version=");
      Serial.println(packetBuffer[4]);
      // record the incoming clear color
      swarmClear[setAndReturnMySwarmIndex(packetBuffer[2])] = packetBuffer[5] * 256 + packetBuffer[6];
      swarmVersion[setAndReturnMySwarmIndex(packetBuffer[2])] = packetBuffer[4];
      swarmState[setAndReturnMySwarmIndex(packetBuffer[2])] = packetBuffer[3];
      swarmTimeStamp[setAndReturnMySwarmIndex(packetBuffer[2])] = millis();
      // Check to see if I am master!
      checkAndSetIfMaster();
    }
    if (packetBuffer[1] == RESET_SWARM_PACKET)
    {
      Serial.println(">>>>>>>>>RESET_SWARM_PACKETPacket Recieved");
      masterState = true;
      Serial.println("Reset Swarm:  I just BECAME Master (and everybody else!)");
      digitalWrite(a, LOW);
      //delay(3000);
    }
  }

  if (packetBuffer[1] ==  DEFINE_SERVER_LOGGER_PACKET)
  {
    Serial.println(">>>>>>>>>DEFINE_SERVER_LOGGER_PACKET Packet Recieved");
    serverAddress = IPAddress(packetBuffer[4], packetBuffer[5], packetBuffer[6], packetBuffer[7]);
    Serial.print("Server address received: ");
    Serial.println(serverAddress);
  }

  Serial.print("MasterStatus:");
  if (masterState == true)
  {
    digitalWrite(a, LOW);
    Serial.println("MASTER");
  }
  else
  {
    digitalWrite(a, HIGH);
    Serial.println("SLAVE");
  }
  Serial.print("/KS:");
  Serial.println(serverAddress);
  
  Serial.println("--------");
  for (int i = 0; i < SWARMSIZE; i++)
  {
    Serial.print("swarmAddress[");
    Serial.print(i);
    Serial.print("] = ");
    Serial.println(swarmAddresses[i]); 
  }
  Serial.println("--------");
  broadcastARandomUpdatePacket();
  sendLogToServer();
}

// send an LIGHT Packet request to the swarms at the given address
unsigned long sendLightUpdatePacket(IPAddress & address)
{
  // set all bytes in the buffer to 0
  memset(packetBuffer, 0, PACKET_SIZE);
  // Initialize values needed to form Light Packet
  packetBuffer[0] = 0xF0;   // StartByte
  packetBuffer[1] = LIGHT_UPDATE_PACKET;     // Packet Type
  packetBuffer[2] = localIP[3];     // Sending Swarm Number
  packetBuffer[3] = masterState;  // 0 = slave, 1 = master
  packetBuffer[4] = VERSIONNUMBER;  // Software Version
  packetBuffer[5] = (ldr & 0xFF00) >> 8; // Clear High Byte
  packetBuffer[6] = (ldr & 0x00FF); // Clear Low Byte
  packetBuffer[7] = (redColor & 0xFF00) >> 8; // Red High Byte
  packetBuffer[8] = (redColor & 0x00FF); // Red Low Byte
  packetBuffer[9] = (greenColor & 0xFF00) >> 8; // green High Byte
  packetBuffer[10] = (greenColor & 0x00FF); // green Low Byte
  packetBuffer[11] = (blueColor & 0xFF00) >> 8; // blue High Byte
  packetBuffer[12] = (blueColor & 0x00FF); // blue Low Byte
  packetBuffer[13] = 0x0F;  //End Byte
  // all Light Packet fields have been given values, now
  // you can send a packet requesting coordination
  udp.beginPacketMulticast(address,  localPort, WiFi.localIP()); //
  //udp.beginPacket(address,  localPort); //
  udp.write(packetBuffer, PACKET_SIZE);
  udp.endPacket();
  Serial.println("Packet Broadcasted");
  Serial.print("Master Status: ");
  Serial.println(masterState);
  
  return 0;
}

// delay 0-MAXDELAY seconds
#define MAXDELAY 500
void broadcastARandomUpdatePacket()
{
  int sendToLightSwarm = 255;
  Serial.print("Broadcast To Swarm = ");
  Serial.print(sendToLightSwarm);
  Serial.print(" ");
  // delay 0-MAXDELAY seconds
  //int randomDelay;
  //randomDelay = random(0, MAXDELAY);
  //Serial.print("Delay = ");
  //Serial.print(randomDelay);
  //Serial.print("ms : ");
  //delay(randomDelay);
  IPAddress sendSwarmAddress(192, 168, 0, sendToLightSwarm); // my Swarm Address
  sendLightUpdatePacket(sendSwarmAddress);
}

void checkAndSetIfMaster()
{
  for (int i = 0; i < SWARMSIZE; i++)
  {
#ifdef DEBUG
    Serial.print("swarmClear[");
    Serial.print(i);
    Serial.print("] = ");
    Serial.print(swarmClear[i]);
    Serial.print("  swarmTimeStamp[");
    Serial.print(i);
    Serial.print("] = ");
    Serial.println(swarmTimeStamp[i]);
#endif
    Serial.print("#");
    Serial.print(i);
    Serial.print("/");
    Serial.print(swarmState[i]);
    Serial.print("/");
    Serial.print(swarmVersion[i]);
    Serial.print(":");
    // age data
    int howLongAgo = millis() - swarmTimeStamp[i] ;
    if (swarmTimeStamp[i] == 0)
    {
      Serial.print("TO ");
    }
    else if (swarmTimeStamp[i] == -1)
    {
      Serial.print("NP ");
    }
    else if (swarmTimeStamp[i] == 1)
    {
      Serial.print("ME ");
    }
    else if (howLongAgo > SWARMTOOOLD)
    {
      Serial.print("TO ");
      swarmTimeStamp[i] = 0;
      swarmClear[i] = 0;
    }
    else
    {
      Serial.print("PR ");
    }
  }
  Serial.println();
  boolean setMaster = true;
  for (int i = 0; i < SWARMSIZE; i++)
  {
    if (swarmClear[mySwarmID] >= swarmClear[i])
    {
      // I might be master!
    }
    else
    {
      // nope, not master
      setMaster = false;
      break;
    }
  }
  if (setMaster == true)
  {
    if (masterState == false)
    {
      Serial.println("I just BECAME Master");
      digitalWrite(a, LOW);
    }
    masterState = true;

  }
  else
  {
    if (masterState == true)
    {
      Serial.println("I just LOST Master");
      digitalWrite(a, HIGH);
    }
    masterState = false;
  }
  swarmState[mySwarmID] = masterState;
}

int setAndReturnMySwarmIndex(int incomingID)
{
  for (int i = 0; i< SWARMSIZE; i++)
  {
    if (swarmAddresses[i] == incomingID)
    {
      return i;
    } 
    else
    if (swarmAddresses[i] == 0)  // not in the system, so put it in
    {
    
      swarmAddresses[i] = incomingID;
      Serial.print("incomingID ");
      Serial.print(incomingID);
      Serial.print("  assigned #");
      Serial.println(i);
      return i;
    }
    
  }  

  // if we get here, then we have a new swarm member.   
  // Delete the oldest swarm member and add the new one in 
  // (this will probably be the one that dropped out)
  int oldSwarmID;
  long oldTime;
  oldTime = millis();
  for (int i = 0;  i < SWARMSIZE; i++)
 {
  if (oldTime > swarmTimeStamp[i])
  {
    oldTime = swarmTimeStamp[i];
    oldSwarmID = i;
  }
 } 

 // remove the old one and put this one in....
 swarmAddresses[oldSwarmID] = incomingID;
 // the rest will be filled in by Light Packet Receive
 return oldSwarmID;
}
// send log packet to Server if master and server address defined
void sendLogToServer()
{
  // build the string
  char myBuildString[1000];
  myBuildString[0] = '\0';
  if (masterState == true)
  {
    // now check for server address defined
    if ((serverAddress[0] == 0) && (serverAddress[1] == 0))
    {
      return;  // we are done.  not defined
    }
    else
    {
      // now send the packet as a string with the following format:
      // swarmID, MasterSlave, SoftwareVersion, ldr, Status | ....next Swarm ID
      // 0,1,15,3883, PR | 1,0,14,399, PR | ....
      int i;
      char swarmString[20];
      swarmString[0] = '\0';
      for (i = 0; i < SWARMSIZE; i++)
      {
        char stateString[5];
        stateString[0] = '\0';
        if (swarmTimeStamp[i] == 0)
        {
          strcat(stateString, "TO");
        }
        else if (swarmTimeStamp[i] == -1)
        {
          strcat(stateString, "NP");
        }
        else if (swarmTimeStamp[i] == 1)
        {
          strcat(stateString, "PR");
        }
        else
        {
          strcat(stateString, "PR");
        }
        sprintf(swarmString, " %i,%i,%i,%i,%s,%i ", i, swarmState[i], swarmVersion[i], swarmClear[i], stateString, swarmAddresses[i]);
        strcat(myBuildString, swarmString);
        if (i < SWARMSIZE - 1)
        {
          strcat(myBuildString, "|");
        }
      }
    }
    // set all bytes in the buffer to 0
    memset(packetBuffer, 0, BUFFERSIZE);
    // Initialize values needed to form Light Packet
    // (see URL above for details on the packets)
    packetBuffer[0] = 0xF0;   // StartByte
    packetBuffer[1] = LOG_TO_SERVER_PACKET;     // Packet Type
    packetBuffer[2] = localIP[3];     // Sending Swarm Number
    packetBuffer[3] = strlen(myBuildString); // length of string in bytes
    packetBuffer[4] = VERSIONNUMBER;  // Software Version
    int i;
    for (i = 0; i < strlen(myBuildString); i++)
    {
      packetBuffer[i + 5] = myBuildString[i];// first string byte
    }
    packetBuffer[i + 5] = 0x0F; //End Byte
    Serial.print("Sending Log to Sever:");
    Serial.println(myBuildString);
    int packetLength;
    packetLength = i + 5 + 1;
    udp.beginPacket(serverAddress,  localPort); //
    udp.write(packetBuffer, packetLength);
    udp.endPacket();
  }
}