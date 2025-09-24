# selenium_fetch.py

Automates EECS Office Hours login and fetches outstanding request JSON data.

## Setup
```bash
pip install selenium requests
```
Install ChromeDriver and add to PATH.

## Usage
```bash
python3 selenium_fetch.py
```

First run:
Browser opens for manual login (90s timeout). Cookies saved to `oh_cookies.json`.
You must wait for this timeout to end for cookies to be saved.

Subsequent runs:
Uses saved cookies automatically to fetch queue.

## Output
- `outstanding_json/outstanding_YYYYMMDDTHHMMSSZ.json`: Timestamped data
- `outstanding_json/latest.json`: Most recent data
