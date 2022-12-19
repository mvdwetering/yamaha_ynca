# Yamaha YNCA

Custom integration for Home Assistant to support Yamaha AV receivers with the YNCA protocol (serial and IP).

According to reports of users and info found on the internet the following AV receivers should be supported (not all tested), there might be more. If your receiver works and is not in the list please let us know!

> RX-A700, RX-A710, RX-A720, RX-A800, RX-A810, RX-A820, RX-A840, RX-A850, RX-A1000, RX-A1010, RX-A1020, RX-A1040, RX-A2000, RX-A2010, RX-A2020, RX-A3000, RX-A3010, RX-A3020, RX-V475, RX-V671, RX-V673, RX-V867, RX-V871, RX-V1067, RX-V2067, RX-V3067, TSR-700

In case of issues or feature requests please [submit an issue on Github](https://github.com/mvdwetering/yamaha_ynca/issues)

## Features

* Full UI support for adding devices
* Connect through serial, IP or any [URL handler supported by PySerial](https://pyserial.readthedocs.io/en/latest/url_handlers.html)
* Support for multiple zones
* Power on/off
* Volume and mute
* Source selection
* Sound mode selection
* Show metadata like artist, album, song (depends on source)
* Control playback (depends on source)
* Activate scenes
* Hide unused inputs per zone
* Hide soundmodes


## Limitations

It is not possible to autodetect all features of a receiver. However there are some things you can do yourself to solve/workaround this.

### Scene buttons not working

For some receivers (e.g. RX-V475) the command to activate the scenes does not work even though scenes are supported by the receiver. As a workaround, hide the scene button entities in Home Assistant

### Inputs do not match zone

For most receivers the inputs available on the receiver can be detected, but it is not possible to detect which of those inputs are available per zone.

You can select the inputs per zone in the integration configuration which can be accessed by pressing the "Configure" button on the integration card in the "Devices & Services" section of the Home Assistant settings.

### Soundmodes do not match receiver

The list of soundmodes can not be detected, so by default the whole list of known soundmodes is shown.

You can select the soundmodes applicable the specific receiver in the integration configuration which can be accessed by pressing the "Configure" button on the integration card in the "Devices & Services" section of the Home Assistant settings.

## Installation

### HACS

*Recommended as you get notified of updates.*

* Add integration within HACS (use the + button and search for "YNCA")
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)". You might need to clear the browser cache for it to show up (e.g. reload with CTRL+F5).

### Manual

* Install the custom component by downloading the zipfile from the release
* Extract the zip and copy the contents to the `custom_components` directory as usual.
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)". You might need to clear the browser cache for it to show up (e.g. reload with CTRL+F5).
