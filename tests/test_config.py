from multi_agent_memory.config import Settings


def test_yaml_config_and_environment_override(tmp_path, monkeypatch):
    config = tmp_path / "settings.yaml"
    config.write_text("vault: yaml-vault\nrecall_limit: 3\n", encoding="utf-8")
    monkeypatch.setenv("AGENT_MEMORY_VAULT", str(tmp_path / "environment-vault"))
    settings = Settings.load(config)
    assert settings.vault == (tmp_path / "environment-vault").resolve()
    assert settings.recall_limit == 3


def test_invalid_recall_limit_is_rejected(tmp_path):
    config = tmp_path / "settings.yaml"
    config.write_text("recall_limit: 0\n", encoding="utf-8")
    try:
        Settings.load(config)
    except ValueError as error:
        assert "recall_limit" in str(error)
    else:
        raise AssertionError("invalid recall limit was accepted")


def test_auto_sync_adapters_can_be_disabled(tmp_path, monkeypatch):
    config = tmp_path / "settings.yaml"
    config.write_text("auto_sync_adapters: false\n", encoding="utf-8")
    monkeypatch.delenv("AGENT_MEMORY_AUTO_SYNC_ADAPTERS", raising=False)

    assert Settings.load(config).auto_sync_adapters is False
