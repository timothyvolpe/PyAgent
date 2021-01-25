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
import pyagentui
import json
import importlib
import random
import haversine
import hashlib
from base64 import b64encode
from scrapy.crawler import CrawlerProcess

has_browsers_file = False

LOG_FILE = "output.log"
PERFECT_SCORE = 0.8

logger = logging.getLogger(__name__)
log_formatter = logging.Formatter("[%(asctime)s][%(threadName)12.12s][%(levelname)5.5s] %(message)s")
handler_info = logging.StreamHandler(sys.stdout)
regular_filter = None

CONFIG_FILE = "options.ini"
OUTPUT_DIR = "output"
OUTPUT_CACHE_BASE = "scrape_results_*.json"
CHAR_OUTPUT_FILE = "output/characterization.json"

scrape_website_list = []
train_data = None

housing_criteria = [pyagent.CriterionLesser(name="Rent", key="rent", weight=100, lower=800,
                                            result_format=pyagent.ResultFormat.Currency, upper=1500),
                    pyagent.CriterionSqFt(name="Square Footage", key="sqft", weight=10, lower=0,
                                          result_format=pyagent.ResultFormat.SquareFoot, upper=1200, maximum=2500),
                    pyagent.CriterionBeds(name="Bedrooms", key="beds", lower=2, weight=50, upper=3,
                                          result_format=pyagent.ResultFormat.Bedrooms, minimum=2, required=True),
                    pyagent.CriterionGreater(name="Bathrooms", key="baths_str", lower=0, weight=15, upper=2,
                                             result_format=pyagent.ResultFormat.Bathrooms, maximum=3),
                    pyagent.CriterionLesser(name="Deposit", key="deposit", lower=0, weight=100, upper=4000,
                                            result_format=pyagent.ResultFormat.Currency, ),
                    pyagent.CriterionTrain(name="Train Proximity", key="coordinates", weight=50, max_distance=2,
                                           result_format=pyagent.ResultFormat.Miles, )]


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


def generate_uid(address, unit) -> str:
    s = b64encode(address.encode())
    unit = str(unit)
    if unit is None:
        unit = "0"
    p = b64encode(unit.encode())
    return hashlib.sha256(s + p).hexdigest()


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
    print("Usage: pyagent [-h] [-v level] [-s] [--gui]")
    print()
    print("Options:")
    print("\t-h\t\t\tDisplays command help")
    print("\t-v level\tEnables verbose output, 1 is only info, 2 is debug")
    print("\t-s\t\t\tScrapes the enabled websites and caches the results")
    print("\t-n\t\t\tDo not perform characterization")
    print("\t--gui\t\tOpen the characterization UI. Mutually exclusive with scraping.")
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


def get_latest_cache(caches: list) -> (str, int):
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


def get_nearby_trains(location, radius_mi: float):
    """
    Returns a list of nearby trains in a radius around location
    :param location: Location to center search radius
    :param radius_mi: Radius of search circle in miles
    :return: List of trains serviced at stations within radius
    """
    if not location:
        return None
    nearby_stations = {}
    for station in train_data:
        distance = haversine.haversine(station["coords"], location, unit=haversine.Unit.MILES)
        if distance < radius_mi:
            lines = station["lines"]
            for line in lines:
                lines_to_add = []
                if "Commuter Rail" in line:
                    lines_to_add = ["Commuter Rail"]
                elif "Silver Line" in line:
                    lines_to_add = ["Silver Line"]
                elif "Green Line" in line:
                    line_branches = line[line.find("(") + 1:line.find(")")]
                    branch_tokens = line_branches.split(",")
                    for branch in branch_tokens:
                        lines_to_add.append("Green Line (" + branch.replace(" ", "") + ")")
                elif "Red Line" in line:
                    line_branches = line[line.find("(") + 1:line.find(")")]
                    branch_tokens = line_branches.split(",")
                    for branch in branch_tokens:
                        lines_to_add.append("Red Line (" + branch.replace(" ", "") + ")")
                else:
                    lines_to_add = [line]

                for add in lines_to_add:
                    if add in nearby_stations:
                        nearby_stations[add].append(station["name"])
                    else:
                        nearby_stations[add] = [station["name"]]

    return nearby_stations


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

    # Crawler settings
    crawler_settings ={
        "FEEDS": {
            cache_path: {"format": "jsonlines"},
        },
        'DOWNLOAD_DELAY': 1,
        'LOG_LEVEL': 'WARNING',
        'DOWNLOADER_CLIENT_TLS_METHOD': "TLSv1.2"       # for craigslist?
    }
    # Get a header
    if has_browsers_file:
        headers = random.choice(browsers.header_list)
        crawler_settings["DEFAULT_REQUEST_HEADERS"] = headers
        # Set custom headers for each source that has them
        for source in pyagent.get_source_list():
            if isinstance(source.spider, pyagent.ScrapySpider):
                source_key = source.key
                if source_key in browsers.headers_per_source:
                    source_header = random.choice(browsers.headers_per_source[source_key])
                    if not source.spider.scrapy_spider.custom_settings:
                        source.spider.scrapy_spider.custom_settings = {}
                    source.spider.scrapy_spider.custom_settings["DEFAULT_REQUEST_HEADERS"] = source_header
                cache_specific_path = cache_path + "_" + source_key
                source.spider.scrapy_spider.custom_settings["FEEDS"] = {
                    cache_specific_path: {"format": "json"}
                }
    else:
        logger.warning("You have not provided any headers! Your scrape requests may get blocked. Please see README for "
                       "information.")
        crawler_settings["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0"

    # Crawl scrapy sources
    process = CrawlerProcess(crawler_settings)
    for source in pyagent.get_source_list():
        if isinstance(source.spider, pyagent.ScrapySpider):
            if source.key in scrape_website_list:
                logger.debug("Scraping source: {0} ({1})".format(source.name, source.key))
                process.crawl(source.spider.scrapy_spider)
            else:
                logger.debug("Skipping source: {0}".format(source.name))
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
        return False
    # Get the latest cache
    cache_name, cache_index = get_latest_cache(cache_files)
    if cache_name == "":
        logger.info("Could not find valid housing data cache. Try running pyagent -s to scrape data.")
        return False
    cache_name = OUTPUT_DIR + "/" + cache_name

    logger.info("Characterizing housing data from cache '{0}'...".format(cache_name))

    try:
        with open(cache_name, "r") as cache_file:
            jsonlines = cache_file.readlines()
            housing_data = [json.loads(jline) for jline in jsonlines]
    except json.decoder.JSONDecodeError as e:
        logger.critical("Failed to read scraped data file: {0}".format(e))
        return False
    except OSError as e:
        logger.critical("Failed to load scrapy data from {0}: {1}".format(cache_name, e))
        return False

    # Characterize each
    char_results_good = []      # Good apartments
    char_results_bad = []       # Bad apartments (have a 0 in some category)
    char_results_dq = []        # Disqualified apartments
    char_output = {}            # Dumps to JSON file for GUI
    total_houses = len(housing_data)
    used_uids = []
    for housing in housing_data:
        result_dict = {
            "uid": -1,
            "address": housing["address"],
            "link": housing["link"],
            "source": housing["source"],
            "unit": housing["unit"],
            "criterion": [],
            "TOTAL": 0.0,
            "SCORE": 0.0,
            "POSSIBLE_POINTS": 0.0
        }
        output_data = {
            "address": "",
            "score": 0.0,
            "total": 0.0,
            "possible": 0.0,
            "trains": []
        }
        total = 0
        possible_points = 0
        for criterion in housing_criteria:
            if criterion.key not in housing:
                logger.error("Invalid key '{0}' for criterion {1}".format(criterion.key, criterion.name))
            result = criterion.evaluate(housing[criterion.key])
            result_dict["criterion"].append([criterion, result, criterion.result_info])
            if result != -1:
                total += result
                possible_points += criterion.weight
        result_dict["TOTAL"] = total
        if possible_points > 0:
            result_dict["SCORE"] = total / possible_points
        else:
            result_dict["SCORE"] = 0.0
        result_dict["POSSIBLE_POINTS"] = possible_points
        result_dict["uid"] = housing["uid"]
        if housing["uid"] in used_uids:
            logger.error("UID {0} has already been used!".format(used_uids))
        else:
            used_uids.append(housing["uid"])

        # Add to characterization data
        output_data["address"] = housing["address"]
        output_data["score"] = result_dict["SCORE"]
        output_data["total"] = result_dict["TOTAL"]
        output_data["possible"] = result_dict["POSSIBLE_POINTS"]
        output_data["trains"] = get_nearby_trains(housing["coordinates"], radius_mi=0.5)

        hash_uid = generate_uid(housing["address"], housing["unit"])
        char_output[hash_uid] = {
            "housing_data": housing,
            "char_output": output_data,
        }

        if result_dict["SCORE"] > PERFECT_SCORE:

            char_results_good.append(result_dict)
        else:
            char_results_bad.append(result_dict)

    def print_results(result_list, name):
        result_list = sorted(result_list, key=lambda x: x["SCORE"])
        logger.info("Printing Results for {0}:".format(name))
        for result in result_list:
            logger.info("{0}\tUnit {1}".format(result["address"], result["unit"]))
            logger.info("  " + result["link"])
            logger.info("  Source: " + result["source"])
            for criterion_data in result["criterion"]:
                criterion = criterion_data[0]
                result_val = criterion_data[1]
                key_val = criterion_data[2]
                if result_val != -1:
                    logger.info("  {0:16.16s} = {1:2.2f}\t({2})".format(criterion.name, result_val, key_val))
                else:
                    logger.info("  {0:16.16s} = ----\t({1})".format(criterion.name, key_val))
            logger.info("  {0:16.16s} = {1:2.2f}/{2}".format("POSSIBLE POINTS", result["TOTAL"], result["POSSIBLE_POINTS"]))
            logger.info("  {0:16.16s} = {1:2.2f}%".format("SCORE", result["SCORE"]*100))

        logger.info("\nResults Printed Bottom Down (Best Result at Bottom)\n")

    #print_results(char_results_bad, "Okay Housing")
    #print_results(char_results_good, "Perfect Housing")

    # Write characterization output
    try:
        with open(CHAR_OUTPUT_FILE, "w") as output_file:
            json.dump(char_output, output_file)
    except OSError as e:
        logger.error("Failed to write characterization.json: {0}".format(e))

    logger.info("\nCharacterized {0} Entries of Housing Data".format(total_houses))
    logger.info("  Of those entries, {0} were considered PERFECT and {1} were considered OKAY".format(
        len(char_results_good), len(char_results_bad)))

    return True


def load_options() -> bool:
    """
    Loads the options file. If it does not exist, a default one will be created.
    :return: True if successfully loaded or created the file, false if otherwise.
    """
    global train_data
    config = configparser.ConfigParser()
    if not os.path.isfile(CONFIG_FILE):
        logger.debug("Config file {0} not found, creating default".format(CONFIG_FILE))

        config["scrape_websites"] = {"apartments_com": "1",
                                     "craigslist_bos": "1",
                                     "zillow": "1"}

        config["apartments_com"] = {"search_url": "boston-ma/2-to-3-bedrooms-under-1500/"}
        config["craigslist_bos"] = {"subdomain": "boston",
                                    "search_url": "search/apa?hasPic=1&bundleDuplicates=1&min_bedrooms=2&max_bedrooms=2&min_bathrooms=1&availabilityMode=0&sale_date=all+dates"}
        config["zillow"] = {"search_url": 'boston-ma/apartments/2-bedrooms/?searchQueryState={"pagination"%%3A{}%%2C"usersSearchTerm"%%3A"Boston%%2C MA"%%2C"mapBounds"%%3A{"west"%%3A-71.24846881103517%%2C"east"%%3A-70.84678118896485%%2C"south"%%3A42.21141701120901%%2C"north"%%3A42.41528103566799}%%2C"regionSelection"%%3A[{"regionId"%%3A44269%%2C"regionType"%%3A6}]%%2C"isMapVisible"%%3Atrue%%2C"filterState"%%3A{"fsba"%%3A{"value"%%3Afalse}%%2C"fsbo"%%3A{"value"%%3Afalse}%%2C"nc"%%3A{"value"%%3Afalse}%%2C"fore"%%3A{"value"%%3Afalse}%%2C"cmsn"%%3A{"value"%%3Afalse}%%2C"auc"%%3A{"value"%%3Afalse}%%2C"pmf"%%3A{"value"%%3Afalse}%%2C"pf"%%3A{"value"%%3Afalse}%%2C"fr"%%3A{"value"%%3Atrue}%%2C"ah"%%3A{"value"%%3Atrue}%%2C"sf"%%3A{"value"%%3Afalse}%%2C"mf"%%3A{"value"%%3Afalse}%%2C"manu"%%3A{"value"%%3Afalse}%%2C"land"%%3A{"value"%%3Afalse}%%2C"tow"%%3A{"value"%%3Afalse}%%2C"beds"%%3A{"min"%%3A2%%2C"max"%%3A2}%%2C"mp"%%3A{"max"%%3A3000}%%2C"price"%%3A{"max"%%3A913943}}%%2C"isListVisible"%%3Atrue%%2C"mapZoom"%%3A12}'}

        config["train_data"] = {"source": "data/mbta.json"}

        config["gui_settings"] = {"filter_city": "", "filter_suburb": "", "filter_neighborhood": ""}

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
            if config["scrape_websites"][key] == "1":
                if pyagent.get_source(key):
                    scrape_website_list.append(key)
                else:
                    logger.warning("Unknown source key {0}".format(key))
    else:
        logger.critical("Config file missing section [scrape_websites]")
        return False

    if config.has_option("train_data", "source"):
        # Load train data
        train_source = config["train_data"]["source"]
        logger.debug("Loading train data from {0}".format(train_source))
        try:
            with open(train_source, "r") as train_file:
                train_data = json.load(train_file)
        except OSError as e:
            logger.critical("Failed to load train data from {0}: {1}".format(train_source, e))
            return False
        except json.JSONDecodeError as e:
            logger.critical("Failed to decode train data from {0}: {1}".format(train_source, e))
            return False
        pyagent.set_train_data(train_data)
    else:
        logger.critical("Missing train data!")
        return False

    # Get settings for each source
    for source_key in scrape_sites:
        if not config.has_section(source_key):
            logger.critical("Missing config section for source {0}".format(source_key))
            return False
        # Add to source
        source_obj = pyagent.get_source(source_key)
        if source_obj:
            for key in config[source_key]:
                source_obj.add_config(key, config[source_key][key])
            if not source_obj.verify_config():
                logger.critical("Invalid config for source {0}".format(source_key))
                return False
        else:
            logger.critical("No source with name {0}".format(source_key))
            return False

    return True


def open_gui() -> bool:
    """
    Opens the PyAgent GUI
    :return: Nothing
    """
    logger.info("Opening graphical user inferface...")

    # Check for characterization data
    if not os.path.exists(CHAR_OUTPUT_FILE):
        logger.error("There was no characterization data. Run pyagent.py without arguments to generate "
                     "characterization data.")
        return False

    pyagentui.open_gui(char_file=CHAR_OUTPUT_FILE)
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
        opts, args = getopt.getopt(argv, "hvsn", ["gui"])
    except getopt.GetoptError:
        logger.critical("Invalid command line arguments.")
        print_help()
        return 2

    do_help = False
    do_scrape = False
    do_verbose = False
    do_charact = True
    do_gui = False

    for opt, arg in opts:
        if opt == "-h":
            do_help = True
        elif opt == "-v":
            do_verbose = True
        elif opt == "-s":
            do_scrape = True
        elif opt == "-n":
            do_charact = False
        elif opt == "--gui":
            do_gui = True

    if do_help:
        logger.debug("Showing help, no other action is performed")
        print_help()
        return 0
    if do_verbose:
        enable_verbose()

    # Load the options file
    if not load_options():
        return 1

    if do_gui:
        if not open_gui():
            return 1
        return 0

    if do_scrape:
        if not perform_scrape():
            return 1

    if do_charact:
        if not perform_characterization():
            return 1

    return 0


setup_logger()
if __name__ == "__main__":
    print("PyAgent  Copyright (C) 2021  Timothy Volpe")
    print("This program comes with ABSOLUTELY NO WARRANTY.")
    print("This is free software, and you are welcome to redistribute it under certain conditions.")
    print("", flush=True)

    browsers_spec = importlib.util.find_spec("browsers")
    if browsers_spec:
        has_browsers_file = True
        import browsers

    pyagent.LocationCache.init_cache()
    ret_val = main(sys.argv[1:])
    pyagent.LocationCache.save_cache()
    sys.exit(ret_val)

