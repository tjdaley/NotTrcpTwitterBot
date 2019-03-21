"""
lock.py - A simple locking mechanism.
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

import json
import os
import socket
import threading
import time

from lib.logger import Logger

class Lock(object):
    """
    Encapsulates a platform-independent, simple locking mechanism.
    """
    def __init__(self, port:int=8089, wait:bool=False, log_name="lock"):
        """
        Class initializer.

        Args:
            port (int): TCP port number to use for locking. Must be the same value for each process or section
                of code that wants to coordinate a lock on a resource.
            wait (bool): True if the lock should wait or False if it should raise an exception if already locked.
        """
        self.logger = Logger.get_logger()
        self.port = port
        self.wait = wait
        self.process_name = "another process"
        self.serversocket = None
        self.monitor_thread = None

    def __del__(self):
        """
        Clean up.
        """
        try:
            self.serversocket.close()
        except Exception:
            pass

    def lock(self, process_name:str="another process")->bool:
        """
        Locks the database to prevent others from accessing it.
        The "lock" is implemented as a socket bind. If we can bind to the port,
        then no other process must be running that will access the DB. If we can't
        bind, then there's another process out there.

        Args:
            process_name (str): Description of this process. Will be given to others who try to lock this resource.

        Returns:
            (bool): True if successful otherwise False

        Raises:
            Exception: If database is locked and caller does not want to wait.
        """
        attempted = False
        self.process_name = process_name

        while self.wait or not attempted:
            try:
                attempted = True
                serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                serversocket.bind(('localhost', self.port))
                serversocket.listen(5)
                self.start_monitor(process_name, serversocket)
                self.serversocket = serversocket
                return True
            except OSError as e:
                lock_owner = self.get_lock_owner()
                message = "Locked by {} (pid {}). Try later or retry with --wait" \
                    .format(lock_owner["process_name"], lock_owner["pid"])
                self.logger.info(message)
                if self.wait:
                    self.logger.info(message)
                    time.sleep(30)

        raise Exception(message)

    def start_monitor(self, process_name:str, serversocket):
        """
        Listen for lock inquiries and announce our identity.

        Args:
            process_name (str): Name that will be transmitted to inquirers.
        """
        self.monitor_thread = \
            threading.Thread(target=monitor, kwargs={"process_name": process_name, "serversocket": serversocket})
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def get_lock_owner(self)->dict:
        """
        Get the name of the process that owns this lock.

        Returns:
            (dict): Dictionary disclosing process description and PID of lock owner.
        """
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(('localhost', self.port))
        data = clientsocket.recv(1024).decode()
        clientsocket.close()
        lock_owner = json.loads(data)
        return lock_owner

def monitor(process_name:str, serversocket):
    """
    Thread method.
    """

    try:
        while True:
            connection, address = serversocket.accept()
            response = json.dumps({"process_name": process_name, "pid": os.getpid()})
            connection.send(response.encode())
            connection.close()
    except OSError:
        pass
