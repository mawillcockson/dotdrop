"""
common, standalone types and interfaces
"""
from pathlib import Path
from typing import TYPE_CHECKING, AnyStr, Generic, Protocol
from unittest.mock import Mock

if TYPE_CHECKING:
    from typing import Union, Type


class PathInterface(Protocol[AnyStr]):
    "abstraction of the used parts of pathlib.Path and os.path"
    # inspired by a YouTube video of someone describing abstracting the
    # filesystem interface to make it mock-able

    # positional-only parameter syntax was first introduced in Python 3.8:
    # https://docs.python.org/3/whatsnew/3.8.html#positional-only-parameters
    def __init__(self, path: "Union[AnyStr, Path, PathInterface]", /):
        "initialize a path object"
        raise NotImplementedError

    def read_text(self, *, encoding: str) -> str:
        "reads the entire contents of the file"
        raise NotImplementedError

    def resolve(self, *, strict: bool = False) -> "PathInterface":
        """
        Make the path absolute, resolving all symlinks on the way and also
        normalizing it (for example turning slashes into backslashes under
        Windows).
        """
        raise NotImplementedError

    def write_text(self, text: str, /, *, encoding: str) -> None:
        """
        writes the string to the file in text mode, overwriting the current
        contents
        """
        raise NotImplementedError

    def __truediv__(
        self, other: "Union[AnyStr, Path, PathInterface]", /
    ) -> "PathInterface":
        "allow Path('dir') / Path('file') -> Path('dir/file')"
        return NotImplementedError

    def __fspath__(self) -> AnyStr:
        "return a str or bytes representation of the filesystem path"
        raise NotImplementedError

    def __str__(self) -> str:
        "return the str representation of the filesystem path"
        raise NotImplementedError


class APath(Generic[AnyStr]):
    """
    an implementation of PathInterface that passes everything to real functions
    on pathlib.Path and in os.path
    """

    def __init__(self, path: "Union[AnyStr, Path, APath]", /):
        "record the path object"
        if isinstance(path, Path):
            self._path: Path = path
        elif isinstance(path, APath):
            self._path = path._path
        else:
            self._path = Path(path)

    def read_text(self, *, encoding: str) -> str:
        "reads the entire contents of the file"
        return self._path.read_text(encoding=encoding)

    def resolve(self, *, strict: bool = False) -> "APath":
        """
        Make the path absolute, resolving all symlinks on the way and also
        normalizing it (for example turning slashes into backslashes under
        Windows).
        """
        self._path = self._path.resolve(strict=strict)
        return self

    def write_text(self, text: str, /, *, encoding: str) -> None:
        """
        writes the string to the file in text mode, overwriting the current
        contents
        """
        self._path.write_text(text, encoding=encoding)

    def __truediv__(self, other: "Union[AnyStr, Path, APath]", /) -> "APath":
        "allow Path('dir') / Path('file') -> Path('dir/file')"
        if not isinstance(other, (Path, bytes, str, APath)):
            raise NotImplementedError(
                f"cannot divide {self!r} by {other!r}, unkown type {type(other)}"
            )

        if isinstance(other, (Path, bytes, str)):
            self._path = self._path / other
        if isinstance(other, APath):
            self._path = self._path / other._path

        return self
    def __fspath__(self) -> AnyStr:
        "return a str or bytes representation of the filesystem path"
        return self._path.__fspath__()
    def __str__(self) -> str:
        "return the str representation of the filesystem path"
        return str(self._path)


class PathMockError(Exception):
    "exception for the test version of the path interface"


def path_interface_mock() -> Mock:
    "makes a test double that matches the PathInterface"
    # I like that with mocks I can make assertions about their calls. It makes
    # it easier to tell if a file was written to twice vs once. I could write
    # my own recording instrumentation, but I'm more confident in Mock's.
    # Unfortunately, subclassing Mock disables call recording for methods
    # defined on the subclass.
    path: Path = Path()
    content: bytes = b""
    mock = Mock(
        spec_set=("read_text", "resolve", "write_text", "__truediv__", "__str__", "__fspath__")
    )
    # Raise an error whenever a method that the mock doesn't have is called,
    # instead of the default of returning a copy of the mock
    mock.return_value = PathMockError(f"unexpected call")
    mock.side_effect = __init__

    def __init__(path: "Union[AnyStr, Path, APath]", /) -> None:
        "record the path object"
        if isinstance(path, Path):
            path = path
        elif isinstance(path, APath):
            path = path._path
        else:
            path = Path(path)

        return 

    def read_text(*, encoding: str) -> str:
        "reads the entire contents of the file"
        return content.decode(encoding=encoding)

    def resolve(*, strict: bool = False) -> Mock:
        """
        Make the path absolute, resolving all symlinks on the way and also
        normalizing it (for example turning slashes into backslashes under
        Windows).
        """
        # Don't want to actually check for the existence of anything
        path = path.resolve(strict=False)
        return mock

    def write_text(text: str, /, *, encoding: str) -> None:
        """
        writes the string to the file in text mode, overwriting the current
        contents
        """
        content = text.encode(encoding=encoding)

    def __truediv__(self: Mock, other: "Union[AnyStr, Path, APath]", /) -> Mock:
        "allow Path('dir') / Path('file') -> Path('dir/file')"
        if not isinstance(other, (Path, bytes, str, APath)):
            raise NotImplementedError(
                f"cannot divide {mock!r} by {other!r}, unkown type {type(other)}"
            )

        if isinstance(other, (Path, bytes, str)):
            path = path / other
        if isinstance(other, APath):
            path = path / other._path

        return self

    mock.read_text.side_effect = read_text
    mock.resolve.side_effect = resolve
    mock.write_text.side_effect = write_text
    mock.__truediv__.side_effect = __truediv__

    return mock
