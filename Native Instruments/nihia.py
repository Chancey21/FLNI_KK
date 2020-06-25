# Copyright (c) 2020 Hobyst

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Library for using the NIHIA protocol on FL Studio's MIDI Scripting API

# This script contains all the functions and methods needed to take advantage of the deep integration
# features on Native Instruments' devices
# Any device with this kind of features will make use of this script

import patterns
import mixer
import device
import transport
import arrangement
import general
import launchMapPages
import playlist

import midi
import utils


# Method to make talking to the device less annoying
# All the messages the device is expecting have a structure of "BF XX XX"
# The STATUS byte always stays the same and only the DATA1 and DATA2 vary

buttons = {
    "PLAY": 16,
    "RESTART": 17,
    "REC": 18,
    "COUNT_IN": 19,
    "STOP": 20,
    "CLEAR": 21,
    "LOOP": 22,
    "METRO": 23,
    "TEMPO": 24,
    
    "UNDO": 32,
    "REDO": 33,
    "QUANTIZE": 34,
    "AUTO": 35,

    "MUTE": 67,
    "SOLO": 68,

    # The 4D encoder events use the same data1, but different data2
    # For example, if you want to retrieve the data1 value for ENCODER_PLUS you would do nihia.buttons.get("ENCODER_PLUS")[0]
    "ENCODER_BUTTON": 96,
    "SHIFT+ENCODER_BUTTON": 97,

    
    "ENCODER_RIGHT": [50, 1],
    "ENCODER_LEFT": [50, 127],
    
    "ENCODER_UP": [48, 127],
    "ENCODER_DOWN": [48, 1],

    "ENCODER_PLUS": [52, 1],
    "ENCODER_MINUS": [52, 127],

    "ENCODER_HORIZONTAL": 50,
    "ENCODER_VERTICAL": 48,   

    "ENCODER_SPIN": 52

}


def dataOut(data1, data2):
    """ Funtion that makes commmuication with the keyboard easier. By just entering the DATA1 and DATA2 of the MIDI message, 
    it composes the full message in forther to satisfy the syntax required by the midiOut functions, as well as the setting 
    the STATUS of the message to BF as expected.""" 
    
    # Composes the MIDI message and sends it
    convertmsg = [240, 191, data1, data2] # takes message and add the header required for communication with device
    msgtom32 = bytearray(convertmsg) #converts message array into bytes, 1 turns into 0x01 but in b/01/ format
    device.midiOutSysex(bytes(msgtom32)) #converts to 0x01 format

def KPrntScrn(trkn, word, delaytime):

      """ Function for easing the communication with the device OLED easier. The device has 8 slots 
      that correspond to the 8 knobs. Knobs 0 through 7 on the device. Slot 0 (aka Knob 0 aka the
      first knob from the left) is also use to display temporary messages. """

      lettersh = [] #an arrary to store message (broken out by letter in each slot of the array) to screen once it's converted from a string
      header = [240, 0, 33, 9, 0, 0, 68, 67, 1, 0, 72, 0] #required header in message to tell device where to place track title

      n = 0
      m = 0

      letters = list(word) #convert word into letters in array

      if len(letters) <= 10: #if the message's letter count is less than 10 it sends as is
         while n < len(letters): #convert letters in array to integer representing the Unicode character
            lettersh.append(ord(letters[n]))
            n += 1
      else: #if the message's letter count is more than 10 it cuts off letters.
         while n < 11: #convert letters in array to integer representing the Unicode character
            lettersh.append(ord(letters[n]))
            n += 1
         
      header.append(trkn) #adding track number to header at the end 

      while m < len(lettersh): #combining header array and unicode value array together; just makes it easier to send to device
         header.append(lettersh[m])
         m += 1 

      header.append(247) #tells m32, that's it that's the whole word
      
      device.midiOutSysex(bytes(header)) #send unicode values as bytes to OLED screen
    

# Method to enable the deep integration features on the device
def initiate():
    """ Acknowledges the device that a compatible host has been launched, wakes it up from MIDI mode and activates the deep
    integration features of the device. TODO: Then waits for the answer of the device in order to confirm if the handshake 
    was successful and returns True if affirmative."""

    # Sends the MIDI message that initiates the handshake: BF 01 01
    dataOut(1, 1)

    # TODO: Waits and reads the handshake confirmation message
   

# Method to deactivate the deep integration mode. Intended to be executed on close.
def terminate():
    """ Sends the goodbye message to the device and exits it from deep integration mode. 
    Intended to be executed before FL Studio closes."""

    # Sends the goodbye message: BF 02 01
    dataOut(2, 1)


# Method for restarting the protocol on demand. Intended to be used by the end user in case the keyboard behaves 
# unexpectedly.
def restartProtocol():
    """ Sends the goodbye message to then send the handshake message again. """

    # Turns off the deep integration mode
    terminate()

    # Then activates it again
    initiate()

    
# Method for controlling the lighting on the buttons (for those who have idle/highlighted two state lights)
# Examples of this kind of buttons are the PLAY or REC buttons, where the PLAY button alternates between low and high light and so on.
# SHIFT buttons are also included in this range of buttons, but instead of low/high light they alternate between on/off light states.
def buttonSetLight(buttonName: str, lightMode: int):
    """ Method for controlling the lights on the buttons of the device. 
    
    buttonName -- Name of the button as shown in the device in caps and enclosed in quotes. ("PLAY", "AUTO", "REDO"...)
    EXCEPTION: declare the Count-In button as COUNT_IN
    
    lightMode -- If set to 0, sets the first light mode of the button. If set to 1, sets the second light mode."""

    #Light mode integer to light mode hex dictionary
    lightModes = {
        0: 0,
        1: 1
    }

    # Then sends the MIDI message using dataOut
    dataOut(buttons.get(buttonName), lightModes.get(lightMode))


# Dictionary that goes between the different kinds of information that can be sent to the device to specify information about the mixer tracks
# and their corresponding identificative bytes
mixerinfo_types = {
    "VOLUME": 70,
    "PAN": 71,
    "IS_MUTE": 67,
    "IS_SOLO": 68,
    "NAME": 72,
    
    # This one makes more sense on DAWs that create more tracks as the user requests it, as there might be projects (for example) on Ableton Live
    # with only two tracks
    # However, since FL Studio has all playlist and mixer tracks created, it has no use at all (maybe on the channel rack) and all tracks should have
    # their existance reported as 1 (which means the track exists) in order to light on the Mute and Solo buttons on the device
    "EXIST": 64,
    "SELECTED": 66,
}


# Method for reporting information about the mixer tracks, which is done through Sysex
# Couldn't make this one as two different functions under the same name since Python doesn't admit function overloading
def mixerSendInfo(info_type: str, trackID: int, **kwargs):
    """ Sends info about the mixer tracks to the device.
    
    info_type -- The kind of information you're going to send. ("VOLUME", "PAN"...) Defined on nihia.mixerinfo_types
    
    trackID -- From 0 to 7. Tells the device which track from the ones that are showing up in the screen you're going to tell info about.
    Third agument depends on what kind of information you are going to send:
    value (integer) -- Can be 0 (no) or 1 (yes). Used for two-state properties like to tell if the track is solo-ed or not.
    
    or
    info (string) -- Used for track name, track pan and track volume.
    """

    # Gets the inputed values for the optional arguments from **kwargs
    value = kwargs.get("value", 0)
    info = kwargs.get("info", None)

    # Defines the behaviour for when additional info is reported (for track name, track pan and track volume)
    if info != None:

        # Tells Python that the additional_info argument is in UTF-8
        info = info.encode("UTF-8")
        
        # Conforms the kind of message midiOutSysex is waiting for
        msg = [240, 0, 33, 9, 0, 0, 68, 67, 1, 0, mixerinfo_types.get(info_type), value, trackID] + list(bytes(info)) + [247]

        # Warps the data and sends it to the device
        device.midiOutSysex(bytes(msg))

    # Defines how the method should work normally
    else:
        
        # Takes the information and wraps it on how it should be sent and sends the message
        device.midiOutSysex(bytes([240, 0, 33, 9, 0, 0, 68, 67, 1, 0, mixerinfo_types.get(info_type), value, trackID, 247]))

