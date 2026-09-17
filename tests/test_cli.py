from conftest import implemented

from dp_activity.cli import build_parser


def test_parser_supports_run_command() -> None:
    parser = implemented(build_parser)
    arguments = parser.parse_args(["run"])
    assert arguments.command == "run"

