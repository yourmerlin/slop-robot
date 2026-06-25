# how to use / set up!

AP mode → your computer joins RoArm-M2, arm is 192.168.4.1.
STA mode → your computer + arm both on your WiFi, arm is 192.168.2.xxx (from its screen).

## physical set up

(AP MODE) 
    -- works anywhere. the arm makes its OWN WiFi hotspot,
        so it does NOT need to be near a router.

(STA MODE) 
    -- the arm must be within range of your WiFi router,
        and that router must be 2.4GHz (NOT 5GHz).

    safety: if a servo or the base ever gets HOT or smells burnt,
        unplug the power immediately and let it cool before inspecting. 

  1. place the arm
       - put it on a stable, flat surface
       - give it room to move freely: keep cups, objects, cables, and the
         other arm OUT of its swing reach so it can't hit anything
       - if you can, clamp or weight the base so it doesn't tip over

  2. power the arm
       - plug the wall power adapter into the arm's power port, then into
         the wall outlet  (this is the main power -- the servos need it)
       - the little OLED screen lights up and shows status when it's on
       - wait ~30 seconds for it to finish booting

  3. manage the cables   (important -- a pinched wire caused problems before)
       - keep all cables OUT of the joints and out of the swing path
       - don't let anything drape over the arm or get pinched as it moves

  4. (optional) USB-C to the computer  -- "the middle port"
       - NOT required for WiFi control: the arm is controlled wirelessly
       - only needed if controlling over serial, or for first-time config
       - for this code (WiFi), you can leave it unplugged



## software set up

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
