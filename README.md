## rotel

This is a media player custom component that can control a Rotel RSP-1570 processor

The component utilises the [rsp1570serial](https://pypi.org/project/rsp1570serial-pp81381/) library on PyPi for communications with the device

### Configuration

Here is a basic example of the `configuration.yaml` entry needed:

```
media_player:
- platform: rotel
  unique_id: rotel_rsp1570
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

The `unique_id` parameter is required by HA

A `name` parameter is optional.   The "slugified" name will be used as the basis for the names of all of the states associated with the entity.   The default is "Rotel RSP-1570" which will result in states prefixed with `media_player.rotel_rsp_1570`.

Obviously the `device` parameter needs to match your own environment.   Some examples might be:

* `/dev/ttyUSB0` (Linux)
* `COM3` (Windows)
* `socket://192.168.0.100:50000` (if you are using a TCP/IP to serial  converter)

The parameter `source_aliases` is an *optional* argument that allows the media player source list to be customised.   The keys must be from the following set:

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

The values in `source_aliases` should ideally exactly match the source names for any inputs that have custom names.   A blank value will cause the corresponding source to be suppressed from the media player source list.   If a default source isn't aliased or suppressed then it will appear as-is.

Note that the state of the media player component is set by messages received from the device.
* When you start Home Assistant it is assumed that the device is turned off.  If that isn't the case then any device activity will be enough for the component to align with the device.  If you click the POWER_ON button and the device is already on then that will be enough for the component to work it out.
* If the device state is changed externally (perhaps by the remote) then Home Assistant will keep in sync with it.

If you want to see a bit more about what's going on then add the following to configuration.yaml

```
logger:
  default: info
  logs:
    custom_components.rotel.media_player: debug
```

### Services

The media player component offers the followiing services:

Service Name | Parameters | Description
-------------|------------|------------
`rotel_send_command`|`entity_id`, `command_name`|Send a command to the media player.   See `commands.py` ([here](https://github.com/pp81381/rsp1570serial/blob/master/rsp1570serial/commands.py)) in the [rsp1570serial](https://github.com/pp81381/rsp1570serial) GitHub project for a full list of available commands.
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

### Setting up sensors and binary_sensors

A script is provided to simplify the creation of yaml configuration files that define sensor and binary sensor entities that will reflect the state of the device.

Usage of the script is summarised below.

```
usage: make_config.py [-h] [-F OUTPUT_FOLDER] [-l LEGACY_FILE_BASENAME] [-m MODERN_FILE_BASENAME] [-i ID_PREFIX] [-p LEGACY_NAME_PREFIX] [-P MODERN_NAME_PREFIX] [-e ENTITY_NAME]

options:
  -h, --help            show this help message and exit
  -F, --output-folder OUTPUT_FOLDER
  -l, --legacy-file-basename LEGACY_FILE_BASENAME
  -m, --modern-file-basename MODERN_FILE_BASENAME
  -i, --id-prefix ID_PREFIX
  -p, --legacy-name-prefix LEGACY_NAME_PREFIX
  -P, --modern-name-prefix MODERN_NAME_PREFIX
  -e, --entity-name ENTITY_NAME
  ```

The script will generate yaml for both legacy and modern template sensor definitions for all available device state information.  All parameters are optional and have sensible defaults.   Simply take the preferred file and remove any entries that aren't needed.

The legacy format looks like this:

```yaml
sensor:
- platform: template
    sensors:
      <id-prefix>_source:
        unique_id: uid_<id-prefix>-source
        friendly_name: "<legacy-name-prefix> Source"
        value_template: "{{ state_attr('<entity-name>', 'source') }}"
        icon_template: mdi:video-input-hdmi
```

The modern format looks like this:

```yaml
template:
  - unique_id: uid_<id-prefix>_modern
    sensor:
    - unique_id: source
      name: "<modern-name-prefix> Source"
      icon: mdi:video-input-hdmi
      state: "{{ state_attr('<entity-name>', 'source') }}"
```

The default settings for the legacy format should generate the same entity ids and names as were used in the example configuration that used to be provided with this custom component.

The generated yaml can simply be included in the main `configuration.yaml` file.  Another option is to leverage [Home Assistant Packages](https://www.home-assistant.io/docs/configuration/packages/).  Put the generated yaml into a folder called `packages` and then modify the `homeassistant` entry in `configuration.yaml` as follows:

```yaml
homeassistant:
  packages: !include_dir_named packages
```