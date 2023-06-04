# Yamaha YNCA

Custom integration for Home Assistant to support Yamaha AV receivers with the YNCA protocol (serial and IP).

According to reports of users and info found on the internet the following AV receivers should be working (not all tested), there might be more. If your receiver works and is not in the list please post a message in the [discussions](https://github.com/mvdwetering/yamaha_ynca/discussions).

> RX-A700, RX-A710, RX-A720, RX-A740, RX-A800, RX-A810, RX-A820, RX-A840, RX-A850, RX-A1000, RX-A1010, RX-A1020, RX-A1030, RX-A1040, RX-A2000, RX-A2010, RX-A2020, RX-A2070, RX-A3000, RX-A3010, RX-A3020, RX-V475, RX-V477, RX-V671, RX-V673, RX-V675, RX-V677, RX-V771, RX-V773, RX-V777, RX-V867, RX-V871, RX-V1067, RX-V2067, RX-V3067, TSR-700, TSR-7850

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
  * Pure Direct


## FAQ

### Q: Some entities unavailable when receiver in standby

The receiver does not allow changing of settings when it is in standby, so the entities become Unavailable in Home Assistant to indicate this.

### Q: Scenes are not detected or not working

On newer receivers the autodetection of the amount of Scenes supported per zone does not work anymore, so no Scenes are detected.
For the RX-V475 with firmware 1.34/2.06 the command to activate the scenes does not work even though scenes seem to be supported by the receiver.

*Solution:* Override the autodetect and manually configure the amount of Scenes supported per zone in the integration configuration.

### Q: Sources list does not match receiver zone capabilities

For most receivers the total amount/type of inputs available on the receiver can be detected, but it is not possible to detect which of those inputs are available per zone.

*Solution:* Manually hide the sources that are not supported per zone in the integration configuration.

### Q: Soundmodes do not match receiver

The list of soundmodes can not be detected, for some models the list is known, for the rest the whole list of known soundmodes is shown.

*Solution:* Manually hide Soundmodes that are not supported in the integration configuration.

If you want your receiver added to the list of models with known soundmodes start a [discussion](https://github.com/mvdwetering/yamaha_ynca/discussions) or [submit an issue](https://github.com/mvdwetering/yamaha_ynca/issues)

### Q: How can I change the connection settings

When the integration can not connect to the receiver (e.g. due to changed IP address) you can use the "Configure" button on the integration card. A dialog appear with a message that it can't connect. Press "Submit" in this dialog to mark the integration for reconfiguration. Home Assistant will now allow you to reconfigure the integration (reload of the page in the browser seems required to show the reconfigure card).


## Installation

### Home Assistant Community Store (HACS)

*Recommended as you get notified of updates.*

HACS is a 3rd party downloader for Home Assistant to easily install and update custom integrations made by the community. More information and installation instructions can be found on their site https://hacs.xyz/

* Add integration within HACS (use the + button and search for "YNCA")
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)". You might need to clear the browser cache for it to show up (e.g. reload with CTRL+F5).

### Manual

* Install the custom component by downloading the zipfile from the release
* Extract the zip and copy the contents to the `custom_components` directory as usual.
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)". You might need to clear the browser cache for it to show up (e.g. reload with CTRL+F5).
