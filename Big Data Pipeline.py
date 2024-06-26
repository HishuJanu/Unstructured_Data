import pandas as pd
import string
from geopy.distance import Distance
import tkinter as tk
from tkinter import *
from tkinter import filedialog
import math as m
import requests
import cv2 as cv
import numpy as np
from os.path import exists
from statistics import mean


# -------------------------------------------------------------------------- 1) SRT -> .CSV --------------------------------------------------------------------------
# -------------------------------------------------------------------------- 1) SRT -> .CSV --------------------------------------------------------------------------
# -------------------------------------------------------------------------- 1) SRT -> .CSV --------------------------------------------------------------------------


def convertToMilisecond(timecode):
  time,ms = timecode.split(',')
  hr,min,sec = time.split(':')
  return int( int(ms) + int(hr)*(3.6e+6) + int(min)*60000 + int(sec)*1000 )


def getDistance(lat1,lon1,alt1,lat2,lon2,alt2):
  r = 6371000

  lat1,lon1,alt1 = m.radians(lat1),m.radians(lon1),m.radians(alt1)
  lat2,lon2,alt2 = m.radians(lat2),m.radians(lon2),m.radians(alt2)  
  
  x2 = (r+alt2)*m.cos(lat2)*m.cos(lon2)
  y2 = (r+alt2)*m.cos(lat2)*m.sin(lon2)
  z2 = (r+alt2)*m.sin(lat2)

  x1 = (r+alt1)*m.cos(lat1)*m.cos(lon1)
  y1 = (r+alt1)*m.cos(lat1)*m.sin(lon1)
  z1 = (r+alt1)*m.sin(lat1)

  d = m.sqrt((x2-x1)**2+(y2-y1)**2+(z2-z1)**2)
  return d


# ------------------------ READ .SRT FILE ------------------------
filename = filedialog.askopenfilename(initialdir=".",title = "Select a File", filetypes=(("SRT files","*.srt"),("All files","*.*")))
with open(filename) as f:
    lines = f.readlines()

# ------------------------ EXTRACT THE REQUIRED LINES ------------------------
block = {}
length = len(lines)
for lineNum in range(0,length):
  blocStartLine = lineNum*14
  if blocStartLine < length:
    block[f'{lineNum+1}'] = []
    block[f'{lineNum+1}'].append(lines[blocStartLine+1:blocStartLine+2]+lines[blocStartLine+5:blocStartLine+6])
  else :
    break

# ------------------------ EXTRACT THE REQUIRED VALUES ------------------------
StartTime,EndTime,Lattitude,Longitude,Altitude = [],[],[],[],[]
FrameNumber = [*range(1,29023)]

# ------------------------ CREATE DATAFRAME ------------------------
for i in block:
  blockNum = block[i][0]
  temp = blockNum[0].replace('\n','').split(' --> ')
  StartTime.append(temp[0])
  EndTime.append(temp[1])
  temp = blockNum[1].translate(str.maketrans('', '', '[]:')).split(' ')
  Lattitude.append(float(temp[1]))
  Longitude.append(float(temp[3]))
  Altitude.append(float(temp[5]))

df = pd.DataFrame(list(zip(StartTime,EndTime,FrameNumber,Lattitude,Longitude,Altitude)),
                  columns=['StartTime','EndTime','FrameNumber','Lattitude','Longitude','Altitude'])
df.set_index('FrameNumber',inplace=True)

# ------------------------ CONVERT TIME TO MILLISECONDS ------------------------
starttime = df['StartTime'].tolist()
endtime = df['EndTime'].tolist()
starttime_ms,endtime_ms = [],[]

for i in range(len(starttime)):
  starttime_ms.append(convertToMilisecond(starttime[i]))
  endtime_ms.append(convertToMilisecond(endtime[i]))

starttime.clear()
endtime.clear()


# ------------------------ CALCULATE DISTANCE OF TWO POINTS ------------------------
lat = df['Lattitude'].tolist()
lon = df['Longitude'].tolist()
alt = df['Altitude'].tolist()
distance = []
distance_from_start = []

for i in range(len(lat)):
  if i+1 == len(lat):
    distance.append(0.0)
  else:
    distance.append(getDistance(lat[i],lon[i],alt[i],lat[i+1],lon[i+1],alt[i+1]))
  distance_from_start.append(getDistance(lat[0],lon[0],alt[0],lat[i],lon[i],alt[i]))  

lat.clear()
lon.clear()
alt.clear()

# ------------------------ CALCULATE THE SPEED ------------------------
speed = []
for i in range(len(starttime_ms)):
  time = endtime_ms[i]-starttime_ms[i]
  spd = round(distance[i]*1800/time,2)
  speed.append(spd)

# ------------------------ REARRANGE DATAFRAME ------------------------
df.drop(['StartTime','EndTime'], axis = 1, inplace=True)
df.insert(0,"EndTime(ms)",endtime_ms)
df.insert(0,"StartTime(ms)",starttime_ms)
df.insert(5,"Speed",speed)
df.insert(5,"Distance_from_start(m)",distance_from_start)
print(df)
starttime_ms.clear()
endtime_ms.clear()

df.to_csv('DJI_20230124113730_0001_W_Waypoint1.csv')


# --------------------------------------------------------------------- 2) Download Google images ---------------------------------------------------------------------
# --------------------------------------------------------------------- 2) Download Google images ---------------------------------------------------------------------
# --------------------------------------------------------------------- 2) Download Google images ---------------------------------------------------------------------

map_dir = './map'

def download_image(image_url, path_to_write):
    img_data = requests.get(image_url).content

    with open(path_to_write, 'wb') as handler:
        handler.write(img_data)

#df = pd.read_csv(csv_file)

for index, row in df.iterrows():
    index = index-1
    if index == 21:
        break
    else:
        url ="https://maps.googleapis.com/maps/api/staticmap?center={0},{1}&zoom=19&size=400x300&maptype=hybrid&markers=color:red%7Clabel:S%7C{0},{1}&markers=size:tiny%22&key=AIzaSyCUIK90jYIXusR43siewRD9Rw2gtPI-7lg&path=color:0x0000ff|weight:3".format(row["Lattitude"],row["Longitude"])
        download_image(url, map_dir + "/" + str(index) + ".png")
        print(str(index),".png downloaded")


# ----------------------------------------------------------------------- 3) Augment the footage ----------------------------------------------------------------------
# ----------------------------------------------------------------------- 3) Augment the footage ----------------------------------------------------------------------
# ----------------------------------------------------------------------- 3) Augment the footage ----------------------------------------------------------------------

file_prefix = "./DJI_20230124113730_0001_W_Waypoint1"
waypoint_srt_records = df
file_name = file_prefix + ".mp4"
cv.namedWindow('Processing', cv.WINDOW_NORMAL)

source = cv.VideoCapture(file_name)
framespersecond = float(source.get(cv.CAP_PROP_FPS))
success, image = source.read()
height, width, layers = image.shape
out = cv.VideoWriter(file_prefix + "_processed.mp4", cv.VideoWriter_fourcc(*'mp4v'), framespersecond, (width, height))

video_frame_count = 1
alpha = 0.7
lat = waypoint_srt_records['Lattitude'].tolist()[2:]
lng = waypoint_srt_records['Longitude'].tolist()[2:]
alt = waypoint_srt_records['Altitude'].tolist()[2:]
speed = waypoint_srt_records['Speed'].tolist()[2:]

begining_second_frame_index = 0
second = 0
while success and (cv.waitKey(1) & 0xFF != ord('q')): # 27 for esc

    frame_index = int(video_frame_count / framespersecond)
    if frame_index == 21:
        break
    else:
        map_file = './map/' + str(frame_index) + '.png'
        overlay = image.copy()

        index = int(video_frame_count*1.5 / framespersecond)
        end_second_frame_index = int(frame_index*framespersecond + framespersecond)
        
        if begining_second_frame_index != end_second_frame_index:
            avg_speed = round(mean(speed[begining_second_frame_index : end_second_frame_index]),2)
            latitude = round(mean(lat[begining_second_frame_index : end_second_frame_index]),6)
            longitude = round(mean(lng[begining_second_frame_index : end_second_frame_index]),6)
            altitude = round(mean(alt[begining_second_frame_index : end_second_frame_index]),3)
            begining_second_frame_index = end_second_frame_index
        
        cv.line(overlay, (width-750,height-150), (width-150,height-150), (150,50,50), 100)
        cv.putText(overlay, str(avg_speed), (width-750,height-150), cv.FONT_HERSHEY_COMPLEX, 1.1, (0,255,0), 2, 1)
        cv.putText(overlay, 'SPEED (km/h)', (width-750,height-120), cv.FONT_HERSHEY_COMPLEX, 0.7, (0,255,0), 2, 1)
        cv.putText(overlay, str(altitude), (width-525,height-150), cv.FONT_HERSHEY_COMPLEX, 1.1, (0,255,0), 2, 1)
        cv.putText(overlay, 'ALTITUDE (m):', (width-525,height-120), cv.FONT_HERSHEY_COMPLEX, 0.7, (0,255,0), 2, 1)
        cv.putText(overlay, 'LON: ' + str(longitude), (width-300,height-150), cv.FONT_HERSHEY_COMPLEX, 0.7, (0,255,0), 2, 1)
        cv.putText(overlay, 'LAT: '+ str(latitude), (width-300,height-120), cv.FONT_HERSHEY_COMPLEX, 0.7, (0,255,0), 2, 1)
        result = cv.addWeighted(overlay, alpha, image, 1 -alpha, 0)

        if exists(map_file):
            map = cv.imread(map_file, -1)
            ht,wt,lyr = map.shape
            result[height-ht-15:height-15, 15:wt+15] = map
            if frame_index != second:
              print("second ",second+1," Completed!!!")
              second = frame_index
        else:
            print('Map Image Does not Exist!!!')
            break

        out.write(result)
        cv.imshow('Processing', result)
        success, image = source.read()

        video_frame_count +=1
print("Process Completed!!!")
source.release()
out.release()
cv.destroyAllWindows()
