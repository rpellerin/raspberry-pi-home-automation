#!/usr/bin/env python3
from os import path, DirEntry
import configparser
import os
import requests
import sys
import math
import time
import calendar
from datetime import date
from datetime import datetime
import re
from enum import Enum
import redis
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from inky.inky_uc8159 import Inky, BLACK, WHITE, GREEN, RED, YELLOW, ORANGE, BLUE, DESATURATED_PALETTE as color_palette
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm, rcParams, ticker
import numpy as np

r = redis.Redis()

saturation = 0.5
canvasSizeInPixels = (600, 448)

tmpfs_path = "/dev/shm/"

# font file path(Adjust or change whatever you want)
repo_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(repo_path)
project_root = os.getcwd()

colorMap = {
    '01d':ORANGE, # clear sky
    '01n':YELLOW,
    '02d':BLACK, # few clouds
    '02n':BLACK,
    '03d':BLACK, # scattered clouds
    '03n':BLACK,
    '04d':BLACK, # broken clouds
    '04n':BLACK,
    '09d':BLACK, # shower rain
    '09n':BLACK,
    '10d':BLUE,  # rain
    '10n':BLUE, 
    '11d':RED,   # thunderstorm
    '11n':RED,
    '13d':BLUE,  # snow
    '13n':BLUE, 
    '50d':BLACK, # fog
    '50n':BLACK,
    'sunrise':BLACK,
    'sunset':BLACK
}
# icon name to weather icon mapping
iconMap = {
    '01d':u'', # clear sky
    '01n':u'',
    '02d':u'', # few clouds
    '02n':u'',
    '03d':u'', # scattered clouds
    '03n':u'',
    '04d':u'', # broken clouds
    '04n':u'',
    '09d':u'', # shower rain
    '09n':u'',
    '10d':u'', # rain
    '10n':u'',
    '11d':u'', # thunderstorm
    '11n':u'',
    '13d':u'', # snow
    '13n':u'',
    '50d':u'', # fog
    '50n':u'',

    'clock0':u'', # same as 12
    'clock1':u'',
    'clock2':u'',
    'clock3':u'',
    'clock4':u'',
    'clock5':u'',
    'clock6':u'',
    'clock7':u'',
    'clock8':u'',
    'clock9':u'',
    'clock10':u'',
    'clock11':u'',
    'clock12':u'',

    'celsius':u'',
    'sunrise':u'',
    'sunset':u''
}

class weatherInfomation(object):
    def __init__(self):
        #load configuration from config.txt using configparser
        self.config = configparser.ConfigParser()
        try:
            self.config.read_file(open(project_root + '/config.txt'))
            self.lat = self.config.get('openweathermap', 'LAT', raw=False)
            self.lon = self.config.get('openweathermap', 'LON', raw=False)
            self.api_key = self.config.get('openweathermap', 'API_KEY', raw=False)
            # API document at https://openweathermap.org/api/one-call-api
            self.cold_temp = float(self.config.get('openweathermap', 'cold_temp', raw=False))
            self.hot_temp = float(self.config.get('openweathermap', 'hot_temp', raw=False))
            self.forecast_api_uri = 'https://api.openweathermap.org/data/3.0/onecall?&lat=' + self.lat + '&lon=' + self.lon +'&appid=' + self.api_key + '&exclude=daily'
            self.forecast_api_uri = self.forecast_api_uri + "&units=metric"
            self.loadWeatherData()
        except:
            self.one_time_message = "Configuration file is not found or settings are wrong.\nplease check the file : " + project_root + "/config.txt\n\nAlso check your internet connection."
            return

        # load one time messge and remove it from the file. one_time_message can be None.
        try:
            self.one_time_message = self.config.get('openweathermap', 'one_time_message', raw=False)
            self.config.set("openweathermap", "one_time_message", "")
            # remove it.
            with open(project_root + '/config.txt', 'w') as configfile:
                self.config.write(configfile)
        except:
            self.one_time_message = ""
            pass

    def loadWeatherData(self):
        openweather_response = requests.get(self.forecast_api_uri).json()
        self.weatherInfo = self.loadLocalWeatherData()
        self.weatherInfo['current']['outside_temp'] = openweather_response['current']['temp']
        self.weatherInfo['current']['weather'] = openweather_response['current']['weather']
    
    def loadLocalWeatherData(self):
        # We want last 4 hours. There are 20 reports per hour, so 80.
        weather_reports = r.lrange('weather_reports', 0, 80-1)
        def sanitize(row):
            json_row = json.loads(row)
            return {
                'temp': json_row['temperature'],
                'humidity': round(json_row['humidity'], 1),
                'pressure': json_row['pressure'],
                'dt': datetime.strptime(json_row['timestamp'], '%d/%m/%Y %H:%M:%S').timestamp()
            }

        hourly = list(map(sanitize, weather_reports))[::-1] # [::-1] reverses it
        current = hourly[-1].copy()
        return { 'current': current, 'hourly': hourly }


class fonts(Enum):
    thin = project_root + "/fonts/Roboto-Thin.ttf"
    light =  project_root + "/fonts/Roboto-Light.ttf"
    normal = project_root + "/fonts/Roboto-Black.ttf"
    icon = project_root + "/fonts/weathericons-regular-webfont.ttf"

def getFont(type, fontsize=12):
    return ImageFont.truetype(type.value, fontsize)

def getFontColor(temp, wi):
    if temp < wi.cold_temp:
        return (0,0,255)
    if temp > wi.hot_temp:
        return (255,0,0)
    return getDisplayColor(BLACK)

def getHumidityColor(humidity):
    if humidity < 35:
        return (0,0,255)
    if humidity > 70:
        return (255,0,0)
    return getDisplayColor(BLACK)

def getUnitSign():
    return iconMap['celsius']

# return rgb in 0 ~ 255
def getDisplayColor(color):
    return tuple(color_palette[color])

def getTemperatureString(temp):
    formattedString = "%0.0f" % temp
    if formattedString == "-0":
        return "0"
    else:
        return formattedString
    
# return color rgb in 0 ~ 1.0 scale
def getGraphColor(color):
    r = color_palette[color][0] / 255
    g = color_palette[color][1] / 255
    b = color_palette[color][2] / 255
    return (r,g,b)

# draw current weather and forecast into canvas
def drawWeather(wi, cv):
    draw = ImageDraw.Draw(cv)
    width, height = cv.size

    # one time message
    if hasattr( wi, "weatherInfo") == False:
        draw.rectangle((0, 0, width, height), fill=getDisplayColor(ORANGE))
        draw.text((20, 70), u"", getDisplayColor(BLACK), anchor="lm", font =getFont(fonts.icon, fontsize=130))
        draw.text((150, 80), "Weather information is not available at this time.", getDisplayColor(BLACK), anchor="lm", font=getFont(fonts.normal, fontsize=18) )
        draw.text((width / 2, height / 2), wi.one_time_message, getDisplayColor(BLACK), anchor="mm", font=getFont(fonts.normal, fontsize=16) )
        return
    draw.text((width - 10, 2), wi.one_time_message, getDisplayColor(BLACK), anchor="ra", font=getFont(fonts.normal, fontsize=12))
    
    temp_cur = wi.weatherInfo[u'current'][u'temp']
    outside_temp_cur = wi.weatherInfo[u'current'][u'outside_temp']
    icon = str(wi.weatherInfo[u'current'][u'weather'][0][u'icon'])
    description = wi.weatherInfo[u'current'][u'weather'][0][u'description']
    humidity = wi.weatherInfo[u'current'][u'humidity']
    pressure = wi.weatherInfo[u'current'][u'pressure']
    epoch = int(wi.weatherInfo[u'current'][u'dt'])
    recorded_time = time.localtime(epoch)
    dateString = time.strftime("%B %-d", recorded_time)
    weekDayString = time.strftime("%a", recorded_time)
    weekDayNumber = time.strftime("%w", recorded_time)
    hourMinutes = time.strftime("%H:%M", recorded_time)

    # date 
    draw.text((15 , 5), dateString, getDisplayColor(BLACK),font=getFont(fonts.normal, fontsize=64))
    draw.text((width - 8 , 5), weekDayString, getDisplayColor(BLACK), anchor="ra", font =getFont(fonts.normal, fontsize=64))

    offsetX = 10
    offsetY = 40

    draw.text((5 + offsetX , 35 + offsetY), hourMinutes, getDisplayColor(BLACK),font=getFont(fonts.light,fontsize=24))

    # draw current weather icon
    draw.text((440 + offsetX, 40 + offsetY), iconMap[icon], getDisplayColor(colorMap[icon]), anchor="ma",font=getFont(fonts.icon, fontsize=160))
    draw.text((width - 8, 35 + offsetY), description, getDisplayColor(BLACK), anchor="ra", font =getFont(fonts.light,fontsize=24))

    def draw_value(label, value, unit, unit_font, color, x, y):
        draw.text((x, y), label, getDisplayColor(BLACK),font =getFont(fonts.light,fontsize=24))
        draw.text((x, y + 25), value, color, font =getFont(fonts.normal, fontsize=50))
        textSize = round(draw.textlength(value, font =getFont(fonts.normal, fontsize=50)))
        draw.text((x + textSize + 5, y + 49), unit, color, font=getFont(unit_font,fontsize=22))

    # Inside temperature
    draw_value("Inside", getTemperatureString(temp_cur), getUnitSign(), fonts.icon, getFontColor(temp_cur, wi), offsetX + 5, offsetY + 80)

    # Outside temperature
    draw_value("Outside", getTemperatureString(outside_temp_cur), getUnitSign(), fonts.icon, getFontColor(outside_temp_cur, wi), offsetX + 185, offsetY + 80)

    offsetY = 210
    
    # Humidity (lastest value)
    draw_value("Humidity", str(humidity), '%', fonts.normal, getHumidityColor(humidity), offsetX + 5, 215)

    # Pressure (lastest value)
    draw_value("Pressure", "%d" % pressure, 'hPa', fonts.normal, getDisplayColor(BLACK), offsetX + 185, 215)
    
    time_dt_array = []
    tempArray = []
    humidityArray = []
    for item in wi.weatherInfo[u'hourly']:
        time_dt = item[u'dt']
        temp = item[u'temp']
        humidity = item[u'humidity']
        pressure = item[u'pressure']
        time_dt_array.append(time_dt)
        tempArray.append(temp)
        humidityArray.append(humidity)

    # Documentation: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/two_scales.html
    graph_height = 1.67
    graph_width = 6.3
    fig, ax1 = plt.subplots()
    fig.set_figheight(graph_height)
    fig.set_figwidth(graph_width)

    color = getGraphColor(BLUE)
    #ax1.set_xlabel('Time')
    #ax1.set_ylabel('Temp', color=color)
    ax1.plot(time_dt_array, tempArray, linewidth=3, color=color)

    def xmajor_formatter(tick_value, position):
        return time.strftime('%H:%M', time.localtime(tick_value))

    ax1.xaxis.set_major_formatter(xmajor_formatter)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.spines['top'].set_visible(False)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = getGraphColor(RED)
    #ax2.set_ylabel('Humidity', color=color)  # we already handled the x-label with ax1
    ax2.plot(time_dt_array, humidityArray, linewidth=3, color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.spines['top'].set_visible(False)
    fig.tight_layout()

    plt.savefig(tmpfs_path+'temp.png', bbox_inches='tight', pad_inches=0, transparent=True)
    tempGraphImage = Image.open(tmpfs_path+"temp.png")
    cv.paste(tempGraphImage, (0, 305), tempGraphImage)

    # Draw temperature + humidity labels
    offsetX = width - 60
    squareWitdh = 15
    ## Temperature
    offsetY = 265
    draw.rectangle((offsetX, offsetY, offsetX + squareWitdh, offsetY + squareWitdh), fill=getDisplayColor(BLUE))
    draw.text((offsetX + squareWitdh + 2, offsetY), "Temp", getDisplayColor(BLACK),font=getFont(fonts.normal, fontsize=16))
    
    ## Humidity
    offsetY = offsetY + 20
    draw.rectangle((offsetX, offsetY, offsetX + squareWitdh, offsetY + squareWitdh), fill=getDisplayColor(RED))
    draw.text((offsetX + squareWitdh + 2, offsetY), "Humi", getDisplayColor(BLACK),font=getFont(fonts.normal, fontsize=16))

def update():
    wi = weatherInfomation()
    cv = Image.new("RGB", canvasSizeInPixels, getDisplayColor(WHITE) )
    drawWeather(wi, cv)
    cv.save('/tmp/weather.jpg', "JPEG", optimize=True, quality=90)
    print('Image saved')

if __name__ == "__main__":
    update()
