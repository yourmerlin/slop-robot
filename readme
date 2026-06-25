## how to use / set up!

AP mode → your computer joins RoArm-M2, arm is 192.168.4.1.
STA mode → your computer + arm both on your WiFi, arm is 192.168.2.xxx (from its screen).

# physical set up

(STA MODE)
connect robot via usb-c to the computer (the middle port in the hardware)
make sure both robots are connected via usb-c

(AP MODE)

# software set up

(STA MODE) -- run on ur personal wifi

first-time setup:

    1. first connect to the arm DIRECTLY (this part starts in AP mode):
    join the WiFi: RoArm-M2 (password: 12345678)

    2. open a browser, paste this into the address bar, swap the two CAPS
    parts for your real WiFi name + password, then press Enter:

       http://192.168.4.1/js?json={"T":403,"ssid":"YOUR_WIFI_NAME","password":"YOUR_WIFI_PASSWORD"}

        ** must be a 2.4GHz WiFi (NOT 5GHz), and NOT a guest network **

    3. look at the arm's screen -- the ST: line now shows its new IP
       ex:  ST: 192.168.2.239     <- write this number down

    4. (optional) make it auto-join every time it powers on:
       http://192.168.4.1/js?json={"T":401,"cmd":3}

    5. reconnect your computer to your OWN WiFi
     (the same network the arm just joined)

RUNNING (after the one-time setup):

    1. go to the folder location + copy path
        ex: cd C:\Users\susan\OneDrive\Desktop\robot-arm\slop-robot

    2. run it, using the IP from the arm's screen:
            > python my_first_arm.py --ip 192.168.2.239
            ** the IP can CHANGE when the arm reboots -- if it stops connecting,
            check the ST: line on the screen again for the new number **
        # arm ips:
            > LEFT ARM:
                #STA mode: 192.168.2.239
                #AP mode: 192.168.4.1
            > RIGHT ARM:
                # STA mode: 192.168.2.190
                # AP mode: 192.168.4.1

open terminal:

(print test, no actual hardware movement---for debug purposes)

> python my_first_arm.py --dry-run

(actual run, with hardware movement)

> python my_first_arm.py

if in vscode:
open the terminal with Terminal → New Terminal (top menu)

to stop running:
press Ctrl + C in the terminal.
