from flask import Flask, jsonify, render_template
from db import Session, JobListing, SourceHealth

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/jobs")
def api_jobs():
    session = Session()

    try:
        jobs = (
            session.query(JobListing)
            .order_by(JobListing.scraped_at.desc())
            .limit(100)
            .all()
        )

        return jsonify([
            {
                "id": job.id,
                "title": job.title or "",
                "company": job.company or "",
                "location": job.location or "",
                "experience": job.experience or "",
                "url": job.url or "",
                "scraped_at": (
                    job.scraped_at.isoformat()
                    if job.scraped_at
                    else ""
                ),
            }
            for job in jobs
        ])

    finally:
        session.close()


@app.route("/api/health")
def api_health():
    session = Session()

    try:
        health = (
            session.query(SourceHealth)
            .order_by(SourceHealth.checked_at.desc())
            .limit(5)
            .all()
        )

        return jsonify([
            {
                "source": item.source,
                "status": item.status,
                "note": item.note or "",
                "checked_at": (
                    item.checked_at.isoformat()
                    if item.checked_at
                    else ""
                ),
            }
            for item in health
        ])

    finally:
        session.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
    )