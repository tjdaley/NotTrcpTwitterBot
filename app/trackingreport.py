"""
trackingreport.py - Send a report to our subscribers about changes to their networks.
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

import argparse
from datetime import datetime
import json
import twitter

from lib.clients_db import ClientDb
from lib.keys import Keys
from lib.logger import Logger
from lib.substitution import PhraseMaker
from lib.progress_bar import ProgressBar

VOCABULARY = "./lib/vocabulary.json"
LAST_REPORT_FILE = "../data/last_report.json"
ADDED_TEMPLATE = "{{POSITIVE}} You {{ADDED}} %s {{ADDITIONAL}} {{FOLLOWERS}}."
LOST_TEMPLATE = "{{NEGATIVE}} Your account {{LOST}} %s {{FOLLOWERS}}."
DATE_FORMAT  = "%Y-%m-%d %X"

class TrackingReporter(object):
    """
    Encapsulates our Twitter publisher functions.
    """
    def __init__(self, clients:list):
        """
        Class initializer.

        Args:
            clients (list): List of client screen_names.
        """
        self.my_screen_name = None
        self.logger = Logger.get_logger("nottrcp.reporter")
        self.api = self.connect()
        self.clients = clients

        with open(VOCABULARY, "r") as vocab_file:
            self.vocabulary = json.load(vocab_file)

        self.phrase_maker = PhraseMaker(self.vocabulary)

        try:
            with open(LAST_REPORT_FILE, "r") as report_file:
                self.last_report = json.load(report_file)
        except FileNotFoundError:
            self.last_report = {}

    def connect(self):
        """
        Connect our API to the servers.
        """
        api = twitter.Api(consumer_key=Keys.consumer_key(),
                        consumer_secret=Keys.consumer_secret(),
                        access_token_key=Keys.access_token_key(),
                        access_token_secret=Keys.access_token_secret(),
                        sleep_on_rate_limit=True)

        verified_credentials = api.VerifyCredentials()
        self.my_screen_name = verified_credentials.screen_name
        return api

    def report(self, report_data:dict)->str:
        """
        Create a report string to DM to the user.

        Args:
            report_data (dict): Data read from a report file.
        
        Returns:
            (str): The report to send to the user or None if nothing to report.
        """

        report = ""
        for report_key in ["added", "deleted"]:
            if report_data[report_key]:
                report += self.phrase_maker.make(ADDED_TEMPLATE, len(report_data[report_key]))
                report = report % len(report_data[report_key])

        if report:
            return report

        return None

    def is_new_report(self, report_date:str, screen_name:str)->bool:
        """
        Determine whether the report has been generated since the last time we sent a report
        to this screen name.

        Args:
            report_date (str): Date that this report was generated.
            screen_name (str): Twitter screen name being processed.

        Returns:
            (bool): True if this is a new report and we should send it, otherwise False.
        """
        if screen_name not in self.last_report:
            return True

        last_dm_time = datetime.strptime(self.last_report[screen_name], DATE_FORMAT)
        report_generated_time = datetime.strptime(report_date, DATE_FORMAT)
        return last_dm_time < report_generated_time

    def send_report(self, report:str, screen_name:str)->bool:
        """
        Send a status report to the client.

        Args:
            report (str): The text of the report to send.
            screen_name (str): The screen name of the target client.

        Returns:
            (bool): True if successful, otherwise False.
        """
        try:
            self.api.PostDirectMessage(report, screen_name=screen_name)
            self.last_report[screen_name] = datetime.strftime(datetime.now(), DATE_FORMAT)
        except Exception as e:
            self.logger.error("Error sending DM to %s: %s.", screen_name, report)
            self.logger.exception(e)
            return False

        return True

    def save_last_report_time(self)->bool:
        """
        Save the last report times to a json-encoded file.

        Returns:
            (bool): True if successful, otherwise False.
        """
        try:
            with open(LAST_REPORT_FILE, "w") as outfile:
                json.dump(self.last_report, outfile)
            return True
        except Exception as e:
            self.logger.error("Error saving %s: %s", LAST_REPORT_FILE, e)
            self.logger.exception(e)

        return False

def get_options()->dict:
    """
    Read command line options.

    Args:
        None.

    Returns:
        (dict): Contains one entry for each command line option.
    """

    parser = argparse.ArgumentParser(description="Report network changes.")
    parser.add_argument("--notweet", action="store_true", default=False, help="Indicates that you want a dry-run...no actual tweeting.")
    parser.add_argument('--status', '-s', action='store_true', default=False, help='Indicates you want a status bar on the screen. Default is no.')
    args = parser.parse_args()
    return args

def main():
    """
    main routine for this app.

    For each client, send a report if something has changed.
    """
    options = get_options()

    client_db = ClientDb()
    screen_names = client_db.active_clients(client_db.load_clients())
    reporter = TrackingReporter(screen_names)
    reporter.logger.info("Started.")

    if options.status:
        progress_bar = ProgressBar(len(screen_names))
        progress_counter = 0

    for screen_name in screen_names:

        if options.status:
            progress_counter += 1
            progress_bar.update(progress_counter, f'{screen_name:10}')

        report_filename = client_db.report_filename(screen_name)
        try:
            with open(report_filename, "r") as report_file:
                report_data = json.load(report_file)

            report = reporter.report(report_data)
            if report:
                if reporter.is_new_report(report_data["generated"], screen_name):
                    if options.notweet:
                        reporter.logger.info("Would have sent '%s' to %s.", report, screen_name)
                    else:
                        reporter.send_report(report, screen_name)
                else:
                    reporter.logger.debug("Suppressing previously sent DM to %s.", screen_name)
        except Exception as e:
            reporter.logger.error("Error processing report for %s", screen_name)
            reporter.logger.exception(e)

    reporter.save_last_report_time()
    reporter.logger.info("Complete.")

if __name__ == "__main__":
    main()