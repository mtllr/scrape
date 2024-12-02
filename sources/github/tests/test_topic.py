import pytest
from pathlib import Path
from models import ScrapeModel
from sources.github.topic import run, GithubTopicModel
from click.testing import CliRunner


def test_call():
    filename = "test_gdpr.json"
    runner = CliRunner()
    result = runner.invoke(run, ["gdpr", "-m", "2", "-o", filename])
    assert result.exit_code == 0
    try:
        with open(filename, "r") as f:
            ScrapeModel[list[GithubTopicModel]].model_validate_json(f.read())
    except Exception as e:
        pytest.fail(f"Data Model does not conform: {e}")

    Path(filename).unlink()
