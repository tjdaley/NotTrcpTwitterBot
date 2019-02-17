# NotTrcpTwitterBot
_Twitter Bot that publishes my version of the Texas Rules of Civil Procedure._

This is a very simple Tweet publisher that publishes a Tweet every 24 hours from a CSV file of pre-created tweets.

This version focuses on the Texas Rules of Civil Procedure. The only thing that is TRCP-centric about this is that the publisher
looks at the "TRCP _X_:" prefix of the last Tweet, where _X_ is an index into the CSV file. From there it determines the _next_
Tweet in the CSV file to send. If you have a different way of keeping track of what has been tweeted and what has not, then the
publish.py script can be easily adopted for your purposes.

# Usage Scenarios

This Twitter publisher can be run a number of ways.

## From a Terminal Session

If you run this from a terminal session, then you may want to use the **--status** option, which will print a simple progress bar
that counts down the minutes until the next tweet will be published. The following command

```
$ python publish.py --status --time 10:00
```

will publish a Tweet at 10:00 a.m. every day of the week and display a status bar like the one below:

```
Remaining |XXXXXXXXXX-----------------------| 74.4% 1075 min
```

## From a _cron_ Job

If you want to Tweet out at a different interval than every 24-hours, which is baked into this publisher, you can run it
from a cron job, have it publish its Tweet and then quit, rather than sit there waiting until it is time to publish the
next update, e.g. the following crontab entry will publish a Tweet at 6:30 p.m. MON-FRI (no weekend tweeting).
 
```
30  18 *  *  1-5         cd ~/NotTrcpTwitterBot/app && /usr/bin/python publish.py --once
```

## As a Systemd Service

If you want to run this as a _systemd_ service, you can have it publish a Tweet every day at 9:00 a.m. (the default for --time)
with this command, which comes from my AWS environment, thus the "ubuntu" username.

```
[Unit]
Description=Starts and Stops the NotTrcpTwitterBot service

[Service]
User=ubuntu
ExecStart=/usr/bin/python3 publish.py
RestartSec=10
Restart=on-failure
RestartPreventExitStatus=SIGKILL
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=nottrcptwitterbot
WorkingDirectory=/home/ubuntu/NotTrcpTwitterBot/app

[Install]
WantedBy=multi-user.target
```

## During Testing

If you need to run without actually publishing to Twitter, then you can include the **--notweet** option. For example, if you use
this command line:

```
$ python publish.py --status --time 17:24 --notweet
```

The above command line will print a status bar, pretend to send a tweet, then wait until 5:24 p.m. to (fake) send the next tweet.
I use this to test the logic for analyzing thelast tweet to determine the next tweet.

# Resources and Inspiration

I wrote this as my first Twitterbot after reading (most of) Tony Veale's and Mike Cook's amazing book, 
[TwitterBots: Making Machines that Make Meaning](https://mitpress.mit.edu/books/twitterbots). This script does not do justice to their
work. But before I can get into the meat of what they have to teach, I have to sate my curiosity about the mechanics of getting
a Twitter Bot account set up and publishing Tweets.

Another resource that I like is 
[How to Make a Twitterbot: The Definitive Guide](https://botwiki.org/resource/tutorial/how-to-make-a-twitter-bot-the-definitive-guide/).

Veale & Cook have a lot to say about the non-programming aspects of Twitterbot development and it is worth reading. I know, I know. We
all just want to read the code and start tweeting or whatever. But give it a try. I promise you will be happier with your workproduct
if you'll take the time to read this book. They offer useful Java code on their companion web site.

# The Missing File

There is a file from the ```lib``` folder that is missing because it contains my private keys. It is in this form:

```python
"""
keys.py - Our Twitter Keys

Make sure this is NOT synced to GitHub or published in any way.
"""
_KEYS = {
    "CONSUMER_KEY": "...supplied by Twitter...",
    "CONSUMER_SECRET": "...supplied by Twitter...",
    "ACCESS_TOKEN_KEY": "...supplied by Twitter...",
    "ACCESS_TOKEN_SECRET": "...supplied by Twitter..."
}

class Keys(object):
    @staticmethod
    def consumer_key():
        return _KEYS["CONSUMER_KEY"]

    @staticmethod
    def consumer_secret()->str:
        return _KEYS["CONSUMER_SECRET"]
    
    @staticmethod
    def access_token_key()->str:
        return _KEYS["ACCESS_TOKEN_KEY"]
    
    @staticmethod
    def access_token_secret()->str:
        return _KEYS["ACCESS_TOKEN_SECRET"]
```

# Copyright

Copyright 2019 by Thomas J. Daley.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
