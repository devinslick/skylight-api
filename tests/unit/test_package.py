"""Tests for the public package surface."""

import skylight_api


def test_version_is_declared():
    assert skylight_api.__version__ == "0.1.0"


def test_all_exports_resolve():
    for name in skylight_api.__all__:
        assert hasattr(skylight_api, name), name


def test_exception_hierarchy():
    assert issubclass(skylight_api.SkylightAuthError, skylight_api.SkylightError)
    assert issubclass(skylight_api.SkylightAPIError, skylight_api.SkylightError)
    assert issubclass(skylight_api.SkylightError, Exception)


def test_api_error_str_includes_status():
    err = skylight_api.SkylightAPIError("boom", status_code=422)
    assert "422" in str(err)
