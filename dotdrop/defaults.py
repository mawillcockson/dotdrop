"""
default configuration values
"""
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, NamedTuple, Optional, Tuple, Union

from pydantic import BaseSettings, PositiveInt  # pylint: disable=no-name-in-module

from dotdrop.exceptions import YamlException
from dotdrop.linktypes import LinkTypes
from dotdrop.version import __version__ as VERSION

VersionLike = Tuple[PositiveInt, PositiveInt, PositiveInt]

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, Iterator

    VersionValidators = Iterator[
        Union[Callable[[VersionLike], Version], Callable[[str], Version]]
    ]


class Version(NamedTuple):
    """
    like sys.version_info

    allows use of built-in comparisons:

    if Settings.version < (1, 4, 0):

    Even works with checks for e.g. 1.x:

    Settings.version > (1,)
    """

    major: PositiveInt
    minor: PositiveInt
    patch: PositiveInt

    @classmethod
    def from_str(cls, val: str) -> "Version":
        "major.minor.patch to Version(major, minor, patch)"
        if not isinstance(val, str):
            raise TypeError(f"expected a str, got type {type(val)!r}")

        parts = val.split(".")
        if len(parts) != 3:
            raise ValueError(f"expected format is 'major.minor.patch', got {parts!r}")

        # allow ValueError to propagate
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2])

        if any(value < 0 for value in [major, minor, patch]):
            raise ValueError("all parts must be greater than 0")

        return cls(major, minor, patch)

    @classmethod
    def from_tuple(cls, val: "VersionLike") -> "Version":
        "(major, minor, patch) to Version(major, minor, patch)"
        if not isinstance(val, tuple):
            raise TypeError(f"expected a tuple, got type '{type(val)}'")

        if not (len(val) == 3 and all(isinstance(i, int) and i >= 0 for i in val)):
            raise ValueError(f"expected a tuple of 3 positive integers, got {val!r}")

        major = val[0]
        minor = val[1]
        patch = val[2]

        return cls(major, minor, patch)

    @classmethod
    def parse(cls, val: "Union[Version, str, VersionLike]") -> "Version":
        "tuples or str into Version"
        if isinstance(val, cls):
            return val
        if isinstance(val, str):
            return cls.from_str(val)
        if isinstance(val, tuple):
            return cls.from_tuple(val)
        raise TypeError(f"expected Version, tuple, or str; got {type(val)!r}")

    @classmethod
    def __get_validators__(cls) -> "VersionValidators":
        "for pydantic"
        yield cls.parse

    def __str__(self) -> str:
        "for pretty-printing"
        return f"{self.major}.{self.minor}.{self.patch}"


ENV_WORKDIR = "DOTDROP_WORKDIR"


class Settings(BaseSettings):
    # pylint: disable=too-few-public-methods
    "settings block in config"

    # backup: bool = True
    # banner: bool = True
    # create: bool = True
    # default_actions: "Optional[List[]]" = None
    # dotpath: str = "dotfiles"
    # ignoreempty: bool = False
    # keepdot: bool = False
    # longkey: bool = False
    # link_dotfile_default: LinkTypes = LinkTypes.NOLINK
    # link_on_import: LinkTypes = LinkTypes.NOLINK
    # showdiff: bool = False
    # upignore: "Optional[List[]]" = None
    # impignore: "Optional[List[]]" = None
    # cmpignore: "Optional[List[]]" = None
    # instignore: "Optional[List[]]" = None
    # The original implementation overrode any passed in value with the
    # environment variable, for this key specifically, but I think that's
    # because there was no way of differentiating between the default value
    # being passed, or a custom value being passed. I'd prefer the init value
    # to override the environment, as it would make testing more consistent,
    # and the environment variable overrides the default value already.
    workdir: Path = Path("~/.config/dotdrop").expanduser()
    minversion: Version = Version.from_str(VERSION)
    # func_file: Optional[str]
    # filter_file: Optional[str]
    # diff_command: str = ("git", "--no-index", "--")
    # force_chmod: bool = False
    # template_dotfile_default: bool = True
    # ignore_missing_in_dotdrop: bool = False
    # chmod_on_import: bool = False
    # check_version: bool = False
    # clear_workdir: bool = False
    # compare_workdir: bool = False
    # key_prefix: bool = True
    # key_separator: str = "_"

    # # import keys
    # import_actions: "Optional[List[]]" = None
    # import_configs: "Optional[List[]]" = None
    # import_variables: "Optional[List[]]" = None

    class Config:
        "pydantic model config"
        env_prefix = "dotdrop_"

        # self.func_file = func_file or []
        # self.filter_file = filter_file or []
        # self.diff_command = diff_command
        # self.template_dotfile_default = template_dotfile_default
        # self.ignore_missing_in_dotdrop = ignore_missing_in_dotdrop
        # self.force_chmod = force_chmod
        # self.chmod_on_import = chmod_on_import
        # self.check_version = check_version
        # self.clear_workdir = clear_workdir
        # self.compare_workdir = compare_workdir
        # self.key_prefix = key_prefix
        # self.key_separator = key_separator

        # # check diff command
        # if not is_bin_in_path(self.diff_command):
        #     err = 'bad diff_command: {}'.format(self.diff_command)
        #     raise YamlException(err)

    def serialize(self) -> "Dict[str, Any]":
        "return key-value pair representation of the settings"
        return {"config": self.dict()}
