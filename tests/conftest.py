from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_msa_pdf(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "sample_msa.pdf"
    if not path.exists():
        pytest.skip("sample_msa.pdf not generated; run scripts/build_fixtures.py")
    return path


@pytest.fixture
def sample_msa_docx(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "sample_msa.docx"
    if not path.exists():
        pytest.skip("sample_msa.docx not generated; run scripts/build_fixtures.py")
    return path
