import asyncio
import requests
from datetime import datetime, timezone
from telegram import Bot

# Configuration settings for our bot
TELEGRAM_BOT_TOKEN = "7829379039:AAGNg5C2smnmJOWFGJSLaNFcuiZmH7fyjEQ"
GROUP_CHAT_ID = "-4707697711"
API_URL = "https://ap-south-1.cdn.hygraph.com/content/clyfggcvi02yv07uxmtl5gva8/master"
CHECK_INTERVAL = 60  # How often to check for new jobs (in seconds)

# GraphQL query to fetch jobs
QUERY = """
query JobPosts {
  jobPosts(orderBy: createdAt_DESC, first: 100) {
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

class JobBot:
    def __init__(self):
        # Initialize our bot with the Telegram token
        self.bot = Bot(TELEGRAM_BOT_TOKEN)
        # Store the timestamp of the most recent job we've seen
        self.last_job_time = None
        print(f"Bot initialized at {datetime.now(timezone.utc)}")

    def fetch_jobs(self):
        """Fetch jobs from the GraphQL API"""
        try:
            response = requests.post(
                API_URL,
                json={"query": QUERY},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            jobs = response.json().get("data", {}).get("jobPosts", [])
            print(f"Fetched {len(jobs)} jobs at {datetime.now(timezone.utc)}")
            return jobs
        except Exception as e:
            print(f"Error fetching jobs: {e}")
            return []

    def format_message(self, job):
        """Format the job information into a Telegram message"""
        prefix = "🚨🚨🚨🚨🚨🚨🚨🚨" if job["jobTypeReference"]["jobType"].lower() == "internship" else ""
        return f"""{prefix}
<b>{job['title']}</b>

<i>Job Type:</i> {job['jobTypeReference']['jobType']}

<i>Salary:</i> {job['salary'] or 'Not Specified'}

<i>Description Link:</i> jobfound.org/job/{job['slug']}

<i>Apply Link:</i> {job['apply']}

<i>Posted:</i> {job['createdAt']}"""

    def is_new_job(self, job_time_str):
        """Check if a job is newer than the last job we've seen"""
        if not self.last_job_time:
            return True

        job_time = datetime.fromisoformat(job_time_str.replace('Z', '+00:00'))
        last_time = datetime.fromisoformat(self.last_job_time.replace('Z', '+00:00'))
        return job_time > last_time

    async def send_message(self, message):
        """Send a message to the Telegram group"""
        try:
            await self.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            print(f"Message sent successfully at {datetime.now(timezone.utc)}")
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def should_process_job(self, job):
        """Determine if we should process and send this job"""
        # Check if it's a new job
        if not self.is_new_job(job["createdAt"]):
            return False

        # Check if the experience requirement is 0
        try:
            experience = job.get("experience", {}).get("experience", "0")
            experience_value = int(experience) if experience else 0
            return experience_value == 0
        except (ValueError, TypeError):
            print(f"Invalid experience value for job {job['id']}")
            return False

    async def process_jobs(self):
        """Process all jobs and send messages for new ones"""
        jobs = self.fetch_jobs()
        if not jobs:
            return

        processed_count = 0
        for job in jobs:
            if self.should_process_job(job):
                message = self.format_message(job)
                if await self.send_message(message):
                    processed_count += 1
                    # Update last_job_time only after successfully processing the job
                    self.last_job_time = job["createdAt"]
                await asyncio.sleep(1)  # Prevent hitting rate limits

        if processed_count > 0:
            print(f"Processed {processed_count} new jobs")

    async def run(self):
        """Main bot loop"""
        print("Bot started...")
        while True:
            try:
                await self.process_jobs()
                print(f"Sleeping for {CHECK_INTERVAL} seconds")
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

async def main():
    """Main function to run the bot"""
    bot = JobBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())