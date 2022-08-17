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

Another slightly lesser worry is that it's reading the whole file into memory, then passing that around.

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

Checking for broken links is a good idea, and it would probably be easier to leave that as a shell script, but it could be possible to include it with `tox`, or find a suitable python-based alternative.

Also, it will be nice to have the tool configuration passed as command line arguments to `pylint` and `pycodestyle` and `nose` folded into the `pyproject.toml`.

Line `48-52` is a bit confusing for me, as it looks like it could be shortened to:

```sh
[ -n "${DOTDROP_WORKERS}" ] && echo "DISABLE workers"
unset -v DOTDROP_WORKERS > /dev/null 2>&1
```

Ah, line `76`: it's storing the state of `DOTDROP_WORKERS` so it can disable it for a section, then re-enable it for a later part.

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
