# Yamaha YNCA

- [Description](#description)
- [Features](#features)
- [Installation](#installation)
- [Volume (dB) entity](#volume-db-entity)
- [Remote control](#remote-control)
- [Q & A](#q--a)

## Description

Custom integration for Home Assistant to support Yamaha AV receivers with the YNCA protocol (serial and network).

According to reports of users and info found on the internet the following AV receivers should be working, there are probably more, just give it a try. If your receiver works and is not in the list please post a message in the [discussions](https://github.com/mvdwetering/yamaha_ynca/discussions) so the list can be updated.

> HTR-4065, HTR-4071, HTR-6064, RX-A660, RX-A700, RX-A710, RX-A720, RX-A740, RX-A750, RX-A800, RX-A810, RX-A820, RX-A830, RX-A840, RX-A850, RX-A1000, RX-A1010, RX-A1020, RX-A1030, RX-A1040, RX-A2000, RX-A2010, RX-A2020, RX-A2070, RX-A3000, RX-A3010, RX-A3020, RX-A3030, RX-A3070, RX-S600D, RX-V475, RX-V477, RX-V481D, RX-V483, RX-V575, RX-V671, RX-V673, RX-V675, RX-V677, RX-V679, RX-V681, RX-V771, RX-V773, RX-V775, RX-V777, RX-V867, RX-V871, RX-V1067, RX-V1071, RX-V1085, RX-V2067, RX-V2071, RX-V3067, RX-V3071, TSR-700, TSR-7850

In case of issues or feature requests please [submit an issue on Github](https://github.com/mvdwetering/yamaha_ynca/issues)


## Features

* Full UI support for adding devices
* Connect through serial, IP or any [URL handler supported by PySerial](https://pyserial.readthedocs.io/en/latest/url_handlers.html)
* Support for zones
* Power on/off
* Volume control and mute
* Source selection
* Soundmode selection
* Show metadata like artist, album, song (depends on source)
* Control playback (depends on source)
* Activate scenes
* Send remote control commands
* Several controllable settings (if supported by receiver):
  * CINEMA DSP 3D mode
  * Adaptive DRC
  * Compressed Music Enhancer
  * HDMI Out enable/disable
  * Initial volume
  * Max volume
  * Sleep timer
  * Speaker bass/treble (default disabled)
  * Headphone bass/treble (default disabled)
  * Surround Decoder
  * Pure Direct

## Installation

### Home Assistant Community Store (HACS)

*Recommended as you get notified of updates.*

HACS is a 3rd party downloader for Home Assistant to easily install and update custom integrations made by the community. More information and installation instructions can be found on their site https://hacs.xyz/

* Add integration within HACS (use the + button and search for "YNCA")
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)". You might need to clear the browser cache for it to show up (e.g. reload with CTRL+F5).

### Manual

* Install the custom component by downloading the zipfile from the releases.
* Extract the zip and copy the contents to the `custom_components` directory.
* Restart Home Assistant
* Go to the Home Assistant integrations menu and press the Add button and search for "Yamaha (YNCA)". You might need to clear the browser cache for it to show up (e.g. reload with CTRL+F5).

## Volume (dB) entity

The volume of a `media_player` entity in Home Assistant has to be in the range 0-to-1. The range of a Yamaha receiver is typically -80.5dB to 16.5dB and is shown in dB unit on the display. This integration maps the full dB range onto the 0-to-1 range in Home Assistant. But this makes setting volume in Home Assistant difficult as those Home Assistant numbers are not easily convertible to the dB numbers shown by the receiver.

The "Volume (dB)" entity was added to work around this. It is basically the same as the `media_player` volume, but using the familiar dB values that the receiver shows.

## Remote control

The remote control entity allows sending remote control codes and commands to the receiver. There is remote entity for each zone. Some remote commands are forwarded through HDMI-CEC and can be used to control other devices that way. I guess the commands are also sent over the remote out of the receiver, but that needs to be validated by someone that has equipment connected to the remote out port.

The current list of commands is below. For the list of supported commands for a specific entity check the "commands" attribute of the remote entity. Note that this command list does not take zone capabilities into account, just that there is a known remote control code for that command.

> on, standby, receiver_power_toggle, source_power_toggle, info, scene_1, scene_2, scene_3, scene_4, on_screen, option, up, down, left, right, enter, return, display, top_menu, popup_menu, stop, pause, play, rewind, fast_forward, previous, next, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, +10, ent"

More remote control commands exist, but for now the commands included are the ones that are not available on the normal entities or that are potentially useful in other ways. E.g. sending `scene_1` might be usable as a workaround for unsupported scene command on some receivers and commands like `play` are forwarded over HDMI-CEC so it allows you to control devices that do not have an API otherwise. More can be added later if more use cases are discovered.

Next to sending the predefined commands it is possible to send IR codes directly in case you want to send something that is not in the commands list. The Yamaha IR commands are NEC commands and are 4, 6 or 8 characters long. E.g. the `on` command for the main zone has code `7E81-7E81`. The separator is optional. Since each code includes the zone it is possible to send a code through any of the remote entities.

Sending the commands is done through the `remote.send_command` service offered by Home Assistant. For manualy experimentation use the Developer Tools in Home Assistant. Select the device or entity and type the command or IR code you want send and call the service. The repeat, delay and hold options are _not_ supported. 

Example:

```yaml
service: remote.send_command
data:
  command: receiver_power_toggle
target:
  entity_id: remote.rx_a810_main_remote
```


In case you want to have buttons on a dashboard to send the commands the code below can be used as a starting point. It uses only standard built-in Home Assistant cards, so should work everywhere. 

On a dashboard add a "manual" card. Paste the code below and search and replace the `entity_id` with your own.

<details>
<summary>Grid with buttons for remote control commands.</summary>

![image](https://github.com/mvdwetering/yamaha_ynca/assets/732514/321181e2-81c3-4a1d-8084-8efceb94f7ff)

```yaml
type: vertical-stack
cards:
  - square: false
    columns: 2
    type: grid
    cards:
      - show_name: true
        show_icon: false
        type: button
        name: 'ON'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: 'on'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: STANDBY
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: standby
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: RECEIVER POWER
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: receiver_power_toggle
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: SOURCE POWER
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: source_power_toggle
          target:
            entity_id: remote.rx_a810_main_remote
  - square: true
    columns: 4
    type: grid
    cards:
      - type: button
        show_icon: false
        name: SCENE 1
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: scene_1
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: SCENE 2
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: scene_2
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: SCENE 3
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: scene_3
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: SCENE 4
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: scene_4
          target:
            entity_id: remote.rx_a810_main_remote
  - square: false
    columns: 3
    type: grid
    cards:
      - type: button
        show_icon: false
        name: ON SCREEN
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: on_screen
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:arrow-up-bold
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: up
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: OPTION
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: option
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:arrow-left-bold
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: left
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: ENTER
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: enter
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:arrow-right-bold
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: right
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: RETURN
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: return
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:arrow-down-bold
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: down
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: DISPLAY
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: display
          target:
            entity_id: remote.rx_a810_main_remote
  - square: false
    columns: 2
    type: grid
    cards:
      - show_name: true
        show_icon: false
        type: button
        name: TOP MENU
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: top_menu
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: POPUP MENU
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: popup_menu
          target:
            entity_id: remote.rx_a810_main_remote
  - square: false
    columns: 4
    type: grid
    cards:
      - type: button
        show_icon: false
        name: INFO
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: info
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:stop
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: stop
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:pause
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: pause
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:play
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: play
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:rewind
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: rewind
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:fast-forward
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: fast_forward
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:skip-backward
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: previous
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        icon: mdi:skip-forward
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: next
          target:
            entity_id: remote.rx_a810_main_remote
  - square: false
    columns: 4
    type: grid
    cards:
      - type: button
        show_icon: false
        name: '1'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '1'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '2'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '2'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '3'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '3'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '4'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '4'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '5'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '5'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '6'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '6'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '7'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '7'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '8'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '8'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '9'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '9'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '0'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '0'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: '+10'
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: '+10'
          target:
            entity_id: remote.rx_a810_main_remote
      - type: button
        show_icon: false
        name: ENT
        tap_action:
          action: call-service
          service: remote.send_command
          data:
            command: ent
          target:
            entity_id: remote.rx_a810_main_remote
```
</details>

## Q & A

* **Q: Why are entities unavailable when receiver in standby?**  
  The receiver does not allow changing of settings when it is in standby, so the entities become Unavailable in Home Assistant to indicate this.

* **Q: Why are the Scene buttons are not created automatically?**  
  It is not possible to autodetect the amount of supported scenes on all receivers. If no scene buttons are created and the Zone does support scenes you can specify the amount of scenes manually in the integration configuration.

* **Q: Why are Scene buttons are not working?**  
  On some receivers (e.g. RX-V475 with firmware 1.34/2.06) the command to activate the scenes does not work even though the receiver indicates support for them. There might be more receivers with this issue, please report them in an issue or start a discussion.

  It might be possible to send scene commands using the remote entity as a workaround.
  _Please drop a message in the [discussions](https://github.com/mvdwetering/yamaha_ynca/discussions) if this actually works as I don't have an RX-V475 to test with._

* **Q: Why do the sources not match receiver zone capabilities?**  
  It is not possible to detect which sources are supported per zone, only for the whole receiver. In the integration configuration it is possible to select which sources are avaialble per Zone.

  If a source is not listed at all it might not be supported or could be a bug, [submit an issue](https://github.com/mvdwetering/yamaha_ynca/issues) in that case.

* **Q: Why do the soundmodes not match the ones supported by the receiver**  
  The list of supported soundmodes can not be detected, for some models the list is known, for the rest the whole list of known soundmodes is shown.
  You can select the soundmodes that are supported by your receiver in the integration configuration.

  If you want your receiver added to the list of models with known soundmodes start a [discussion](https://github.com/mvdwetering/yamaha_ynca/discussions) or [submit an issue](https://github.com/mvdwetering/yamaha_ynca/issues)

* **Q: How can I fix the connection settings if the connection is not working?**  
  When the integration can not connect to the receiver (e.g. due to changed IP address) you can use the "Configure" button on the integration card. A dialog will appear with a message that it can't connect. Press "Submit" in this dialog to mark the integration for reconfiguration. Home Assistant will now allow you to reconfigure the integration (reload of the page in the browser seems required to show the reconfigure card).

* **Q: How can I stream audio?**  
  You can't with integration since the protocol does not support that. You might be able to use the "DLNA Digital Media Renderer" that comes with Home Assistant.

