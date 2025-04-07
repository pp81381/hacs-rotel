from pytest import fixture, raises
from rsp1570serial.messages import SmartDisplayMessage

from custom_components.rotel.media_player import make_smart_display_lines


@fixture
def smart_display_type_1():
    return SmartDisplayMessage(["Line 1"], 1)


@fixture
def smart_display_type_2():
    return SmartDisplayMessage(
        [
            "Line 2",
            "Line 3",
            "Line 4",
            "Line 5",
            "Line 6",
            "Line 7",
            "Line 8",
            "Line 9",
            "Line 10",
        ],
        2,
    )


@fixture
def smart_display_type_2_bad():
    return SmartDisplayMessage(
        [
            "Line 2",
            "Line 3",
            "Line 4",
            "Line 5",
            "Line 6",
            "Line 7",
            "Line 8",
            "Line 9",
            "Line 10",
            "Line 11",
        ],
        2,
    )


def test1(smart_display_type_1):
    l = make_smart_display_lines(None, smart_display_type_1)
    assert l == ["Line 1", "", "", "", "", "", "", "", "", ""]


def test2(smart_display_type_2):
    l = make_smart_display_lines(None, smart_display_type_2)
    assert l == [
        "",
        "Line 2",
        "Line 3",
        "Line 4",
        "Line 5",
        "Line 6",
        "Line 7",
        "Line 8",
        "Line 9",
        "Line 10",
    ]


def test3(smart_display_type_1):
    l = make_smart_display_lines(10 * ["PREV"], smart_display_type_1)
    assert l == [
        "Line 1",
        "PREV",
        "PREV",
        "PREV",
        "PREV",
        "PREV",
        "PREV",
        "PREV",
        "PREV",
        "PREV",
    ]


def test4(smart_display_type_2):
    l = make_smart_display_lines(10 * ["PREV"], smart_display_type_2)
    assert l == [
        "PREV",
        "Line 2",
        "Line 3",
        "Line 4",
        "Line 5",
        "Line 6",
        "Line 7",
        "Line 8",
        "Line 9",
        "Line 10",
    ]


def test5(smart_display_type_2):
    with raises(IndexError) as exc_info:
        l = make_smart_display_lines(5 * ["PREV"], smart_display_type_2)
    assert str(exc_info.value) == "list assignment index out of range"


def test6(smart_display_type_2_bad):
    l = make_smart_display_lines(10 * ["PREV"], smart_display_type_2_bad)
    assert l == [
        "PREV",
        "Line 2",
        "Line 3",
        "Line 4",
        "Line 5",
        "Line 6",
        "Line 7",
        "Line 8",
        "Line 9",
        "Line 10",
    ]
