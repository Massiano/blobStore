# blobstore — deploy once, done

Timestamped snapshot store for GroupChat (or anything). Keeps the newest BLOB_KEEP files on the container disk.
The whole point: this service is FINISHED. Never redeploy it, and its disk lives as long as the container does.

Env: BLOB_TOKEN (required, any long random string), BLOB_KEEP=200, BLOB_MAX_MB=50, BLOB_DIR=./blobs
Endpoints: PUT /blob, GET /blob (newest), GET /blobs (list), GET /blob/<name>, GET /health
Auth: X-Blob-Token header.

Caveat, stated once: a container disk survives *your* inactivity, not platform node replacement. Rare; accepted.
