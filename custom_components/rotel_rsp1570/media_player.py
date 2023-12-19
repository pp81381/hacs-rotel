"""Rotel RSP-1570 media player platform."""
import asyncio
import logging

from rsp1570serial import ROTEL_RSP1570_SOURCES
from rsp1570serial.commands import MAX_VOLUME
from rsp1570serial.connection import RotelAmpConn
from rsp1570serial.messages import FeedbackMessage, TriggerMessage
import voluptuous as vol

from homeassistant.components.media_player import (
    DOMAIN,
    PLATFORM_SCHEMA,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
    STATE_OFF,
    STATE_ON,
)
import homeassistant.helpers.config_validation as cv

DEFAULT_NAME = "Rotel RSP-1570"

_LOGGER = logging.getLogger(__name__)

SUPPORT_ROTEL_RSP1570 = (
    SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOURCE
)

CONF_SOURCE_ALIASES = "source_aliases"
CONF_UNIQUE_ID = "unique_id"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE): cv.string,
        vol.Required(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SOURCE_ALIASES): vol.Schema(
            {vol.Any(*ROTEL_RSP1570_SOURCES.keys()): vol.Any(str, None)}
        ),
    }
)

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

ATTR_COMMAND_NAME = "command_name"
SERVICE_SEND_COMMAND = "rotel_send_command"
SERVICE_SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
        vol.Required(ATTR_COMMAND_NAME): cv.string,
    }
)
SERVICE_RECONNECT = "rotel_reconnect"
SERVICE_RECONNECT_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids}
)

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


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the rsp1570serial platform."""
    # pylint: disable=unused-argument

    source_map = make_source_map(config.get(CONF_SOURCE_ALIASES))

    entity = RotelMediaPlayer(
        config[CONF_UNIQUE_ID],
        config[CONF_NAME],
        config[CONF_DEVICE],
        source_map,
    )

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
            await entity.send_command(command_name)
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
            await entity.reconnect()
        else:
            _LOGGER.error(
                "%s service not reconnecting incompatible entity %s",
                SERVICE_RECONNECT,
                entity.entity_id,
            )

    component = hass.data[DOMAIN]
    component.async_register_entity_service(
        SERVICE_SEND_COMMAND, SERVICE_SEND_COMMAND_SCHEMA, async_handle_send_command
    )
    component.async_register_entity_service(
        SERVICE_RECONNECT, SERVICE_RECONNECT_SCHEMA, async_handle_reconnect
    )


def make_source_map(source_aliases):
    """Return a dict of selectable source aliases mapped to command_code."""
    source_map = {}
    sources_seen = set()
    if source_aliases is not None:
        for source, alias in source_aliases.items():
            sources_seen.add(source)
            if alias is not None:
                command_code = ROTEL_RSP1570_SOURCES[source]
                source_map[alias] = command_code
    for source, command_code in ROTEL_RSP1570_SOURCES.items():
        if source not in sources_seen:
            source_map[source] = command_code
    _LOGGER.debug("Sources to select: %r", source_map)
    return source_map


def make_icon_state_dict(message_icons, icon_names):
    """Extract the icon state for icon_names from message."""

    def binary_sensor_value(icon_flag):
        return False if icon_flag is None else bool(icon_flag)

    return {k: binary_sensor_value(message_icons[k]) for k in icon_names}


def init_icon_state_dict(icon_names):
    """Initialise the icon state for icon_names."""
    return {k: False for k in icon_names}


class RotelMediaPlayer(MediaPlayerEntity):
    """Representation of a Rotel media player."""

    # pylint: disable=abstract-method
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, unique_id, name, device, source_map):
        """Initialize the device."""
        self._unique_id = unique_id
        self._name = name
        self._device = device
        self._conn = None  # Make sure that you call open_connection...
        self._read_messages_task = None  # ... and start_read_messages
        self._state = STATE_OFF
        self._source_name = None
        self._volume = None
        self._source_map = source_map
        self._mute_on = None
        self._party_mode_on = None
        self._info = None
        self._icons = None
        self._speaker_icons = init_icon_state_dict(SPEAKER_ICON_NAMES)
        self._state_icons = init_icon_state_dict(STATE_ICON_NAMES)
        self._sound_mode_icons = init_icon_state_dict(SOUND_MODE_ICON_NAMES)
        self._input_icons = init_icon_state_dict(INPUT_ICON_NAMES)
        self._misc_icons = init_icon_state_dict(MISC_ICON_NAMES)
        self._triggers = None

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Do not poll because this entity pushes its state to HA."""
        return False

    async def async_added_to_hass(self):
        """Open connection and set up remove event when entity added to hass."""
        await self.open_connection()
        self.start_read_messages()

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

    async def open_connection(self):
        """Open a connection to the device."""

        conn = RotelAmpConn(self._device)
        await conn.open()
        self._conn = conn

    def close_connection(self):
        """Close the connection to the device."""
        if self._conn is not None:
            self._conn.close()

    def start_read_messages(self):
        """Create a task to start reading messages."""
        self._read_messages_task = self.hass.loop.create_task(
            self.async_read_messages()
        )

    async def cancel_read_messages(self):
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

    async def async_read_messages(self):
        """
        Read messages published by the device.

        Read messages published by the device and use them to maintain the
        state of this object.
        Send a DISPLAY_REFRESH command before we start reading.
        If the device is already on then this is a null command that will
        simply trigger a feedback message that will sync the state of this
        object with the physical device.
        """
        try:
            await self.send_command("DISPLAY_REFRESH")
            async for message in self._conn.read_messages():
                _LOGGER.debug("Message received by %s.", self.unique_id)
                self.handle_message(message)
        except asyncio.CancelledError:
            _LOGGER.info("Message reader cancelled for %s", self.unique_id)

    async def reconnect(self):
        """
        Reconnect.

        Don't call this more often than needed - it is asynchronous
        and it doesn't check for activity in progress on the connection
        so there could be a risk of a conflict.
        """
        await self.cancel_read_messages()

        # Ignore any errors while closing the connection because
        # the reason we'd be doing this would probably be due to some
        # sort of issue with the existing connection anyway.
        try:
            self.close_connection()
        # pylint: disable=broad-except
        except Exception:
            _LOGGER.exception("Could not close connection for '%s'", self.unique_id)

        # Set the state to OFF by default
        # If the player is actually on then the state will be refreshed
        # when the message reader restarts
        self._state = STATE_OFF
        self.async_schedule_update_ha_state()

        await self.open_connection()
        self.start_read_messages()

    async def cleanup(self):
        """Close connection and stop message reader."""
        _LOGGER.info("Cleaning up '%s'", self.unique_id)
        await self.cancel_read_messages()
        self.close_connection()
        _LOGGER.info("Finished cleaning up '%s'", self.unique_id)

    def handle_message(self, message):
        """Route each type of message to an appropriate handler."""

        if isinstance(message, FeedbackMessage):
            self.handle_feedback_message(message)
        elif isinstance(message, TriggerMessage):
            self.handle_trigger_message(message)
        else:
            _LOGGER.error("Unknown message type encountered")

    def handle_feedback_message(self, message):
        """Map feedback message to object attributes."""
        fields = message.parse_display_lines()
        self._state = STATE_ON if fields["is_on"] else STATE_OFF
        self._source_name = fields["source_name"]
        self._volume = fields["volume"]
        self._mute_on = fields["mute_on"]
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

    def handle_trigger_message(self, message):
        """Map trigger message to object attributes."""
        self._triggers = message.flags_to_list(message.flags)
        self.async_schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_ROTEL_RSP1570

    @property
    def assumed_state(self):
        """Indicate that state is assumed."""
        return True

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    async def async_turn_on(self):
        """Turn the media player on."""
        await self._conn.send_command("POWER_ON")
        self._state = STATE_ON

    async def async_turn_off(self):
        """Turn off media player."""
        await self._conn.send_command("POWER_OFF")
        self._state = STATE_OFF

    @property
    def source_list(self):
        """Return the list of available input sources."""
        return sorted(self._source_map.keys())

    @property
    def source(self):
        """Return the current input source."""
        return self._source_name

    async def async_select_source(self, source):
        """Select input source."""
        await self._conn.send_command(self._source_map[source])

    async def async_volume_up(self):
        """Volume up media player."""
        await self._conn.send_command("VOLUME_UP")

    async def async_volume_down(self):
        """Volume down media player."""
        await self._conn.send_command("VOLUME_DOWN")

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        # Note that the main zone has a MUTE_ON and MUTE_OFF command
        # Could switch to that instead but for now sticking with the
        # regular mute commands that affect whatever zone is on the
        # info display
        if self._mute_on is None:
            # Chances are that this is the right thing to do
            await self._conn.send_command("MUTE_TOGGLE")
        elif self._mute_on and not mute:
            await self._conn.send_command("MUTE_TOGGLE")
        elif not self._mute_on and mute:
            await self._conn.send_command("MUTE_TOGGLE")

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        return {
            ATTR_DISPLAY_VOLUME: self._volume,  # Scaled differently to volume_level
            ATTR_PARTY_MODE_ON: self._party_mode_on,
            ATTR_INFO: self._info,
            ATTR_ICONS: self._icons,
            ATTR_SPEAKER_ICONS: self._speaker_icons,
            ATTR_STATE_ICONS: self._state_icons,
            ATTR_INPUT_ICONS: self._input_icons,
            ATTR_SOUND_MODE_ICONS: self._sound_mode_icons,
            ATTR_MISC_ICONS: self._misc_icons,
            ATTR_TRIGGERS: self._triggers,
        }

    @property
    def _volume_max(self):
        """Max volume level of the media player."""
        return MAX_VOLUME

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume is None:
            return None
        return self._volume / self._volume_max

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        scaled_volume = round(volume * self._volume_max)
        _LOGGER.debug("Set volume to: %r", scaled_volume)
        await self._conn.send_volume_direct_command(1, scaled_volume)

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._mute_on

    async def send_command(self, command_name):
        """Send a command to the device."""
        await self._conn.send_command(command_name)
