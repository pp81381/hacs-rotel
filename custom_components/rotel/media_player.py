"""Rotel RSP-1570 media player platform."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import voluptuous as vol
from rsp1570serial.connection import RotelAmpConn
from rsp1570serial.messages import (
    AnyMessage,
    FeedbackMessage,
    SmartDisplayMessage,
    TriggerMessage,
)
from rsp1570serial.rotel_model_meta import (
    ROTEL_MODELS,
    RSP1570_MODEL_ID,
    RotelModelMeta,
)

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.const import (
    CONF_DEVICE,
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

DEFAULT_NAME = "Rotel RSP-1570"
DEFAULT_MODEL = RSP1570_MODEL_ID

_LOGGER = logging.getLogger(__name__)

CONF_MODEL_SPEC = "model_spec"
CONF_MODEL = "model"
CONF_SOURCE_ALIASES = "source_aliases"


def make_model_spec_schema(meta: RotelModelMeta) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MODEL): vol.Literal(meta.model_id),
            vol.Optional(CONF_SOURCE_ALIASES): vol.Schema(
                {vol.Any(*[m.standard_name for m in meta.sources]): vol.Any(str, None)}
            ),
        },
    )


def validate_model_spec(value: Any) -> dict:
    """Validate a model spec"""
    if not isinstance(value, dict):
        raise vol.Invalid("expected dictionary")
    model = value.get(CONF_MODEL, DEFAULT_MODEL)
    meta = ROTEL_MODELS[model]
    model_spec_schema = make_model_spec_schema(meta)
    return model_spec_schema(value)


ROTEL_SCHEMA = {
    vol.Required(CONF_DEVICE): cv.string,
    vol.Required(CONF_UNIQUE_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Exclusive(CONF_SOURCE_ALIASES, "model_spec"): {
        vol.Any(
            *[m.standard_name for m in ROTEL_MODELS[DEFAULT_MODEL].sources]
        ): vol.Any(str, None)
    },
    vol.Exclusive(CONF_MODEL_SPEC, "model_spec"): validate_model_spec,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(ROTEL_SCHEMA)

ATTR_DISPLAY_VOLUME = "display_volume"
ATTR_PARTY_MODE_ON = "party_mode_on"
ATTR_INFO = "info"
ATTR_ICONS = "icons"
ATTR_SPEAKER_ICONS = "speaker_icons"
ATTR_STATE_ICONS = "state_icons"
ATTR_INPUT_ICONS = "input_icons"
ATTR_SOUND_MODE_ICONS = "sound_mode_icons"
ATTR_MISC_ICONS = "misc_icons"
ATTR_TRIGGERS = "triggers"
ATTR_SMART_DISPLAY = "smart_display"  # RSP1572 only

ATTR_COMMAND_NAME = "command_name"
SERVICE_SEND_COMMAND = "rotel_send_command"
SERVICE_RECONNECT = "rotel_reconnect"

SPEAKER_ICON_NAMES = ("CBL", "CBR", "SB", "SL", "SR", "SW", "FL", "C", "FR")
STATE_ICON_NAMES = (
    "Standby LED",
    "Zone",
    "Zone 2",
    "Zone 3",
    "Zone 4",
    "Display Mode0",
    "Display Mode1",
)
SOUND_MODE_ICON_NAMES = (
    "Pro Logic",
    "II",
    "x",
    "Dolby Digital",
    "dts",
    "ES",
    "EX",
    "5.1",
    "7.1",
)
INPUT_ICON_NAMES = ("HDMI", "Coaxial", "Optical", "A", "1", "2", "3", "4", "5")
# Not actually sure what these are.
# Might move them if I ever work it out.
MISC_ICON_NAMES = ("<", ">")


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
):
    """Set up the rsp1570serial platform."""
    # pylint: disable=unused-argument

    if CONF_MODEL_SPEC in config:
        model_spec = config.get(CONF_MODEL_SPEC)
        assert model_spec is not None
        model = model_spec.get(CONF_MODEL)
        source_aliases = model_spec.get(CONF_SOURCE_ALIASES)
    else:
        model = DEFAULT_MODEL
        source_aliases = config.get(CONF_SOURCE_ALIASES)

    meta = ROTEL_MODELS[model]

    source_map = make_alias_source_map(meta, source_aliases)

    serial_port = config[CONF_DEVICE]
    unique_id = config[CONF_UNIQUE_ID]
    conn_factory = RotelConnectionWrapperFactory(serial_port, unique_id, meta)

    entity = RotelMediaPlayer(unique_id, config[CONF_NAME], conn_factory, source_map)

    async_add_entities([entity])
    setup_hass_services(hass)


def setup_hass_services(hass):
    """
    Register services.

    Note that this function is called for every entity but it
    only needs to be called once for the platform.
    It doesn't seem to do any harm but I'd like to tidy that up at some point.
    """

    async def async_handle_send_command(entity, call):
        command_name = call.data[ATTR_COMMAND_NAME]
        if isinstance(entity, RotelMediaPlayer):
            _LOGGER.debug(
                "%s service sending command %s to entity %s",
                SERVICE_SEND_COMMAND,
                command_name,
                entity.entity_id,
            )
            await entity.async_send_command(command_name)
        else:
            _LOGGER.error(
                "%s service not sending command %s to incompatible entity %s",
                SERVICE_SEND_COMMAND,
                command_name,
                entity.entity_id,
            )

    async def async_handle_reconnect(entity, call):
        # pylint: disable=unused-argument
        if isinstance(entity, RotelMediaPlayer):
            _LOGGER.debug(
                "%s service reconnecting entity %s", SERVICE_RECONNECT, entity.entity_id
            )
            await entity.async_reconnect()
        else:
            _LOGGER.error(
                "%s service not reconnecting incompatible entity %s",
                SERVICE_RECONNECT,
                entity.entity_id,
            )

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_SEND_COMMAND,
        {vol.Required(ATTR_COMMAND_NAME): cv.string},
        async_handle_send_command,
    )
    platform.async_register_entity_service(
        SERVICE_RECONNECT, {}, async_handle_reconnect
    )


def make_alias_source_map(
    meta: RotelModelMeta,
    source_aliases: Optional[Dict[str, str]],
) -> Dict[str, str]:
    """Return a dict of selectable source aliases mapped to command_code."""
    standard_source_map = {m.standard_name: m.command_code for m in meta.sources}
    alias_source_map = {}
    sources_seen = set()
    if source_aliases is not None:
        for source, alias in source_aliases.items():
            sources_seen.add(source)
            if alias is not None:
                command_code = standard_source_map[source]
                alias_source_map[alias] = command_code
    for source, command_code in standard_source_map.items():
        if source not in sources_seen:
            alias_source_map[source] = command_code
    _LOGGER.debug("Sources to select: %r", alias_source_map)
    return alias_source_map


def make_icon_state_dict(message_icons, icon_names):
    """Extract the icon state for icon_names from message."""

    def binary_sensor_value(icon_flag):
        return False if icon_flag is None else bool(icon_flag)

    return {k: binary_sensor_value(message_icons[k]) for k in icon_names}


def init_icon_state_dict(icon_names):
    """Initialise the icon state for icon_names."""
    return {k: False for k in icon_names}


class RotelConnectionWrapper:
    def __init__(self, conn: RotelAmpConn, unique_id: str):
        """Wraps device connection to ensure correct management of state"""
        self._unique_id = unique_id
        self._conn = conn

    @property
    def meta(self) -> RotelModelMeta:
        return self._conn.meta

    async def async_open(self):
        """Open a connection to the device."""
        await self._conn.open()

    async def async_close(self):
        """Close the connection to the device."""
        await self._conn.close()

    async def async_read_messages(
        self,
        message_handler: Callable[[AnyMessage], None],
    ) -> None:
        """
        Read messages published by the device.

        Send a DISPLAY_REFRESH command before we start reading.
        If the device is already on then this is a null command that will
        simply trigger a feedback message that will sync the state of this
        object with the physical device.
        """
        assert self._conn is not None
        try:
            await self.async_send_command("DISPLAY_REFRESH")
            async for message in self._conn.read_messages():
                _LOGGER.debug("Message received by %s.", self._unique_id)
                message_handler(message)
        except asyncio.CancelledError:
            _LOGGER.info("Message reader cancelled for %s", self._unique_id)

    async def async_send_command(self, command: str) -> None:
        assert self._conn is not None
        await self._conn.send_command(command)

    async def async_send_volume_direct_command(
        self, zone: int, device_volume: int
    ) -> None:
        assert self._conn is not None
        await self._conn.send_volume_direct_command(zone, device_volume)


@dataclass
class RotelConnectionWrapperFactory:
    serial_port: str
    unique_id: str
    meta: RotelModelMeta

    def make_conn(self) -> RotelConnectionWrapper:
        conn = RotelAmpConn(self.serial_port, self.meta)
        return RotelConnectionWrapper(conn, self.unique_id)


def make_smart_display_lines(
    prev_lines: Optional[List[str]],
    message: SmartDisplayMessage,
) -> List[str]:
    if prev_lines is None:
        lines = 10 * [""]
    else:
        lines = prev_lines.copy()

    for lineno, line in enumerate(message.lines, message.start):
        if lineno <= 10:
            lines[lineno - 1] = line

    return lines


class RotelMediaPlayer(MediaPlayerEntity):
    """Representation of a Rotel media player."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    # pylint: disable=abstract-method
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        unique_id: str,
        name: str,
        conn_factory: RotelConnectionWrapperFactory,
        source_map: Dict[str, str],
    ):
        """Initialize the device."""
        self._conn_factory = conn_factory
        self._conn = self._conn_factory.make_conn()
        self._source_map = source_map

        self._read_messages_task = None

        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_should_poll = False
        self._attr_assumed_state = True
        self._attr_source_list = sorted(self._source_map.keys())
        self._attr_source = None
        self._attr_state = MediaPlayerState.OFF
        self._attr_volume_level = None
        self._attr_is_volume_muted = None

        self._device_volume = None  # Raw volume level from the device
        self._party_mode_on = None
        self._info = None
        self._icons = None
        self._speaker_icons = init_icon_state_dict(SPEAKER_ICON_NAMES)
        self._state_icons = init_icon_state_dict(STATE_ICON_NAMES)
        self._sound_mode_icons = init_icon_state_dict(SOUND_MODE_ICON_NAMES)
        self._input_icons = init_icon_state_dict(INPUT_ICON_NAMES)
        self._misc_icons = init_icon_state_dict(MISC_ICON_NAMES)
        self._triggers = None
        self._smart_display: Optional[List[str]] = None

    async def async_added_to_hass(self):
        """Open connection and set up remove event when entity added to hass."""
        await self._conn.async_open()
        self._start_read_messages()

        async def handle_hass_stop_event(event):
            """Clean up when hass stops."""
            await self.cleanup()

        self.async_on_remove(
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, handle_hass_stop_event
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await self.cleanup()

    def _start_read_messages(self):
        """Create a task to start reading messages."""
        self._read_messages_task = self.hass.loop.create_task(
            self._conn.async_read_messages(self.handle_message)
        )

    async def _cancel_read_messages(self):
        """Cancel the _read_messages_task."""
        if self._read_messages_task is not None:
            _LOGGER.info(
                "Cancelling read_messages task.  Done was: %r.",
                self._read_messages_task.done(),
            )
            if not self._read_messages_task.done():
                self._read_messages_task.cancel()
                await self._read_messages_task
            else:
                ex = self._read_messages_task.exception()
                if ex is not None:
                    _LOGGER.error(
                        "Read messages task contained an exception.", exc_info=ex
                    )
            self._read_messages_task = None

    async def async_reconnect(self):
        """
        Reconnect.

        Don't call this more often than needed - it is asynchronous
        and it doesn't check for activity in progress on the connection
        so there could be a risk of a conflict.
        """
        await self._cancel_read_messages()

        # Ignore any errors while closing the connection because
        # the reason we'd be doing this would probably be due to some
        # sort of issue with the existing connection anyway.
        try:
            await self._conn.async_close()
        # pylint: disable=broad-except
        except Exception:
            _LOGGER.exception("Could not close connection for '%s'", self.unique_id)

        # Set the state to OFF by default
        # If the player is actually on then the state will be refreshed
        # when the message reader restarts
        self._attr_state = MediaPlayerState.OFF
        self.async_schedule_update_ha_state()

        # Replace the old connection object
        # Not strictly necessary but better safe than sorry
        self._conn = self._conn_factory.make_conn()

        # Open the connection
        await self._conn.async_open()
        self._start_read_messages()

    async def cleanup(self):
        """Close connection and stop message reader."""
        _LOGGER.info("Cleaning up '%s'", self.unique_id)
        await self._cancel_read_messages()
        await self._conn.async_close()
        _LOGGER.info("Finished cleaning up '%s'", self.unique_id)

    def handle_message(self, message: AnyMessage):
        """Route each type of message to an appropriate handler."""

        if isinstance(message, FeedbackMessage):
            self.handle_feedback_message(message)
        elif isinstance(message, TriggerMessage):
            self.handle_trigger_message(message)
        elif isinstance(message, SmartDisplayMessage):
            self.handle_smart_display_message(message)
        else:
            _LOGGER.error("Unknown message type encountered")

    def device_vol_to_vol_level(self, device_volume: Optional[int]) -> Optional[float]:
        if device_volume is None:
            return None
        return device_volume / self._conn.meta.max_volume

    def handle_feedback_message(self, message: FeedbackMessage):
        """Map feedback message to object attributes."""
        fields = message.parse_display_lines()
        self._attr_state = (
            MediaPlayerState.ON if fields["is_on"] else MediaPlayerState.OFF
        )
        self._attr_source = fields["source_name"]
        self._device_volume = fields["volume"]
        self._attr_volume_level = self.device_vol_to_vol_level(self._device_volume)
        self._attr_is_volume_muted = fields["mute_on"]
        self._party_mode_on = fields["party_mode_on"]
        self._info = fields["info"]
        self._icons = message.icons_that_are_on()
        self._speaker_icons = make_icon_state_dict(message.icons, SPEAKER_ICON_NAMES)
        self._state_icons = make_icon_state_dict(message.icons, STATE_ICON_NAMES)
        self._sound_mode_icons = make_icon_state_dict(
            message.icons, SOUND_MODE_ICON_NAMES
        )
        self._input_icons = make_icon_state_dict(message.icons, INPUT_ICON_NAMES)
        self._misc_icons = make_icon_state_dict(message.icons, MISC_ICON_NAMES)
        self.async_schedule_update_ha_state()

    def handle_trigger_message(self, message: TriggerMessage):
        """Map trigger message to object attributes."""
        self._triggers = message.flags_to_list(message.flags)
        self.async_schedule_update_ha_state()

    def handle_smart_display_message(self, message: SmartDisplayMessage):
        """Map smart display message to object attributes."""
        self._smart_display = make_smart_display_lines(self._smart_display, message)
        self.async_schedule_update_ha_state()

    async def async_turn_on(self):
        """Turn the media player on."""
        await self.async_send_command("POWER_ON")
        self._attr_state = MediaPlayerState.ON

    async def async_turn_off(self):
        """Turn off media player."""
        await self.async_send_command("POWER_OFF")
        self._attr_state = MediaPlayerState.OFF

    async def async_select_source(self, source):
        """Select input source."""
        await self.async_send_command(self._source_map[source])

    async def async_volume_up(self):
        """Volume up media player."""
        await self.async_send_command("VOLUME_UP")

    async def async_volume_down(self):
        """Volume down media player."""
        await self.async_send_command("VOLUME_DOWN")

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        # Note that the main zone has a MUTE_ON and MUTE_OFF command
        # Could switch to that instead but for now sticking with the
        # regular mute commands that affect whatever zone is on the
        # info display
        if self._attr_is_volume_muted is None:
            # Chances are that this is the right thing to do
            await self.async_send_command("MUTE_TOGGLE")
        elif self._attr_is_volume_muted and not mute:
            await self.async_send_command("MUTE_TOGGLE")
        elif not self._attr_is_volume_muted and mute:
            await self.async_send_command("MUTE_TOGGLE")

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        return {
            ATTR_DISPLAY_VOLUME: self._device_volume,
            ATTR_PARTY_MODE_ON: self._party_mode_on,
            ATTR_INFO: self._info,
            ATTR_ICONS: self._icons,
            ATTR_SPEAKER_ICONS: self._speaker_icons,
            ATTR_STATE_ICONS: self._state_icons,
            ATTR_INPUT_ICONS: self._input_icons,
            ATTR_SOUND_MODE_ICONS: self._sound_mode_icons,
            ATTR_MISC_ICONS: self._misc_icons,
            ATTR_TRIGGERS: self._triggers,
            ATTR_SMART_DISPLAY: self._smart_display,
        }

    async def async_set_volume_level(self, volume: float):
        """Set volume level, range 0..1."""
        scaled_volume: int = round(volume * self._conn.meta.max_volume)
        _LOGGER.debug("Set volume to: %r", scaled_volume)
        await self._conn.async_send_volume_direct_command(1, scaled_volume)

    async def async_send_command(self, command_name: str):
        """Send a command to the device."""
        await self._conn.async_send_command(command_name)
