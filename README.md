# Yamaha YNCA

Minimum required Home Assistant version is: 2025.2.0

* [About Yamaha (YNCA)](#description)
* [Working models](#working-models)
* [Features](#features)
  * [Overview](#overview)
  * [Volume (dB) entity](#volume-db-entity)
  * [Presets](#presets)
  * [Remote entity](#remote-entity)
* [Downloading](#downloading)
  * [Home Assistant Community Store (HACS)](#home-assistant-community-store-hacs)
  * [Manual download](#manual-download)
* [Configuration](#configuration)
* [Removal](#removal)
* [Actions](#actions)
  * [Action yamaha_ynca.store_preset](#action-yamaha_yncastore_preset)
  * [Action yamaha_ynca.send_raw_ynca](#action-yamaha_yncasend_raw_ynca)
* [Q & A](#q--a)
* [Development notes](#development-notes)

## Description

Yamaha (YNCA) is a custom integration for Home Assistant to support [Yamaha AV receivers](https://uk.yamaha.com/en/audio/home-audio/products/av-receivers-amps/) that support the YNCA protocol (serial and network).

For issues or feature requests please [submit an issue on Github](https://github.com/mvdwetering/yamaha_ynca/issues)

## Working models

Yamaha does not mention in the manuals if a model supports the YNCA protocol that this integration uses. The table of working models below is based on reports from users and info found on the internet. Model years were taken from the [Yamaha AVR model history page](https://kane.site44.com/Yamaha/Yamaha_AVR_model_history.html).

Based on this information, receivers in the mentioned series from 2010 onwards are likely to work. So even if your model is not listed, just give it a try.

If your receiver works but is not in the list, please post a message in the [discussions](https://github.com/mvdwetering/yamaha_ynca/discussions) so it can be added.

| Year | Series | Models |
| --- | --- | --- |
| 2010 | AVENTAGE | RX-A700, RX-A800, RX-A1000, RX-A2000, RX-A3000 |
| | RX-V | RX-V867, RX-V1067, RX-V2067, RX-V3067 |
| | HTR | HTR-8063 |
| 2011 | AVENTAGE | RX-A710, RX-A810, RX-A1010, RX-A2010, RX-A3010 |
| | RX-V | RX-V671, RX-V771, RX-V871, RX-V1071, RX-V2071, RX-V3071 |
| | HTR | HTR-6064 |
| 2012 | AVENTAGE | RX-A720, RX-A820, RX-A1020, RX-A2020, RX-A3020 |
| | RX-V | RX-V473, RX-V573, RX-V673, RX-V773 |
| | HTR | HTR-4065, HTR-7065 |
| 2013 | AVENTAGE | RX-A730, RX-A830, RX-A1030, RX-A2030, RX-A3030 |
| | RX-V | RX-V475, RX-V575, RX-V675, RX-V775, RX-V1075, RX-V2075, RX-V3075 |
| | HTR | HTR-4066 |
| | Other | CX-A5000, R-N500, RX-V500D, RX-S600D |
| 2014 | AVENTAGE | RX-A740, RX-A840, RX-A1040, RX-A2040, RX-A3040 |
| | RX-V | RX-V477, RX-V677, RX-V777, RX-V1077, RX-V2077, RX-V3077 |
| 2015 | AVENTAGE | RX-AS710D, RX-A750, RX-A850, RX-A2050, RX-A3050 |
| | RX-V | RX-V679 |
| | Other | CX-A5100, RX-S601D |
| 2016 | AVENTAGE | RX-A660 |
| | RX-V | RX-V481D, RX-V581, RX-V681 |
| | TSR | TSR-7810 |
| | Other | WXC-50 |
| 2017 | AVENTAGE | RX-A870, RX-A2070, RX-A3070 |
| | RX-V | RX-V483, RX-V683 |
| | HTR | HTR-4071 |
| 2018 | AVENTAGE | RX-A880, RX-A3080 |
| | RX-V | RX-V585, RX-V685, RX-V1085 |
| | HTR | HTR-4072 |
| | TSR | TSR-7850 |
| | Other | CX-A5200 |
| 2020 | AVENTAGE | RX-A2A, RX-A4A, RX-A6A |
| | RX-V | RX-V4A, RX-V6A |
| | TSR | TSR-700 |

## Features

### Overview

* Full UI support for adding devices
* Connect through serial cable, TCP/IP network or any [URL handler supported by PySerial](https://pyserial.readthedocs.io/en/latest/url_handlers.html)
* Local Push, so updates are instant
* Support for zones (each zone is a device in Home Assistant)
* Power on/off
* Mute/Unmute
* Volume control
  * Standard Home Assistant media player
  * Separate [number entity with Volume in dB](#volume-db-entity)
* Source selection
  * Source names are taken from the receiver if provided
  * External inputs: AUDIO1-AUDIO5, AV1-AV7, DOCK, HDMI1-HDMI7, MULTI CH, OPTICAL1-OPTICAL2, PHONO, TV, USB, V-AUX
  * Media sources: AirPlay, Bluetooth, Deezer, iPod, iPod (USB), MusicCast Link, Napster, NET RADIO, Pandora, PC, Rhapsody, SERVER, SIRIUS, SIRIUS InternetRadio, SiriusXM, Spotify, TIDAL, TUNER (AM/FM or DAB/FM), UAW, USB
  * Other: Main Zone Sync
* Soundmode selection
* Control playback state (depends on source)
* Provide metadata like artist, album, song (depends on source)
* Activate scenes with button entities like the buttons on the front panel
* Select and store [Presets](#presets) for radio or other sources
* Send [remote control commands and IR codes](#remote-entity)
* Several controllable settings (if supported by receiver):
  * Adaptive DRC enable/disable
  * CINEMA DSP 3D mode enable/disable
  * Compressed Music Enhancer enable/disable
  * Direct / Pure Direct enable/disable
  * HDMI Out enable/disable
  * Initial volume
  * Max volume level
  * Sleep timer
  * Surround:AI enable/disable
  * Surround Decoder selection
  * Speaker pattern selection
  * Headphone bass/treble (default disabled)
  * Speaker bass/treble (default disabled)

### Volume (dB) entity

The "Volume (dB)" entity was added to simplify volume control in Home Assistant. It is a number entity that controls the volume of a zone, like the volume in the media_player, but using the familiar dB unit instead of the percent numbers.

<details>
<summary>
Background
</summary>

The volume of a `media_player` entity in Home Assistant has to be in the range 0-to-1 (shown as 0-100% in the dashboard). The range of a Yamaha receiver is typically -80.5dB to 16.5dB and is shown in the dB unit on the display/overlay. To provide the full volume range to Home Assistant this integration maps the full dB range onto the 0-to-1 range in Home Assistant. However, this makes controlling volume in Home Assistant difficult because the Home Assistant numbers are not easily convertible to the dB numbers as shown by the receiver.
</details>

### Presets

Presets can be activated and stored with the integration for some sources that support it. The AM/FM or DAB radio input seems to work for all models. Other sources that may support presets on some models include: Napster, Netradio, Pandora, PC, Rhapsody, Sirius, SiriusIR, and USB. Presets for these sources seem to work only on pre‑2012 models. The integration will auto‑detect whether presets are supported for available sources.

Presets can be selected in the mediabrowser of the mediaplayer or in automations with the `media_player.play_media` action. When selecting a preset, the receiver will turn on and switch input if needed.

Due to limitations on the protocol the integration can only show the preset number, no name or what is stored.

#### Manage presets

Some presets can be managed in the Yamaha AV Control app (e.g. Tuner presets). But you can also store them from within Home Assistant with the [store_preset action](#action-yamaha_yncastore_preset)

#### Media content format

In some cases it is not possible to browse for presets in the UI and it is needed to manually provide the `media_content_id` and `media_content_type`.

The `media_content_type` is always "music". The `media_content_id` format is listed in the table below. Replace the "1" at the end with the preset number you need.

| Input         | Content ID                        |
|---------------|-----------------------------------|
| Napster       | napster:preset:1                  |
| Netradio      | netradio:preset:1                 |
| Pandora       | pandora:preset:1                  |
| PC            | pc:preset:1                       |
| Rhapsody      | rhap:preset:1                     |
| Sirius        | sirius:preset:1                   |
| SiriusIR      | siriusir:preset:1                 |
| Tuner (AM/FM) | tun:preset:1                      |
| Tuner (DAB), FM presets | dab:fmpreset:1          |
| Tuner (DAB), DAB presets | dab:dabpreset:1        |
| USB           | usb:preset:1                      |

### Remote entity

The remote entity allows sending remote control codes and commands to the receiver. There is a remote entity for each zone.

The current list of commands is below, check the "commands" attribute of the remote entity for the most up-to-date version. Note that this command list does not take zone capabilities into account, just that there is a known remote control IR code for that command.

> on, standby, receiver_power_toggle, source_power_toggle, info, scene_1, scene_2, scene_3, scene_4, on_screen, option, up, down, left, right, enter, return, display, top_menu, popup_menu, stop, pause, play, rewind, fast_forward, previous, next, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, +10, ent

More remote control commands exist, but for now the commands included are the ones that are not available on the normal entities or that are potentially useful in other ways. E.g. sending `scene_1` can be used as a workaround for unsupported scene command on some receivers and commands like `play` are forwarded over HDMI-CEC so it allows you to control devices that do not have an API otherwise. More commands can be added later if more use cases are discovered.

Next to sending the predefined commands it is possible to send IR codes directly in case you need to send something that is not in the commands list. The Yamaha IR commands are NEC commands and consist of 4, 6 or 8 hexadecimal digits. For example the `on` command for the main zone has IR code `7E81-7E81`. The separator is optional. Because each IR code includes the zone it is possible to send an IR code through any of the remote entities.

Sending the commands and IR codes is done through the `remote.send_command` action offered by Home Assistant. For manual experimentation, go to the Actions tab of the Developer Tools in Home Assistant. Select the device or entity, enter the command or IR code you want to send and perform the action. The hold option is *not* supported because the protocol does not support it.

Example:

```yaml
action: remote.send_command
target:
  entity_id: remote.rx_a810_main_remote
data:
  command: receiver_power_toggle
```

In case you want to have buttons on a dashboard to send the commands the code below can be used as a starting point. It uses only standard built-in Home Assistant cards, so it should work on all configurations.

![image](https://github.com/mvdwetering/yamaha_ynca/assets/732514/321181e2-81c3-4a1d-8084-8efceb94f7ff)

<details>
<summary>Code for the grid with buttons for remote control commands.</summary>

On a dashboard, add a "manual" card. Paste the code below and search and replace the `entity_id` with your own.

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

## Downloading

### Home Assistant Community Store (HACS)

*Recommended because you get notified of updates.*

> HACS is a third-party downloader for Home Assistant to easily install and update custom integrations made by the community. See <https://hacs.xyz/> for more details.

You can add the repository to HACS on your Home Assistant instance with the button below

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mvdwetering&repository=yamaha_ynca&category=integration)

If the button does not work, or you don't want to use it, follow these steps to add the integration to HACS manually.

<details>
<summary>Manual HACS configuration steps</summary>

* Go to your Home Assistant instance
* Open the HACS page
* Search for "Yamaha (YNCA)" in the HACS search bar
* Click/tap on the integration to open the integration page
* Press the Download button to download the integration
* **Restart Home Assistant**

</details>

### Manual download

* Go to the [releases section on Github](https://github.com/mvdwetering/yamaha_ynca/releases)
* Download the zip file for the version you want to install
* Extract the zip
* Ensure the `config/custom_components/yamaha_ynca` directory exists (create it if needed)
* Copy the files from the zip into the `config/custom_components/yamaha_ynca` directory
* **Restart Home Assistant**

## Configuration

To add the Yamaha (YNCA) integration to your Home Assistant instance use this My button:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=yamaha_ynca)

If the above My button doesn’t work, you can also perform the following steps manually

<details>
<summary>Manual configuration steps</summary>

* Go to Settings > Devices & Services.
* Press the "Add Integration" button
* Select the "Yamaha (YNCA)" integration from the list
* Follow the instructions on screen to complete the setup

</details>

<br/>

> After initial configuration, check the integration options (sound modes, inputs, etc.) to match your receiver; not everything can be autodetected.
>
> You can access the integration options via the cogwheel⚙️ on `Settings > Devices & Services > Yamaha (YNCA) > Your Receiver`.

## Removal

This integration follows standard integration removal. No extra steps are required.

Go to "Settings > Devices & Services".
Select Yamaha (YNCA). Click the three dots ⋮ menu and then select Delete.

## Actions

### Action yamaha_ynca.store_preset

Store the currently playing media as a preset with the provided `preset_id`. This will only work for sources that support presets. See the [Presets section](#presets) for more details.

```yaml
action: yamaha_ynca.store_preset
target:
  entity_id: media_player.rx_a810_main
data:
  preset_id: 12
```

### Action yamaha_ynca.send_raw_ynca

This action allows sending raw YNCA commands. It is intended for debugging only.

```yaml
action: yamaha_ynca.send_raw_ynca
target:
  entity_id: media_player.rx_a810_main
data:
  raw_data: "@MAIN:INP=HDMI3"
```

## Q & A

* **Q: Why are entities unavailable when receiver is in standby?**  
  The receiver does not allow changing of settings when it is in standby, so the entities become Unavailable in Home Assistant to indicate this.

* **Q: Why does the integration not show all features mentioned in the README even when my receiver supports them?**  
  The integration tries to autodetect as many features as possible, but it is not possible for all features on all receivers. You can adjust detected/supported features for your receiver in the integration configuration.
  
  It can also be that your receiver does not expose that feature.
  
  You can open an issue if you believe it is supposed to be supported on your receiver.

* **Q: How can I stream audio from a URL?**  
  You can't do that with this integration because the protocol does not support that. You might be able to use the [DLNA Digital Media Renderer integration](https://www.home-assistant.io/integrations/dlna_dmr/) that comes with Home Assistant.

* **Q: Why are Scene buttons not working for my receiver?**  
  On some receivers (e.g. RX-V475) the command to activate the scenes does not work even though the receiver seems to indicate support for them. There might be more receivers with this issue, please report them in an issue or start a discussion.

  The non-working buttons can be disabled in the integration configuration by selecting "0" for number of scenes instead of "Auto detect".

  As a workaround the scenes can be activated by sending the scene commands by performing the `remote.send_command` action on the [Remote entity](#remote-entity).

```yaml
action: remote.send_command
target:
  entity_id: remote.rx_v475_main_remote
data:
  command: scene_1
```

## Development notes

Just a quick reminder on how to set up the development environment.

```bash
$ python3.13 -m venv venv
. ./venv/bin/activate
(venv) $ pip install -e .[dev]
```

Some useful commands

```bash
(venv) $ mypy --check-untyped-defs custom_components
(venv) $ pytest
(venv) $ ruff format
```
