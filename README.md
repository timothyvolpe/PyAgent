# PyAgent
Tool for aggregating and analyzing housing rental information

## Overview

This tool is used to scrape housing information from various sources, aggregate all of the important information, then evaluate each option based on a set of criteria.

### Credits

Timothy Volpe © 2021

## Installation

### Browser Headers

In order to properly mimic a browser, we need a set of headers to use that match what the websites are expecting.

Create a file `PyAgent/browsers.py` and add user agents in the format below (you can use a website such as https://httpbin.org/headers to get the headers):

```
header_list = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.5",
        "Host": "httpbin.org",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
    },
]
```

Its good to have a referral URL in there as well.

### Requirements

- Python 3.8.7
- scrapy 2.4.1
- geopy 2.1.0
- haversine 2.3.0
- setuptools 51.1.1
- wheel 0.36.2
- pywebview 3.4

Requires the [Edge Chromium runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) on Windows if you intend to use the GUI.

