from machine import Pin, ADC, WDT
import dht, time, network
import urequests as requests
import secrets
import firebase, gc

USE_WDT = True   # watchdog: set True once running standalone / False when editing
SEND_EVERY = 60      # seconds (ThingSpeak minimum interval 15s)

sensor = dht.DHT11(Pin(15))
ldr = ADC(26)
led = Pin("LED", Pin.OUT)
wdt = WDT(timeout=8000) if USE_WDT else None

def feed():
    if wdt:
        wdt.feed()

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    print("Connecting to Wi-Fi...")
    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
    for _ in range(20):
        if wlan.isconnected():
            print("Wi-Fi OK:", wlan.ifconfig()[0])
            return True
        feed()
        time.sleep(1)
    print("Wi-Fi failed, will retry")
    return False

def send(t, h, l):
    url = ("https://api.thingspeak.com/update?api_key={}&field1={}&field2={}&field3={}"
           .format(secrets.TS_WRITE_KEY, t, h, l))
    r = requests.get(url)
    ok = r.text.strip() != "0"   # ThingSpeak replies 0 if it rejected the update
    r.close()
    return ok

while True:
    feed()
    if wifi_connect():
        try:
            sensor.measure()
            t, h = sensor.temperature(), sensor.humidity()
            l = ldr.read_u16() * 100 // 65535
            print("Read:", t, "C", h, "%", l, "% light")

            # ThingSpeak
            feed()
            try:
                if send(t, h, l):
                    print("ThingSpeak OK")
                else:
                    print("ThingSpeak rejected the update")
            except Exception as e:
                print("ThingSpeak error:", e)
            gc.collect()

            # Firebase
            feed()
            try:
                if firebase.send("bedroom", t, h, l):
                    print("Firebase OK")
                else:
                    print("Firebase rejected the write")
            except Exception as e:
                print("Firebase error:", e)
            gc.collect()

            led.toggle()
        except Exception as e:
            print("Sensor error:", e)

    for _ in range(SEND_EVERY):   # sleep in 1s chunks so the watchdog stays fed
        feed()
        time.sleep(1)