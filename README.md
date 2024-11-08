# Web Scraping Methods and Error Handling Guide

## Table of Contents
1. [Common Error Patterns](#common-error-patterns)
2. [Requests Library](#requests-library)
3. [HTTPX Library](#httpx-library)
4. [cURL](#curl)
5. [Playwright](#playwright)
6. [Selenium](#selenium)
7. [aiohttp](#aiohttp)
8. [General Best Practices](#general-best-practices)

## Common Error Patterns

### HTTP Status Codes to Handle
- `403 Forbidden`: Access denied
- `429 Too Many Requests`: Rate limiting
- `503 Service Unavailable`: Server overload/maintenance
- `404 Not Found`: Invalid URL
- `502 Bad Gateway`: Proxy/server issues
- `401 Unauthorized`: Authentication required

### Common Ban Indicators
```python
BAN_PATTERNS = [
    'captcha',
    'blocked',
    'banned',
    'security check',
    'unusual traffic',
    'access denied',
    'ddos protection by cloudflare',
    'please verify you are a human',
    'your ip has been blocked',
    'too many requests'
]
```

## Requests Library

### Basic Error Handling
```python
import requests
from requests.exceptions import RequestException
import time

def make_request(url, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    session = requests.Session()
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check for ban patterns
            if any(pattern in response.text.lower() for pattern in BAN_PATTERNS):
                raise Exception("Detected potential ban")
                
            return response
            
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
            else:
                time.sleep(2 ** retry_count)  # Exponential backoff
                
        except Exception as e:
            print(f"Error: {str(e)}")
            retry_count += 1
            
    return None
```

## HTTPX Library

### Async Error Handling
```python
import httpx
import asyncio
import backoff

class HTTPXScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            proxies={
                'http://': 'http://proxy.example.com',
                'https://': 'http://proxy.example.com',
            }
        )
    
    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, httpx.TimeoutException),
        max_tries=3
    )
    async def fetch(self, url):
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 30))
                await asyncio.sleep(retry_after)
                raise
            raise
```

## cURL

### Error Handling with PycURL
```python
import pycurl
from io import BytesIO

def curl_request(url):
    buffer = BytesIO()
    c = pycurl.Curl()
    
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.FOLLOWLOCATION, True)
    c.setopt(c.MAXREDIRS, 5)
    c.setopt(c.CONNECTTIMEOUT, 30)
    c.setopt(c.TIMEOUT, 60)
    c.setopt(c.NOSIGNAL, 1)
    
    # SSL Verification
    c.setopt(c.SSL_VERIFYPEER, 1)
    c.setopt(c.SSL_VERIFYHOST, 2)
    
    try:
        c.perform()
        
        # Check HTTP status
        status_code = c.getinfo(pycurl.HTTP_CODE)
        if status_code != 200:
            raise Exception(f"HTTP Error {status_code}")
            
        return buffer.getvalue()
    except pycurl.error as e:
        print(f"Curl Error: {e}")
    finally:
        c.close()
```

## Playwright

### Automated Browser Error Handling
```python
from playwright.sync_api import sync_playwright, TimeoutError

class PlaywrightScraper:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        )
    
    def handle_request(self, url, wait_for_selector='body'):
        page = self.context.new_page()
        try:
            # Navigate with timeout
            page.goto(url, timeout=30000, wait_until='networkidle')
            
            # Wait for content
            page.wait_for_selector(wait_for_selector)
            
            # Check for common protection systems
            cloudflare = page.locator("text=DDoS protection by Cloudflare")
            if cloudflare.count() > 0:
                raise Exception("Cloudflare detected")
            
            # Check for CAPTCHA
            captcha = page.locator("text=CAPTCHA")
            if captcha.count() > 0:
                raise Exception("CAPTCHA detected")
                
            return page.content()
            
        except TimeoutError:
            print("Page load timeout")
        finally:
            page.close()
    
    def cleanup(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()
```

## Selenium

### WebDriver Error Handling
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class SeleniumScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        
    def check_for_blocks(self):
        # Check for common blocking elements
        block_texts = [
            'captcha',
            'security check',
            'access denied'
        ]
        
        page_source = self.driver.page_source.lower()
        for text in block_texts:
            if text in page_source:
                raise Exception(f"Blocked: {text} detected")
    
    def get_page(self, url, timeout=10):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            self.check_for_blocks()
            return self.driver.page_source
            
        except TimeoutException:
            print("Page load timeout")
        except Exception as e:
            print(f"Error: {str(e)}")
        
    def cleanup(self):
        self.driver.quit()
```

## aiohttp

### Async Error Handling
```python
import aiohttp
import asyncio
from aiohttp import ClientTimeout

class AsyncScraper:
    def __init__(self):
        self.timeout = ClientTimeout(total=30)
        self.session = None
    
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def fetch(self, url, max_retries=3):
        await self.init_session()
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with self.session.get(url) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 30))
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                        
                    response.raise_for_status()
                    return await response.text()
                    
            except aiohttp.ClientError as e:
                print(f"Error: {str(e)}")
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)
                
        return None
    
    async def cleanup(self):
        if self.session:
            await self.session.close()
```

## General Best Practices

### Rate Limiting
```python
import time
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, requests_per_second=1):
        self.requests_per_second = requests_per_second
        self.timestamps = deque()
    
    def wait(self):
        now = datetime.now()
        
        # Remove timestamps older than 1 second
        while self.timestamps and now - self.timestamps[0] > timedelta(seconds=1):
            self.timestamps.popleft()
        
        # If at rate limit, wait until oldest request expires
        if len(self.timestamps) >= self.requests_per_second:
            sleep_time = (self.timestamps[0] + timedelta(seconds=1) - now).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.timestamps.append(now)
```

### Proxy Rotation
```python
import random

class ProxyRotator:
    def __init__(self, proxy_list):
        self.proxies = proxy_list
        self.current_index = 0
        
    def get_proxy(self):
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return {
            'http': proxy,
            'https': proxy
        }
    
    def remove_proxy(self, proxy):
        if proxy in self.proxies:
            self.proxies.remove(proxy)
    
    def add_proxy(self, proxy):
        if proxy not in self.proxies:
            self.proxies.append(proxy)
```

### User-Agent Rotation
```python
class UserAgentRotator:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Firefox/89.0'
        ]
    
    def get_random_user_agent(self):
        return random.choice(self.user_agents)
```

Remember to implement these practices based on your specific needs and the website's requirements. Always check and respect the website's robots.txt and terms of service.