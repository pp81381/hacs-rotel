"""
Support for the Rotel RSP-1570 processor.
Although only the RSP-1570 is supported at the moment, the
low level library could easily be updated to support other
products of a similar vintage.
"""
import asyncio
import logging
import voluptuous as vol
from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP, SUPPORT_VOLUME_SET)
from homeassistant.const import (
    CONF_DEVICE, CONF_NAME, STATE_OFF, STATE_ON,
    EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['rsp1570serial-pp81381==0.0.5']

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Rotel RSP-1570'

SUPPORT_ROTEL_RSP1570 = \
    SUPPORT_VOLUME_SET | SUPPORT_VOLUME_STEP | SUPPORT_VOLUME_MUTE | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

CONF_SOURCE_MAP = "source_map"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICE): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SOURCE_MAP): vol.Schema({cv.string: cv.string}),
})

ROTEL_RSP1570_SOURCES = {
    ' CD': 'SOURCE_CD',
    'TUNER': 'SOURCE_TUNER',
    'TAPE': 'SOURCE_TAPE',
    'VIDEO 1': 'SOURCE_VIDEO_1',
    'VIDEO 2': 'SOURCE_VIDEO_2',
    'VIDEO 3': 'SOURCE_VIDEO_3',
    'VIDEO 4': 'SOURCE_VIDEO_4',
    'VIDEO 5': 'SOURCE_VIDEO_5',
    'MULTI': 'SOURCE_MULTI_INPUT',
}

ATTR_SOURCE_NAME = "source_name"
ATTR_VOLUME = "volume"
ATTR_MUTE_ON = "mute_on"
ATTR_PARTY_MODE_ON = "party_mode_on"
ATTR_INFO = "info"
ATTR_ICONS = "icons"
ATTR_SPEAKER_ICONS = "speaker_icons"
ATTR_STATE_ICONS = "state_icons"
ATTR_INPUT_ICONS = "input_icons"
ATTR_SOUND_MODE_ICONS = "sound_mode_icons"
ATTR_MISC_ICONS = "misc_icons"
ATTR_TRIGGERS = "triggers"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the rsp1570serial platform."""
    # pylint: disable=unused-argument

    from rsp1570serial.connection import RotelAmpConn

    conn = RotelAmpConn(config.get(CONF_DEVICE))

    source_map = config.get(CONF_SOURCE_MAP)
    _LOGGER.debug("CONF_SOURCE_MAP: %r", source_map)

    @callback
    def close_rotel_rsp1570_conn(event):
        """Close Rotel RSP-1570 connection."""
        _LOGGER.debug("Closing Rotel RSP-1570 connection")
        conn.close()
        _LOGGER.debug("Rotel RSP-1570 connection closed.")

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close_rotel_rsp1570_conn)
    _LOGGER.debug("Registered for HASS stop event")

    try:
        await conn.open()
    except:
        _LOGGER.error("Could not open connection", exc_info=True)
        raise
    else:
        device = RotelRSP1570Device(config.get(CONF_NAME), conn, source_map)
        async_add_entities([device])
        hass.loop.create_task(device.async_read_messages())

class RotelRSP1570Device(MediaPlayerDevice):
    """Representation of a Rotel RSP-1570 device."""
    # pylint: disable=abstract-method
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, conn, source_map):
        """Initialize the Rotel RSP-1570 device."""
        self._name = name
        self._conn = conn
        self._state = STATE_OFF
        self._source_name = None
        self._volume = None
        self.set_source_lists(source_map)
        self._mute_on = None
        self._party_mode_on = None
        self._info = None
        self._icons = None
        self._speaker_icons = None
        self._state_icons = None
        self._input_icons = None
        self._sound_mode_icons = None
        self._misc_icons = None
        self._triggers = None

    def set_source_lists(self, source_map):
        """
        Set list of sources that can be selected.
        For sources that have an alias defined then let the user pick that instead.
        """
        sources_to_select = {}
        aliased_sources = set()
        for alias, source in source_map.items():
            aliased_sources.add(source)
            sources_to_select[alias] = ROTEL_RSP1570_SOURCES[source]
        for source, cmd in ROTEL_RSP1570_SOURCES.items():
            if source not in aliased_sources:
                sources_to_select[source] = cmd
        _LOGGER.debug("Sources to select: %r", sources_to_select)
        self._sources_to_select = sources_to_select

    async def async_read_messages(self):
        """
        Read messages published by the device and use them to maintain state in this device
        This routine is intended to be run in a new asyncio task
        """
        from rsp1570serial.messages import FeedbackMessage, TriggerMessage

        _LOGGER.debug("Message reader started.")
        try:
            async for message in self._conn.read_messages():
                _LOGGER.debug("Message received.")
                if isinstance(message, FeedbackMessage):
                    self.handle_feedback_message(message)
                elif isinstance(message, TriggerMessage):
                    self.handle_trigger_message(message)
                else:
                    _LOGGER.warning("Unknown message type encountered")
        except asyncio.CancelledError:
            _LOGGER.info("Message reader cancelled")

    def handle_feedback_message(self, message):
        """Map feedback message to object attributes."""
        fields = message.parse_display_lines()
        self._state = STATE_ON if fields['is_on'] else STATE_OFF
        self._source_name = fields['source_name']
        self._volume = fields['volume']
        _LOGGER.debug("Volume from amp is %r", self._volume)
        self._mute_on = fields['mute_on']
        self._party_mode_on = fields['party_mode_on']
        self._info = fields['info']
        self._icons = message.icons_that_are_on()
        bs_value = lambda x: False if x is None else bool(x)
        self._speaker_icons = {
            k:bs_value(message.icons[k]) for k in ('CBL', 'CBR', 'SL', 'SR', 'SW', 'FL', 'C', 'FR')}
        self._state_icons = {
            k:bs_value(message.icons[k]) for k in (
                'Standby LED', 'Zone', 'Zone 2', 'Zone 3', 'Zone 4',
                'Display Mode0', 'Display Mode1')}
        self._sound_mode_icons = {
            k:bs_value(message.icons[k]) for k in (
                'Pro Logic', 'II', 'x', 'Dolby Digital', 'dts', 'ES', 'EX', '5.1', '7.1')}
        self._input_icons = {
            k:bs_value(message.icons[k]) for k in (
                'HDMI', 'Coaxial', 'Optical', 'A', '1', '2', '3', '4', '5')}
        # Not actually sure what these are.  Might move them if I ever work it out.
        self._misc_icons = {k:bs_value(message.icons[k]) for k in ('SB', '<', '>')}
        self.async_schedule_update_ha_state()

    def handle_trigger_message(self, message):
        """Map trigger message to object attributes."""
        self._triggers = message.flags_to_list(message.flags)
        self.async_schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the device."""
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
        """Return the state of the device."""
        return self._state

    async def async_turn_on(self):
        """Turn the media player on."""
        await self._conn.send_command('POWER_ON')
        self._state = STATE_ON

    async def async_turn_off(self):
        """Turn off media player."""
        await self._conn.send_command('POWER_OFF')
        self._state = STATE_OFF

    @property
    def source_list(self):
        """Return the list of available input sources."""
        return sorted((self._sources_to_select.keys()))

    @property
    def source(self):
        """Return the current input source."""
        return self._source_name

    async def async_select_source(self, source):
        """Select input source."""
        await self._conn.send_command(self._sources_to_select[source])

    async def async_volume_up(self):
        """Volume up media player."""
        await self._conn.send_command('VOLUME_UP')

    async def async_volume_down(self):
        """Volume down media player."""
        await self._conn.send_command('VOLUME_DOWN')

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        # Note that the main zone has a MUTE_ON and MUTE_OFF command
        # Could switch to that instead but for now sticking with the
        # regular mute commands that affect whatever zone is on the
        # info display
        if self._mute_on is None:
            # Chances are that this is the right thing to do
            await self._conn.send_command('MUTE_TOGGLE')
        elif self._mute_on and not mute:
            await self._conn.send_command('MUTE_TOGGLE')
        elif not self._mute_on and mute:
            await self._conn.send_command('MUTE_TOGGLE')

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        if self.state == STATE_OFF:
            return None
        attributes = {
            ATTR_SOURCE_NAME: self._source_name,
            ATTR_VOLUME: self._volume,
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
        return attributes

    @property
    def _volume_max(self):
        """Max volume level of the media player."""
        from rsp1570serial.commands import MAX_VOLUME
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
