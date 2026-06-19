#!/usr/bin/env python3
"""
社区种子数据生成脚本 — 填充测试用帖子、动态、私信等。
使用方式:
    python scripts/seed_community.py
依赖: 本地 PostgreSQL 已运行，DATABASE_URL 或 .env 可访问。
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://voice:voice_dev@127.0.0.1:5432/voice_platform")

from voice_platform.config import get_db_session


# ── 测试用户 ID ──────────────────────────────────────────────
MAIN_USER_ID   = UUID("00000000-0000-0000-0000-000000000001")  # 13800000001 (dev seed)
ADMIN_USER_ID  = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")  # admin

# 补充 5 个虚拟用户
FAKE_USERS = [
    (UUID("10000000-0000-0000-0000-000000000001"), "13800000002"),
    (UUID("10000000-0000-0000-0000-000000000002"), "13800000003"),
    (UUID("10000000-0000-0000-0000-000000000003"), "13800000004"),
    (UUID("10000000-0000-0000-0000-000000000004"), "13800000005"),
    (UUID("10000000-0000-0000-0000-000000000005"), "13800000006"),
]

PROFILES = [
    {"display_name": "声优阿杰",     "bio": "专注影视配音 8 年｜接短剧、广播剧、广告配音", "is_public": True},
    {"display_name": "小鹿的声线工坊", "bio": "少女音/正太音/御姐音｜日更创作者", "is_public": True},
    {"display_name": "老陈配音室",   "bio": "纪录片、企业宣传片配音｜价格实惠", "is_public": True},
    {"display_name": "AI配音探索者",  "bio": "研究 AI 配音与真人配音的融合应用", "is_public": True},
    {"display_name": "声音设计师Lily", "bio": "游戏配音 & 虚拟偶像声音设计", "is_public": True},
]

# ── 帖子内容 (每条含标签) ──────────────────────────────────
POSTS_DATA = [
    # 声优阿杰 的帖子
    {"body": "刚完成一部悬疑短剧的全员配音，角色声线跨度从 6 岁到 60 岁，这应该是我今年最满意的作品了！AI 克隆音色帮我省了不少重复录制的时间。", "tags": ["短剧", "配音心得", "AI克隆"]},
    {"body": "分享一个实用技巧：用 GPT-SoVITS 做参考音色时，尽量选 30 秒以上、语速均匀的干净干音，效果会好很多。", "tags": ["教程", "GPT-SoVITS"]},
    {"body": "有人问商用授权的流程，简单说下：音色馆上架→设置价格→买家购买/申请授权→自动结算。整个流程平台都帮你走完了，省心。", "tags": ["商用", "授权", "答疑"]},

    # 小鹿的声线工坊 的帖子
    {"body": "今天录了一条正太音 demo，试了 3 个不同情感方向：活泼、冷静、撒娇，大家觉得哪个更有市场？", "tags": ["正太音", "demo", "讨论"]},
    {"body": "终于把工作室搬到新录音棚了！隔音效果比之前好太多，明天开始恢复日更节奏", "tags": ["日常", "工作室"]},
    {"body": "最近在尝试 AI 辅助多角色对话合成，一个项目里 8 个角色全部用克隆音色完成，导演说完全听不出是 AI… 技术真的在改变行业。", "tags": ["AI克隆", "多角色", "技术分享"]},

    # 老陈配音室 的帖子
    {"body": "新上架了纪录片解说音色「沉稳男中音」，试听请去音色馆。适合企业宣传片、历史纪录片、教育培训类项目。", "tags": ["上架", "纪录片", "男中音"]},
    {"body": "接了个急单，客户明天就要 10 分钟的英文配音。AI 音色 + 我的审听，2 小时搞定，客户很满意。效率提升不是一点半点。", "tags": ["急单", "英文", "效率"]},

    # AI配音探索者 的帖子
    {"body": "深度对比了 3 个开源 TTS 方案在中文短剧场景下的表现：GPT-SoVITS 在情感表达和音色一致性上明显领先，ChatTTS 在自然度上有优势但稳定性不够。", "tags": ["测评", "开源TTS", "对比"]},
    {"body": "一个有趣的现象：用真人素材 + AI 克隆做出来的配音，听众盲测时 80% 分辨不出是不是真人配的。这到底是好事还是坏事？", "tags": ["讨论", "AI伦理", "行业思考"]},
    {"body": "周末花时间整理了一份《AI 配音入门指南》，从素材准备到上架发布全流程，需要的留言我私发。", "tags": ["教程", "入门", "分享"]},

    # 声音设计师Lily 的帖子
    {"body": "为某二次元手游设计了 3 个 NPC 角色的声音，全部通过平台完成从训练到合成的全流程。甲方对角色辨识度很满意！", "tags": ["游戏", "二次元", "NPC"]},
    {"body": "虚拟偶像项目进入声音调优阶段了，每天和调参斗智斗勇… 有没有大佬分享下情感标签的调参经验？", "tags": ["虚拟偶像", "调参", "求助"]},
]

# ── 社区事件 ──────────────────────────────────────────────
EVENTS_DATA = [
    {"kind": "catalog_published", "actor_idx": 0, "target_type": "catalog_voice",
     "target_id": UUID("20000000-0000-0000-0000-000000000001"),
     "payload": {"title": "悬疑剧女声·冷艳御姐", "price_cents": 29900}},
    {"kind": "catalog_published", "actor_idx": 1, "target_type": "catalog_voice",
     "target_id": UUID("20000000-0000-0000-0000-000000000002"),
     "payload": {"title": "正太音·活泼少年", "price_cents": 19900}},
    {"kind": "catalog_published", "actor_idx": 2, "target_type": "catalog_voice",
     "target_id": UUID("20000000-0000-0000-0000-000000000003"),
     "payload": {"title": "沉稳男中音·纪录片解说", "price_cents": 0}},
    {"kind": "catalog_published", "actor_idx": 0, "target_type": "catalog_voice",
     "target_id": UUID("20000000-0000-0000-0000-000000000004"),
     "payload": {"title": "温柔女声·有声书专用", "price_cents": 15900}},
    {"kind": "catalog_published", "actor_idx": 4, "target_type": "catalog_voice",
     "target_id": UUID("20000000-0000-0000-0000-000000000005"),
     "payload": {"title": "二次元少女·元气满满", "price_cents": 24900}},
    {"kind": "catalog_published", "actor_idx": 3, "target_type": "catalog_voice",
     "target_id": UUID("20000000-0000-0000-0000-000000000006"),
     "payload": {"title": "评测男声·技术解说", "price_cents": 0}},
]

# ── 私信对话 ──────────────────────────────────────────────
MESSAGES_DATA = [
    # 小鹿 → 声优阿杰
    {"sender": 1, "recipient": 0, "body": "阿杰老师好！看了你分享的悬疑短剧经验贴，受益匪浅。想请教一下多角色声线管理有什么技巧吗？"},
    {"sender": 0, "recipient": 1, "body": "客气啦！我的做法是先给每个角色建一个独立的参考音频库，合成时按角色切换，这样不会串色。"},
    {"sender": 1, "recipient": 0, "body": "原来如此！我现在是全部混在一起，确实容易出问题。多谢指点！"},
    {"sender": 0, "recipient": 1, "body": "不客气，有问题随时交流。你的正太音我也听了，很有辨识度 👍"},

    # 老陈 → AI配音探索者
    {"sender": 2, "recipient": 3, "body": "看了你的开源 TTS 对比文章，数据很扎实！想问下 GPT-SoVITS 在低资源场景（10条以内素材）的表现如何？"},
    {"sender": 3, "recipient": 2, "body": "10 条以内确实挑战比较大，建议每条素材至少 15-30 秒，语速均匀、背景干净。如果素材质量好，5-8 条也能出不错的效果。"},
    {"sender": 2, "recipient": 3, "body": "好的，我试试看。另外你那篇入门指南写好了吗？想拜读一下。"},
    {"sender": 3, "recipient": 2, "body": "还在完善中，预计下周发。写好第一时间告诉你！"},

    # Lily → 小鹿
    {"sender": 4, "recipient": 1, "body": "小鹿你好！看到你的正太音 demo 了，很有感觉。我们项目需要类似风格的 NPC 配音，方便聊聊合作吗？"},
    {"sender": 1, "recipient": 4, "body": "当然可以！方便说说具体需求吗？角色类型、台词量、工期这些。"},

    # AI配音探索者 → Lily
    {"sender": 3, "recipient": 4, "body": "Lily 你好，看到你做的虚拟偶像声音设计，很感兴趣！想了解下你们用的是什么情感标注体系？"},
    {"sender": 4, "recipient": 3, "body": "我们用的是自定义的 12 维情感标签，基于 Plutchik 情感轮扩展的。回头我把标签体系发你参考。"},
]


def main() -> None:
    session = get_db_session()
    now = datetime.now(timezone.utc)

    try:
        # ── 1. 创建测试用户 ────────────────────────────────
        print(">>> 创建测试用户...")
        for uid, phone in FAKE_USERS:
            session.execute(
                text(
                    "INSERT INTO users (id, phone, status) VALUES (:id, :phone, 'active') "
                    "ON CONFLICT (phone) DO UPDATE SET status = 'active'"
                ),
                {"id": uid, "phone": phone},
            )
        session.commit()
        print(f"    已确保 {len(FAKE_USERS)} 个测试用户存在")

        # ── 2. 创建用户资料 ────────────────────────────────
        print(">>> 创建用户资料...")
        for i, (uid, _) in enumerate(FAKE_USERS):
            p = PROFILES[i]
            session.execute(
                text(
                    "INSERT INTO user_profiles (user_id, display_name, bio, is_public) "
                    "VALUES (:uid, :name, :bio, :pub) "
                    "ON CONFLICT (user_id) DO UPDATE SET display_name=EXCLUDED.display_name, "
                    "bio=EXCLUDED.bio, is_public=EXCLUDED.is_public, updated_at=NOW()"
                ),
                {"uid": uid, "name": p["display_name"], "bio": p["bio"], "pub": p["is_public"]},
            )
        # 也为主用户设个 profile
        session.execute(
            text(
                "INSERT INTO user_profiles (user_id, display_name, bio, is_public) "
                "VALUES (:uid, :name, :bio, :pub) "
                "ON CONFLICT (user_id) DO UPDATE SET display_name=EXCLUDED.display_name, "
                "bio=EXCLUDED.bio, is_public=EXCLUDED.is_public, updated_at=NOW()"
            ),
            {"uid": MAIN_USER_ID, "name": "配音练习生", "bio": "热爱声音创作，正在学习 AI 配音技术", "pub": True},
        )
        session.commit()
        print(f"    已设置 {len(FAKE_USERS) + 1} 个用户资料")

        # ── 3. 创建帖子 ─────────────────────────────────────
        print(">>> 创建社区帖子...")
        post_ids = []
        for i, pdata in enumerate(POSTS_DATA):
            author_idx = i // 3  # 每个用户约 3 条帖子 (按顺序分配)
            author_idx = min(author_idx, len(FAKE_USERS) - 1)
            author_id = FAKE_USERS[author_idx][0]
            tags_str = ",".join(pdata["tags"])
            # 帖子时间分散在过去 7 天内
            created = now - timedelta(hours=i * 8 + (i % 5) * 3, minutes=(i * 17) % 60)

            result = session.execute(
                text(
                    "INSERT INTO community_posts (author_user_id, body, tags, created_at) "
                    "VALUES (:uid, :body, :tags, :ts) RETURNING id"
                ),
                {"uid": author_id, "body": pdata["body"], "tags": tags_str, "ts": created},
            )
            pid = result.scalar()
            if pid:
                post_ids.append((pid, author_id, created))
        session.commit()
        print(f"    已创建 {len(post_ids)} 条帖子")

        # ── 4. 创建点赞 ─────────────────────────────────────
        print(">>> 创建帖子点赞...")
        like_count = 0
        all_users = [MAIN_USER_ID] + [u[0] for u in FAKE_USERS]
        for pid, author_id, _ in post_ids:
            rng = random.Random(int(str(pid).replace("-", ""), 16) % 1000)
            n = rng.randint(0, min(3, len(all_users)))
            likers = rng.sample(all_users, k=n) if n > 0 else []
            for uid in likers:
                if uid == author_id:
                    continue
                session.execute(
                    text(
                        "INSERT INTO community_post_likes (post_id, user_id) "
                        "VALUES (:pid, :uid) ON CONFLICT DO NOTHING"
                    ),
                    {"pid": pid, "uid": uid},
                )
                like_count += 1
        session.commit()
        print(f"    已创建 {like_count} 个点赞")

        # ── 5. 创建社区事件 (上新) ───────────────────────────
        print(">>> 创建社区事件...")
        event_count = 0
        for e in EVENTS_DATA:
            actor_id = FAKE_USERS[e["actor_idx"]][0]
            created = now - timedelta(hours=event_count * 12 + 6, minutes=(event_count * 23) % 60)

            session.execute(
                text(
                    "INSERT INTO community_events (kind, actor_user_id, target_type, target_id, payload, created_at) "
                    "VALUES (:kind, :uid, :ttype, :tid, CAST(:payload AS jsonb), :ts)"
                ),
                {
                    "kind": e["kind"],
                    "uid": actor_id,
                    "ttype": e["target_type"],
                    "tid": e["target_id"],
                    "payload": json.dumps(e["payload"], ensure_ascii=False),
                    "ts": created,
                },
            )
            event_count += 1
        session.commit()
        print(f"    已创建 {event_count} 个社区事件")

        # ── 6. 创建私信 ─────────────────────────────────────
        print(">>> 创建私信对话...")
        msg_count = 0
        for m in MESSAGES_DATA:
            sender_id = FAKE_USERS[m["sender"]][0]
            recipient_id = FAKE_USERS[m["recipient"]][0]
            created = now - timedelta(hours=msg_count * 2 + 1, minutes=(msg_count * 7) % 60)

            session.execute(
                text(
                    "INSERT INTO user_messages (sender_user_id, recipient_user_id, body, created_at) "
                    "VALUES (:sid, :rid, :body, :ts)"
                ),
                {"sid": sender_id, "rid": recipient_id, "body": m["body"], "ts": created},
            )
            msg_count += 1
        session.commit()
        print(f"    已创建 {msg_count} 条私信")

        print("\n[OK] 社区种子数据填充完成！")
        print(f"   用户: {len(FAKE_USERS) + 1} 个")
        print(f"   帖子: {len(post_ids)} 条")
        print(f"   点赞: {like_count} 个")
        print(f"   事件: {event_count} 条")
        print(f"   私信: {msg_count} 条")
        print("\n刷新 /discover/feed 和 /community 页面即可看到效果。")

    except Exception as exc:
        session.rollback()
        print(f"\n[FAIL] 种子数据填充失败: {exc}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
