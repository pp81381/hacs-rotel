# hassdev

My Home Assistant customisations

## rotel_rsp1570

This is a media player custom component that can control a Rotel RSP-1570 processor

The component utilises the [rsp1570serial](https://pypi.org/project/rsp1570serial-pp81381/) library on PyPi for communications with the device

### Configuration

Take a look at configuration.yaml and groups.yaml in the .homeassistant folder for usage examples.

Here is a basic example of the configuration.yaml entry needed.  Obviously the device parameter needs to match your own environment.   The keys in source_map should ideally exactly match the source names for any inputs that have custom names.

```
media_player:
- platform: rotel_rsp1570
  device: /dev/ttyUSB0
  source_map:
    CATV: VIDEO 1
    NMT: VIDEO 2
    APPLE TV: VIDEO 3
    FIRE TV: VIDEO 4
    BLU RAY: VIDEO 5

```

The sample configuration file also demonstrates how to access the granular state of the device via template sensor and binary template sensor elements.

Note that the state of the media player component is set by messages received from the device.
* When you start Home Assistant it is assumed that the device is turned off.  If that isn't the case then any device activity will be enough for the component to align with the device.  If you click the POWER_ON button and the device is already on then that will be enough for the component to work it out.
* If the device state is changed externally (perhaps by the remote) then Home Assistant will keep in sync with it.

### Infra Red Control

My Raspberry Pi has an IR Hat so I can use lirc to trigger Home Assistant automations.

Please see .lircrc and automations.yaml for my PoC configuration.

I chose a random remote control from the lirc remotes database and then configured my Harmony Hub with the same device.   Now I can use this fake remote to control Home Assistant as part of a Harmony activity.