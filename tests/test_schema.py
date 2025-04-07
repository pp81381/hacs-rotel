from typing import Dict, Optional

import voluptuous as vol
from pytest import fixture, raises

from custom_components.rotel.media_player import DEFAULT_NAME, ROTEL_SCHEMA


@fixture
def rotel_schema():
    return vol.Schema(ROTEL_SCHEMA)


@fixture
def test_aliases_rsp1570() -> Dict[str, Optional[str]]:
    return {
        "TUNER": None,
        "TAPE": None,
        "MULTI": None,
        "VIDEO 1": "CATV",
        "VIDEO 2": "NMT",
        "VIDEO 3": "APPLE TV",
        "VIDEO 4": "FIRE TV",
        "VIDEO 5": "BLU RAY",
    }


def test_schema_simple(rotel_schema):
    cfg_in = {
        "device": "/dev/ttyUSB0",
        "unique_id": "rotel_rsp1570",
    }
    cfg_out = rotel_schema(cfg_in)
    assert cfg_out.get("device") == "/dev/ttyUSB0"
    assert cfg_out.get("unique_id") == "rotel_rsp1570"
    assert cfg_out.get("name") == DEFAULT_NAME


def test_schema_with_aliases(rotel_schema, test_aliases_rsp1570):
    cfg_in = {
        "device": "/dev/ttyUSB0",
        "unique_id": "rotel_rsp1570",
        "name": "My Name",
        "source_aliases": test_aliases_rsp1570,
    }
    cfg_out = rotel_schema(cfg_in)
    assert cfg_out.get("device") == "/dev/ttyUSB0"
    assert cfg_out.get("unique_id") == "rotel_rsp1570"
    assert cfg_out.get("name") == "My Name"
    assert cfg_out.get("source_aliases") == test_aliases_rsp1570


def test_schema_with_model_spec(rotel_schema, test_aliases_rsp1570):
    cfg_in = {
        "device": "/dev/ttyUSB0",
        "unique_id": "rotel_rsp1570",
        "name": "My Name",
        "model_spec": {
            "model": "rsp1570",
            "source_aliases": test_aliases_rsp1570,
        },
    }
    cfg_out = rotel_schema(cfg_in)
    assert cfg_out.get("device") == "/dev/ttyUSB0"
    assert cfg_out.get("unique_id") == "rotel_rsp1570"
    assert cfg_out.get("name") == "My Name"
    assert cfg_out.get("model_spec").get("model") == "rsp1570"
    assert cfg_out.get("model_spec").get("source_aliases") == test_aliases_rsp1570


def test_schema_with_aliases_and_model_spec(rotel_schema, test_aliases_rsp1570):
    cfg_in = {
        "device": "/dev/ttyUSB0",
        "unique_id": "rotel_rsp1570",
        "name": "My Name",
        "source_aliases": test_aliases_rsp1570,
        "model_spec": {
            "model": "rsp1570",
            "source_aliases": test_aliases_rsp1570,
        },
    }
    with raises(vol.MultipleInvalid) as exc_info:
        rotel_schema(cfg_in)
    assert (
        str(exc_info.value)
        == "two or more values in the same group of exclusion 'model_spec' @ data[<model_spec>]"
    )


def test_schema_with_bad_source_for_rsp1572(rotel_schema, test_aliases_rsp1570):
    cfg_in = {
        "device": "/dev/ttyUSB0",
        "unique_id": "rotel_rsp1570",
        "name": "My Name",
        "model_spec": {
            "model": "rsp1572",
            "source_aliases": test_aliases_rsp1570,
        },
    }
    with raises(vol.MultipleInvalid) as exc_info:
        rotel_schema(cfg_in)
    assert (
        str(exc_info.value)
        == "not a valid value @ data['model_spec']['source_aliases']['TAPE']"
    )
