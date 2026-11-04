"""Fitness checks: what may be versioned and what the collector may reference."""
from pathlib import Path
import re
import subprocess
import uuid

import psycopg
import pytest
from sqlalchemy.engine import make_url

from tests.dbsetup import ensure_database

ROOT = Path(__file__).resolve().parent.parent


FORBIDDEN = re.compile(r"playwright|selenium|firecrawl|/_int/|olx\.com\.br|vivareal", re.I)
HTML_FIXTURES = ("tests/fixtures/", "e2e/fixtures/")


def scan_tracked(paths):
    return [path for path in paths if _forbidden_path(path)]


def _forbidden_path(path):
    name = path.rsplit("/", 1)[-1]
    if path.startswith(("data/", ".venv/")):
        return True
    if name.lower().startswith(".env") and name != ".env.example":
        return True
    return name.lower().endswith(".html") and not path.startswith(HTML_FIXTURES)


def scan_forbidden(root):
    root = Path(root)
    return [path.relative_to(root).as_posix() for path in sorted((root / "alugai").rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
            and (FORBIDDEN.search(path.name)
                 or FORBIDDEN.search(path.read_text(encoding="utf-8", errors="ignore")))]


@pytest.mark.parametrize("path", [
    "data/listings.json", "data/photos/1.jpg", ".env", ".env.local", ".env.collector",
    ".ENV", ".Env.local", "foo/.ENV", ".envrc", "foo/.env",
    ".venv/bin/python", "alugai/amostra.html", "docs/pagina.HTML", "tests/pagina.html",
])
def test_t0_1_scan_tracked_flags_forbidden_paths(path):
    assert scan_tracked([path]) == [path]


@pytest.mark.parametrize("path", [
    ".env.example", "alugai/network.py", "tests/fixtures/code49/anuncio.html",
    "e2e/fixtures/anuncio.html", "PLANO.md",
])
def test_t0_1_scan_tracked_accepts_allowed_paths(path):
    assert scan_tracked([path]) == []


def test_t0_1_repository_has_no_forbidden_tracked_path():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.splitlines()
    assert scan_tracked(tracked) == []


@pytest.mark.parametrize("text", [
    "from playwright.sync_api import sync_playwright", "import selenium",
    "from .firecrawl import FirecrawlFetcher", 'URL = "https://x.example/_int/busca"',
    'SEED = "https://www.olx.com.br/imoveis"', 'SOURCE = "VivaReal"',
])
def test_t0_2_scan_forbidden_flags_each_term(tmp_path, text):
    package = tmp_path / "alugai" / "adapters"
    package.mkdir(parents=True)
    (package / "fonte.py").write_text(text, encoding="utf-8")
    assert scan_forbidden(tmp_path) == ["alugai/adapters/fonte.py"]


@pytest.mark.parametrize("name", ["config.toml", "notas.txt", "dados.json", "LEIAME"])
def test_t0_2_scan_forbidden_reads_files_that_are_not_python(tmp_path, name):
    package = tmp_path / "alugai"
    package.mkdir()
    (package / name).write_text("olx.com.br", encoding="utf-8")
    assert scan_forbidden(tmp_path) == [f"alugai/{name}"]


def test_t0_2_scan_forbidden_flags_the_file_name(tmp_path):
    package = tmp_path / "alugai"
    package.mkdir()
    (package / "firecrawl.py").write_text("x = 1", encoding="utf-8")
    assert scan_forbidden(tmp_path) == ["alugai/firecrawl.py"]


def test_t0_2_scan_forbidden_only_looks_inside_the_package(tmp_path):
    package = tmp_path / "alugai"
    package.mkdir()
    (package / "limpo.py").write_text('SOURCE = "fonte.example"', encoding="utf-8")
    (tmp_path / "PLANO.md").write_text("OLX e firecrawl ficam de fora", encoding="utf-8")
    assert scan_forbidden(tmp_path) == []


def test_t0_2_collector_has_no_forbidden_reference():
    assert (ROOT / "alugai").is_dir()
    assert scan_forbidden(ROOT) == []


def test_t0_3_env_example_has_no_firecrawl_and_declares_variables():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "firecrawl" not in text.lower()
    names = {line.split("=", 1)[0] for line in text.splitlines()
             if line and not line.startswith("#")}
    assert names == {
        "ALUGAI_DB_PORT", "POSTGRES_PASSWORD", "ALUGAI_DATABASE_URL", "ALUGAI_TEST_DATABASE_URL",
        "ALUGAI_SITE_DATABASE_URL", "ALUGAI_E2E_ADMIN_DATABASE_URL", "ALUGAI_E2E_SITE_DATABASE_URL",
        "ALUGAI_SITE_DB_PASSWORD", "ALUGAI_PHOTOS_DIR", "ALUGAI_RETIRADAS_LOG",
        "ALUGAI_USER_AGENT", "ALUGAI_REVIEWER",
    }


def test_t0_4_compose_port_is_configurable_and_local_only():
    lines = (ROOT / "compose.yaml").read_text(encoding="utf-8").splitlines()
    published = [line.strip() for line in lines
                 if ":5432" in line and not line.lstrip().startswith("#")]
    assert published == ['- "127.0.0.1:${ALUGAI_DB_PORT:-55432}:5432"']


@pytest.mark.parametrize("database", [
    "alugai", "alugai_test_prod", "test", "alugai-test", "alugaitest", "ALUGAI_TEST", "_test",
    "alugai%22_test", "alugai%20x_test", "", "a" * 59 + "_test",
])
def test_t0_5_refuses_database_without_test_suffix(database):
    # A closed port proves the refusal happens before any connection.
    with pytest.raises(ValueError, match="_test"):
        ensure_database(f"postgresql+psycopg://user:pass@127.0.0.1:1/{database}")


def test_t0_7_creates_database_and_is_idempotent(test_database_url):
    name = f"alugai_guard_{uuid.uuid4().hex[:8]}_test"
    url = make_url(test_database_url).set(database=name)
    admin = url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)

    def exists():
        with psycopg.connect(admin) as connection:
            row = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        return row is not None

    assert not exists()
    try:
        ensure_database(url.render_as_string(hide_password=False))
        assert exists()
        ensure_database(url.render_as_string(hide_password=False))
        assert exists()
    finally:
        with psycopg.connect(admin, autocommit=True) as connection:
            connection.execute(f'DROP DATABASE IF EXISTS "{name}"')
