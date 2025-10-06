
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.resolve()

def to_abs_path(p: Optional[str | os.PathLike]) -> Optional[Path]:
    """Convert p to an absolute path.
    Sequence:
      1) Absolute: expanduser+resolve
      2) Relative to CWD
      3) Relative to script folder (BASE_DIR)
    """
    if not p:
        return None
    pp = Path(p).expanduser()
    if pp.is_absolute():
        return pp.resolve()
    p1 = (Path.cwd() / pp)
    if p1.exists():
        return p1.resolve()
    p2 = (BASE_DIR / pp)
    return p2.resolve()