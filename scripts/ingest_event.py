"""Send normalized enterprise observations from any platform using stdlib Python."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def main() -> int:
    parser = argparse.ArgumentParser(description='Send inventory observations to DecisionMesh; create the entity in Enterprise lab first.')
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--entity', required=True)
    parser.add_argument('--source', default='external-observer')
    parser.add_argument('--changes', required=True, help='JSON state changes, e.g. {"demand":180,"capacity":40}')
    parser.add_argument('--count', type=int, default=1)
    parser.add_argument('--interval', type=float, default=5)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000 or args.interval < 0:
        parser.error('count must be 1–10000 and interval must be nonnegative')
    try:
        changes = json.loads(args.changes)
    except ValueError:
        parser.error('changes must be valid JSON')
    if not isinstance(changes, dict):
        parser.error('changes must be a JSON object')
    for index in range(args.count):
        event = {'event_id': uuid4().hex, 'source': args.source, 'entity_id': args.entity,
                 'occurred_at': datetime.now(timezone.utc).isoformat(), 'changes': changes,
                 'description': 'Observation supplied by the external producer CLI'}
        request = Request(args.base_url.rstrip('/') + '/api/enterprise/events', data=json.dumps(event).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(request, timeout=20) as response:
                receipt = json.load(response)
            print(json.dumps(receipt))
            if receipt['status'] == 'rejected':
                return 1
        except HTTPError as exc:
            print(f'HTTP {exc.code}: {exc.read().decode()}', file=sys.stderr)
            return 1
        except URLError as exc:
            print(f'Cannot reach DecisionMesh: {exc.reason}', file=sys.stderr)
            return 1
        if index + 1 < args.count:
            time.sleep(args.interval)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
