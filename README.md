## rotel

This is a media player custom component that can control a Rotel RSP-1570 or RSP-1572 processor

The component utilises the [rsp1570serial](https://pypi.org/project/rsp1570serial-pp81381/) library on PyPi for communications with the device

### Configuration

Here is a basic example of the `configuration.yaml` entry needed:

```yaml
media_player:
- platform: rotel
  unique_id: rotel_rsp1570
  device: /dev/ttyUSB0
```

Here is a more advanced example:

```yaml
media_player:
- platform: rotel
  name: My Rotel
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

The default model is the RSP-1570.  To specify the model explicitly, use this alternate format:

```yaml
media_player:
- platform: rotel
  unique_id: rotel_rsp1572
  name: My Rotel RSP-1572
  device: socket://192.168.0.100:50000
  model_spec:
    model: rsp1572
    source_aliases:
      TUNER:
      MULTI:
      VIDEO 1: CATV
      VIDEO 2: NMT
      VIDEO 3: APPLE TV
      VIDEO 4: FIRE TV
      VIDEO 5: BLU RAY
      VIDEO 6: SAT
      iPod/USB: IPOD
```

The `unique_id` parameter is required by HA

A `name` parameter is optional.   The "slugified" name will be used as the basis for the names of all of the states associated with the entity.   The default is "Rotel RSP-1570" which will result in states prefixed with `media_player.rotel_rsp_1570`.

Obviously the `device` parameter needs to match your own environment.   Some examples might be:

| Context                      | Serial Port Parameter              |
|------------------------------|------------------------------------|
| Linux port                   | `/dev/ttyUSB0`                     |
| Windows port                 | `COM3`                             |
| TCP/IP to serial  converter  | `socket://192.168.0.100:50000`     |

The parameter `source_aliases` is an *optional* argument that allows the media player source aliases to be customised.  This is important for Home Assistant to recognise which source the receiver is set to.  It should be a dictionary that maps the standard source ID to the source alias defined in the receiver.

If this parameter is specified at the top level of the configuration then the receiver model is assumed to be an RSP-1570. See the table in the section on `model_spec` for the list of valid standard source IDs.

The values in `source_aliases` must exactly match the custom names for any inputs that have custom names.   A blank value will cause the corresponding source to be suppressed from the media player source list if it isn't used.   If a default source isn't aliased or suppressed then it will use the standard name.

The parameter `model_spec` is an optional dictionary argument that allows a model and any model specific configuration to be specified.   If `model_spec` is defined at the top level then `source_aliases` cannot be defined at the top level (because the valid sources are model-specific).

Within `model_spec`, the following keys are valid:

* `model` (required) should be either `rsp1570` or `rsp1572`
* `source_aliases` (optional) defines the source aliases.  See the table below for the list of valid sources for each model.

| Model | Standard Source IDs |
|----|----|
| rsp1570 | ' CD', MULTI, TAPE, TUNER, VIDEO 1, VIDEO 2, VIDEO 3, VIDEO 4, VIDEO 5 |
| rsp1572 | ' CD', MULTI, TUNER, VIDEO 1, VIDEO 2, VIDEO 3, VIDEO 4, VIDEO 5, VIDEO 6, iPod/USB |

Note that the Source IDs are case sensitive and also that the quoting and space-prefix of the source ' CD' is intentional.

### Logging Configuration

If you want to see a bit more about what's going on then add the following to configuration.yaml

```yaml
logger:
  default: info
  logs:
    custom_components.rotel.media_player: debug
    rsp1570serial: debug
```

### Notes

Note that the state of the media player component is set by messages received from the device.
* When you start Home Assistant it is assumed that the device is turned off.  If that isn't the case then any device activity will be enough for the component to align with the device.  If you click the POWER_ON button and the device is already on then that will be enough for the component to work it out.
* If the device state is changed externally (perhaps by the remote) then Home Assistant will keep in sync with it.

### Services

The media player component offers the followiing services:

Service Name | Parameters | Description
-------------|------------|------------
`rotel_send_command`|`entity_id`, `command_name`|Send a command to the media player.   See [rsp1570_messages.py](https://github.com/pp81381/rsp1570serial/blob/master/rsp1570serial/rsp1570_messages.py) or [rsp1572_messages.py](https://github.com/pp81381/rsp1570serial/blob/master/rsp1570serial/rsp1572_messages.py) in the [rsp1570serial](https://github.com/pp81381/rsp1570serial) GitHub project for a full list of available commands.
`rotel_reconnect`|`entity_id`|Reconnect to the media player

The `entity_id` parameter can be a single entity id, a comma separated list or the word `all`.

Examples of parameters for `rotel_send_command`
```json
{"entity_id": "media_player.rotel_rsp_1570_emulator", "command_name": "ZONE_2_SOURCE_VIDEO_1"}

{"entity_id": ["media_player.rotel_rsp_1570_emulator","media_player.rotel_rsp_1570"], "command_name": "VOLUME_UP"}

{"entity_id": "all", "command_name": "MUTE_TOGGLE"}
```

Examples of parameters for `rotel_reconnect`:
```json
{"entity_id": "media_player.rotel_rsp_1570"}
```

See `services.yaml` for more information.

Note that `services.yaml` provides a list of valid values for `command_name` in order to make the `rotel_send_command` service easier to use from the Home Assistant front end.  This list is the union of all valid RSP-1570 and RSP-1572 commands because it can't be made dynamic.   If an attempt is made to send a command to the wrong model then it will simply be ignored.  See [rsp1570_messages.py](https://github.com/pp81381/rsp1570serial/blob/master/rsp1570serial/rsp1570_messages.py) or [rsp1572_messages.py](https://github.com/pp81381/rsp1570serial/blob/master/rsp1570serial/rsp1572_messages.py) in the [rsp1570serial](https://github.com/pp81381/rsp1570serial) GitHub project for a full list of supported commands for each model.

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