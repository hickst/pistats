#!/bin/env python3
#
# Program to show system statistics on an Adafruit PiTFT (240x240) display on a Raspberry Pi 4.
#   Written by: Tom Hicks. 9/9/21. After code on Adafruit site:
#     https://learn.adafruit.com/adafruit-mini-pitft-135x240-color-tft-add-on-for-raspberry-pi/python-stats
#   Last Modified: Add reboot/shutdown logic.
#
import board
import digitalio
import os
import subprocess
import time

from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789


ROTATION = 180                              # rotation angle for top-to-bottom text

COLORS = { "pink": "#FF9999", "aqua": "#00FFFF", "green": "#00FF00",
           "white": "#FFFFFF", "yellow": "#FFFF00", "magenta": "#FF00FF",
           "blue": "#0000FF", "red": "#FF0000" }

FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
TEXT_HEIGHT = FONT.getsize('T')[1]
BIG_FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 28)
BIG_TEXT_HEIGHT = BIG_FONT.getsize('T')[1]



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
            baudrate=64000000,              # the pi can be very fast!
            width=240,                      # width of display
            height=240,                     # height of display
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



def action_or_cancel (disp, draw, image, reboot=True):
    "Give the user a chance to cancel the reboot or shutdown action, otherwise do the action."
    act = 'REBOOT' if (reboot) else 'SHUTDOWN'
    act_msg = 'Rebooting...' if (reboot) else 'Shutting down...'
    color = COLORS['green'] if (reboot) else COLORS['yellow']

    time.sleep(1)                           # got here too fast: need to let buttons clear!
    for countdown in range(9, 0, -1):
        reset_to_black(disp, draw)          # clear the drawing area

        y = TEXT_HEIGHT
        draw.text((0, y), f"{act}", font=BIG_FONT, fill=color)
        y += BIG_TEXT_HEIGHT
        draw.text((0, y), f"  in {countdown} seconds!!", font=BIG_FONT, fill=COLORS['aqua'])
        y += 3 * BIG_TEXT_HEIGHT
        draw.text((0, y), f"TO CANCEL:", font=BIG_FONT, fill=COLORS['white'])
        y += BIG_TEXT_HEIGHT
        draw.text((0, y), f" hold any button", font=BIG_FONT, fill=COLORS['white'])
        y += 2 * BIG_TEXT_HEIGHT

        disp.display.image(image, ROTATION)
        time.sleep(1)

        if (disp.buttonA_on() or disp.buttonB_on()):  # if either button pressed
            one_msg(disp, draw, image, msg='  CANCELLED!', fill=color)
            return


    one_msg(disp, draw, image, msg=act_msg, fill=color)
    flag = '-r' if (reboot) else '-P'
    # print(f"sudo /usr/sbin/shutdown {flag} now --no-wall")
    os.system(f"sudo /usr/sbin/shutdown {flag} now --no-wall")


def draw_size (disp):
    "Return the size (width, height) of the drawable area for the given display object."
    return (disp.display.width - 1, disp.display.height - 1)


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


def one_msg (disp, draw, image, msg='', fill='#FFFFFF'):
    "Clear the display and show the single given message, roughly centered."
    reset_to_black(disp, draw)              # clear the drawing area
    y = 3 * BIG_TEXT_HEIGHT
    draw.text((0, y), msg, font=BIG_FONT, fill=fill)
    disp.display.image(image, ROTATION)
    time.sleep(2)


def reset_to_black (disp, draw):
    " Clear the given drawing area by drawing a black rectangle."
    dwidth, dheight = draw_size(disp)
    draw.rectangle((0, 0, dwidth, dheight), outline=(0, 0, 0), fill=(0, 0, 0))


def restart_menu (disp, image, draw):
    "Show the reboot/shutdown menu for a limited time; dispatch an action or timeout."
    for countdown in range(10, 0, -1):
        reset_to_black(disp, draw)          # clear the drawing area

        y = TEXT_HEIGHT
        draw.text((0, y), f"to REBOOT:", font=BIG_FONT, fill=COLORS['green'])
        y += BIG_TEXT_HEIGHT
        draw.text((0, y), f"   hold button A", font=FONT, fill=COLORS['white'])
        y += 2 * TEXT_HEIGHT

        draw.text((0, y), f"to SHUTDOWN:", font=BIG_FONT, fill=COLORS['yellow'])
        y += BIG_TEXT_HEIGHT
        draw.text((0, y), f"   hold button B", font=FONT, fill=COLORS['white'])
        y += 2 * TEXT_HEIGHT

        draw.text((0, y), f"Times out in:", font=BIG_FONT, fill=COLORS['red'])
        y += BIG_TEXT_HEIGHT
        draw.text((0, y), f"   {countdown} seconds", font=BIG_FONT, fill=COLORS['pink'])

        if (disp.buttonA_on() and disp.buttonB_off()):  # just button A pressed
            action_or_cancel(disp, draw, image, True)   # true => reboot
            break

        elif (disp.buttonB_on() and disp.buttonA_off()):  # just button B pressed
            action_or_cancel(disp, draw, image, False)    # false => shutdown
            break

        disp.display.image(image, ROTATION)
        time.sleep(1)


def main (argv=None):
    disp = DisplaySt7789()
    dwidth, dheight = draw_size(disp)

    image = Image.new('RGB', (disp.display.width, disp.display.height))
    draw = ImageDraw.Draw(image)

    sleep_time = 1                          # time to sleep (in seconds) in each iteration

    # Main loop:
    while True:
        reset_to_black(disp, draw)          # clear the drawing area

        y = 0
        stats = get_stats()
        if (stats):
            fill_colors = list(COLORS.values())
            for ndx, stat in enumerate(stats):
                fill_color = fill_colors[ndx % len(fill_colors)]
                draw.text((0, y), stat, font=FONT, fill=fill_color)
                y += TEXT_HEIGHT

        if (disp.buttonA_on() and disp.buttonB_off()):  # just button A pressed
            draw.text((0, y), f"Btns: A=ON, B=OFF", font=FONT, fill=COLORS['white'])

        elif (disp.buttonB_on() and disp.buttonA_off()):  # just button B pressed
            draw.text((0, y), f"Btns: A=OFF, B=ON", font=FONT, fill=COLORS['white'])

        elif (disp.buttonB_on() and disp.buttonA_on()):   # both on
            restart_menu(disp, image, draw)

        else:
            draw.text((0, y), f"Btns: both OFF", font=FONT, fill=COLORS['red'])

        disp.display.image(image, ROTATION)
        time.sleep(sleep_time)



if __name__ == "__main__":
    main()
