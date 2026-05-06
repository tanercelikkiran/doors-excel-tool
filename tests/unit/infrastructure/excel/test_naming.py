"""Unit tests for Excel sheet-naming helpers (REQ-FUN-113.1)."""
from __future__ import annotations

import pytest

from doors_excel.infrastructure.excel.naming import (
    MAX_SHEET_NAME_LEN,
    crc32_hex8,
    make_sheet_name,
    sanitize_module_name,
)


class TestSanitizeModuleName:
    """REQ-FUN-113.1 sanitization: trim then replace forbidden chars."""

    def test_plain_name_unchanged(self) -> None:
        assert sanitize_module_name("SystemRequirements") == "SystemRequirements"

    def test_leading_trailing_whitespace_trimmed(self) -> None:
        assert sanitize_module_name("  My Module  ") == "My Module"

    def test_backslash_replaced(self) -> None:
        assert sanitize_module_name("A\\B") == "A_B"

    def test_forward_slash_replaced(self) -> None:
        assert sanitize_module_name("A/B") == "A_B"

    def test_question_mark_replaced(self) -> None:
        assert sanitize_module_name("A?B") == "A_B"

    def test_asterisk_replaced(self) -> None:
        assert sanitize_module_name("A*B") == "A_B"

    def test_open_bracket_replaced(self) -> None:
        assert sanitize_module_name("A[B") == "A_B"

    def test_close_bracket_replaced(self) -> None:
        assert sanitize_module_name("A]B") == "A_B"

    def test_colon_replaced(self) -> None:
        assert sanitize_module_name("A:B") == "A_B"

    def test_multiple_forbidden_chars(self) -> None:
        assert sanitize_module_name("A/B\\C?D") == "A_B_C_D"

    def test_trim_then_replace_order(self) -> None:
        # Leading whitespace trimmed first, then forbidden chars replaced
        assert sanitize_module_name("  A/B  ") == "A_B"

    def test_trim_then_replace_leading_forbidden(self) -> None:
        # Leading whitespace + forbidden char right after
        assert sanitize_module_name("  [Module]  ") == "_Module_"

    def test_empty_string(self) -> None:
        assert sanitize_module_name("") == ""

    def test_only_whitespace(self) -> None:
        assert sanitize_module_name("   ") == ""


class TestCrc32Hex8:
    """CRC32 must be unsigned, 8-char zero-padded lower-hex string."""

    def test_returns_string(self) -> None:
        result = crc32_hex8("/Project/Module")
        assert isinstance(result, str)

    def test_exactly_8_chars(self) -> None:
        assert len(crc32_hex8("/Project/Module")) == 8

    def test_lowercase_hex(self) -> None:
        result = crc32_hex8("/Project/Module")
        assert result == result.lower()
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self) -> None:
        assert crc32_hex8("/same/path") == crc32_hex8("/same/path")

    def test_different_paths_differ(self) -> None:
        assert crc32_hex8("/a/b") != crc32_hex8("/a/c")

    def test_unsigned_no_leading_minus(self) -> None:
        # Python signed CRC32 can produce negative numbers; result must not start with '-'
        for path in ["/a", "/b", "/c/d/e", "X" * 100]:
            assert not crc32_hex8(path).startswith("-")

    def test_zero_padded_short_crc(self) -> None:
        # Construct a string whose CRC32 is 0 (edge case for zero padding)
        # We don't know which string gives CRC=0, but we can verify the format invariant
        # by checking that a short hex value is still 8 chars.
        result = crc32_hex8("")
        assert len(result) == 8


class TestMakeSheetName:
    """REQ-FUN-113.1: Sanitize(name)[:22] + '_' + CRC32(path) <= 31 chars."""

    MAX = MAX_SHEET_NAME_LEN  # 31

    def test_short_name(self) -> None:
        name = make_sheet_name("Reqs", "/proj/Reqs")
        assert len(name) <= self.MAX
        assert name.endswith("_" + crc32_hex8("/proj/Reqs"))

    def test_name_truncated_to_22(self) -> None:
        long_name = "A" * 30
        result = make_sheet_name(long_name, "/proj/Long")
        prefix = result.split("_")[0]
        assert len(prefix) <= 22

    def test_total_length_le_31(self) -> None:
        result = make_sheet_name("SystemRequirementsDocument", "/proj/SRD")
        assert len(result) <= 31

    def test_forbidden_chars_sanitized(self) -> None:
        result = make_sheet_name("A/B\\C", "/proj/A")
        assert "/" not in result
        assert "\\" not in result

    def test_structure_name_underscore_crc(self) -> None:
        result = make_sheet_name("MyModule", "/project/MyModule")
        parts = result.rsplit("_", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 8  # CRC hex

    def test_empty_path_still_valid(self) -> None:
        result = make_sheet_name("Module", "")
        assert len(result) <= self.MAX

    def test_uniqueness_same_name_different_paths(self) -> None:
        r1 = make_sheet_name("SRS", "/project/A/SRS")
        r2 = make_sheet_name("SRS", "/project/B/SRS")
        assert r1 != r2
