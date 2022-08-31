# Progress on [Windows Support][]

`dotdrop --help` produces:

```
[ERR] The tool "file" was not found in the PATH!
```

## Codebase review

### `dotdrop.py`

The use of `\` to continue lines in import statements makes me want to run
`black` on the whole project, but I think the code is in quite a readable state
as-is.

It looks like a lot of functions in `dotdrop.dotdrop` take `opts` as their
first parameter, and that looks perfect for making into a class with a `self`
object, to reduce having to pass the context to every call.

I definitely want the throw in as much `pathlib` as I can, replacing `os.path`,
but I'm not sure if it'd make the codebase any better. There are a few spots
that would improve, but would it make the whole thing more readable? I could
replace some functions at a time, converting strings to `Path` objects inside
the function, and if it's enough, _then_ go through and refactor everything.

From the brief overview, the `dotdrop.dotdrop` module seems like it's already
almost perfectly formatted for use with `Typer` or `click` or something that
decorates functions as cli arguments (e.g. the functions prefixed with `cmd_`).

Line `656`: the helper functions that instantiate a class using the `opts`
context look like what would be included in an `__init__()`, furthering the
case for making a class.

Line `685`: why are the double quotes escaped, inside a single-quotes string?

Line `817`: the time recording could be done more reliably with a context manager:

```python
time = Timer()

with time("options"):
    ...

log(time.results)
# {
#     "options": 0.02,
#     ...
# }
```

Many variables can be renamed to clarify intent (e.g. line `833`: `ret` would be better as `success` in my opinion).

I didn't realize dotdrop used multithreading. I've generally avoided it, as it's seemed a bit complicated. I don't see any reason to change it out for `trio` or something async, though I do want to as I generally find that to be easier to reason about. This doesn't heavily use it, though.

### `utils.py`

The fully qualified imports of `dotdrop` components makes me uneasy: I wonder
if it would reduce code reuse and make other parts easier if things like
`Logger()` didn't have to be imported in a lot of modules, and could instead be
imported from one place.

I realize this comes from my subpar understanding of Python imports, and at
least for `Logger()` it makes sense to have one per-module, to make tracing of
logs easier, if the module is included in the location of the message.

Line `33`: switching to `pathlib.Path` would ensure things like
`os.path.expanduser('~/.config')` are expanded using the appropriate `os.sep`,
though this might only be useful when printing the paths for humans, as long as
the other parts are fine with mixing separators and are separator-agnostic.

`utils.run` is a straight wrapper around `subprocess.run`, which has been in
Python since 3.5. It also doesn't close the process, and so should at least use
`Popen`'s context manager support (e.g. a `with` block).

I wonder how many places `utils.get_tmpdir()` is called, and if the global
`TMPDIR` variable can be replaced with a context manager that's guaranteed to
clean up its state, even if Python has to bail.

Also, `utils.get_tmpdir` uses `tempfile.mkdtemp()` instead of
`tempfile.TemporaryDirectory`, while `utils.get_tmpfile` uses
`tempfile.NamedTemporaryFile`.

Line `125`: in general, I'm probably going to change these to create a
temporary variable so it's easier to see that an attribute is being returned,
rather than the whole object.

Line `135`: I'll want to investigate where the `logger` parameter is coming
from, and see if it can't be folded into `LOG=Logger()`.

Line `188`: This function doesn't quite do what its docstring says it does. A CRLF in Python is `\r\n`. However, this may be for processing strings that come from a file that's been opened with univeral newline support, normalizing all line endings to `\n`. Still, this entire function could probably be replaced with `if not string.strip(): ...`, as that removes all leading and trailing whitespace, and if the string is only whitespace, it becomes an empty string which evaluates as false. However, it may be important to ensure only a maximum of one newline is present to be considered empty.

As-is, I think the function would be better as:

```python
def content_empty(string: bytes) -> bool:
    return string in [b"", b"\n"]:
```

`utils.strip_home()` should definitely be implemented with `Path`, as I don't
trust string manipulation to handle evaluating file paths:

```python
def strip_home(path: Path) -> Path:
    home = Path.home()
    if home in path.parents:
        return path.relative_to(home)
    return path
```

[From the note on
`Path.relative_to()`](https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.relative_to),
it seems like the original function is basically what `pathlib` does currently,
anyways.

Line `291`: misspelling in docstring.

`utils.dependencies_met()` looks like it's unfinished? Unless there aren't any dependencies?

GitHub blame leads to:

- 

### `dotdrop.sh`

This has a number of quoting uncertainties, like `opwd=$(pwd)` does not record
correct results when the current working directory has spaces in it.

Also, what's the point of pivoting back if this is run as a script and not with
`source`? If it's only intended to be run as a script, then the last line could
be `exec`.

Why test one command's existence by using it (`9`), then check another's with `hash`?

Line `18`: I'm not sure the bash-specific features are necessary if the
argument list isn't processed by the script. I think `$*` would to the same, as
then shell-quoting would be re-applied for the subsequent function call, so no
weird quoting issues would arise? Actually, looking at `pyenv`, it uses `exec
"$command" "$@"`. `$*` would cause quoting issues; `"$@"` would pass along the
arguments as the shell interpreted them when they were passed in.

Lastly, why is it important to resolve symlinks in the first place? If the
`dotdrop.sh` file is a symlink, does that prevent it from functioning properly?

It looks like it's to help run `dotdrop` with the directory `dotdrop.sh` is
_really_ in as the current one, so that it can find the `config.yaml` file
that's supposed to be relative to that directory, and so it can set
`PYTHONPATH` so Python has access to the dotdrop package in that directory.

I'm not sure that Python can run dotdrop with only access to the package
directory, as dotdrop relies on other packages being installed.

The first part can also be obviated by adding a feature for reliably indicating
where `config.yaml` is located.

This would aid Windows, which can have symlinks disabled, or something like
that.

I would eventually like to phase out this shell-script in favor of running the
`console_scripts` entry points directly.

If I were to do that, the shell script would just directly call `dotdrop` with
the passed arguments, but not before issuing a deprecation notice, for those
that have auto updates enabled.

Also, there were some comments about using `python3` vs. `python`, and that
affecting running the script in contexts where `python3` isn't needed as
`python2` is phased out, and it would increase the startup time, but testing
for a `python3` first, using that preferentially, and falling back to `python`
after testing it to see what version it is, would solve this, I think:

```sh
if command -v "python3" > /dev/null 2>&1; then
    PYTHON="python3"
elif command -v "python" && python -c "import sys;sys.exit(0 if sys.version_info[0]==3 else 1)" ; then
    PYTHON="python"
else
    echo "cannot find Python 3"
    exit 1
fi
```

### `templategen.py`

It looks like `dotdrop` uses the Unix `file` command in case the package [`magic`][magic pypi] is missing, and both to determine whether a template file is binary or text.

Before looking at the two functions that handle text and binary template files, respectively, [`magic`][magic pypi] is a module with only a single verion uploaded in 2003, and a link to a website that no longer works.

On second thought, it looks like [`python-magic`][] is a package that exports the `magic` module, and is also what's listed in the `requirements.txt`.

That makes much more sense.

So `utils.dependencies_met()` can check for `file` only if it can't find `magic`.

Also, it looks like the canonical [`python-magic`][] package does not bundle the C library it's wrapping, even though that should be possible now. It's also Linux only.

It could be possible to re-use these. There's also a [circa 2014 alpha-level, abandoned project to wrap the library with Cython for Python 2,][python cymagic] which could be cleaned up with what looks to be only minor effort. Since the repository available from the link has a broken hardlink in the tar file, [I included a new one in this repository][python-cymagic.txz]. I believe this would enable builds with the library bundled. [A circa 2009 attempt was made with Python 3][pyfilemagic].

There is the [`python-magic-bin`][] library that looks like it has support for loading the binaries required on Windows, but still doesn't lool like it bundles the libraries with the package wheel.

It does point to a couple projects:

- [File for Windows](http://gnuwin32.sourceforge.net/packages/file.htm) (ca. 2009)
- [nscaife/file-windows](https://github.com/nscaife/file-windows) (currently maintained)

There's also a [(currently ongoing) discussion about how to bundle the libraries and data with `python-magic`][typecode discussion], and the person who proposed the discussion has made the package [`typecode`][] which does bundle these things.

It could be possible to re-implement the library in pure Python, but at probably significant effort.

What's the code being used for anyways? That's the important part. I suspect if it's just being decoded, a `try: / except:` could be used to attempt decoding to text, and fall back to binary, obviating the need for the library and program in the first place.

It looks like it only templates text files, and binary files are copied unmodified.

However, if the file is detected as text, but it can't be decoded, it won't be templated and instead will be decoded, with the undecodable sequences replaces with the Unicode replacement character.

That to me sounds like it's modifying data that it doesn't need to. A round trip of "copy into place" then "update from in-place" would result in changes to the original file in the repository. I think it would be better to make the templating something that has to be explicitly opted into, and make it fail if the whole file isn't perfectly decodable.

Another slightly lesser worry is that it's reading the whole file into memory, then passing that around. I wonder if that's what the comment in `_handle_bin_file()` is alluding to.

Might be better to only do that with templating, and leave the copying to something like `shutil.copy2()`

If there's a strong desire to keep the same behaviour, [`cdgriffith/puremagic`][] is a pure-Python drop-in replacement for `python-magic` that looks to be currently maintained. The downside is it only uses magic numbers, instead of libmagic's other heuristics. I wonder if this will be good enough for text vs binary.

I still think the best option would be to make templating explicitly opt-in. That would reduce the magic behaviour, and may make the config file more verbose, but it would make it more predictable, and fail more predictably.

It would also eliminate a dependency.

### `tests/`

It looks like a lot of the tests rely on [`nose`, which has been in maintenance for a while now.][]

I think it would do a lot of good anyways to convert everything to `tox + pytest`, as reimplementing stuff is one of the best ways to become familiar with it.

#### `tests-ng/`

It would take a lot of time, but I think most of these can be converted to `pytest` tests, with the [`tmpdir` fixture][] providing space for file munging.

#### `tests.sh`

Checking for broken links is a good idea, and it would probably be easier to leave that as a shell script, but it could be possible to include it with `tox`, or find a suitable python-based alternative. [Especially since `remark-validate-links` requires nodejs,][remark-validate-links] though this is trivial to setup in CI.

Also, it will be nice to have the tool configuration passed as command line arguments to `pylint` and `pycodestyle` and `nose` folded into the `pyproject.toml`.

Line `48-52` is a bit confusing for me, as it looks like it could be shortened to:

```sh
[ -n "${DOTDROP_WORKERS}" ] && echo "DISABLE workers"
unset -v DOTDROP_WORKERS > /dev/null 2>&1
```

Ah, line `76`: it's storing the state of `DOTDROP_WORKERS` so it can disable it for a section, then re-enable it for a later part.

### `options.py`

I think the first thing to do is tackle the most disconnected part of the code,
define how it interfaces with the calling code, and rewrite it to be testable
while maintaining that interface.

I don't think it's the least tightly-coupled part, but having trust in the way
configuration data is collected and presented would be really useful in further
refactors/rewrites. Configuration seems to be the secondary concern of this
project, after filesystem interaction.

I am picturing using [`pydantic`][] to handle merging various configuration
sources, and using [`python-inject`][] to handle providing this configuration
data further down the call stack.

Tests should be easy to write, taking examples of valid and invalid
configuration files from existing tests and examples.

I would also like to have a test that demonstrates all the possible options in
the config file, as well as a minimal config file.

This way, when another function is supposed to manipulate and write to the
configuration file, it's much easier to make assertions about whether only the
specific portions the test is concerned with have been updated or not.

The main `Options` class is a bit odd, with how it subclasses from
`AttrMonitor`. I imagine `AttrMonitor` might have been intended to be an
abstract base class, with how it's `_attr_set` method is empty. I wonder how the
rest of the methods are used later, what with how the `__setattr__` method calls
its `super()`, which I _think_ is returning the `AttrMonitor` class.

```python
class _object:
    def __setattr__(self, key, value):
        print("in _object")
        return super().__setattr__(key, value)


class T(_object):
    def __setattr__(self, key, value):
        print("in T")
        return super().__setattr__(key, value)

class F(T): pass

F().hello = "world"
```

prints

```text
in T
in _object
```

Since every class without an explicit superclass subclasses `object`, I think
the `AttrMonitor` class doesn't do anything but prevent a value from being
returned from setting an attribute.

It looks like this was original added to help catch misnamed attributes:

<https://github.com/dotdrop/dotdrop/commit/ad2d74e0f18c3632b33e5d92f819e8a94b2a6c15>

The `pylint` config comment lines could also be condensed down to one line in
the scope of the function body.

I think vendoring this app's dependencies using something like [`vendoring`][]
should be considered after refactoring. [`pipx` supports running the app
directly from the source directory][pipx __main__.py], and I think that would be
useful for this app, too. Vendoring the dependencies would make it possible to
add the app's source code repository as a submodule, and then all that would be
needed would be a supported Python installation. No virtual environment, no
installation with `pip`, no adding packages to the system Python environment. It
would significantly decrease any bootstrapping necessary. I think it would
ultimately be cool, but I think a first step is to iron everything else out,
increase test coverage, and then consider vendoring dependencies. `pipx` can be
used to install the app in the meantime.

The `Options` class looks like it does the following:

- Sets a bunch of attributes to "empty" values
- If it wasn't called with `Options(args)`, it calls `docopt` here to do the
  argument parsing
- Sets the `debug` instance attribute to `True` if the `DOTDROP_DEBUG`
  environment variable is set at all, or if `--verbose` is given on the command
  line
- Allows the existence of `DOTDROP_FORCE_NODEBUG` to override `DOTDROP_DEBUG`
  and set `self.debug` to `False`
- `--dry` -> `self.dry`
- `--profile` -> `self.profile`
- `self.confpath` <- first of:
  - `osp.expanduser(--cfg)`
  - `osp.expanduser(os.environ["DOTDROP_CONFIG"])`
  - `./config.yaml`
  - `./config.toml`
  - `osp.join(osp.expanduser(os.environ["XDG_CONFIG_HOME"], "dotdrop", "config.yaml")`
  - `osp.join(osp.expanduser(os.environ["XDG_CONFIG_HOME"], "dotdrop", "config.toml")`
  - `osp.expanduser("~/.config/dotdrop/config.yaml")`
  - `/etc/xdg/dotdrop/config.yaml`
  - `/etc/dotdrop/config.yaml`
  - `osp.expanduser("~/.config/dotdrop/config.toml")`
  - `/etc/xdg/dotdrop/config.toml`
  - `/etc/dotdrop/config.toml`
- `Options()`
  - `Options._read_config()`
    - `CfgAggregator()`
      - `CfgAggregator._load()`
        - `CfgYaml._load_yaml()`
          - `CfgYaml._yaml_load()`
            - if suffix is `.toml`
              - `toml.loads()`
              - Creates keys for `dotdrop` and `profiles` if they didn't exist
              - The note indicates that `toml.loads()` doesn't handle empty empty
                sections, but it does, it just loads them as an empty dictionary, and
                when dumping if the section is `None`, it removes the key
            - else use `ruamel.yaml` to load the yaml file in "round-trip" mode, not
              "safe mode"
              - `CfgYaml.__yaml_load()`
- Fix deprecated configuration values:
  - `link_by_default` -> `link_on_import`
    - Mark the configuration as `_dirty` and `_dirty_deprecated`
  - `link: true/false` -> `link/nolink`
  - `link: link` -> `absolute`
  - `link_children: true/false` -> `link: link_children`
- `CfgYaml._validate()`
  - An empty dictionary validates
  - Do the following keys exist at top-level?
    - `config`
    - `dotfiles`
    - `profiles`
  - If `config` is empty, validate
  - Only fail if `link_dotfile_default` under `config` exists and isn't one of
    `LinkTypes`
- 
- `CfgAggregator._validate()`

It looks like it checks configuration data sources in the following order:

1. 

I think a good way to go about refactoring `Options` is to write a parallel
provider of the same interface, write tests to assert that it behaves the same,
increase test coverage of the existing interface (if possible), and then swap
one for the other.

The way I'm picturing the tests to be written is starting with functions that
take a configuration source (e.g. a file path) and return a dictionary. Those
source functions are called in the constructor for `Options`, but I'm not sure
that `Options` would be able to be called during its refactoring, so I think it
would be better to have a [`pydantic.BaseSettings`][] class that will replace
the current `Options`, and use that to test and compare what is sure to be a
nested dictionary data structure.

In the configuration sources, I saw that it would be nice to use
[`platformdirs`][], with the one caveat that [that package doesn't currently
use `XDG_CONFIG_HOME` on Windows and macOS platforms][platformdirs win XDG].
That can be worked around.

The `CfgYaml` class has a `_dbg` method defined on it which appears to be a
wrapper to print the file that caused the error. It also uses the `self._debug`
attribute to check if debugging is enabled. These functionalities can be folded
into the logging configuration: `self._debug` checks can be replaced with
setting a log level, and there are a few ways to add extra context to a logging
call, like a filter or formatter.

I think the [`with open(` used to re-read the config file][yaml debug] is an
arbitrary choice, as later, [`file.read()` is used to read a TOML file][toml
load].

The `CfgYaml` class has a `_load_yaml` method that may call `_yaml_load` which
may call `__toml_load` or `__yaml_load`. That seems like it could use some
de-nesting.

The `dotdropt/logger.py` file is also a good first candidate for refactoring, as
it looks like it provides a consistent interface that could easily be replaces
by Python's builtin logging framework. It might take a bit of work to have color
output, but I'm willing to sacrifice that for consistent use of a better logging
interface everywhere.

A lot of the options also look like they are set from `settings.Settings`,
which looks like it could be a dataclass. Not using dataclasses is
understandable, though, considering this project is designed to work on Python 3.5

I think I'm personally going to part ways with any Python prior to 3.7, and
anything earlier will be what I feel is useful to me.

That said, there is a [backport of dataclasses available to 3.6][dataclasses
backport], though CPython 3.6 has been end-of-life for 8 months at the time of
writing.

It also has `diff -r -u {0} {1}` as the `default_diff_command`, and I'm curious
why `diff` was chosen when it feels more guaranteed that `git` is installed. I
don't know if it's _that_ well-known that `git --no-index -- {0} {1}` works
outside `git` directories.

I think the unique construction of the warning message in `dotdrop/cfg_yaml.py`
on lines 1161--1163 is from `pylint` complaining that the line is too long in an
already heavily-indented section. I do want to use `isort` and `black`
everywhere, but I'm holding off on only doing the files I change, and only the
parts I work on.

I think it's a bit confusing how a lot of the names for config file keys are set
as `CfgYaml` class instance attributes, and stranger the seemingly arbitrary
split between some of them being defined directly on the class, and some being
imported from `dotdrop/settings.py`.

`dotdrop/cfg_yaml.py:1243` won't run, since the previous check emits an error if
that key is missing. Was the intent originally to allow validation to succeed
when that key is missing? [No, both checks were introduced by the same
commit.][9c54a524b765] I'm not sure what the intent was.

The `CfgYaml.allowed_link_val` attribute seems to be redundant when the values
it collects are checkable using the `dotdrop/linktypes.py:LinkTypes` enum.

The `CfgYaml._get_entry()` function returns a `deepcopy()` which is immediately
`.copy()`-d in a few places.

[issue]: <https://github.com/deadc0de6/dotdrop/issues/55>
[windows support]: <https://github.com/mawillcockson/dotdrop/projects/1>
[magic pypi]: <https://pypi.org/project/magic/#history>
[`python-magic`]: <https://pypi.org/project/python-magic/>
[`python-magic-bin`]: <https://github.com/julian-r/python-magic>
[typecode discussion]: <https://github.com/ahupp/python-magic/issues/233>
[`typecode`]: <https://github.com/nexB/typecode>
[python cymagic]: <https://bitbucket-archive.softwareheritage.org/projects/fc/fcayre/python-cymagic.html>
[pyfilemagic]: <https://github.com/chemoelectric/pyfilemagic>
[`cdgriffith/puremagic`]: <https://github.com/cdgriffith/puremagic>
[`shutil.copy2()`]: <https://docs.python.org/3/library/shutil.html#shutil.copy2>
[`tmpdir` fixture]: <https://docs.pytest.org/en/stable/reference.html#std-fixture-tmpdir>
[`nose`, which has been in maintenance for a while now.]: <https://nose.readthedocs.io/en/latest/#>
[python-cymagic.txz]: <https://github.com/mawillcockson/dotdrop/raw/4662d62c9a3e73e474732f390ea42e066b300fd9/python-cymagic.txz>
[remark-validate-links]: <https://github.com/remarkjs/remark-validate-links#install>
[`pydantic`]: <https://github.com/samuelcolvin/pydantic/>
[`python-inject`]: <https://github.com/ivankorobkov/python-inject>
[pipx __main__.py]: <https://github.com/pypa/pipx/blob/4c0f2892c8f932f345a379b84bffe816c7c7206c/src/pipx/__main__.py>
[`platformdirs`]: <https://github.com/platformdirs/platformdirs>
[platformdirs win XDG]: <https://github.com/platformdirs/platformdirs/issues/4>
[`pydantic.BaseSettings`]: <https://pydantic-docs.helpmanual.io/usage/settings/>
[yaml debug]: <https://github.com/mawillcockson/dotdrop/commit/e8f4d9afe859c9f981cd70ae359442fb54473e46#diff-9ece3374f74361dfb8d8302a46b66cf5c1c324f9411ca6ecea2e7703a847abd5R1001-R1008>
[toml load]: <https://github.com/mawillcockson/dotdrop/blob/81a306dd3903034eda47d26f022913dabcc733b7/dotdrop/cfg_yaml.py#L1281-L1282>
[dataclasses backport]: <https://github.com/ericvsmith/dataclasses>
[9c54a524b765]: <https://github.com/mawillcockson/dotdrop/commit/9c54a524b7654845ba1fa4d1591a5bb72cd3c03c#diff-9ece3374f74361dfb8d8302a46b66cf5c1c324f9411ca6ecea2e7703a847abd5R1025-R1034>
