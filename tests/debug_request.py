import os
import sys
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so imports like `api.app` work when
# running this script directly (executing from the repository root).
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.app.main import app

def main():
    client = TestClient(app)
    headers = {"X-API-Key": "deepdarshak_ais_2025"}
    params = {
        "start": "2020-01-01T00:00:09.000Z",
        "end": "2020-01-01T00:00:09.000Z",
        "max_points": "500",
    }
    resp = client.get("/vessels/205460000/positions", headers=headers, params=params)
    print("Status code:", resp.status_code)
    print("Response body:", resp.text)

if __name__ == '__main__':
    main()
