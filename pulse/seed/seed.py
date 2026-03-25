# Copyright (c) 2026, Tridz and contributors
# License: MIT
"""
Backward-compatibility shim.

The canonical seeder has moved to pulse.demo.seed.
Import from there directly; these aliases will be removed in a future release.
"""

from pulse.demo.seed import clear_demo_data as clear_dummy_data  # noqa: F401
from pulse.demo.seed import seed_demo_data as seed_dummy_data  # noqa: F401
