#!/bin/env python3

import board
import digitalio
import subprocess
import time

from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789


# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000                         # The pi can be very fast!

WIDTH = 240
HEIGHT = 240
ROTATION = 180


def get_stats():
    """
    Run shell scripts for system monitoring from here and return a list of result strings to be displayed.
    https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    """
    cmd = "hostname"
    stats = [ "Hostname: " + subprocess.check_output(cmd, shell=True).decode("utf-8") ]

    cmd = "hostname -I | cut -d' ' -f1"
    stats.append("IP: " + subprocess.check_output(cmd, shell=True).decode("utf-8"))

    cmd = "uptime | awk '{printf \"Load Avg: %.2f\", $(NF-2)}'"
    stats.append(subprocess.check_output(cmd, shell=True).decode("utf-8"))

    cmd = "uptime | awk '{print $3 \" \" $4}'"
    stats.append("Uptime: " + subprocess.check_output(cmd, shell=True).decode("utf-8"))

    cmd = "cat /sys/class/thermal/thermal_zone0/temp |  awk '{printf \"CPU Temp: %.1f C\", $(NF-0) / 1000}'"  # pylint: disable=line-too-long
    stats.append(subprocess.check_output(cmd, shell=True).decode("utf-8"))

    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
    stats.append(subprocess.check_output(cmd, shell=True).decode("utf-8"))

    cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\''
    stats.append(subprocess.check_output(cmd, shell=True).decode("utf-8"))
    return stats


def initialize_display ():
    # Configuration for CS and DC pins for Raspberry Pi
    cs_pin = digitalio.DigitalInOut(board.CE0)
    dc_pin = digitalio.DigitalInOut(board.D25)
    reset_pin = None

    # Create the ST7789 display:
    display = st7789.ST7789(
        board.SPI(),
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=BAUDRATE,
        width=WIDTH,
        height=HEIGHT,
        x_offset=0,
        y_offset=80,
    )

    backlight = digitalio.DigitalInOut(board.D22)
    backlight.switch_to_output()
    backlight.value = True  # turn on backlight

    buttonA = digitalio.DigitalInOut(board.D24)
    buttonB = digitalio.DigitalInOut(board.D23)
    buttonA.switch_to_input()
    buttonB.switch_to_input()

    return (display, backlight, buttonA, buttonB)


def main (argv=None):
    # Colors used to display the various computer stats returned from get stats function:
    fill_colors = [ "#FFFFFF", "#00FFFF", "#00FF00", "#FF0000", "#FFFF00", "#FF00FF", "#0000FF" ]
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)

    display, backlight, buttonA, buttonB = initialize_display()

    dwidth = WIDTH - 1
    dheight = HEIGHT - 1

    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    # Main loop:
    while True:
        # clear the drawing area: reset to black
        draw.rectangle((0, 0, dwidth, dheight), outline=(0, 0, 0), fill=(0, 0, 0))

        y = 0
        stats = get_stats()
        if (stats):
            text_height = font.getsize(stats[0])[1]
            for ndx, stat in enumerate(stats):
                fill_color = fill_colors[ndx % len(fill_colors)]
                draw.text((0, y), stat, font=font, fill=fill_color)
                y += text_height

        if (not buttonA.value and buttonB.value):   # just button A pressed
            fill_color = fill_colors[0]
            draw.text((0, y), f"ButtonA={buttonA.value}, {buttonB.value}", font=font, fill=fill_color)

        elif (not buttonB.value and buttonA):       # just button B pressed
            fill_color = fill_colors[0]
            draw.text((0, y), f"ButtonB={buttonA.value}, {buttonB.value}", font=font, fill=fill_color)

        else:
            fill_color = fill_colors[0]
            draw.text((0, y), f"BOTH={buttonA.value}, {buttonB.value}", font=font, fill=fill_color)

        display.image(image, ROTATION)
        time.sleep(1)



if __name__ == "__main__":
    main()
