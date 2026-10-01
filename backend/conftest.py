"""Point every test at a throwaway database so the real feeprint.db is never touched."""

import os
import tempfile

os.environ["FEEPRINT_DB"] = os.path.join(tempfile.mkdtemp(), "feeprint-test.db")
