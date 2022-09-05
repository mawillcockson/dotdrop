"""
does the mock filesystem interface record all interactions?
"""
from dotdrop.types import path_interface_mock
import pytest

def test_read_write() -> None:
    "can a fake file be read to and written from"
    path.write_text("hello")
    text = path.read_text()
    assert text == 
