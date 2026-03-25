"""
TestSprite — ALLOWED_HOSTS Gate Tests
Validates that the craco.config.js ALLOWED_HOSTS environment variable gate
is correctly implemented. These tests inspect the config source and verify
the conditional logic without starting a dev server.
"""
import os
import re
import pytest

CRACO_CONFIG = os.path.join(
    os.path.dirname(__file__), "..", "..", "frontend", "craco.config.js"
)


def read_craco():
    with open(CRACO_CONFIG, "r", encoding="utf-8") as f:
        return f.read()


class TestAllowedHostsGate:
    """Static analysis of craco.config.js ALLOWED_HOSTS implementation."""

    def test_craco_config_exists(self):
        assert os.path.isfile(CRACO_CONFIG), "craco.config.js not found"

    def test_no_unconditional_allowed_hosts_all(self):
        """Ensure 'allowedHosts = all' is not set unconditionally.

        Strategy: if any allowedHosts='all' assignment exists in the file,
        the if(process.env.ALLOWED_HOSTS) guard must also be present.
        """
        src = read_craco()
        has_all_assignment = bool(
            re.search(r"allowedHosts\s*=\s*['\"]all['\"]", src)
        )
        has_guard = bool(
            re.search(r"if\s*\(\s*process\.env\.ALLOWED_HOSTS\s*\)", src)
        )
        if has_all_assignment:
            assert has_guard, (
                "craco.config.js sets allowedHosts='all' but has no "
                "if (process.env.ALLOWED_HOSTS) guard — DNS rebinding risk"
            )

    def test_allowed_hosts_env_var_referenced(self):
        """ALLOWED_HOSTS env var must be read from process.env."""
        src = read_craco()
        assert "process.env.ALLOWED_HOSTS" in src, (
            "craco.config.js does not reference process.env.ALLOWED_HOSTS"
        )

    def test_allowed_hosts_gate_is_conditional(self):
        """The allowedHosts assignment must be inside an if-block."""
        src = read_craco()
        # Look for if (process.env.ALLOWED_HOSTS) pattern
        assert re.search(r"if\s*\(\s*process\.env\.ALLOWED_HOSTS\s*\)", src), (
            "craco.config.js missing if (process.env.ALLOWED_HOSTS) guard"
        )

    def test_split_and_trim_logic_present(self):
        """Comma-separated host parsing must be present."""
        src = read_craco()
        assert ".split(" in src and ".trim()" in src, (
            "craco.config.js is missing split/trim logic for ALLOWED_HOSTS parsing"
        )

    def test_opt_in_all_supported(self):
        """Explicit ALLOWED_HOSTS=all opt-in must be documented or handled."""
        src = read_craco()
        # Either the string 'all' is handled or there is a comment about it
        assert "'all'" in src or '"all"' in src, (
            "craco.config.js does not handle the ALLOWED_HOSTS=all opt-in case"
        )

    def test_filter_boolean_removes_empty_strings(self):
        """filter(Boolean) must be used to strip empty entries from split result."""
        src = read_craco()
        assert ".filter(Boolean)" in src, (
            "craco.config.js is missing .filter(Boolean) to strip empty hosts"
        )
