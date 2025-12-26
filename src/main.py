from __future__ import annotations

import logging
import os

from app.runtime import main

LOGGER = logging.getLogger(__name__)


if __name__ == "__main__":
    LOGGER.info("Discord Bot を起動します。pid=%s", os.getpid())
    main()
