"""blobstore: a finished service. Deploy once, never touch again.

PUT  /blob   (X-Blob-Token) body = anything -> writes blobs/state-<utc timestamp>.json, keeps newest KEEP files
GET  /blob   (X-Blob-Token)                 -> newest blob
GET  /blobs  (X-Blob-Token)                 -> list [{name, size, mtime}]
GET  /blob/<name> (X-Blob-Token)            -> that blob (restore points)
GET  /health                                -> {"ok": true, "blobs": n}
"""
import hmac
import os
import re
import time

from flask import Flask, request, jsonify, Response

TOKEN = os.environ.get("BLOB_TOKEN", "")
DIR = os.environ.get("BLOB_DIR", "./blobs")
KEEP = int(os.environ.get("BLOB_KEEP", "200"))
MAX_MB = int(os.environ.get("BLOB_MAX_MB", "50"))
NAME_RE = re.compile(r"^state-[0-9TZ\-]+\.json$")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024
os.makedirs(DIR, exist_ok=True)


def denied():
    t = request.headers.get("X-Blob-Token", "")
    return not (TOKEN and t and hmac.compare_digest(t, TOKEN))


def listing():
    out = []
    for n in os.listdir(DIR):
        if NAME_RE.match(n):
            p = os.path.join(DIR, n)
            out.append({"name": n, "size": os.path.getsize(p), "mtime": os.path.getmtime(p)})
    out.sort(key=lambda x: x["name"])
    return out


@app.get("/health")
def health():
    return jsonify({"ok": True, "blobs": len(listing()), "keep": KEEP})


@app.put("/blob")
def put_blob():
    if denied():
        return jsonify({"error": "token"}), 401
    data = request.get_data()
    if not data:
        return jsonify({"error": "empty body refused"}), 400
    name = "state-" + time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime()) + ".json"
    tmp = os.path.join(DIR, "." + name)
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, os.path.join(DIR, name))
    blobs = listing()
    for b in blobs[:-KEEP]:
        os.remove(os.path.join(DIR, b["name"]))
    return jsonify({"ok": True, "name": name, "size": len(data), "blobs": min(len(blobs), KEEP)})


@app.get("/blob")
def get_blob():
    if denied():
        return jsonify({"error": "token"}), 401
    blobs = listing()
    if not blobs:
        return jsonify({"error": "no blobs"}), 404
    with open(os.path.join(DIR, blobs[-1]["name"]), "rb") as f:
        return Response(f.read(), mimetype="application/json",
                        headers={"X-Blob-Name": blobs[-1]["name"]})


@app.get("/blobs")
def get_list():
    if denied():
        return jsonify({"error": "token"}), 401
    return jsonify(listing())


@app.get("/blob/<name>")
def get_named(name):
    if denied():
        return jsonify({"error": "token"}), 401
    if not NAME_RE.match(name) or not os.path.exists(os.path.join(DIR, name)):
        return jsonify({"error": "no such blob"}), 404
    with open(os.path.join(DIR, name), "rb") as f:
        return Response(f.read(), mimetype="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8010)))
