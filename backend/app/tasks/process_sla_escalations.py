import logging

from app.db.session import SessionLocal
from app.services.ticket_escalation import process_sla_escalations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()

    try:
        created_count = process_sla_escalations(db=db)

        logger.info(
            "SLA escalation processing completed. New escalations created: %s",
            created_count,
        )

    except Exception:
        logger.exception("SLA escalation processing failed.")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
