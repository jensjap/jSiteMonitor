import ConfigParser
import os
import logging
import urllib

from urlparse import urlparse

"""
Monitors a list of sites. The urls are listed in the file site.list and the list
of email recipients to send updates to is found in the file email.list. Configuration
is outlined in config.ini, which can be build dynamically via lib/jConfigMaker.py

Adapted from: https://github.com/davetromp/SiteMonitor/blob/master/SiteMonitor.py
"""


class monitor(object):
    """representation of a site up or down monitor"""

    def __init__(self, site_url, prevStatus, lof_emails=[]):
        self.site_url = site_url
        self.hostname = urlparse(site_url).hostname
        self.lof_emails = lof_emails
        self.prevStatus = prevStatus
        self.currStatus = prevStatus

    def checkStatus(self):
        self.logger = logging.getLogger('root.' + self.site_url)
        try:
            Gstatus = self.getStatus('http://www.google.com') # See if we can hit google
        except Exception as e:
            self.logger.info("Can't even hit www.google.com. Better luck next time")
        if Gstatus != 200:
            self.logger.info("Can't even hit www.google.com. Better luck next time. Returned with" +
                             Gstatus)
            return

        self.logger.info("Checking status of %s", self.site_url)
        try:
            status = self.getStatus(self.site_url)
        except IOError as e:
            status = 0
        if status != 200 and self.prevStatus != 'down':
            self.logger.info("%s is down. Site status is %s" % (self.site_url, status))
            self.currStatus = 'down'
            self.sendEmail(0) # Notify recipients that site just went down
        elif status == 200 and self.prevStatus == 'down':
            self.logger.info("%s is up again. Site status is %s" % (self.site_url, status))
            self.currStatus = 'up'
            self.sendEmail(1) # Notify recipients that site came back up!

    def getStatus(self, url):
        """
        makes a request to an url and returns the header status.
        returns zero if url does not exist.
        """
        a = urllib.urlopen(url)
        print(a.getcode())
        try:
            a = urllib.urlopen(url)
            return a.getcode()
        except:
            self.logger.info(url + ' did not return any header status.')
            return 0

    def sendEmail(self, code):
        """0: site just went down, 1: site just came back up"""
        print('Send email to', self.lof_emails)


def monitorFactory(config):
    """Takes a config object as argument and returns a list of monitors"""

    lof_monitors = []
    lof_sites = []

    sites_path = config.get('Lists', 'sites_path')

    with open(sites_path, 'rb') as f:
        for line in f.readlines():
            lof_sites.append(line.strip())

    logging.info("Number of site monitors to build: %s", len(lof_sites))
    for site in lof_sites:
        # Let's get the hostname
        s = urlparse(site)
        hostname = s.hostname
        logger = logging.getLogger("root." + hostname)
        logger.debug("Found hostname %s", hostname)

        # Get the status of the site from config ini
        try:
            prevStatus = config.get('Site status', hostname)
        except ConfigParser.NoOptionError as e:
            updateConfig('./config.ini', 'Site status', hostname, '')
        logger.debug("%s was %s last time it was checked" % (hostname, prevStatus))

        # Find the list of email recipients for this site url
        try:
            email_string = config.get('Site to email list mapping', hostname).strip().replace(" ","")
        except ConfigParser.NoOptionError as e:
            updateConfig('./config.ini', 'Site to email list mapping', hostname, config.get('Email', 'default_recipient'))
        lof_emails = email_string.split(',')
        logger.debug("Alert for %s need to be sent to %s" % (hostname, lof_emails))

        # Instantiate monitor object and append to list of monitors
        lof_monitors.append(monitor(site, prevStatus, lof_emails))

    return lof_monitors

def updateConfig(path, section, option, value):
    configPath = './config.ini'
    config = ConfigParser.ConfigParser()
    config.read(configPath)
    config.set(section, option, value)
    with open(configPath, 'wb') as configfile:
        config.write(configfile)

def main():
    config_path = './config.ini'
    config = ConfigParser.ConfigParser()
    config.read(config_path)

    logging.basicConfig(filename='log/jSiteMonitor.log',
            level=config.get('Settings', 'logging_level'),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.info('Main program started')

    monitors = monitorFactory(config)
    for m in monitors:
        m.checkStatus()
        updateConfig(config_path, 'Site status', m.hostname, m.currStatus)



main()

