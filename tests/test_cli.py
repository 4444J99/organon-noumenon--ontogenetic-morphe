"""
Tests for autogenrec CLI and demo execution.
"""

import sys
from unittest.mock import patch

from autogenrec.__main__ import main
from autogenrec.demo import run_demo


def test_run_demo_executes_without_errors(capsys) -> None:
    """Test that run_demo executes the 6 phases without exceptions."""
    run_demo()
    captured = capsys.readouterr()
    assert "Full System Demo: Research-to-Revenue Pipeline" in captured.out
    assert "Full System Demo Complete!" in captured.out


def test_main_cli_demo_flag(capsys) -> None:
    """Test that main() with --demo flag executes demo and exits cleanly."""
    with patch.object(sys, "argv", ["autogenrec", "--demo"]):
        try:
            main()
        except SystemExit as exc:
            assert exc.code == 0
    captured = capsys.readouterr()
    assert "Full System Demo Complete!" in captured.out
