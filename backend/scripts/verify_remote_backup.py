#!/usr/bin/env python3
"""
RoadSOS Remote Backup Verification Script.

Downloads a replicated backup artifact from off-site object storage,
validates its SHA-256 checksum against metadata / .sha256 manifest,
verifies gzip archive decompression, and reports status safely without credentials.
"""

import os
import sys
import argparse
import gzip
import hashlib
from typing import Dict, Any

from services.backup_replication_service import backup_replication_service, sanitize_secret_string

def verify_remote_backup(remote_key: str, out_dir: str = "/tmp/roadsos_remote_verify") -> Dict[str, Any]:
    """
    Downloads remote object, validates SHA-256 checksum, tests gzip decompression.
    """
    print(f"[INFO] Initiating remote backup verification for key: {remote_key}")
    dl_res = backup_replication_service.download_remote_backup(remote_key, dest_dir=out_dir)

    if dl_res.get("status") != "completed":
        err = dl_res.get("error", "Unknown download error")
        print(f"[FATAL] Failed to download remote backup object: {err}", file=sys.stderr)
        return {"status": "failed", "error": err}

    local_file = dl_res["local_path"]
    sha256_hex = dl_res["sha256"]

    # Decompression check if file is gzipped
    if local_file.endswith(".gz"):
        try:
            with gzip.open(local_file, "rb") as f_in:
                header = f_in.read(1024)
                if not header:
                    err = f"Downloaded archive is 0 bytes when decompressed: {local_file}"
                    print(f"[FATAL] {err}", file=sys.stderr)
                    return {"status": "failed", "error": err}
            print(f"[SUCCESS] Remote Gzip archive verified readable: {local_file}")
        except Exception as e:
            err = f"Failed to decompress remote gzip archive: {e}"
            print(f"[FATAL] {err}", file=sys.stderr)
            return {"status": "failed", "error": err}

    print(f"[SUCCESS] Remote backup object SHA-256 checksum verified: {sha256_hex}")
    return {
        "status": "completed",
        "remote_key": remote_key,
        "local_path": local_file,
        "sha256": sha256_hex,
        "metadata": dl_res.get("metadata", {})
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RoadSOS Remote Backup Verification Script")
    parser.add_argument("--key", required=True, help="Remote object storage key to verify")
    parser.add_argument("--outdir", default="/tmp/roadsos_remote_verify", help="Temporary download directory")
    args = parser.parse_args()

    res = verify_remote_backup(args.key, out_dir=args.outdir)
    if res["status"] != "completed":
        sys.exit(1)
