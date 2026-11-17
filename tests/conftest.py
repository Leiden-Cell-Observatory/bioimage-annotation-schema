"""A set folder built from the examples, with the files its records point to."""

import shutil
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples" / "0.1"


@pytest.fixture
def set_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "set"
    folder.mkdir()
    shutil.copy(EXAMPLES / "annotation-set.yaml", folder)
    shutil.copy(EXAMPLES / "annotation-records.csv", folder)
    for name in ("a1b2c3", "d4e5f6"):
        for path in (f"annotation_input/{name}.tif", f"annotation_output/{name}_mask.tif"):
            (folder / path).parent.mkdir(exist_ok=True)
            (folder / path).write_bytes(b"II*\x00" + name.encode())
    return folder
