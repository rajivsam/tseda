import pytest

from tseda.config.config_loader import ConfigurationManager, get_config, get_config_section


def test_load_config_returns_dict_and_uses_cached_values():
    ConfigurationManager.reset()
    config = ConfigurationManager.load_config()
    assert isinstance(config, dict)
    assert config["file_upload"]["min_sampling_frequency_minutes"] == 5
    assert config["file_upload"]["max_file_lines"] == 5000

    # Cached values are reused until reload/reset is invoked.
    ConfigurationManager._config["test_marker"] = 123
    cached = ConfigurationManager.load_config()
    assert cached["test_marker"] == 123


def test_get_config_returns_default_and_section_fallback():
    ConfigurationManager.reset()
    assert get_config("file_upload.min_sampling_frequency_minutes") == 5
    assert get_config("file_upload.max_file_lines") == 5000
    assert get_config("does.not.exist", "fallback") == "fallback"
    assert get_config_section("window_selection")["hourly"] == 24
    assert get_config_section("window_selection")["subhourly_cycle_minutes"] == 1440
    assert get_config_section("missing_section") == {}


def test_reload_clears_existing_cache():
    ConfigurationManager.reset()
    loaded = ConfigurationManager.load_config()
    loaded["temporary_key"] = True
    reloaded = ConfigurationManager.reload()
    assert "temporary_key" not in reloaded
    assert reloaded["file_upload"]["min_sampling_frequency_minutes"] == 5
    assert reloaded["file_upload"]["max_file_lines"] == 5000
