import requests
from bs4 import BeautifulSoup
import time
import logging
import random
from urllib.parse import urljoin, urlencode
from pyvirtualdisplay import Display
import json
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
)
logger = logging.getLogger(__name__)

class IndeedCrawler:
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.indeed.com"
        self.session = requests.Session()
        self.display = Display(visible=0, size=(1920, 1080)) if headless else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'DNT': '1',
        }
        self.max_retries = 4
        self.retry_delay = 2

    def start(self):
        """Start the virtual display if in headless mode"""
        if self.display:
            self.display.start()
            logger.info("Starting X virtual framebuffer")

    def stop(self):
        """Stop the virtual display if in headless mode"""
        if self.display:
            self.display.stop()

    def is_html_blocked(self, html: str) -> bool:
        """Check if the response indicates we're being blocked"""
        blocking_indicators = [
            "Please verify you are a human",
            "Please solve this CAPTCHA",
            "Access to this page has been denied",
            "Your IP address has been temporarily blocked"
        ]
        return any(indicator.lower() in html.lower() for indicator in blocking_indicators)

    def make_request(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """Make a request with retry logic and blocking detection"""
        full_url = urljoin(self.base_url, url)
        retries = 0
        
        while retries < self.max_retries:
            try:
                response = self.session.get(
                    full_url,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                
                if self.is_html_blocked(response.text):
                    logger.warning(
                        f"CurlRequestsCheerioCrawler: Reclaiming failed request back to the list or queue. "
                        f"Blocked by HTML. {{\"retryCount\":{retries+1}}}"
                    )
                    retries += 1
                    time.sleep(self.retry_delay * (1 + random.random()))
                    continue
                    
                return response
                
            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                retries += 1
                if retries < self.max_retries:
                    time.sleep(self.retry_delay * (1 + random.random()))
                    continue
                return None
        
        return None

    def extract_job_details(self, job_url: str) -> Optional[Dict]:
        """Extract details from a job posting page"""
        response = self.make_request(job_url)
        if not response:
            return None
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            job_data = {
                'title': soup.find('h1', {'class': 'jobsearch-JobInfoHeader-title'}).text.strip(),
                'company': soup.find('div', {'class': 'jobsearch-InlineCompanyRating'}).text.strip(),
                'location': soup.find('div', {'class': 'jobsearch-JobInfoHeader-subtitle'}).text.strip(),
                'description': soup.find('div', {'id': 'jobDescriptionText'}).text.strip(),
            }
            logger.info(f"[DETAIL]: Job offer extracted --- {job_url}")
            return job_data
        except Exception as e:
            logger.error(f"Failed to extract job details: {e}")
            return None

    def search_jobs(self, position: str, location: str, max_pages: int = 2) -> List[Dict]:
        """Search for jobs and extract listings"""
        jobs = []
        page = 0
        
        while page < max_pages:
            params = {
                'q': position,
                'l': location,
                'sort': 'date',
                'start': page * 10
            }
            
            response = self.make_request('/jobs', params=params)
            if not response:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', {'class': 'job_seen_beacon'})
            
            if not job_cards:
                break
                
            for card in job_cards:
                try:
                    job_id = card.get('data-jk')
                    job_url = f'/viewjob?jk={job_id}'
                    job_details = self.extract_job_details(job_url)
                    if job_details:
                        jobs.append(job_details)
                except Exception as e:
                    logger.error(f"Failed to process job card: {e}")
                    continue
            
            logger.info(f"[SEARCH][PAGE: {page + 1}]: Enqueued {len(job_cards)} unique pages")
            page += 1
            time.sleep(random.uniform(1, 3))  # Random delay between pages
            
        return jobs

def main():
    crawler = IndeedCrawler(headless=True)
    try:
        crawler.start()
        jobs = crawler.search_jobs(
            position="web developer",
            location="San Francisco",
            max_pages=2
        )
        
        # Save results to file
        with open('jobs.json', 'w') as f:
            json.dump(jobs, f, indent=2)
            
    finally:
        crawler.stop()

if __name__ == "__main__":
    main()