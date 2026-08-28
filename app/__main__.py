"""
NetPulse module execution entrypoint.
Allows running the framework directly via: python -m netpulse
"""

import sys
from app.cli import main

if __name__ == "__main__":
    sys.exit(main())
