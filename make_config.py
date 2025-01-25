import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, TextIO


@dataclass
class SensorDef:
    name: str
    state_name: str
    friendly_name: str
    icon_template: str


@dataclass
class BinarySensorDef:
    name: str
    uid_suffix: str
    state_name: str
    state_item: str
    friendly_name: str


SENSOR_DEFS = [
    SensorDef("source", "source", "Source", "mdi:video-input-hdmi"),
    SensorDef("volume", "display_volume", "Volume", "mdi:volume-high"),
    SensorDef("is_muted", "is_volume_muted", "Is Muted", "mdi:volume-mute"),
    SensorDef(
        "party_mode_on", "party_mode_on", "Party Mode", "mdi:emoticon-excited-outline"
    ),
    SensorDef("info", "info", "Info", "mdi:surround-sound"),
    SensorDef("icons", "icons", "Icons", "mdi:lightbulb-on-outline"),
]

BINARY_SENSOR_DEFS = [
    BinarySensorDef(
        "speaker_center_back_left",
        "speaker_cbl",
        "speaker_icons",
        "CBL",
        "Center Back Left",
    ),
    BinarySensorDef(
        "speaker_center_back_right",
        "speaker_cbr",
        "speaker_icons",
        "CBR",
        "Center Back Right",
    ),
    BinarySensorDef(
        "speaker_center_back", "speaker_cb", "speaker_icons", "CB", "Center Back"
    ),
    BinarySensorDef(
        "speaker_subwoofer", "speaker_sub", "speaker_icons", "SW", "Subwoofer"
    ),
    BinarySensorDef(
        "speaker_surround_right", "speaker_sr", "speaker_icons", "SR", "Surround Right"
    ),
    BinarySensorDef(
        "speaker_surround_left", "speaker_sl", "speaker_icons", "SL", "Surround Left"
    ),
    BinarySensorDef(
        "speaker_front_right", "speaker_fr", "speaker_icons", "FR", "Front Right"
    ),
    BinarySensorDef("speaker_center", "speaker_c", "speaker_icons", "C", "Center"),
    BinarySensorDef(
        "speaker_front_left", "speaker_fl", "speaker_icons", "FL", "Front Left"
    ),
    BinarySensorDef(
        "state_standby_led",
        "state_standby_led",
        "state_icons",
        "Standby LED",
        "Standby LED",
    ),
    BinarySensorDef("state_zone", "state_zone", "state_icons", "Zone", "Zone"),
    BinarySensorDef("state_zone2", "state_zone2", "state_icons", "Zone 2", "Zone 2"),
    BinarySensorDef("state_zone3", "state_zone3", "state_icons", "Zone 3", "Zone 3"),
    BinarySensorDef("state_zone4", "state_zone4", "state_icons", "Zone 4", "Zone 4"),
    BinarySensorDef(
        "state_display_mode0",
        "display_mode0",
        "state_icons",
        "Display Mode0",
        "Display Mode 0",
    ),
    BinarySensorDef(
        "state_display_mode1",
        "display_mode1",
        "state_icons",
        "Display Mode1",
        "Display Mode 1",
    ),
    BinarySensorDef(
        "sound_mode_pro_logic",
        "sound_mode_pro_logic",
        "sound_mode_icons",
        "Pro Logic",
        "Pro Logic",
    ),
    BinarySensorDef("sound_mode_ii", "sound_mode_ii", "sound_mode_icons", "II", "II"),
    BinarySensorDef("sound_mode_x", "sound_mode_x", "sound_mode_icons", "x", "x"),
    BinarySensorDef(
        "sound_mode_dolby_digital",
        "sound_mode_dolby_digital",
        "sound_mode_icons",
        "Dolby Digital",
        "Dolby Digital",
    ),
    BinarySensorDef(
        "sound_mode_dts", "sound_mode_dts", "sound_mode_icons", "dts", "dts"
    ),
    BinarySensorDef("sound_mode_es", "sound_mode_es", "sound_mode_icons", "ES", "ES"),
    BinarySensorDef("sound_mode_ex", "sound_mode_ex", "sound_mode_icons", "EX", "EX"),
    BinarySensorDef("sound_mode_51", "sound_mode_51", "sound_mode_icons", "5.1", "5.1"),
    BinarySensorDef("sound_mode_71", "sound_mode_71", "sound_mode_icons", "7.1", "7.1"),
    BinarySensorDef("input_hdmi", "input_hdmi", "input_icons", "HDMI", "HDMI"),
    BinarySensorDef(
        "input_coaxial", "input_coaxial", "input_icons", "Coaxial", "Coaxial"
    ),
    BinarySensorDef(
        "input_optical", "input_optical", "input_icons", "Optical", "Optical"
    ),
    BinarySensorDef("input_analog", "input_analog", "input_icons", "A", "Analog"),
    BinarySensorDef("input_1", "input_1", "input_icons", "1", "Input 1"),
    BinarySensorDef("input_2", "input_2", "input_icons", "2", "Input 2"),
    BinarySensorDef("input_3", "input_3", "input_icons", "3", "Input 3"),
    BinarySensorDef("input_4", "input_4", "input_icons", "4", "Input 4"),
    BinarySensorDef("input_5", "input_5", "input_icons", "5", "Input 5"),
    BinarySensorDef("misc_lt", "misc_lt", "misc_icons", "<", "Misc <"),
    BinarySensorDef("misc_gt", "misc_gt", "misc_icons", ">", "Misc >"),
]


def make_friendly_name(name_prefix: str, sensor_def: SensorDef | BinarySensorDef):
    return (
        f"{sensor_def.friendly_name}"
        if name_prefix == ""
        else f"{name_prefix} {sensor_def.friendly_name}"
    )


def write_legacy_sensor_def(
    fp: TextIO,
    sensor_def: SensorDef,
    id_prefix: str,
    name_prefix: str,
    entity_name: str,
):
    fp.write(
        f"""      {id_prefix}_{sensor_def.name}:
        unique_id: uid_{id_prefix}-{sensor_def.name}
        friendly_name: "{make_friendly_name(name_prefix, sensor_def)}"
        value_template: "{{{{ state_attr('{entity_name}', '{sensor_def.state_name}') }}}}"
        icon_template: {sensor_def.icon_template}
"""
    )


def write_legacy_binary_sensor_def(
    fp: TextIO,
    sensor_def: BinarySensorDef,
    id_prefix: str,
    name_prefix: str,
    entity_name: str,
):
    fp.write(
        f"""      {id_prefix}_{sensor_def.name}:
        unique_id: uid_{id_prefix}-{sensor_def.uid_suffix}
        friendly_name: "{make_friendly_name(name_prefix, sensor_def)}"
        value_template: >-
            {{{{ state_attr('{entity_name}', '{sensor_def.state_name}')['{sensor_def.state_item}'] == true }}}}
"""
    )


def write_legacy_sensor_defs(
    output_file: Path,
    sensor_defs: List[SensorDef],
    binary_sensor_defs: List[BinarySensorDef],
    id_prefix: str,
    name_prefix: str,
    entity_name: str,
):
    with open(output_file, "w") as fp:
        fp.write(
            f"""sensor:
- platform: template
    sensors:
"""
        )
        for sd in sensor_defs:
            write_legacy_sensor_def(fp, sd, id_prefix, name_prefix, entity_name)

        fp.write(
            f"""binary_sensor:
- platform: template
    sensors:
"""
        )
        for bsd in binary_sensor_defs:
            write_legacy_binary_sensor_def(fp, bsd, id_prefix, name_prefix, entity_name)


def write_modern_sensor_def(
    fp: TextIO,
    sensor_def: SensorDef,
    name_prefix: str,
    entity_name: str,
):
    fp.write(
        f"""    - unique_id: {sensor_def.name}
      name: "{make_friendly_name(name_prefix, sensor_def)}"
      icon: {sensor_def.icon_template}
      state: "{{{{ state_attr('{entity_name}', '{sensor_def.state_name}') }}}}"
"""
    )


def write_modern_binary_sensor_def(
    fp: TextIO,
    sensor_def: BinarySensorDef,
    name_prefix: str,
    entity_name: str,
):
    fp.write(
        f"""    - unique_id: {sensor_def.name}
      name: "{make_friendly_name(name_prefix, sensor_def)}"
      state: "{{{{ state_attr('{entity_name}', '{sensor_def.state_name}')['{sensor_def.state_item}'] == true }}}}"
"""
    )


def write_modern_sensor_defs(
    output_file: Path,
    sensor_defs: List[SensorDef],
    binary_sensor_defs: List[BinarySensorDef],
    id_prefix: str,
    name_prefix: str,
    entity_name: str,
):
    with open(output_file, "w") as fp:
        fp.write(
            f"""template:
  - unique_id: uid_{id_prefix}_modern
    sensor:
"""
        )
        for sd in sensor_defs:
            write_modern_sensor_def(fp, sd, name_prefix, entity_name)

        fp.write(
            f"""    binary_sensor:
"""
        )
        for bsd in binary_sensor_defs:
            write_modern_binary_sensor_def(fp, bsd, name_prefix, entity_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-F", "--output-folder", type=Path, default=".")
    parser.add_argument(
        "-l",
        "--legacy-file-basename",
        type=str,
        default="rotel_sensors_legacy.yaml",
    )
    parser.add_argument(
        "-m",
        "--modern-file-basename",
        type=str,
        default="rotel_sensors_modern.yaml",
    )
    parser.add_argument("-i", "--id-prefix", type=str, default="rsp1570")
    parser.add_argument("-p", "--legacy-name-prefix", type=str, default="")
    parser.add_argument("-P", "--modern-name-prefix", type=str, default="Rotel")
    parser.add_argument(
        "-e", "--entity-name", type=str, default="media_player.rotel_rsp_1570"
    )
    args = parser.parse_args()

    write_legacy_sensor_defs(
        args.output_folder / args.legacy_file_basename,
        SENSOR_DEFS,
        BINARY_SENSOR_DEFS,
        args.id_prefix,
        args.legacy_name_prefix,
        args.entity_name,
    )

    write_modern_sensor_defs(
        args.output_folder / args.modern_file_basename,
        SENSOR_DEFS,
        BINARY_SENSOR_DEFS,
        args.id_prefix,
        args.modern_name_prefix,
        args.entity_name,
    )
