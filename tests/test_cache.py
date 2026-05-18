from pathlib import Path

import pytest

from bard.cache import (
    get_audio_files_from_cache,
    is_parent_directory,
    parse_file,
)


# ---------------------------------------------------------------------------
# parse_file
# ---------------------------------------------------------------------------

TS = "2026-05-18T120000.000000"


@pytest.mark.parametrize(
    "name, expected",
    [
        # Current format: chunk_<ts>_<backend>_<voice>_<index>.<ext>
        (f"chunk_{TS}_openai_alloy_0.mp3", (TS, 0)),
        (f"chunk_{TS}_openai_alloy_7.mp3", (TS, 7)),
        (f"chunk_{TS}_piper_en_US-amy-medium_3.wav", (TS, 3)),
        # Intermediate format: chunk_<ts>_<backend>_<index>.<ext>
        (f"chunk_{TS}_openai_2.mp3", (TS, 2)),
        # Old format (no backend/voice): still parses.
        (f"chunk_{TS}_5.mp3", (TS, 5)),
        # Merged file, no index: returns index = -1.
        (f"merged_{TS}.mp3", (TS, -1)),
    ],
)
def test_parse_file_known_formats(name, expected):
    assert parse_file(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "random_file.mp3",
        "chunk_not-a-timestamp_0.mp3",
        "chunk_2026-05-18.mp3",
        "manifest_2026-05-18T120000.000000_openai_alloy.json",
        "",
    ],
)
def test_parse_file_unrecognized_returns_none_zero(name):
    assert parse_file(name) == (None, 0)


def test_parse_file_accepts_path_objects():
    p = Path(f"/tmp/cache/chunk_{TS}_openai_alloy_4.mp3")
    assert parse_file(p) == (TS, 4)


# ---------------------------------------------------------------------------
# get_audio_files_from_cache
# ---------------------------------------------------------------------------

def _touch(dir_: Path, name: str) -> Path:
    p = dir_ / name
    p.write_bytes(b"")
    return p


def test_returns_empty_list_when_cache_empty(tmp_path):
    assert get_audio_files_from_cache(cache_dir=tmp_path) == []


def test_returns_chunks_of_latest_batch_by_default(tmp_path):
    old_ts = "2026-05-17T100000.000000"
    new_ts = "2026-05-18T120000.000000"
    _touch(tmp_path, f"chunk_{old_ts}_openai_alloy_0.mp3")
    _touch(tmp_path, f"chunk_{old_ts}_openai_alloy_1.mp3")
    new_files = [
        _touch(tmp_path, f"chunk_{new_ts}_openai_alloy_0.mp3"),
        _touch(tmp_path, f"chunk_{new_ts}_openai_alloy_1.mp3"),
        _touch(tmp_path, f"chunk_{new_ts}_openai_alloy_2.mp3"),
    ]
    result = get_audio_files_from_cache(cache_dir=tmp_path)
    assert sorted(result) == sorted(new_files)


def test_chunks_within_batch_are_sorted_by_index(tmp_path):
    ts = "2026-05-18T120000.000000"
    # Create in shuffled order on disk; glob order is not deterministic.
    for i in [2, 0, 1]:
        _touch(tmp_path, f"chunk_{ts}_openai_alloy_{i}.mp3")
    result = get_audio_files_from_cache(cache_dir=tmp_path)
    assert [p.name for p in result] == [
        f"chunk_{ts}_openai_alloy_0.mp3",
        f"chunk_{ts}_openai_alloy_1.mp3",
        f"chunk_{ts}_openai_alloy_2.mp3",
    ]


def test_merged_supersedes_chunks_in_same_batch(tmp_path):
    ts = "2026-05-18T120000.000000"
    _touch(tmp_path, f"chunk_{ts}_openai_alloy_0.mp3")
    _touch(tmp_path, f"chunk_{ts}_openai_alloy_1.mp3")
    merged = _touch(tmp_path, f"merged_{ts}.mp3")
    result = get_audio_files_from_cache(cache_dir=tmp_path)
    assert result == [merged]


def test_index_selects_specific_batch(tmp_path):
    ts1 = "2026-05-16T100000.000000"
    ts2 = "2026-05-17T100000.000000"
    ts3 = "2026-05-18T100000.000000"
    b1 = _touch(tmp_path, f"chunk_{ts1}_openai_alloy_0.mp3")
    b2 = _touch(tmp_path, f"chunk_{ts2}_openai_alloy_0.mp3")
    b3 = _touch(tmp_path, f"chunk_{ts3}_openai_alloy_0.mp3")
    assert get_audio_files_from_cache(index=0, cache_dir=tmp_path) == [b1]
    assert get_audio_files_from_cache(index=1, cache_dir=tmp_path) == [b2]
    assert get_audio_files_from_cache(index=-1, cache_dir=tmp_path) == [b3]


def test_invalid_index_falls_back_to_last_batch(tmp_path):
    ts = "2026-05-18T120000.000000"
    last = _touch(tmp_path, f"chunk_{ts}_openai_alloy_0.mp3")
    # Out-of-range index falls back to the last batch rather than raising.
    assert get_audio_files_from_cache(index=99, cache_dir=tmp_path) == [last]


def test_json_manifests_are_ignored(tmp_path):
    ts = "2026-05-18T120000.000000"
    audio = _touch(tmp_path, f"chunk_{ts}_openai_alloy_0.mp3")
    _touch(tmp_path, f"manifest_{ts}_openai_alloy.json")
    assert get_audio_files_from_cache(cache_dir=tmp_path) == [audio]


# ---------------------------------------------------------------------------
# is_parent_directory
# ---------------------------------------------------------------------------

def test_is_parent_directory_true_for_direct_child(tmp_path):
    child = tmp_path / "file.txt"
    child.write_text("")
    assert is_parent_directory(tmp_path, child) is True


def test_is_parent_directory_true_for_nested_child(tmp_path):
    nested = tmp_path / "a" / "b" / "c.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("")
    assert is_parent_directory(tmp_path, nested) is True


def test_is_parent_directory_false_for_sibling(tmp_path):
    other = tmp_path.parent / (tmp_path.name + "_other")
    assert is_parent_directory(tmp_path, other) is False


def test_is_parent_directory_false_for_self(tmp_path):
    # A directory is not a parent of itself.
    assert is_parent_directory(tmp_path, tmp_path) is False
