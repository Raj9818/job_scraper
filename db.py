from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
import config

Base = declarative_base()


class JobListing(Base):
    __tablename__ = "job_listings"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    experience = Column(String)
    url = Column(String, unique=True, nullable=False)
    scraped_at = Column(DateTime, server_default=func.now(), nullable=False)


class SourceHealth(Base):
    __tablename__ = "source_health"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False)  # healthy / degraded / blocked / error
    note = Column(String)
    checked_at = Column(DateTime, server_default=func.now(), nullable=False)

class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    # running / completed / degraded / blocked / error
    status = Column(String, nullable=False)
    started_at = Column(DateTime, server_default=func.now(), nullable=False,)
    finished_at = Column(DateTime)
    pages_attempted = Column(Integer, default=0)
    pages_succeeded = Column(Integer, default=0)
    listings_found = Column(Integer, default=0)
    listings_saved = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    note = Column(String)

# PostgreSQL engine
engine = create_engine(config.DB_URL, pool_pre_ping=True,)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Job listings
def save_listings(listings):
    session = Session()
    saved = 0
    try:
        for item in listings:
            if not item.get("url"):
                continue
            exists = session.query(JobListing).filter_by(url=item["url"]).first()
            if exists:
                continue
            session.add(JobListing(**item))
            saved += 1
        session.commit()
        return saved
    except Exception:
            session.rollback()
            raise
    finally:
        session.close()


# Source health
def log_health(source, status, note=""):
    session = Session()
    try:
        session.add(SourceHealth(source=source, status=status, note=note))
        session.commit()
    except Exception:
        session.rollback()
        raise

    finally:
        session.close()
    
# ---------------------------------------------------------
# Scrape run tracking
# ---------------------------------------------------------

def start_scrape_run(source):
    session = Session()

    try:
        run = ScrapeRun(
            source=source,
            status="running",
        )

        session.add(run)
        session.commit()

        session.refresh(run)

        return run.id

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def update_scrape_run(
    run_id,
    *,
    status=None,
    pages_attempted=None,
    pages_succeeded=None,
    listings_found=None,
    listings_saved=None,
    failures=None,
    note=None,
    finished=False,
):
    session = Session()

    try:
        run = (
            session.query(ScrapeRun)
            .filter_by(id=run_id)
            .first()
        )

        if not run:
            raise ValueError(
                f"Scrape run {run_id} not found"
            )

        if status is not None:
            run.status = status

        if pages_attempted is not None:
            run.pages_attempted = pages_attempted

        if pages_succeeded is not None:
            run.pages_succeeded = pages_succeeded

        if listings_found is not None:
            run.listings_found = listings_found

        if listings_saved is not None:
            run.listings_saved = listings_saved

        if failures is not None:
            run.failures = failures

        if note is not None:
            run.note = note

        if finished:
            run.finished_at = datetime.utcnow()

        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()