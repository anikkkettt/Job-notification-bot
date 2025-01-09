import requests
import asyncio
import os
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from telegram import Bot
from telegram.ext import Application

# Configuration
TELEGRAM_BOT_TOKEN = "7829379039:AAGNg5C2smnmJOWFGJSLaNFcuiZmH7fyjEQ"
GROUP_CHAT_ID = "-4707697711"
API_URL = "https://ap-south-1.cdn.hygraph.com/content/clyfggcvi02yv07uxmtl5gva8/master"
CHECK_INTERVAL = 60  # Seconds between API checks

# GraphQL query
QUERY = """
query JobPosts {
  jobPosts(orderBy: createdAt_DESC, first: 1000) {
    id
    title
    slug
    salary
    createdAt
    experience {
      experience
    }
    jobTypeReference {
      jobType
    }
    apply
  }
}
"""


class JobState:
    """Manages the state of processed jobs"""

    def __init__(self):
        self.processed_jobs = set()
        self.last_check_time = None

    def is_job_processed(self, job_id):
        return job_id in self.processed_jobs

    def mark_job_processed(self, job_id):
        self.processed_jobs.add(job_id)

    def update_check_time(self):
        self.last_check_time = datetime.now(timezone.utc)


class JobBot:
    def __init__(self, token, chat_id):
        self.application = Application.builder().token(token).build()
        self.bot = self.application.bot
        self.chat_id = chat_id
        self.state = JobState()

    def fetch_jobs(self):
        """Fetch jobs from the API with error handling"""
        try:
            response = requests.post(
                API_URL,
                json={"query": QUERY},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("data", {}).get("jobPosts", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching jobs: {e}")
            return []

    def format_message(self, job):
        """Format job information into a message"""
        prefix = "🚨🚨🚨🚨🚨🚨🚨🚨" if job["jobTypeReference"]["jobType"].lower() == "internship" else ""
        return f"""{prefix}
<b>{job['title']}</b>

<i>Job Type:</i> {job['jobTypeReference']['jobType']}

<i>Salary:</i> {job['salary'] or 'Not Specified'}

<i>Description Link:</i> jobfound.org/job/{job['slug']}

<i>Apply Link:</i> {job['apply']}
"""

    async def send_message(self, message):
        """Send message with error handling"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def should_process_job(self, job):
        """Determine if a job should be processed"""
        # Skip if already processed
        if self.state.is_job_processed(job["id"]):
            return False

        # Check experience requirement
        try:
            experience = job.get("experience", {}).get("experience", "0")
            experience_value = int(experience) if experience else 0
            return experience_value == 0
        except (ValueError, TypeError):
            print(f"Invalid experience value for job {job['id']}: {experience}")
            return False

    async def process_jobs(self):
        """Process new jobs and send messages"""
        jobs = self.fetch_jobs()
        if not jobs:
            return

        for job in jobs:
            if self.should_process_job(job):
                message = self.format_message(job)
                if await self.send_message(message):
                    self.state.mark_job_processed(job["id"])
                    print(f"Sent message for job {job['id']}")
                await asyncio.sleep(1)  # Avoid hitting rate limits

    async def run(self):
        """Main bot loop"""
        print("Bot started...")
        while True:
            try:
                await self.process_jobs()
                self.state.update_check_time()
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(CHECK_INTERVAL)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())


def run_health_check_server(port):
    server = HTTPServer(("", port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()


async def main():
    # Initialize and run the bot
    job_bot = JobBot(TELEGRAM_BOT_TOKEN, GROUP_CHAT_ID)

    # Start health check server
    port = int(os.getenv("PORT", 8000))
    Thread(target=run_health_check_server, args=(port,), daemon=True).start()

    # Run the bot
    await job_bot.run()


if __name__ == "__main__":
    asyncio.run(main())