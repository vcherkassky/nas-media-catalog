#!/usr/bin/env python3
"""Entry point script to run the NAS Media Catalog server."""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nas_media_catalog.main import main  # noqa: E402

if __name__ == "__main__":
    main()
