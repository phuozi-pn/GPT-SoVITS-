"""为已有音色馆条目与创作者批量补齐默认头像/封面。

用法:
  python scripts/backfill_catalog_avatars.py          # 预览
  python scripts/backfill_catalog_avatars.py --apply  # 写入数据库
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from domains.marketplace.avatar_assign import AvatarAssignService
from voice_platform.config import get_db_session


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill catalog covers and creator avatars")
    parser.add_argument("--apply", action="store_true", help="Persist changes (default is dry-run)")
    args = parser.parse_args()

    session = get_db_session()
    try:
        svc = AvatarAssignService(session)
        if not args.apply:
            from sqlalchemy import func, select

            from voice_platform.job.models import VoiceCatalogEntryRow
            from voice_platform.social.models import UserProfileRow

            missing_covers = session.scalar(
                select(func.count())
                .select_from(VoiceCatalogEntryRow)
                .where(
                    VoiceCatalogEntryRow.status.in_(("published", "pending")),
                    (VoiceCatalogEntryRow.cover_image_url.is_(None))
                    | (VoiceCatalogEntryRow.cover_image_url == ""),
                )
            )
            owner_ids = {
                row.owner_user_id
                for row in session.scalars(
                    select(VoiceCatalogEntryRow).where(
                        VoiceCatalogEntryRow.status.in_(("published", "pending"))
                    )
                ).all()
            }
            missing_avatars = 0
            for owner_id in owner_ids:
                profile = session.get(UserProfileRow, owner_id)
                if not profile or not (profile.avatar_url or "").strip():
                    missing_avatars += 1
            print(f"[dry-run] 待补封面: {missing_covers or 0} 条")
            print(f"[dry-run] 待补创作者头像: {missing_avatars} 人")
            print("加 --apply 执行写入")
            return 0

        result = svc.backfill_all()
        print(f"已补封面: {result.covers_assigned} 条")
        print(f"已补创作者头像: {result.avatars_assigned} 人")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
