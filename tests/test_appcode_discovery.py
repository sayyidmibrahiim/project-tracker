from infrastructure.filesystem import discover_appcodes, AppCodeEntry


def test_discover_appcodes_finds_registered(tmp_path):
    appcode_dir = tmp_path / "MYAPP"
    appcode_dir.mkdir()
    (appcode_dir / "appcode.json").write_text('{"display_name":"My App"}', encoding="utf-8")
    (tmp_path / "plain").mkdir()
    result = discover_appcodes(tmp_path)
    assert len(result) == 1
    assert result[0].name == "MYAPP"
    assert result[0].config.display_name == "My App"


def test_discover_appcodes_empty_root(tmp_path):
    assert discover_appcodes(tmp_path) == []


def test_discover_appcodes_skips_plain_folders(tmp_path):
    (tmp_path / "noconfig").mkdir()
    assert discover_appcodes(tmp_path) == []
