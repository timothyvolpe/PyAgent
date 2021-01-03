"""
    PyAgent - Python program for aggregating housing info
    Copyright (C) 2021 Timothy Volpe

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import getopt
import configparser
import logging
from logging.handlers import RotatingFileHandler
import os
import glob
import pyagent
import scrapy
from scrapy.crawler import CrawlerProcess

LOG_FILE = "output.log"

logger = logging.getLogger(__name__)
log_formatter = logging.Formatter("[%(asctime)s][%(threadName)12.12s][%(levelname)5.5s] %(message)s")
handler_info = logging.StreamHandler(sys.stdout)
regular_filter = None

CONFIG_FILE = "options.ini"
OUTPUT_DIR = "output"
OUTPUT_CACHE_BASE = "scrape_results_*.json"

scrape_website_list = []


class RegularFilter(logging.Filter):
    """
    Filter for regular, non-verbose output
    """
    def filter(self, record):
        return record.levelno == logging.INFO and "scrapy" not in record.name


class VerboseFilter(logging.Filter):
    """
    Filter for verbose output
    """
    def filter(self, record):
        return (record.levelno == logging.INFO or record.levelno == logging.WARNING) and "scrapy" not in record.name


def setup_logger():
    global regular_filter

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Output log file handler
    handler_log = RotatingFileHandler(LOG_FILE, mode='a', maxBytes=5 * 1024 * 1024, backupCount=2, encoding=None,
                                      delay=0)
    handler_log.setLevel(logging.DEBUG)
    handler_log.setFormatter(log_formatter)
    root.addHandler(handler_log)

    # stderr handler
    handler_err = logging.StreamHandler(sys.stderr)
    handler_err.setLevel(logging.ERROR)
    handler_err.setFormatter(log_formatter)
    root.addHandler(handler_err)

    # Regular info handler
    regular_filter = RegularFilter()
    handler_info.addFilter(regular_filter)
    root.addHandler(handler_info)


def print_help() -> None:
    """
    Prints the help information
    :return: None
    """
    print()
    print("Usage: pyagent [-h] [-v level] [-s]")
    print()
    print("Options:")
    print("\t-h\t\t\tDisplays command help")
    print("\t-v level\tEnables verbose output, 1 is only info, 2 is debug")
    print("\t-s\t\t\tScrapes the enabled websites and caches the results")
    print()
    print("\tSee options.ini for scrape-able websites.")
    print()


def enable_verbose() -> None:
    """
    Enables verbose output, by turning on the info logger
    :return: Nothing
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(log_formatter)
    handler.addFilter(lambda record: record.levelno == logging.DEBUG or record.levelno == logging.WARNING)
    logging.getLogger().addHandler(handler)

    handler_info.removeFilter(regular_filter)
    handler_info.addFilter(VerboseFilter())

    logger.debug("Using verbose output")


def get_latest_cache(caches: list[str]) -> (str, int):
    """
    Takes a list of cache file names and returns the one with the highest index
    :param caches: List of cache file names
    :return: Cache file name with highest index, and index value
    """
    max_index = 1
    max_cache_name = ""
    for cache in caches:
        cache = cache.split("\\")[1]
        num_pos = OUTPUT_CACHE_BASE.find("*")
        num_str = cache[num_pos:]
        num_end = 0
        for idx, val in enumerate(num_str):
            if val.isdigit():
                num_end = idx
                continue
            break
        num_str = num_str[0:num_end + 1]
        try:
            num_val = int(num_str)
            if num_val >= max_index:
                max_index = num_val
                max_cache_name = cache
        except ValueError:
            continue
    return max_cache_name, max_index


def perform_scrape() -> bool:
    """
    Performs a scrape of the supported and enabled websites.
    :return: True if successfully scraped all websites, false if otherwise
    """
    logging.info("Performing scrape of sources specified in {0}".format(CONFIG_FILE))
    logger.debug("Scraping the following sources: {0}".format(", ".join(scrape_website_list)))

    pyagent.init_sources()

    # Get the most recent cache
    cache_index = 0
    if not os.path.isdir(OUTPUT_DIR):
        logger.debug("Folder {0} does not exist, so it was created".format(OUTPUT_DIR))
        os.makedirs(OUTPUT_DIR)
    else:
        cache_files = glob.glob(OUTPUT_DIR + "/" + OUTPUT_CACHE_BASE)
        _, cache_index = get_latest_cache(cache_files)
    cache_path = OUTPUT_DIR + "\\" + OUTPUT_CACHE_BASE.replace("*", str(cache_index+1))

    # Crawl scrapy sources
    process = CrawlerProcess(settings={
        "FEEDS": {
            cache_path: {"format": "json"},
        },
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'WARNING',
    })
    for source in pyagent.get_source_list():
        if isinstance(source.spider, pyagent.ScrapySpider):
            logger.debug("Scraping source: {0} ({1})".format(source.name, source.key))
            process.crawl(source.spider.scrapy_spider)
    process.start()

    logger.info("Finished scrape of specified sources")

    return True


def perform_characterization() -> bool:
    """
    Characterizes housing data from latest scrape
    :return: True if successfully characterized, false if otherwise
    """
    # Check for cached scrape data
    cache_files = glob.glob(OUTPUT_DIR + "/" + OUTPUT_CACHE_BASE)
    if not cache_files:
        logger.info("There was not cached housing data to characterize. Try running pyagent -s to scrape data.")
        return 0
    # Get the latest cache
    cache_name, cache_index = get_latest_cache(cache_files)
    if cache_name == "":
        logger.info("Could not find valid housing data cache. Try running pyagent -s to scrape data.")
        return 0

    logger.info("Characterizing housing data from cache '{0}'...".format(cache_name))

    return True


def load_options() -> bool:
    """
    Loads the options file. If it does not exist, a default one will be created.
    :return: True if successfully loaded or created the file, false if otherwise.
    """
    config = configparser.ConfigParser()
    if not os.path.isfile(CONFIG_FILE):
        logger.debug("Config file {0} not found, creating default".format(CONFIG_FILE))

        config["scrape_websites"] = {"apartments_com": "1",
                                     "craigslist_bos": "1"}

        config["apartments_com"] = {"search_url": "boston-ma/2-to-3-bedrooms-under-1500/"}
        config["craigslist_bos"] = {"subdomain": "boston"}

        with open(CONFIG_FILE, "w") as configfile:
            config.write(configfile)

    logger.debug("Reading config file {0}".format(CONFIG_FILE))
    read_files = config.read(CONFIG_FILE)
    if not read_files:
        logger.critical("Could not read config file, it should have been created it if did not exist")
        return False

    if config.has_section("scrape_websites"):
        scrape_sites = config["scrape_websites"]
        for key in scrape_sites:
            if pyagent.get_source(key):
                scrape_website_list.append(key)
            else:
                logger.warning("Unknown source key {0}".format(key))
    else:
        logger.critical("Config file missing section [scrape_websites]")
        return False

    # Get settings for each source
    for source_key in scrape_sites:
        if not config.has_section(source_key):
            logger.critical("Missing config section for source {0}".format(source_key))
            return False
        # Add to source
        source_obj = pyagent.get_source(source_key)
        for key in config[source_key]:
            source_obj.add_config(key, config[source_key][key])
        if not source_obj.verify_config():
            logger.critical("Invalid config for source {0}".format(source_key))
            return False

    return True


def main(argv) -> int:
    """
    Program main entry point. Parses command line arguments.
    :param argv: Command line arguments
    :return: Program return code
    """

    logger.info("Starting PyAgent...")

    # Get command line arguments
    try:
        opts, args = getopt.getopt(argv, "hvs", [])
    except getopt.GetoptError:
        logger.critical("Invalid command line arguments.")
        print_help()
        return 2

    do_help = False
    do_scrape = False
    do_verbose = False

    for opt, arg in opts:
        if opt == "-h":
            do_help = True
        elif opt == "-v":
            do_verbose = True
        elif opt == "-s":
            do_scrape = True

    if do_help:
        logger.debug("Showing help, no other action is performed")
        print_help()
        return 0
    if do_verbose:
        enable_verbose()

    # Load the options file
    if not load_options():
        return 1

    if do_scrape:
        if not perform_scrape():
            return 1

    if not perform_characterization():
        return 1

    return 0


setup_logger()
if __name__ == "__main__":
    print("PyAgent  Copyright (C) 2021  Timothy Volpe")
    print("This program comes with ABSOLUTELY NO WARRANTY.")
    print("This is free software, and you are welcome to redistribute it under certain conditions.")
    print("", flush=True)

    pyagent.LocationCache.init_cache()
    ret_val = main(sys.argv[1:])
    pyagent.LocationCache.save_cache()
    sys.exit(ret_val)

