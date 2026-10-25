from practice.grade import is_correct, normalize


def test_int():
    assert is_correct(" 1,234 ", "1234", "int")
    assert is_correct("42.0", 42, "int")
    assert not is_correct("abc", "5", "int")
    assert not is_correct("5", "6", "int")
    assert not is_correct(None, "6", "int")


def test_str():
    assert is_correct("  Hello   World ", "hello world", "str")
    assert not is_correct("hello", "hello world", "str")
    assert normalize("A\tB", "str") == "a b"


def test_grid():
    assert is_correct("1 2 3\n4 5 6", "123\n456", "grid")
    assert is_correct("123 \n\n 456\n", "123\n456", "grid")
    assert is_correct("[1,2,3]\n[4,5,6]", "123\n456", "grid")
    assert not is_correct("123\n457", "123\n456", "grid")
    assert not is_correct("123", "123\n456", "grid")
    assert not is_correct("", "123", "grid")


def test_bad_type():
    import pytest
    with pytest.raises(ValueError):
        normalize("x", "foo")
