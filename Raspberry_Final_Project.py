'''
    LightSwarm Raspberry Pi Logger 
    SwitchDoc Labs 
    December 2020
'''
from __future__ import print_function
from builtins import chr
from builtins import str
from builtins import range
import sys  
import time
from threading import Thread
import random
import RPi.GPIO as GPIO
import datetime
import pytz
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
from netifaces import interfaces, ifaddresses, AF_INET
from socket import *

VERSIONNUMBER = 7
# packet type definitions
LIGHT_UPDATE_PACKET = 0
RESET_SWARM_PACKET = 1
CHANGE_TEST_PACKET = 2   # Not Implemented
RESET_ME_PACKET = 3
DEFINE_SERVER_LOGGER_PACKET = 4
LOG_TO_SERVER_PACKET = 5
MASTER_CHANGE_PACKET = 6
BLINK_BRIGHT_LED = 7

MYPORT = 5006

SWARMSIZE = 6

BUTTONPIN = 17#11
WHITELEDPIN = 27#13
#YELLOWLEDPIN = 12
#GREENLEDPIN = 15
REDLEDPIN = 16

#Edit(Rushabh) Start
#define PINs according to cabling
columnDataPin = 20
rowDataPin = 21
latchPIN = 14
clockPIN = 15

sV_arr = []
sV_arr = [0 for i in range(32)]


#set pins to putput
GPIO.setmode(GPIO.BCM)
GPIO.setup((columnDataPin,rowDataPin,latchPIN,clockPIN),GPIO.OUT)

#map your output into 1 (LED off) and 0 (led on) sequences
gen_mtx=[["11111111"],\
       ["11000011"],\
       ["10111101"],\
       ["01011010"],\
       ["01111110"],\
       ["01100110"],\
       ["10111101"],\
       ["11000011"]]
#Edit(Rushabh) End


#GPIO.setmode(GPIO.BOARD)
#GPIO.setup(GREENLEDPIN, GPIO.OUT)
GPIO.setup(WHITELEDPIN, GPIO.OUT)
#GPIO.setup(YELLOWLEDPIN, GPIO.OUT)
#GPIO.setup(REDLEDPIN, GPIO.OUT)
GPIO.setup(BUTTONPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.output(WHITELEDPIN, False)
#GPIO.output(GREENLEDPIN, False)
#GPIO.output(YELLOWLEDPIN, False)
#GPIO.output(REDLEDPIN, False)

pairs = {}

logString = ""
# command from command Code

def get_key_press(pressed):
    while(1):
        buttonPress = GPIO.input(BUTTONPIN)
        if buttonPress==False:
            time.sleep(0.2)
            pressed[0] = True
            break

#Edit(Rushabh) start
def start_matrix(gen_mtx):
    while(1):
        #edit(rushabh)
        #print(gen_mtx)
        
        #edit (rushabh)
        RowSelect=[1,0,0,0,0,0,0,0]

        for i in range(0,8): # last value in rage is not included by default
          # send row data and row selection to registers
          shift_update_matrix(''.join(map(str, gen_mtx[i])),columnDataPin,\
                              ''.join(map(str, RowSelect)),rowDataPin,clockPIN,latchPIN)
          #shift row selector
          RowSelect = RowSelect[-1:] + RowSelect[:-1]
        #edit(rushabh)

        
    #edit(rushabh)
        
        
#define shift register update function
def shift_update_matrix(input_Col,Column_PIN,input_Row,Row_PIN,clock,latch):
  #put latch down to start data sending
  GPIO.output(clock,0)
  GPIO.output(latch,0)
  GPIO.output(clock,1)

  #load data in reverse order
  for i in range(7, -1, -1):
    GPIO.output(clock,0)
    #instead of controlling only 1 shift register, we drive both together
    GPIO.output(Column_PIN, int(input_Col[i]))
    GPIO.output(Row_PIN, int(input_Row[i]))
    GPIO.output(clock,1)

  #put latch up to store data on register
  GPIO.output(clock,0)
  GPIO.output(latch,1)
  GPIO.output(clock,1)

def generate_matrix(avg):
    
    if avg <= 128:
        row = ["11111110"]
    if avg > 128 and avg < 256:
        row = ["11111100"]
    if avg >= 256 and avg < 384:
        row = ["11111000"]
    if avg >= 384 and avg < 512:
        row = ["11110000"]
    if avg >= 512 and avg < 640:
        row = ["11100000"]
    if avg >= 640 and avg < 768:
        row = ["11000000"]
    if avg >= 768 and avg < 888:
        row = ["10000000"]
    if avg >= 888:
        row = ["00000000"]
    
    return row
#Edit(Rushabh) end

def completeCommand():
        f = open("/home/pi/SDL_Pi_LightSwarm/state/LSCommand.txt", "w+")
        f.write("DONE")
        f.close()

def completeCommandWithValue(value):
        f = open("/home/pi/SDL_Pi_LightSwarm/state/LSResponse.txt", "w+")
        f.write(value)
        print("in completeCommandWithValue=", value)
        f.close()
        completeCommand()

def processCommand(s):
        f = open("//home/pi/SDL_Pi_LightSwarm/state/LSCommand.txt", "r+")
        command = f.read()
        f.close()
        command = command.rstrip()        
        if (command == "") or (command == "DONE"):
            # Nothing to do
            return False
        # Check for our commands
        #pclogging.log(pclogging.INFO, __name__, "Command %s Recieved" % command)
        print("Processing Command: ", command)
        if (command == "STATUS"):
            completeCommandWithValue(logString)
            return True
        if (command == "RESETSWARM"):
            SendRESET_SWARM_PACKET(s)
            completeCommand()
            return True
        # check for , commands
        print("command=%s" % command)
        myCommandList = command.split(',')
        print("myCommandList=", myCommandList)
        if (len(myCommandList) > 1):   
            # we have a list command
            if (myCommandList[0]== "BLINKLIGHT"):
                SendBLINK_BRIGHT_LED(s, int(myCommandList[1]), 1)
            if (myCommandList[0]== "RESETSELECTED"):
                SendRESET_ME_PACKET(s, int(myCommandList[1]))
            if (myCommandList[0]== "SENDSERVER"):
                SendDEFINE_SERVER_LOGGER_PACKET(s)
            completeCommand()
            return True
        completeCommand()
        return False

# UDP Commands and packets
def SendDEFINE_SERVER_LOGGER_PACKET(s):
    #print("DEFINE_SERVER_LOGGER_PACKET Sent") 
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    # get IP address
    for ifaceName in interfaces():
            addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
            print('%s: %s' % (ifaceName, ', '.join(addresses)))
    # last interface (wlan0) grabbed 
    myIP = addresses[0].split('.')
    data= ["" for i in range(14)]
    data[0] = int("F0", 16).to_bytes(1,'little') 
    data[1] = int(DEFINE_SERVER_LOGGER_PACKET).to_bytes(1,'little')
    data[2] = int("FF", 16).to_bytes(1,'little') # swarm id (FF means not part of swarm)
    data[3] = int(VERSIONNUMBER).to_bytes(1,'little')
    data[4] = int(myIP[0]).to_bytes(1,'little') # 1 octet of ip
    data[5] = int(myIP[1]).to_bytes(1,'little') # 2 octet of ip
    data[6] = int(myIP[2]).to_bytes(1,'little') # 3 octet of ip
    data[7] = int(myIP[3]).to_bytes(1,'little') # 4 octet of ip
    data[8] = int(0x00).to_bytes(1,'little')
    data[9] = int(0x00).to_bytes(1,'little')
    data[10] = int(0x00).to_bytes(1,'little')
    data[11] = int(0x00).to_bytes(1,'little')
    data[12] = int(0x00).to_bytes(1,'little')
    data[13] = int(0x0F).to_bytes(1,'little')
    mymessage = ''.encode()  	
    s.sendto(mymessage.join(data), ('<broadcast>'.encode(), MYPORT))

def SendRESET_SWARM_PACKET(s):
    print("RESET_SWARM_PACKET Sent") 
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    data= ["" for i in range(14)]
    data[0] = int("F0", 16).to_bytes(1,'little')
    data[1] = int(RESET_SWARM_PACKET).to_bytes(1,'little')
    data[2] = int("FF", 16).to_bytes(1,'little') # swarm id (FF means not part of swarm)
    data[3] = int(VERSIONNUMBER).to_bytes(1,'little')
    data[4] = int(0x00).to_bytes(1,'little')
    data[5] = int(0x00).to_bytes(1,'little')
    data[6] = int(0x00).to_bytes(1,'little')
    data[7] = int(0x00).to_bytes(1,'little')
    data[8] = int(0x00).to_bytes(1,'little')
    data[9] = int(0x00).to_bytes(1,'little')
    data[10] = int(0x00).to_bytes(1,'little')
    data[11] = int(0x00).to_bytes(1,'little')
    data[12] = int(0x00).to_bytes(1,'little')
    data[13] = int(0x0F).to_bytes(1,'little')
    mymessage = ''.encode()
    s.sendto(mymessage.join(data), ('<broadcast>'.encode(), MYPORT))

def SendRESET_ME_PACKET(s, swarmID):
    print("RESET_ME_PACKET Sent") 
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    data= ["" for i in range(14)]
    data[0] = int("F0", 16).to_bytes(1,'little')
    data[1] = int(RESET_ME_PACKET).to_bytes(1,'little')
    data[2] = int(swarmStatus[swarmID][5]).to_bytes(1,'little')
    data[3] = int(VERSIONNUMBER).to_bytes(1,'little')
    data[4] = int(0x00).to_bytes(1,'little')
    data[5] = int(0x00).to_bytes(1,'little')
    data[6] = int(0x00).to_bytes(1,'little')
    data[7] = int(0x00).to_bytes(1,'little')
    data[8] = int(0x00).to_bytes(1,'little')
    data[9] = int(0x00).to_bytes(1,'little')
    data[10] = int(0x00).to_bytes(1,'little')
    data[11] = int(0x00).to_bytes(1,'little')
    data[12] = int(0x00).to_bytes(1,'little')
    data[13] = int(0x0F).to_bytes(1,'little')
    mymessage = ''.encode()
    s.sendto(mymessage.join(data), ('<broadcast>'.encode(), MYPORT))

def SendCHANGE_TEST_PACKET(s, swarmID):
    print("RESET_ME_PACKET Sent") 
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    data= ["" for i in range(14)]
    data[0] = int("F0", 16).to_bytes(1,'little')
    data[1] = int(RESET_ME_PACKET).to_bytes(1,'little')
    data[2] = int(swarmStatus[swarmID][5]).to_bytes(1,'little')
    data[3] = int(VERSIONNUMBER).to_bytes(1,'little')
    data[4] = int(0x00).to_bytes(1,'little')
    data[5] = int(0x00).to_bytes(1,'little')
    data[6] = int(0x00).to_bytes(1,'little')
    data[7] = int(0x00).to_bytes(1,'little')
    data[8] = int(0x00).to_bytes(1,'little')
    data[9] = int(0x00).to_bytes(1,'little')
    data[10] = int(0x00).to_bytes(1,'little')
    data[11] = int(0x00).to_bytes(1,'little')
    data[12] = int(0x00).to_bytes(1,'little')
    data[13] = int(0x0F).to_bytes(1,'little')
    mymessage = ''.encode()
    s.sendto(mymessage.join(data), ('<broadcast>'.encode(), MYPORT))

def SendBLINK_BRIGHT_LED(s, swarmID, seconds):
    print("BLINK_BRIGHT_LED Sent") 
    print("swarmStatus=", swarmStatus);
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    data= ["" for i in range(0,14)]
    data[0] = int("F0", 16).to_bytes(1,'little')
    data[1] = int(BLINK_BRIGHT_LED).to_bytes(1,'little')
    print("swarmStatus[swarmID][5]", swarmStatus[swarmID][5]) 
    data[2] = int(swarmStatus[swarmID][5]).to_bytes(1,'little')
    data[3] = int(VERSIONNUMBER).to_bytes(1,'little')
    if (seconds > 12.6):
        seconds = 12.6
    data[4] = int(seconds*10).to_bytes(1,'little')
    data[5] = int(0x00).to_bytes(1,'little')
    data[6] = int(0x00).to_bytes(1,'little')
    data[7] = int(0x00).to_bytes(1,'little')
    data[8] = int(0x00).to_bytes(1,'little')
    data[9] = int(0x00).to_bytes(1,'little')
    data[10] = int(0x00).to_bytes(1,'little')
    data[11] = int(0x00).to_bytes(1,'little')
    data[12] = int(0x00).to_bytes(1,'little')
    data[13] = int(0x0F).to_bytes(1,'little')
    mymessage = ''.encode()
    s.sendto(mymessage.join(data), ('<broadcast>'.encode(), MYPORT))
    

master_ip_list=[]
ldr_list = []
def parseLogPacket(message, DataLogList):
    global master_ip_list
    global ldr_list
    incomingSwarmID = setAndReturnSwarmID((message[2]))
    logString = ""
    for i in range(0,(message[3])):
        logString = logString + chr((message[i+5]))

    masterData = logString.split("|")[0]
                
    LDRValue=int(masterData.split(",")[3])
    masterIP=int(masterData.split(",")[5])
    
    logObj = DataLogClass(time.time(), masterIP, LDRValue, logString)
    DataLogList.append(logObj)
    print("LDR Data:" + str(LDRValue));
    print("Master IP:" + str(masterIP));
    master_ip_list.append(masterIP)
    ldr_list.append(LDRValue)  
    
    sV_arr = ldr_list[-32:]
    sV_len = len(sV_arr)
    if len(sV_arr) != 0:
        for i in range(0, 32-sV_len):
            sV_arr.append(0)
    
    avg1 = sum(sV_arr[0:4])/4
    row1 = generate_matrix(avg1)
    gen_mtx[0] = row1
    avg2 = sum(sV_arr[4:8])/4
    row2 = generate_matrix(avg2)
    gen_mtx[1] = row2
    avg3 = sum(sV_arr[8:12])/4
    row3 = generate_matrix(avg3)
    gen_mtx[2] = row3
    avg4 = sum(sV_arr[12:16])/4
    row4 = generate_matrix(avg4)
    gen_mtx[3] = row4
    avg5 = sum(sV_arr[16:20])/4
    row5 = generate_matrix(avg5)
    gen_mtx[4] = row5
    avg6 = sum(sV_arr[20:24])/4
    row6 = generate_matrix(avg6)
    gen_mtx[5] = row6
    avg7 = sum(sV_arr[24:28])/4
    row7 = generate_matrix(avg7)
    gen_mtx[6] = row7
    avg8 = sum(sV_arr[28:32])/4
    row8 = generate_matrix(avg8)
    gen_mtx[7] = row8
    
    return logString

# build Webmap
def buildWebMapToFile(logString, swarmSize ):
    webresponse = ""
    swarmList = logString.split("|")
    for i in range(0,swarmSize):
        swarmElement = swarmList[i].split(",")
        print("swarmElement=", swarmElement)
        webresponse += "<figure>"
        webresponse += "<figcaption"
        webresponse += " style='position: absolute; top: "
        webresponse +=  str(100-20)
        webresponse +=  "px; left: " +str(20+120*i)+  "px;'/>\n"
        if (int(swarmElement[5]) == 0):
            webresponse += "&nbsp;&nbsp;&nbsp&nbsp;&nbsp;---"
        else:
            webresponse += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s" % swarmElement[5]
        webresponse += "</figcaption>"
        #webresponse += "<img src='" + "http://192.168.1.40:9750"
        webresponse += "<img src='" 
        if (swarmElement[4] == "PR"):
            if (swarmElement[1] == "1"):
                webresponse += "On-Master.png' style='position: absolute; top: "
            else:
                webresponse += "On-Slave.png' style='position: absolute; top: "
        else:
            if (swarmElement[4] == "TO"):
                webresponse += "Off-TimeOut.png' style='position: absolute; top: "
            else:
                webresponse += "Off-NotPresent.png' style='position: absolute; top: "
        webresponse +=  str(100)
        webresponse +=  "px; left: " +str(20+120*i)+  "px;'/>\n"
        webresponse += "<figcaption"
        webresponse += " style='position: absolute; top: "
        webresponse +=  str(100+100)
        webresponse +=  "px; left: " +str(20+120*i)+  "px;'/>\n"
        if (swarmElement[4] == "PR"):
            if (swarmElement[1] == "1"):
                webresponse += "&nbsp;&nbsp;&nbsp;&nbsp;Master"
            else:
                webresponse += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Slave"
        else:
            if (swarmElement[4] == "TO"):
                webresponse += "TimeOut" 
            else:
                webresponse += "Not Present"
        webresponse += "</figcaption>"
        webresponse += "</figure>"
    f = open("/home/pi/SDL_Pi_LightSwarm/state/figure.html", "w")
    f.write(webresponse)
    f.close()
    f = open("/home/pi/SDL_Pi_LightSwarm/state/swarm.html", "w")
    fh = open("/home/pi/SDL_Pi_LightSwarm/state/swarmheader.txt", "r")
    ff = open("/home/pi/SDL_Pi_LightSwarm/state/swarmfooter.txt", "r")
    webheader = fh.read()
    webfooter = ff.read()
    f.write(webheader)
    f.write(webresponse)
    f.write(webfooter)
    f.close
    fh.close
    ff.close

def setAndReturnSwarmID(incomingID):
    for i in range(0,SWARMSIZE):
        if (swarmStatus[i][5] == incomingID):
            return i
        else:
            if (swarmStatus[i][5] == 0):  # not in the system, so put it in
                swarmStatus[i][5] = incomingID;
                #print("incomingID %d " % incomingID)
                #print("assigned #%d" % i)
                return i
    # if we get here, then we have a new swarm member.   
    # Delete the oldest swarm member and add the new one in 
    # (this will probably be the one that dropped out)
    oldTime = time.time();
    oldSwarmID = 0
    for i in range(0,SWARMSIZE):
        if (oldTime > swarmStatus[i][1]):
            ldTime = swarmStatus[i][1]
            oldSwarmID = i
    # remove the old one and put this one in....
    swarmStatus[oldSwarmID][5] = incomingID;
    # the rest will be filled in by Light Packet Receive
    print("oldSwarmID %i" % oldSwarmID)
    return oldSwarmID 

# set up sockets for UDP
s=socket(AF_INET, SOCK_DGRAM)
host = 'localhost';
s.bind(('',MYPORT))

print("--------------")
print("LightSwarm Logger")
print("Version ", VERSIONNUMBER)
print("--------------")

# first send out DEFINE_SERVER_LOGGER_PACKET to tell swarm where to send logging information 
SendDEFINE_SERVER_LOGGER_PACKET(s)
time.sleep(3)
SendDEFINE_SERVER_LOGGER_PACKET(s)

last_time = time.time()
# swarmStatus
swarmStatus = [[0 for x  in range(6)] for x in range(SWARMSIZE)]

# 6 items per swarm item
# 0 - NP  Not present, P = present, TO = time out
# 1 - timestamp of last LIGHT_UPDATE_PACKET received
# 2 - Master or slave status   M S
# 3 - Current Test Item - 0 - CC 1 - Lux 2 - Red 3 - Green  4 - Blue
# 4 - Current Test Direction  0 >=   1 <=
# 5 - IP Address of Swarm

for i in range(0,SWARMSIZE):
	swarmStatus[i][0] = "NP"
	swarmStatus[i][5] = 0

#300 seconds round
seconds_300_round = time.time() + 300.0

#120 seconds round
seconds_120_round = time.time() + 120.0

completeCommand() 

class DataLogClass:
    def __init__(self, reported_time, master_ip, master_ldr, ldr_value):
        self.reported_time = reported_time
        self.master_ip = master_ip
        self.master_ldr = master_ldr
        self.ldr_value = ldr_value

date_time = datetime.datetime.now(pytz.timezone("America/Los_Angeles"))
file_name = "LogData/log_file_" + str(date_time) + ".txt"
f = open(file_name, "w+")

while(1):
    pressed = [False]
    t1 = Thread(target=get_key_press, args=(pressed, ))
    t1.start()
    t7 = Thread(target=start_matrix, args=(gen_mtx, ))
    t7.start()

    DataLogList = []

    while(1):
        if pressed[0] == True:
            break
        
      
        d = s.recvfrom(1024)
        
        message = d[0]
        addr = d[1]

        
        if (len(message) == 14):
            if (message[1] == LIGHT_UPDATE_PACKET):
                incomingSwarmID = setAndReturnSwarmID((message[2]))
                swarmStatus[incomingSwarmID][0] = "P"
                swarmStatus[incomingSwarmID][1] = time.time()  
                #print("in LIGHT_UPDATE_PACKET")
                    
            if ((message[1]) == RESET_SWARM_PACKET):
                print("Swarm RESET_SWARM_PACKET Received")
                print("received from addr:",addr)	

            if ((message[1]) == CHANGE_TEST_PACKET):
                print("Swarm CHANGE_TEST_PACKET Received")
                print("received from addr:",addr)	

            if ((message[1]) == RESET_ME_PACKET):
                print("Swarm RESET_ME_PACKET Received")
                print("received from addr:",addr)	

            if ((message[1]) == DEFINE_SERVER_LOGGER_PACKET):
                print("Swarm DEFINE_SERVER_LOGGER_PACKET Received")
                print("received from addr:",addr)	

            if ((message[1]) == MASTER_CHANGE_PACKET):
                print("Swarm MASTER_CHANGE_PACKET Received")
                print("received from addr:",addr)	

            #for i in range(0,14):  
            #    print("ls["+str(i)+"]="+format((message[i]), "#04x"))

        else:
            if ((message[1]) == LOG_TO_SERVER_PACKET):
                #print("Swarm LOG_TO_SERVER_PACKET Received")
                logString = parseLogPacket(message, DataLogList)
                #t7 = Thread(target=start_matrix, args=(gen_mtx, ))
                #t7.start()
                #count=0                
            else:
                print("error message length = ",len(message))
        
        if (time.time() >  seconds_120_round):
            # do our 2 minute round
            print(">>>>doing 120 second task")
            sendTo = random.randint(0,SWARMSIZE-1)
            SendBLINK_BRIGHT_LED(s, sendTo, 1)
            seconds_120_round = time.time() + 120.0	

        if (time.time() >  seconds_300_round):
            # do our 2 minute round
            print(">>>>doing 300 second task")
            SendDEFINE_SERVER_LOGGER_PACKET(s)
            seconds_300_round = time.time() + 300.0	

            processCommand(s)

        #print swarmStatus
    SendRESET_SWARM_PACKET(s)
    
    log_string="IP Address's of Masters: "
    unique_master = list(set(master_ip_list))
    dict_time = {}
    for ele in unique_master:
        pairs[ele] = 0
    for ip in pairs.keys():
        log_string +="192.168.196."
        log_string +=str(ip)
        log_string += ", "
        dict_time[ip]=0
    
    #graph_on = True  
    curr_master = DataLogList[0].master_ip
    since_master = DataLogList[0].reported_time
    for ele in DataLogList:
        if ele.master_ip != curr_master:
            dict_time[curr_master] += (ele.reported_time - since_master)
            curr_master = ele.master_ip
            since_master = ele.reported_time
    
    dict_time[curr_master] += (DataLogList[-1].reported_time - since_master)
    log_string += "\n\n"
    for ip in pairs.keys():
        log_string +="\n192.168.196."
        log_string +=str(ip)
        log_string += " was master for "
        log_string += str(dict_time[ip])
        log_string += " seconds"
    
    log_string += "\n\n\nTime Stamp\t\t\t\tMaster IP\t\tMaster LDR\t\tRaw Data"
    
    for ele in DataLogList:
        local_string = "\n"
        local_string += str(ele.reported_time)
        local_string += "\t\t"
        local_string += str(ele.master_ip)
        local_string += "\t\t\t\t"
        local_string += str(ele.master_ldr)
        local_string += "\t\t\t\t"
        local_string += str(ele.ldr_value)
        log_string += local_string    
    
    f.write(log_string)
    f.close()
    
    master_ip_list=[]
    ldr_list = []
    
    date_time = datetime.datetime.now(pytz.timezone("America/Los_Angeles"))
    file_name = "LogData/log_file_" + str(date_time) + ".txt"
    f = open(file_name, "w")
    
    GPIO.output(WHITELEDPIN, True)
    time.sleep(3)
    GPIO.output(WHITELEDPIN, False)
