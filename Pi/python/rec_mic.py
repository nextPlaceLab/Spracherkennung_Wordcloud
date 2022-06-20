import pyaudio
import wave
#from matrix_lite import led
import RPi.GPIO as GPIO

import webrtcvad

from collections import deque

import sys
import io
import threading

#from threading import Thread
import concurrent.futures
import os

from ftplib import FTP_TLS

import time

def led_set(pin, state):
    if state:
        GPIO.output(pin,GPIO.HIGH)
    else:
        GPIO.output(pin,GPIO.LOW)

class Recorder(object):
    '''A recorder class for recording audio to a WAV file.
    Records in mono by default.
    '''

    def __init__(self, channels=2, rate=44100, frames_per_buffer=2048, vad=1):
        self._ftpsender = FtpSender(self)
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self.vad = webrtcvad.Vad(vad)
        self._framet = int(4*self.rate/100)
        self.audio2send = []
        self.rel = int(self.rate/self.frames_per_buffer)
        self.prev_audio = deque(maxlen=int(0.5 * self.rel))
        self.started = False
        self.silenceCtr = 0
        led_set(14, True)

##    def __enter__(self):
##        return self

##    def __del__(self):
##        self._pa.close()

    def record(self, duration):
        # Use a stream with no callback function in blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer)
        for _ in range(int(self.rate / self.frames_per_buffer * duration)):
            audio = self._stream.read(self.frames_per_buffer)
            self.wavefile.writeframes(audio)
        return None

    def start_recording(self):

        # Use a stream with a callback in non-blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer,
#                                        stream_callback=self.callback)
                                        stream_callback=self.get_callback())
        self._stream.start_stream()

        led_set(18, True)
        led_set(14, False)
        led_set(15, False)

        return self

    def stop_recording(self):
        led_set(15, True)
        led_set(18, False)
        self._stream.stop_stream()
        self._stream.close()
        self._pa.terminate()
        return self

    def get_callback(self):
        def callback(in_data, frame_count, time_info, status):
            cur_data = in_data
            
            detected  = 0
            try:
                detected = sum([self.vad.is_speech(cur_data[i:i+self._framet], self.rate) for i in range(0,self.frames_per_buffer,self._framet)])
            except:
                pass

            print('Speech detected: ',detected)

            if detected < 4:
                self.silenceCtr += 1
            else:
                self.silenceCtr = 0
            
            if(detected > 3 or (self.silenceCtr < 5 and self.started)):
                if(not self.started):
                    print("Starting record of phrase")
                    self.started = True
                self.audio2send.append(cur_data)

            elif (self.started is True and self.silenceCtr > 5):
                print("Finished")

                self._ftpsender.sendFile(list(self.prev_audio) + self.audio2send, 2)
                
                self.started = False
                self.audio2send = []
                self.silenceCtr = 0
                print("Listening ...")
            else:
                self.prev_audio.append(cur_data)
            
            return in_data, pyaudio.paContinue
        return callback

    def callback(self, in_data, frame_count, time_info, status):
        self.wavefile.writeframes(in_data)
        return (in_data, pyaudio.paContinue)


    def close(self):
        print("stream closed")
        self._stream.close()
        self._pa.terminate()

    def stream_isactive(self):
        return self._stream.is_active()

class FtpSender(object):
    def __init__(self, recorder):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.recorder = recorder

    def sendFile(self, data, bytesPerFrame):
        self.executor.submit(self._sendFile, data, bytesPerFrame)
        #self._sendFile(data, bytesPerFrame)

    def _sendFile(self, data, bytesPerFrame):
        filename = 'output_' + time.asctime(time.localtime()).replace(' ','_').replace(':','') + '.wav'

        # create wav file io.BytesIO for sending
        data = b''.join(data)
        print(len(data))

        temp_file = io.BytesIO()
        with wave.open(temp_file, 'wb') as temp_input:
            temp_input.setnchannels(self.recorder.channels)
            temp_input.setsampwidth(bytesPerFrame)
            temp_input.setframerate(self.recorder.rate)
            temp_input.writeframes(data)

        temp_file.seek(0)

        ftpWavDir = "/home/speech/data/wav/"

        ftp = FTP_TLS('your_kaldi_server_host')

        ftp.login(user="your_user",passwd="your_password")
        ftp.cwd(ftpWavDir)

        ftp.storbinary("STOR " + os.path.basename(filename+'.incomplete'), temp_file)
        ftp.rename(ftpWavDir + os.path.basename(filename+'.incomplete'), ftpWavDir + os.path.basename(filename))

        ftp.quit()


### main

print('Speech recording system starting...') 

PIN_SWITCH = 23 # IR receiver on Matrix Creator connected to pin 16 on Pi

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.setup(14,GPIO.OUT) # blue
GPIO.setup(15,GPIO.OUT) # green
GPIO.setup(18,GPIO.OUT) # red

led_set(18, False)
led_set(15, False)
led_set(14, False)

rec_init = False

led_set(14, True)

rec = None #Recorder(channels=1)

while True:
    input_state = GPIO.input(PIN_SWITCH)
    # what on/off for input_state?
    if not input_state:
        if not rec_init:
            print("rec")
            rec_init = True
            rec = Recorder(channels=1, rate=48000,frames_per_buffer=8192, vad=3)
            rec.start_recording()
            led_set(15, True)
            led_set(14, False)
        else:
            print("stop")
            rec.stop_recording()
            led_set(18, True)
            led_set(15, False)
            rec_init = False
    else:
        if rec_init:
            rec.stop_recording()
            led_set(18, False)
            led_set(15, True)


    time.sleep(0.5)

                
##    if 'recfile' in locals():
##        print(recfile.stream_isactive())
##    if (rec_init and not 'recfile' in locals()) or (rec_init and not recfile.stream_isactive()):
##        led_set(18, True)
##        led_set(15, True)
##        led_set(14, True)

