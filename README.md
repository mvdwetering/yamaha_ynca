# Yamaha YNCA

Custom integration for Home Assistant to support Yamaha AV receivers with the YNCA protocol (serial and IP).

According to reports of users and info found on the internet the following AV receivers should be working (not all tested), there might be more. If your receiver works and is not in the list please post a message in the [discussions](https://github.com/mvdwetering/yamaha_ynca/discussions).

> RX-A700, RX-A710, RX-A720, RX-A800, RX-A810, RX-A820, RX-A840, RX-A850, RX-A1000, RX-A1010, RX-A1020, RX-A1030, RX-A1040, RX-A2000, RX-A2010, RX-A2020, RX-A3000, RX-A3010, RX-A3020, RX-V475, RX-V671, RX-V673, RX-V677, RX-V867, RX-V871, RX-V1067, RX-V2067, RX-V3067, TSR-700

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
* Several controllable settings (if supported by receiver):
  * CINEMA DSP 3D mode
  * Adaptive DRC
  * Compressed Music Enhancer
  * HDMI Out selection (Off, HDMI1, HDMI2 or Both)
  * Initial volume
  * Max volume
  * Sleep timer
  * Speaker bass/treble
  * Headphone bass/treble (default disabled)
  * Surround Decoder


## Limitations

This section lists some limitations of the integration and possbile solutions.

### Config entities unavailable when receiver in standby

The receiver does not allow changing of settings when it is in standby, so the entities become Unavailable.

### Scenes not detected

On newer receivers the autodetection of the amount of Scenes supported per zone does not work anymore, so no Scenes are detected.

*Solution:* Override the autodetect and manually configure the amount of Scenes supported per zone in the integration configuration.

### Scene buttons not working

For the RX-V475 with firmware 1.34/2.06 the command to activate the scenes does not work even though scenes are supported by the receiver. As a workaround, disable the Scene button entities in Home Assistant.

### Sources list does not match receiver zone capabilities

For most receivers the total amount/type of inputs available on the receiver can be detected, but it is not possible to detect which of those inputs are available per zone.

*Solution:* Manually hide the sources that are not supported per zone in the integration configuration.

### Soundmodes do not match receiver

The list of soundmodes can not be detected, for some models the list is know, for the rest the whole list of known soundmodes is shown.

*Solution:* Manually hide Soundmodes that are not supported in the integration configuration.

If you want your receiver added to the list of models with known soundmodes start a [discussion](https://github.com/mvdwetering/yamaha_ynca/discussions) or [submit an issue](https://github.com/mvdwetering/yamaha_ynca/issues)


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
