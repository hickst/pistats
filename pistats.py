#!/bin/env python3
#
# Program to show system statistics on an Adafruit PiTFT (240x240) display on a Raspberry Pi 4.
#   Written by: Tom Hicks. 9/9/21. After code on Adafruit site:
#     https://learn.adafruit.com/adafruit-mini-pitft-135x240-color-tft-add-on-for-raspberry-pi/python-stats
#   Last Modified: Create/use display class. Display button status.
#
import board
import digitalio
import subprocess
import time

from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789


# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000                         # The pi can be very fast!
WIDTH = 240                                 # width of display
HEIGHT = 240                                # height of display
ROTATION = 180                              # rotation angle for top-to-bottom text


class DisplaySt7789 ():
    """
    Class to wrap the Adafruit PiTFT display, which uses the st7789 chip.
    """

    def __init__(self):
        """
        Constructor for class which initializes the display.
        """
        super().__init__()

        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = None

        # Create the ST7789 display:
        self.display = st7789.ST7789(
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

        self.backlight = digitalio.DigitalInOut(board.D22)
        self.backlight.switch_to_output()
        self.backlight.value = True  # turn on backlight

        self.buttonA = digitalio.DigitalInOut(board.D23)
        self.buttonB = digitalio.DigitalInOut(board.D24)
        self.buttonA.switch_to_input()
        self.buttonB.switch_to_input()


    def set_backlight (self, on_off=True):
        "Turn the backlighting ON (True) or OFF (False)."
        self.backlight.value = on_off

    def backlight_on (self):
        "Return True if the backlighting is ON else False."
        return self.backlight.value

    def buttonA_on (self):
        "Return True if Button A is depressed else False."
        return not self.buttonA.value

    def buttonA_off (self):
        "Return True if Button A is not depressed else False."
        return self.buttonA.value

    def buttonB_on (self):
        "Return True if Button B is depressed else False."
        return not self.buttonB.value

    def buttonB_off (self):
        "Return True if Button A is not depressed else False."
        return self.buttonB.value



def get_stats():
    """
    Run shell scripts for system monitoring from here and return a list of
    result strings to be displayed.
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


def main (argv=None):
    # Colors used to display the various computer stats returned from get stats function:
    colors = { "pink": "#FF9999", "aqua": "#00FFFF", "green": "#00FF00",
               "white": "#FFFFFF", "yellow": "#FFFF00", "magenta": "#FF00FF",
               "blue": "#0000FF", "red": "#FF0000" }

    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)

    disp = DisplaySt7789()

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
            fill_colors = list(colors.values())
            for ndx, stat in enumerate(stats):
                fill_color = fill_colors[ndx % len(fill_colors)]
                draw.text((0, y), stat, font=font, fill=fill_color)
                y += text_height

        if (disp.buttonA_on() and disp.buttonB_off()):  # just button A pressed
            fill_color = fill_colors[0]
            draw.text((0, y), f"Btns: A=ON, B=OFF", font=font, fill=colors['white'])

        elif (disp.buttonB_on() and disp.buttonA_off()):  # just button B pressed
            fill_color = fill_colors[0]
            draw.text((0, y), f"Btns: A=OFF, B=ON", font=font, fill=colors['white'])

        elif (disp.buttonB_on() and disp.buttonA_on()):   # both on
            fill_color = fill_colors[2]
            draw.text((0, y), f"Btns: both ON", font=font, fill=colors['green'])

        else:
            fill_color = fill_colors[3]
            draw.text((0, y), f"Btns: both OFF", font=font, fill=colors['red'])

        disp.display.image(image, ROTATION)
        time.sleep(1)



if __name__ == "__main__":
    main()
