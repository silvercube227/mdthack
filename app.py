"""Root launcher — run with: streamlit run app.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import main

main()
