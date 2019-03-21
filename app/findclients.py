"""
findclients.py - Find people who want to be tracked.
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

import argparse
from datetime import datetime
import json
import twitter

from lib.clients_db import ClientDb
from lib.keysa import Keys
from lib.logger import Logger

CLIENT_FILE = "../data/clients.json"
DATE_FORMAT  = "%Y-%m-%d"

class ClientFinder(object):
    """
    Encapsulates our client finding function.
    """
    def __init__(self):
        """
        Class initializer.

        Args:
            clients (list): List of client screen_names.
        """
        self.my_screen_name = None
        self.logger = Logger.get_logger("nottrcp.finder")
        self.api = self.connect()
        self.client_db = ClientDb(process_name=__file__, wait=True)

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

    def search(self)-> dict:
        """
        Get a list of twitter users who want us to track them.

        Returns:
            (dict): List of followers
        """
        result = {}

        followers = self.api.GetFollowers \
            (
                cursor=-1,
                count=200,
                include_user_entities=True
            )
        
        for follower in followers:
            client = {
                "screen_name": follower.screen_name,
                "active": True,
                "report_via": "dm",
                "email": None,
                "name": follower.name,
                "lang": follower.lang,
                "subscrption_ends": next_year()
                }
            result[follower.screen_name] = client

        self.logger.info(result)
        return result

    def update_client_list(self, followers:dict)->dict:
        """
        Update our client file based on our new followers list.

        Args:
            followers (dict): From self.search()
        """
        old_clients = self.client_db.load_clients()
        merged_clients = self.client_db.merge_clients(old_clients, followers)
        success = self.update_client_list(merged_clients)
        return success

def next_year():
    year, month, day = datetime.now().timetuple()[:3]
    new_date = datetime(year+1, month, day)
    return new_date.strftime(DATE_FORMAT)

def get_options()->dict:
    """
    Read command line options.

    Args:
        None.

    Returns:
        (dict): Contains one entry for each command line option.
    """

    parser = argparse.ArgumentParser(description="Find clients.")
    args = parser.parse_args()
    return args

def main():
    """
    main routine for this app.

    Will get followers, compare them to the last list of followers, update the followers list and create
    a change list.
    """
    options = get_options()
    finder = ClientFinder()
    finder.logger.info("Started.")
    clients = finder.search()
    success = finder.update_client_list(clients)
    finder.logger.info("Update successful? %s", success)
    finder.logger.info("Complete.")

if __name__ == "__main__":
    main()