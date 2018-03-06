# micropython-max31856
Micropython driver for MAX31856 thermocouple interface

This has been tested on Wemos mini and Adafruit MAX31856 breakout board.

Test code thermo_tx.py reads from MAX31856 and publishes thermocouple and
cold junction temperatures to mqtt broker and local display.

Copy config.json to thermo_tx.json and update with details of your own
setup, copy to the micropython device along with the .py files.
