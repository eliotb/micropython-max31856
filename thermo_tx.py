
import ujson as json
from max31856 import Max31856
from machine import Pin, SPI, I2C
import network
from ssd1306 import SSD1306_I2C
import time
from umqtt.simple import MQTTClient

config = {
    "mqtt": {
        "server": "mqtt.local",
        "user": "mqtt_user",
        "password": "mqtt_password",
        "keepalive": 60
    },
    "tc_type": "K",
    "interval_seconds": 10
}


def load_config():
    global config
    try:
        with open('thermo_tx.json') as cf:
            cfg = json.load(cf)
    except Exception as e:
        print('Config exception', e)

        cfg = {}

    # Update default config
    for k, v in cfg.items():
        config[k] = v


def main():
    load_config()
    print('Config =', config)
    tc_type = config['tc_type']
    led = Pin(2, Pin.OUT)
    led.value(1)

    i2c = I2C(sda=Pin(4), scl=Pin(5), freq=350000)
    disp = SSD1306_I2C(64, 48, i2c)
    disp.text('Type ' + tc_type, 0, 0)
    disp.show()

    spi = SPI(1, baudrate=1000000, polarity=1)
    cs = Pin(16, Pin.OUT)
    max31856 = Max31856(spi, cs, tc_type)

    wlan = network.WLAN(network.STA_IF)
    mqtt = None

    if wlan.isconnected():
        hostname = wlan.config('dhcp_hostname')
        root = b"emon/thermocouple_" + hostname + '/'
        mqtt = MQTTClient(hostname, **config['mqtt'])
        mqtt.connect()
        mqtt.set_last_will(root + 'alive', '0')
        mqtt.publish(root + 'alive', '1')
        mqtt.publish(root + 'status', 'Thermocouple type %s' % max31856.tc_type)

    while True:
        time.sleep(config['interval_seconds'])
        led.value(0)
        tc = max31856.temperature(read_chip=True)
        cj = max31856.cold_junction()
        f, fs = max31856.faults()
        tcs = '{:7.2f}'.format(tc)
        cjs = '{:7.2f}'.format(cj)
        print('Temperatures:', tcs, cjs)
        if mqtt:
            if f:
                print(fs)
                mqtt.publish(root + 'fault', fs)
            else:
                mqtt.publish(root + 'tc', tcs)
                mqtt.publish(root + 'cj', cjs)

        disp.framebuf.fill(0)
        disp.text('Type ' + tc_type, 0, 0)
        if f:
            disp.text('Fault', 0, 9)
            disp.text(fs, 0, 18)
        else:
            disp.text(tcs, 0, 9)
            disp.text(cjs, 0, 18)
        disp.show()
        led.value(1)


if __name__ == "__main__":
    main()
