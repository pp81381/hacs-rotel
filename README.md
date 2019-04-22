# hassdev

My Home Assistant customisations

## rotel_rsp1570

This is a media player custom component that can control a Rotel RSP-1570 processor

The component utilises the [rsp1570serial](https://pypi.org/project/rsp1570serial-pp81381/) library on PyPi for communications with the device

### Configuration

Take a look at configuration.yaml and groups.yaml in the .homeassistant folder for usage examples.

Here is a basic example of the configuration.yaml entry needed:

```
media_player:
- platform: rotel_rsp1570
  device: /dev/ttyUSB0
  source_aliases:
    TUNER:
    TAPE:
    MULTI:
    VIDEO 1: CATV
    VIDEO 2: NMT
    VIDEO 3: APPLE TV
    VIDEO 4: FIRE TV
    VIDEO 5: BLU RAY
```

Obviously the `device` parameter needs to match your own environment.   Some examples might be:

* `/dev/ttyUSB0` (Linux)
* `COM3` (Windows)
* `socket://192.168.0.100:50000` (if you are using a TCP/IP to serial  converter)

The parameter `source_aliases` allows the media player source list to be customised.   The keys must be from the following set:

```
' CD'
MULTI
TAPE
TUNER
VIDEO 1
VIDEO 2
VIDEO 3
VIDEO 4
VIDEO 5
```

The values in `source_aliases` should ideally exactly match the source names for any inputs that have custom names.   A blank value will cause the corresponding source to be suppressed from the media player source list.

The sample configuration file also demonstrates how to access the granular state of the device via template sensor and binary template sensor elements.

Note that the state of the media player component is set by messages received from the device.
* When you start Home Assistant it is assumed that the device is turned off.  If that isn't the case then any device activity will be enough for the component to align with the device.  If you click the POWER_ON button and the device is already on then that will be enough for the component to work it out.
* If the device state is changed externally (perhaps by the remote) then Home Assistant will keep in sync with it.

If you want to see a bit more about what's going on then add the following to configuration.yaml

```
logger:
  default: info
  logs:
    custom_components.rotel_rsp1570.media_player: debug
```

### Services

The media player component offers the followiing services:

Service Name | Parameters | Description
-------------|------------|------------
`rotel_send_command`|`entity_id`, `command_name`|Send any RS-232 command to the media player
`rotel_reconnect`|`entity_id`|Reconnect to the media player

The `entity_id` parameter can be a single entity id, a comma separated list or the word `all`.

Examples of parameters for `rotel_send_command`
```
{"entity_id": "media_player.rotel_rsp_1570_emulator", "command_name": "ZONE_2_SOURCE_VIDEO_1"}

{"entity_id": ["media_player.rotel_rsp_1570_emulator","media_player.rotel_rsp_1570"], "command_name": "VOLUME_UP"}

{"entity_id": "all", "command_name": "MUTE_TOGGLE"}
```

Examples of parameters for `rotel_reconnect`:
```
{"entity_id": "media_player.rotel_rsp_1570"}
```

See `services.yaml` for more information.

### Infra Red Control

My Raspberry Pi has an IR Hat so I can use lirc to trigger Home Assistant automations.

I chose a random remote control from the lirc remotes database and then configured my Harmony Hub with the same device.   Now I can use this fake remote to control Home Assistant as part of a Harmony activity.

Please see .lircrc and automations.yaml for my PoC configuration.    Plus, you need to add the following into your configuration.yaml file:
```
lirc:
```

