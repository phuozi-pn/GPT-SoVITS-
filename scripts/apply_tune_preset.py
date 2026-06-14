"""Apply chosen tune preset to existing VoiceVersion metadata in DB."""
from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy import select

from voice_platform.config import get_db_session
from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.repository import VoiceVersionRepository

PRESET_CUT0_T078_SP105 = {
    "text_split_method": "cut0",
    "temperature": 0.78,
    "speed_factor": 1.05,
    "top_p": 1.0,
    "tune_preset": "cut0_t078_sp105",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch VoiceVersion infer metadata")
    parser.add_argument("--voice-version-id", default="", help="Optional single UUID")
    parser.add_argument("--all-imported", action="store_true", help="Update all imported versions")
    args = parser.parse_args()

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
        else:
            print("Specify --voice-version-id or --all-imported", file=__import__("sys").stderr)
            return 2

        for row in rows:
            meta = dict(row.metadata_json or {})
            meta.update(PRESET_CUT0_T078_SP105)
            row.metadata_json = meta
            updated.append(str(row.id))
        session.commit()
    finally:
        session.close()

    print(json.dumps({"updated": updated, "preset": PRESET_CUT0_T078_SP105}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
