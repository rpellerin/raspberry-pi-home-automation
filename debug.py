import time
import os
import cv2 # python3-opencv
from picamera2 import MappedArray, Picamera2
from picamera2.encoders import H264Encoder

#set variables
now = time.strftime("%y_%m_%d_%H_%M")
h264_output = "/dev/shm/test"+now+".h264"
mp4_output = "test"+now+".mp4"

#set timestamp
colour = (255, 255, 255)
origin = (0, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)

#set video configuration
picam2 = Picamera2()
picam2.pre_callback = apply_timestamp
picam2.video_configuration.controls.FrameRate = 25.0
picam2.video_configuration.buffer_count = 10
picam2.video_configuration.size = (800, 600)
encoder = H264Encoder(bitrate=17000000, repeat=True, iperiod=25)

#set length of footage in seconds
picam2.start_recording(encoder, h264_output)

# Testing perf
last_timestamp = 0
i = 0
while i < 200:
    timestamp = picam2.capture_metadata()['SensorTimestamp']  # nanoseconds
    print(round((timestamp-last_timestamp)/1000000))
    # Should always be 1000/fps
    last_timestamp = timestamp
    i = i + 1

time.sleep(20)
picam2.stop_recording()

#convert h264 to mp4, and delete h264 file
os.system("ffmpeg -r 25 -i "+h264_output+" -c copy "+mp4_output)
#os.remove(h264_output)
