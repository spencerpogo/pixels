import sys
from uuid import uuid4

from replit import db

cmd = sys.argv[1]

if cmd == "add":
    name = sys.argv[2]
    keys = db.get("keys", {})
    k = uuid4().hex
    keys[k] = name
    print(f"API key for {name}:")
    print(k)
elif cmd == "revoke":
    to_revoke = sys.argv[2]
    keys = db.get("keys", {})
    print(f"Before: {len(keys)} keys")
    newkeys = {k: name for k, name in keys.items() if name != to_revoke}
    db["keys"] = newkeys
    print(f"Now: {len(newkeys)} keys")
elif cmd == "regen":
    to_regen = sys.argv[2]
    keys = db.get("keys", {})
    print(f"regening key for {to_regen}:")
    newKey = uuid4().hex
    newKeys = {k: name for k, name in keys.items() if name != to_regen}
    newKeys[newKey] = to_regen
    db["keys"] = newKeys
    print(newKey)
elif cmd == "show":
    for k, name in db["keys"].items():
        print(f"{k} {name}")
