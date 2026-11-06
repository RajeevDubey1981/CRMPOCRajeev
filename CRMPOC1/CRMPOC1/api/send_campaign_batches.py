"""Cron entry point: sends the next due batch of any Marketing campaign that's mid-send.

A campaign over CAMPAIGN_BATCH_SIZE (25) recipients is sent CAMPAIGN_BATCH_SIZE at a time, waiting
CAMPAIGN_BATCH_GAP_MINUTES (20) between batches -- so a large campaign never fires hundreds of emails
in one burst, which is what gets a sending domain flagged. Run this on a schedule shorter than the gap
(every 5 minutes is plenty); it is a no-op whenever nothing is due.

Install once on the server:
    crontab -e
    */5 * * * * cd /var/www/indcool/api && venv/bin/python send_campaign_batches.py >> /var/log/indcool/campaign_batches.log 2>&1
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
os.chdir(API_DIR)
sys.path.insert(0, str(API_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("send_campaign_batches")


def main() -> None:
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.marketing.access import Ctx, is_admin_user, user_ticks
    from app.marketing.db import marketing_enabled, new_marketing_session
    from app.marketing.models import MkCampaign
    from app.marketing.router import _send_campaign_batch
    from app.models.user import User
    from app.sales.db import new_sales_session, sales_enabled

    if not marketing_enabled():
        logger.info("Marketing database not configured, nothing to do.")
        return

    mdb = new_marketing_session()
    main_db = SessionLocal()
    sales_db = new_sales_session() if sales_enabled() else None
    try:
        now = datetime.now(timezone.utc)
        due = list(mdb.scalars(
            select(MkCampaign).where(MkCampaign.status == "sending", MkCampaign.next_batch_at <= now)
        ))
        if not due:
            logger.info("No campaign batches due.")
            return
        for c in due:
            user_id = c.approved_by or c.created_by
            user = main_db.get(User, user_id) if user_id else None
            if user is None:
                logger.error("Campaign %s (%s): no valid user to send as (user_id=%s), skipping.", c.id, c.name, user_id)
                continue
            ctx = Ctx(user=user, ticks=user_ticks(mdb, user), is_admin=is_admin_user(user))
            before_status = c.status
            _send_campaign_batch(mdb, main_db, sales_db, ctx, c)
            mdb.commit()
            logger.info(
                "Campaign %s (%s): batch sent (%s -> %s), %s sent so far, %s skipped, next batch %s",
                c.id, c.name, before_status, c.status, c.sent_count, c.skipped_count, c.next_batch_at,
            )
    finally:
        mdb.close()
        main_db.close()
        if sales_db is not None:
            sales_db.close()


if __name__ == "__main__":
    main()
