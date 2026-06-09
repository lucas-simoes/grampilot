"""Instagram Manager CLI entry point."""
from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path


def _check_env() -> None:
    """Check required env vars are present. Non-fatal — allows init to run."""
    from dotenv import load_dotenv
    load_dotenv()

    required = {
        "META_ACCESS_TOKEN": "Meta Graph API token (60-day user access token)",
        "META_IG_USER_ID": "Instagram Business/Creator account ID",
        "ANTHROPIC_API_KEY": "Anthropic API key for Claude text generation",
    }
    optional = {
        "HF_API_TOKEN": "HuggingFace token (required for AI image generation)",
        "IMAGE_PROVIDER": "Image generation provider (default: huggingface)",
    }

    missing_required = []
    for var, desc in required.items():
        if not os.getenv(var):
            missing_required.append((var, desc))

    if missing_required:
        print(
            "[instagram_manager] Missing required environment variables:\n"
            + "\n".join(f"  ✗ {var}: {desc}" for var, desc in missing_required)
            + "\n  → Configure in your .env file. See .env.example for reference.",
            file=sys.stderr,
        )
    # Note: we do NOT exit — allow init to proceed


def _cmd_init(args: argparse.Namespace) -> None:
    from instagram_manager.brand import save_brand
    from instagram_manager.models import BrandProfile
    print("[instagram-init] Interactive brand profile setup.")
    handle = input("Instagram account handle (e.g. @mybrand): ").strip()
    niche = input("Niche/industry (e.g. home cooking): ").strip()
    tone = input("Tone of voice (e.g. warm and friendly): ").strip()
    audience = input("Target audience description: ").strip()
    language = input("Language [en-US]: ").strip() or "en-US"
    pillar1 = input("Content pillar 1: ").strip()
    pillar2 = input("Content pillar 2: ").strip()
    pillars = [p for p in [pillar1, pillar2] if p]
    extra = input("Content pillar 3 (optional, press Enter to skip): ").strip()
    if extra:
        pillars.append(extra)
    branded = input("Branded hashtag (e.g. #mybrand): ").strip()
    brand = BrandProfile(
        account_handle=handle,
        niche=niche,
        tone_of_voice=tone,
        target_audience=audience,
        language=language,
        content_pillars=pillars,
        branded_hashtags=[branded] if branded else [],
    )
    save_brand(brand)
    print(f"[instagram-init] Brand profile saved to .instagram/memory/brand.md")
    print("[instagram-init] Next step: run 'instagram-manager plan' to generate your first content plan.")


def _cmd_plan(args: argparse.Namespace) -> None:
    from instagram_manager.planner import generate_plan
    week = getattr(args, "week", None)
    theme = getattr(args, "theme", None)
    plan = generate_plan(week=week, theme=theme)
    print(f"[instagram-plan] Plan {plan.week} generated with {len(plan.items)} items.")
    print(f"  → Review at .instagram/memory/plans/{plan.week}.md")
    print(f"  → Approve with: instagram-manager approve --week {plan.week}")


def _cmd_approve(args: argparse.Namespace) -> None:
    from instagram_manager.storage import approve_plan, PlanNotFound, AlreadyApproved
    week = getattr(args, "week", None)
    if not week:
        # Find latest draft plan
        from pathlib import Path
        plans_dir = Path(".instagram/memory/plans")
        if not plans_dir.exists():
            print("[instagram-approve] No plans found. Run 'plan' first.", file=sys.stderr)
            sys.exit(1)
        drafts = sorted(plans_dir.glob("*.json"))
        if not drafts:
            print("[instagram-approve] No plans found.", file=sys.stderr)
            sys.exit(1)
        week = drafts[-1].stem
    try:
        plan = approve_plan(week)
        print(f"[instagram-approve] Plan {week} approved ({len(plan.items)} items).")
        print(f"  → Next step: run 'instagram-manager generate --week {week}'")
    except PlanNotFound as e:
        print(f"[instagram-approve] Error: {e}", file=sys.stderr)
        sys.exit(1)
    except AlreadyApproved as e:
        print(f"[instagram-approve] Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_media(args: argparse.Namespace) -> None:
    from instagram_manager.media import (
        add_media, list_media, assign_media, remove_media, analyze_style
    )
    action = getattr(args, "action", None) or "list"
    if action == "list" or action is None:
        result = list_media()
        print(f"[instagram-media] {result['total']} files ({len(result['assigned'])} assigned, {len(result['unassigned'])} unassigned)")
        if result["unassigned"]:
            print("[instagram-media] UNASSIGNED:")
            for f in result["unassigned"]:
                print(f"  {f['id']}  {f['type']}  {f['filename']}")
        if result["assigned"]:
            print("[instagram-media] ASSIGNED TO PLAN:")
            for f in result["assigned"]:
                print(f"  {f['id']}  {f['type']}  {f['filename']}  → {f['assigned_item']}")
    elif action == "add":
        file_path = getattr(args, "file", None)
        if not file_path:
            print("[instagram-media] add requires a file path", file=sys.stderr)
            sys.exit(1)
        entry = add_media(file_path, slot_id=getattr(args, "slot", None), description=getattr(args, "desc", "") or "")
        print(f"[instagram-media] Added {entry['filename']} as {entry['id']} ({entry['type']})")
    elif action == "assign":
        media_id = getattr(args, "file", None)
        slot = getattr(args, "slot", None)
        if not media_id or not slot:
            print("[instagram-media] assign requires <media-id> and --slot", file=sys.stderr)
            sys.exit(1)
        assign_media(media_id, slot)
        print(f"[instagram-media] {media_id} assigned to slot {slot}")
    elif action == "analyze":
        suffix = analyze_style()
        print(f"[instagram-media] Style profile updated. Suffix: {suffix}")
    elif action == "remove":
        media_id = getattr(args, "file", None)
        if not media_id:
            print("[instagram-media] remove requires <media-id>", file=sys.stderr)
            sys.exit(1)
        remove_media(media_id)
        print(f"[instagram-media] {media_id} removed from index")


def _cmd_generate(args: argparse.Namespace) -> None:
    from instagram_manager.generator import generate_plan_assets
    from instagram_manager.storage import PlanNotFound
    from pathlib import Path
    week = getattr(args, "week", None)
    if not week:
        plans_dir = Path(".instagram/memory/plans")
        if plans_dir.exists():
            files = sorted(plans_dir.glob("*.json"))
            if files:
                week = files[-1].stem
    if not week:
        print("[instagram-generate] No approved plan found.", file=sys.stderr)
        sys.exit(1)
    try:
        summary = generate_plan_assets(
            week=week,
            item_id=getattr(args, "item", None),
            format_filter=getattr(args, "format_filter", None),
        )
        print(f"[instagram-generate] Week {week}: {summary['succeeded']} succeeded, "
              f"{summary['blocked']} blocked, {summary['failed']} failed.")
    except PlanNotFound as e:
        print(f"[instagram-generate] Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_publish(args: argparse.Namespace) -> None:
    from instagram_manager.publisher import publish_plan, TokenExpiredError
    from instagram_manager.storage import PlanNotFound
    from pathlib import Path
    week = getattr(args, "week", None)
    if not week:
        plans_dir = Path(".instagram/memory/plans")
        if plans_dir.exists():
            files = sorted(plans_dir.glob("*.json"))
            if files:
                week = files[-1].stem
    if not week:
        print("[instagram-publish] No plan found.", file=sys.stderr)
        sys.exit(1)
    try:
        summary = publish_plan(
            week=week,
            item_id=getattr(args, "item", None),
            publish_all=getattr(args, "publish_all", False),
        )
        if summary.get("token_warning"):
            print(summary["token_warning"])
        print(f"[instagram-publish] Week {week}: {summary['succeeded']} published, "
              f"{summary['failed']} failed, {summary['blocked']} blocked, "
              f"{summary['skipped']} skipped.")
    except TokenExpiredError as e:
        print(f"[instagram-publish] {e}", file=sys.stderr)
        sys.exit(1)
    except PlanNotFound as e:
        print(f"[instagram-publish] Error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_insights(args: argparse.Namespace) -> None:
    from instagram_manager.insights import fetch_week_insights
    from instagram_manager.storage import PlanNotFound
    from pathlib import Path
    week = getattr(args, "week", None)
    if not week:
        plans_dir = Path(".instagram/memory/plans")
        if plans_dir.exists():
            files = sorted(plans_dir.glob("*.json"))
            if files:
                week = files[-1].stem
    if not week:
        print("[instagram-insights] No plan found.", file=sys.stderr)
        sys.exit(1)
    try:
        result = fetch_week_insights(week)
        posts = result.get("posts", [])
        summary = result.get("summary", {})
        print(f"[instagram-insights] Fetched insights for {len(posts)} posts in week {week}")
        for p in posts:
            metrics = p.get("metrics", {})
            avail = "⭐" if p.get("top_performer") else "  "
            print(f"  {avail} {p['item_id']} {p['format']:10s} "
                  f"reach: {metrics.get('reach', 0):,}  "
                  f"engagement: {metrics.get('engagement_rate', 0):.1%}")
        print(f"\nInsights saved to .instagram/memory/insights/{week}.json")
        if summary.get("best_format"):
            print(f"Run /instagram-plan for {week} to use these insights.")
    except PlanNotFound as e:
        print(f"[instagram-insights] Error: {e}", file=sys.stderr)
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instagram_manager",
        description="Instagram Manager CLI — manage your Instagram account through Claude Code",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    sub.add_parser("init", help="Initialize Instagram manager and create brand profile")

    # plan
    p_plan = sub.add_parser("plan", help="Generate weekly content plan")
    p_plan.add_argument("--week", help="ISO week (YYYY-WW). Defaults to current week.")
    p_plan.add_argument("--theme", help="Optional theme override for the week")

    # approve
    p_approve = sub.add_parser("approve", help="Approve weekly content plan")
    p_approve.add_argument("--week", help="ISO week to approve. Defaults to latest draft.")

    # media
    p_media = sub.add_parser("media", help="Manage creator media library")
    p_media.add_argument("action", nargs="?", choices=["add", "list", "assign", "analyze", "remove"])
    p_media.add_argument("file", nargs="?", help="File path (for add/remove)")
    p_media.add_argument("--slot", help="ContentItem id to assign")
    p_media.add_argument("--desc", help="Description for the media file")

    # generate
    p_gen = sub.add_parser("generate", help="Generate content assets")
    p_gen.add_argument("--item", help="Generate for a single item id only")
    p_gen.add_argument("--week", help="ISO week. Defaults to latest approved plan.")
    p_gen.add_argument("--format", dest="format_filter", help="Filter by format")

    # publish
    p_pub = sub.add_parser("publish", help="Publish content to Instagram")
    p_pub.add_argument("--item", help="Publish a single item id only")
    p_pub.add_argument("--week", help="ISO week. Defaults to latest approved plan.")
    p_pub.add_argument("--all", action="store_true", dest="publish_all", help="Publish all ready items")

    # insights
    p_ins = sub.add_parser("insights", help="Fetch post performance insights")
    p_ins.add_argument("--week", help="ISO week. Defaults to previous week.")

    return parser


def main() -> None:
    _check_env()
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "init": _cmd_init,
        "plan": _cmd_plan,
        "approve": _cmd_approve,
        "media": _cmd_media,
        "generate": _cmd_generate,
        "publish": _cmd_publish,
        "insights": _cmd_insights,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
