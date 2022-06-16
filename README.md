# Yamaha YNCA

Custom integration for Home Assistant to support Yamaha AV receivers with the YNCA protocol (serial and IP).

According to the protocol documentation the following AV receivers should be supported (not all tested), there might be more.

> RX-A700, RX-A710, RX-A800, RX-A810, RX-A840, RX-A850, RX-A1000, RX-A1010, RX-A2000, RX-A2010, RX-A3000, RX-A3010, RX-V671, RX-V867, RX-V871, RX-V1067, RX-V2067, RX-V2600, RX-V3067

## Features

* Connect through serial, IP or any [URL handler supported by PySerial](https://pyserial.readthedocs.io/en/latest/url_handlers.html)
* Power on/off
* Volume and mute
* Source selection
* Sound mode selection
* Show metadata like artist, album, song (depends on source)
* Control playback (depends on source)
* Activate scenes
* Hide unused inputs per zone

## Installation

### HACS

Recommended as you get notified of updates.

* Add this repository `https://github.com/mvdwetering/yamaha_ynca` to HACS as a "custom repository" with category "integration"
* Add integration within HACS (use the + button and search for "YNCA")
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)"

### Manual

* Install the custom component by downloading it and copy it to the `custom_components` directory as usual.
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)"
