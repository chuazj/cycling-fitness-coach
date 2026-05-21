"""intervals.icu HTTP client and credential loading."""
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: pip install requests", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://intervals.icu/api/v1"


class IntervalsIcuClient:
    def __init__(self, athlete_id, api_key):
        self.athlete_id = athlete_id
        self.session = requests.Session()
        self.session.auth = ("API_KEY", api_key)

    def __repr__(self):
        return f"IntervalsIcuClient(athlete_id={self.athlete_id!r})"

    def _get(self, endpoint, params=None):
        url = f"{BASE_URL}{endpoint}"
        for attempt in range(3):
            try:
                r = self.session.get(url, params=params, timeout=15)
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < 2:
                    delay = 2 ** (attempt + 1)
                    print(f"WARNING: {type(e).__name__} on {endpoint}, retrying in {delay}s...",
                          file=sys.stderr)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"{type(e).__name__} on {endpoint} after 3 attempts") from e
            if r.status_code == 401:
                raise RuntimeError(f"Authentication failed (401) for {endpoint} — check API key")
            if r.status_code == 404:
                raise RuntimeError(f"Not found (404): {endpoint} — check activity ID")
            if r.status_code in (429, 502, 503, 504):
                if attempt < 2:
                    delay = 2 ** (attempt + 1)
                    print(f"WARNING: HTTP {r.status_code} on {endpoint}, retrying in {delay}s...",
                          file=sys.stderr)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"HTTP {r.status_code} on {endpoint} after 3 attempts")
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                raise RuntimeError(f"Non-JSON response from {endpoint} (HTTP {r.status_code})")

    def get_activity(self, activity_id):
        return self._get(f"/activity/{activity_id}")

    def get_intervals(self, activity_id):
        data = self._get(f"/activity/{activity_id}/intervals")
        # Response is {icu_intervals: [...], icu_groups: [...], ...}
        if isinstance(data, dict):
            return data.get("icu_intervals", [])
        return data

    def get_streams(self, activity_id, types=None):
        if types is None:
            types = ["watts", "heartrate", "cadence"]
        return self._get(f"/activity/{activity_id}/streams.json", {"types": types})

    def get_power_curve(self, activity_id):
        return self._get(f"/activity/{activity_id}/power-curve.json")

    def get_athlete(self):
        return self._get(f"/athlete/{self.athlete_id}")

    def list_activities(self, oldest, newest=None, limit=None):
        params = {"oldest": oldest}
        if newest: params["newest"] = newest
        if limit: params["limit"] = limit
        return self._get(f"/athlete/{self.athlete_id}/activities", params)

    def get_wellness(self, oldest, newest=None):
        """Fetch daily wellness records for date range (YYYY-MM-DD strings)."""
        params = {"oldest": oldest}
        if newest: params["newest"] = newest
        return self._get(f"/athlete/{self.athlete_id}/wellness", params)


def load_env(env_path=None):
    """Load .env file from script dir or project root."""
    if env_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # script_dir is scripts/intervals_icu/; walk up to also check
        # scripts/ and the skill root (where .env actually lives).
        candidates = [
            os.path.join(script_dir, ".env"),
            os.path.join(os.path.dirname(script_dir), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(script_dir)), ".env"),
        ]
    else:
        candidates = [env_path]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    val = val.strip()
                    # Strip matching quotes (single or double)
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                        val = val[1:-1]
                    else:
                        # Strip inline comments only if # is preceded by whitespace
                        # (avoids truncating values that legitimately contain #)
                        val = re.split(r'\s+#', val, maxsplit=1)[0]
                    os.environ.setdefault(key.strip(), val)
            return
