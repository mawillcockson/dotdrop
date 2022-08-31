"""
Is the Version tuple well-behaved, and can the current __version__ be parsed
into it?
"""
from re import escape as e
from typing import TYPE_CHECKING

import pytest

import dotdrop
from dotdrop.defaults import Settings, Version

if TYPE_CHECKING:
    from typing import Type


def test_version_from_str() -> None:
    "can major.minor.patch be used?"
    assert Version.parse("0.0.0") == Version(major=0, minor=0, patch=0)


def test_version_to_str() -> None:
    "does Version display as major.minor.patch?"
    version = Version(major=3, minor=10, patch=4)
    assert str(version) == "3.10.4"


@pytest.mark.parametrize(
    "value,exc,message",
    [
        (3, TypeError, "expected Version, tuple, or str; got"),
        ((3, 10), ValueError, "expected a tuple of 3 positive integers"),
        ("3.10", ValueError, "expected format is 'major.minor.patch'"),
        ("3.10.", ValueError, "invalid literal for int"),
        ("3.10.x", ValueError, "invalid literal for int"),
        ((-1, 0, 0), ValueError, "expected a tuple of 3 positive integers"),
        ("-1.0.0", ValueError, "all parts must be greater than 0"),
    ],
)
def test_version_parse_bad_values(
    value: str, exc: "Type[Exception]", message: str
) -> None:
    "do these values fail to validate?"
    with pytest.raises(exc, match=e(message)) as exc_info:
        Version.parse(value)

    # the note that points to the Python documentation on the try statement
    # says that deleting this breaks a circular dependency and allows the GC to
    # collect it:
    # https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest-raises
    del exc_info


def test_settings_constructor_str() -> None:
    "can the Settings.minversion attribute be passed a str?"
    minversion = Settings(minversion="3.10.4").minversion
    assert minversion == Version(major=3, minor=10, patch=4)


def test_settings_constructor_tuple() -> None:
    "can the Settings.minversion attribute be passed a tuple?"
    minversion = Settings(minversion=(3, 10, 4)).minversion
    assert minversion == Version(major=3, minor=10, patch=4)


def test_settings_constructor_version() -> None:
    "can the Settings.minversion attribute be passed a Version?"
    minversion = Settings(minversion=Version(3, 10, 4)).minversion
    assert minversion == Version(major=3, minor=10, patch=4)


@pytest.mark.xfail(reason="not worth fixing")
def test_version_underscores() -> None:
    "will integers with underscores fail?"
    with pytest.raises(ValueError, match=e("underscores not allowed")) as exc_info:
        Version.parse("3.1_0.4")

    del exc_info


def test_module_version() -> None:
    "can the module version be parsed into a Version, and back?"
    version = Version.parse(dotdrop.version.__version__)
    assert dotdrop.version.__version__ == str(
        version
    ), "version string doesn't round trip"
