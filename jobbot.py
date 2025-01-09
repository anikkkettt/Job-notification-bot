import requests
import asyncio
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from telegram import Bot
from telegram.ext import Application

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "7829379039:AAGNg5C2smnmJOWFGJSLaNFcuiZmH7fyjEQ"
GROUP_CHAT_ID = "-4707697711"  # Replace with the group chat ID
API_URL = "https://ap-south-1.cdn.hygraph.com/content/clyfggcvi02yv07uxmtl5gva8/master"
QUERY = """
query JobPosts {
  jobPosts(orderBy: createdAt_DESC, first: 1000) {
    id
    title
    slug
    salary
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

# Initialize application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
bot = application.bot

# Track last sent job ID
last_sent_job_id = None


def fetch_jobs():
    response = requests.post(API_URL, json={"query": QUERY})
    if response.status_code == 200:
        return response.json()["data"]["jobPosts"]
    else:
        print("Failed to fetch jobs:", response.status_code, response.text)
        return []


def format_message(job):
    prefix = "🚨🚨🚨🚨🚨🚨🚨🚨" if job["jobTypeReference"]["jobType"] == "Internship" else ""
    return f"""{prefix}
<b>{job['title']}</b>

<i>Job Type:</i> {job['jobTypeReference']['jobType']}

<i>Salary:</i> {job['salary'] or 'Not Specified'}

<i>Description Link:</i> jobfound.org/job/{job['slug']}

<i>Apply Link:</i> {job['apply']}
"""


async def send_message(message):
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode="HTML")


async def main():
    global last_sent_job_id
    while True:
        try:
            jobs = fetch_jobs()
            if jobs:
                # Get the newest job
                newest_job = jobs[0]
                
                # Check if this job has already been sent
                if newest_job["id"] != last_sent_job_id:
                    # Skip jobs with experience > 0
                    try:
                        experience_value = int(newest_job["experience"]["experience"]) if newest_job["experience"] else 0
                        if experience_value > 0:
                            print(f"Skipping job {newest_job['id']} due to experience > 0.")
                            await asyncio.sleep(60)
                            continue
                    except ValueError:
                        print(f"Invalid experience value for job ID {newest_job['id']}: {newest_job['experience']}")
                        await asyncio.sleep(60)
                        continue

                    # Send the message
                    message = format_message(newest_job)
                    await send_message(message)

                    # Update the last sent job ID
                    last_sent_job_id = newest_job["id"]
                else:
                    print("No new jobs found.")
            await asyncio.sleep(60)  # Check every 60 seconds
        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(60)


# HTTP server for health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")


def run_health_check_server():
    port = int(os.getenv("PORT", 8000))  # Default to port 8000 if no PORT env variable is set
    server = HTTPServer(("", port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    # Start the health check server in a separate thread
    Thread(target=run_health_check_server, daemon=True).start()

    # Run the Telegram bot
    asyncio.run(main())
