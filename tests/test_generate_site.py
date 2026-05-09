import json
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
import generate_site


def test_generate_site_main(tmp_path):
    automated_path = tmp_path / "automated.json"
    automated_path.write_text(json.dumps({"developers": [], "aggregates": {}}), encoding="utf-8")

    with patch("generate_site.AUTOMATED_PATH", str(automated_path)), \
         patch("generate_site.load_config", return_value={}), \
         patch("generate_site.build_site_outputs") as mock_build:
        generate_site.main()
        assert mock_build.called
