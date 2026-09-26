"""Tests for the iterator helpers."""

from string import ascii_lowercase

from aio_remeha_modbus.helpers.iterators import consecutive_groups


def test_consecutive_groups_numbers():
    """Test that runs of numbers are grouped."""

    groups = [list(group) for group in consecutive_groups([1, 10, 11, 12, 20, 30, 31, 32, 33, 40])]
    assert groups == [[1], [10, 11, 12], [20], [30, 31, 32, 33], [40]]


def test_consecutive_groups_ordering():
    """Test that a custom ordering determines adjacency."""

    groups = [
        list(group) for group in consecutive_groups("abcdfgilmnop", ordering=ascii_lowercase.index)
    ]
    assert groups == [["a", "b", "c", "d"], ["f", "g"], ["i"], ["l", "m", "n", "o", "p"]]


def test_consecutive_groups_empty():
    """Test that an empty iterable yields no groups."""

    assert list(consecutive_groups([])) == []


def test_consecutive_groups_single_group():
    """Test that a fully consecutive iterable yields one group."""

    assert [list(group) for group in consecutive_groups(range(5))] == [[0, 1, 2, 3, 4]]
