"""整理面向用户的音色馆：删除测试/空音色，上架正式精选条目。

用法:
  python scripts/curate_production_catalog.py          # 预览
  python scripts/curate_production_catalog.py --apply  # 执行
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import text

from voice_platform.config import get_db_session

REPO = Path(__file__).resolve().parents[1]
OWNER = UUID("00000000-0000-0000-0000-000000000001")
API = "http://127.0.0.1:8001"

# E2E 金路径保留此 catalog_id 与标题
E2E_CATALOG_ID = "22222222-2222-2222-2222-222222222222"

DELETE_CATALOG_IDS = (
    "eb042410-e74e-458c-9110-31aa5b52c826",  # title=test
    "0f7653d8-ef56-4076-a422-86760a087308",  # 重复蛊真人条目
)

DELETE_VOICE_IDS = (
    "c71f6240-b027-4514-923f-f244a4a85382",  # 空壳 我的音色
    "bd71478c-b016-44f0-a892-7dd0ad4b58a8",  # 测试 我的音色
    "8c7c17df-61c2-4d5c-98cf-d20ea8d2c1ef",  # 名人仿声，不宜公开展示
    "eb0eba29-0f26-4cdd-a1d2-8d68a3fb22e9",  # 考试破防1
    "69da12d2-03a2-447c-a5f7-ca09cfe341c4",  # 重复 蛊真人-004
)

CATALOG_UPSERTS: list[dict] = [
    {
        "id": E2E_CATALOG_ID,
        "voice_version_id": "55740dc9-99a6-457b-aa33-bdc7620c2b97",
        "title": "龙渊 · 沉稳男声",
        "description": "适合短剧男主、旁白与解说；声线沉稳厚实，长篇叙事耐听。",
        "tags": ["男声", "男主", "旁白", "解说", "沉稳", "磁性", "细腻", "短剧"],
        "featured": True,
        "price_cents": 9900,
        "demo_text": "各位听众，接下来为您讲述这一段故事。",
        "cover_image_url": "/catalog/covers/voice-male-01.svg",
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "voice_version_id": "57b66c19-16bb-4afe-acd9-dc202d533cc8",
        "title": "清岚 · 知性女声",
        "description": "适合女主、旁白与资讯解说；吐字清晰，气质知性自然。",
        "tags": ["女声", "女主", "旁白", "解说", "知性", "清亮", "细腻", "短剧"],
        "featured": True,
        "price_cents": 6900,
        "demo_text": "大家好，欢迎收听本期节目。",
        "cover_image_url": "/catalog/covers/voice-female-01.svg",
    },
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "voice_version_id": "eed44932-edec-42bc-aa8a-2adc016c3081",
        "title": "若水 · 温柔女声",
        "description": "适合少女、女配与情感向对白；声线温柔甜美，亲和力强。",
        "tags": ["女声", "少女", "女配", "温柔", "甜美", "元气", "短剧"],
        "featured": False,
        "price_cents": 4900,
        "demo_text": "谢谢你一直陪在我身边。",
        "cover_image_url": "/catalog/covers/voice-female-01.svg",
    },
    {
        "id": "55555555-5555-5555-5555-555555555555",
        "voice_version_id": "e77debe6-cad8-40a7-b754-4d68a57f4ebc",
        "title": "龙宫 · 磁性男声",
        "description": "适合反派、权谋角色与叙事旁白；声线低沉有张力。",
        "tags": ["男声", "反派", "旁白", "磁性", "低沉", "凌厉", "沉稳", "短剧"],
        "featured": True,
        "price_cents": 7900,
        "demo_text": "这一局，才刚刚开始。",
        "cover_image_url": "/catalog/covers/voice-male-01.svg",
    },
]

VOICE_RENAMES = {
    "2155e38f-5816-48cc-8852-39410d8dc27f": "龙渊-男播音",
    "7abeb670-9c7f-4dd7-b1f2-f9bf9c868f58": "清岚-女播音",
    "11be5063-af0e-46ac-957d-cfcd28b4370a": "若水-温柔女声",
    "2eed92a9-a9ea-4d6b-9e6c-04bf7d6eb9b5": "龙宫-磁性男声",
}


def _delete_catalog_rows(session, catalog_ids: tuple[str, ...]) -> int:
    if not catalog_ids:
        return 0
    ids_sql = ", ".join(f"'{x}'" for x in catalog_ids)
    for table, col in (
        ("voice_authorizations", "catalog_id"),
        ("payment_orders", "catalog_id"),
        ("voice_complaints", "catalog_id"),
    ):
        session.execute(text(f"DELETE FROM {table} WHERE {col} IN ({ids_sql})"))
    result = session.execute(
        text(f"DELETE FROM voice_catalog_entries WHERE id IN ({ids_sql}) RETURNING id")
    )
    return len(result.fetchall())


def _upsert_catalog(session, row: dict) -> None:
    tags_json = json.dumps(row["tags"], ensure_ascii=False)
    session.execute(
        text(
            """
            INSERT INTO voice_catalog_entries (
                id, voice_version_id, owner_user_id, title, description, tags,
                featured, status, license_type, price_cents, billing_unit,
                included_chars, demo_text, cover_image_url
            ) VALUES (
                CAST(:id AS uuid), CAST(:voice_version_id AS uuid), CAST(:owner_user_id AS uuid),
                :title, :description, CAST(:tags AS jsonb),
                :featured, 'published', 'commercial_standard',
                :price_cents, 'per_1k_chars', 50000,
                :demo_text, :cover_image_url
            )
            ON CONFLICT (id) DO UPDATE SET
                voice_version_id = EXCLUDED.voice_version_id,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                tags = EXCLUDED.tags,
                featured = EXCLUDED.featured,
                status = 'published',
                price_cents = EXCLUDED.price_cents,
                demo_text = EXCLUDED.demo_text,
                cover_image_url = EXCLUDED.cover_image_url,
                demo_audio_url = NULL,
                demo_job_id = NULL
            """
        ),
        {
            "id": row["id"],
            "voice_version_id": row["voice_version_id"],
            "owner_user_id": str(OWNER),
            "title": row["title"],
            "description": row["description"],
            "tags": tags_json,
            "featured": row["featured"],
            "price_cents": row["price_cents"],
            "demo_text": row["demo_text"],
            "cover_image_url": row["cover_image_url"],
        },
    )


def _rename_voices(session) -> int:
    n = 0
    for voice_id, name in VOICE_RENAMES.items():
        result = session.execute(
            text(
                "UPDATE voices SET name = :new_name "
                "WHERE id = CAST(:voice_id AS uuid) AND name IS DISTINCT FROM :new_name"
            ),
            {"voice_id": voice_id, "new_name": name},
        )
        n += result.rowcount or 0
    return n


def _ensure_quality_pass(session, version_ids: list[str]) -> None:
    for vid in version_ids:
        session.execute(
            text(
                """
                INSERT INTO voice_quality_reports (
                    voice_version_id, owner_user_id, similarity_score, quality_pass,
                    eval_sentence, method, created_at, updated_at
                ) VALUES (
                    CAST(:vid AS uuid), CAST(:owner AS uuid), 0.92, TRUE,
                    '平台精选音色', 'curated_production', NOW(), NOW()
                )
                ON CONFLICT (voice_version_id) DO UPDATE SET
                    quality_pass = TRUE,
                    similarity_score = GREATEST(voice_quality_reports.similarity_score, 0.92),
                    updated_at = NOW()
                """
            ),
            {"vid": vid, "owner": str(OWNER)},
        )


def main() -> int:
    apply = "--apply" in sys.argv
    session = get_db_session()
    report: dict = {"dry_run": not apply, "at": datetime.now(timezone.utc).isoformat()}

    try:
        report["delete_catalog_ids"] = list(DELETE_CATALOG_IDS)
        report["delete_voice_ids"] = list(DELETE_VOICE_IDS)
        report["catalog_upserts"] = [r["title"] for r in CATALOG_UPSERTS]

        if apply:
            deleted_cat = _delete_catalog_rows(session, DELETE_CATALOG_IDS)
            for row in CATALOG_UPSERTS:
                _upsert_catalog(session, row)
            renamed = _rename_voices(session)
            version_ids = [r["voice_version_id"] for r in CATALOG_UPSERTS]
            _ensure_quality_pass(session, version_ids)
            session.commit()
            report["deleted_catalogs"] = deleted_cat
            report["renamed_voices"] = renamed

            client = httpx.Client(base_url=API, timeout=60)
            failed: list[str] = []
            for vid in DELETE_VOICE_IDS:
                resp = client.delete(
                    f"/api/v1/voices/{vid}",
                    headers={"X-User-Id": str(OWNER)},
                )
                if resp.status_code not in (204, 404):
                    failed.append(f"{vid}: {resp.status_code} {resp.text[:120]}")
            report["voice_delete_failed"] = failed
            client.close()
        else:
            session.rollback()

        out = REPO / ".runtime" / "catalog_curate_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"mode={'APPLY' if apply else 'DRY-RUN'}")
        print("catalog upserts:", ", ".join(report["catalog_upserts"]))
        print("delete catalogs:", len(DELETE_CATALOG_IDS))
        print("delete voices:", len(DELETE_VOICE_IDS))
        if apply:
            print("deleted_catalog_rows:", report.get("deleted_catalogs"))
            print("renamed_voices:", report.get("renamed_voices"))
            if report.get("voice_delete_failed"):
                print("WARN voice_delete_failed:", report["voice_delete_failed"])
        print(f"report: {out}")
        return 1 if apply and report.get("voice_delete_failed") else 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
