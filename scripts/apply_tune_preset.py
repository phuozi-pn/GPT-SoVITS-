"""Apply chosen tune preset to existing VoiceVersion metadata in DB."""
from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy import select

from voice_platform.config import get_db_session
from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.repository import VoiceVersionRepository
from voice_platform.engine.infer_defaults import default_infer_metadata, stable_infer_metadata

def main() -> int:
    parser = argparse.ArgumentParser(description="Patch VoiceVersion infer metadata")
    parser.add_argument("--voice-version-id", default="", help="Optional single UUID")
    parser.add_argument("--all-imported", action="store_true", help="Update all imported versions")
    parser.add_argument(
        "--all-real",
        action="store_true",
        help="Update all non-mock versions (quick_clone / cloud / import)",
    )
    parser.add_argument(
        "--stable",
        action="store_true",
        help="Use stabler preset (temp 0.68, speed 1.0, top_p 0.95)",
    )
    args = parser.parse_args()

    preset = stable_infer_metadata() if args.stable else default_infer_metadata()

    session = get_db_session()
    repo = VoiceVersionRepository(session)
    updated: list[str] = []

    try:
        if args.voice_version_id:
            rows = [repo.get(UUID(args.voice_version_id))]
            rows = [r for r in rows if r]
        elif args.all_imported:
            rows = list(
                session.scalars(select(VoiceVersionRow)).all()
            )
            rows = [r for r in rows if (r.metadata_json or {}).get("imported")]
        elif args.all_real:
            rows = list(session.scalars(select(VoiceVersionRow)).all())
            rows = [r for r in rows if not (r.metadata_json or {}).get("mock")]
        else:
            print(
                "Specify --voice-version-id, --all-imported, or --all-real",
                file=__import__("sys").stderr,
            )
            return 2

        for row in rows:
            meta = dict(row.metadata_json or {})
            meta.update(preset)
            row.metadata_json = meta
            updated.append(str(row.id))
        session.commit()
    finally:
        session.close()

    print(json.dumps({"updated": updated, "preset": preset}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
