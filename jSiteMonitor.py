import ConfigParser
import os
import logging
import urllib
import smtplib

from urlparse import urlparse

"""
Monitors a list of sites. The urls are listed in the file site.list and the list
of email recipients to send updates to is found in the file email.list. Configuration
is outlined in config.ini, which can be build dynamically via lib/jConfigMaker.py

Adapted from: https://github.com/davetromp/SiteMonitor/blob/master/SiteMonitor.py
"""


class monitor(object):
    """representation of a site up or down monitor"""

    def __init__(self, site_url, prevStatus, smtp_info, lof_emails=[]):
        self.site_url = site_url
        self.hostname = urlparse(site_url).hostname
        self.prevStatus = prevStatus
        self.currStatus = prevStatus
        self.lof_emails = lof_emails
        self.smtp_info = smtp_info

    def checkStatus(self):
        self.logger = logging.getLogger('root.' + self.hostname)
        try:
            Gstatus = self.getStatus('http://www.google.com') # See if we can hit google
        except Exception as e:
            self.logger.info("Unexpected error while accessing www.google.com: " + e)
            return
        if Gstatus != 200:
            self.logger.info("Can't even hit www.google.com. Better luck next time. Returned with " + Gstatus)
            return

        self.logger.info("Checking status of %s", self.hostname)
        status = self.getStatus(self.site_url)
        if status != 200 and self.prevStatus != 'down':
            msg = "%s is down. Site status returned: %s" % (self.hostname, status)
            self.logger.info(msg)
            self.sendEmail(msg) # Notify recipients that the site went down.
            self.currStatus = 'down'
        elif status == 200 and self.prevStatus == 'down':
            msg = "%s is up again. Site status returned: %s" % (self.hostname, status)
            self.logger.info(msg)
            self.sendEmail(msg) # Notify recipients that site came back up!
            self.currStatus = 'up'

    def getStatus(self, url):
        """
        makes a request to an url and returns the header status.
        returns zero if url does not exist.
        """
        try:
            a = urllib.urlopen(url)
            return a.getcode()
        except:
            self.logger.info(url + ' did not return any header status.')
            return 0

    def sendEmail(self, msg, subject="Site down / up again message"):
        """0: site just went down, 1: site just came back up"""
        to_addr = self.lof_emails
        server = self.smtp_info['server']
        from_addr = self.smtp_info['from_addr']
        username = self.smtp_info['username']
        password = self.smtp_info['password']

        m = "From: %s\r\nTo: %s\r\nSubject: %s\r\nX-Mailer: My-Mail\r\n\r\n" % (from_addr, ", ".join(to_addr), subject)

        try:
            server = smtplib.SMTP(server)
            server.starttls()
            server.login(username,password)
            server.sendmail(from_addr, to_addr, m+msg)
            server.quit()
            self.logger.debug('Email sent to ' + ", ".join(to_addr))
        except Exception as e:
            self.logger.debug('Email not sent: ' + str(e))



def monitorFactory(config):
    """Takes a config object as argument and returns a list of monitors"""

    lof_monitors = []
    lof_sites = []
    smtp_info = {}

    smtp_info['server'] = config.get('Email', 'server')
    smtp_info['username'] = config.get('Email', 'username')
    smtp_info['password'] = config.get('Email', 'password')
    smtp_info['from_addr'] = config.get('Email', 'from')

    sites_path = config.get('Lists', 'sites_path')
    default_recipient = config.get('Email', 'default_recipient')

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
            updateConfig('./config.ini', 'Site status', hostname)
            prevStatus = None
        logger.debug("%s was %s last time it was checked" % (hostname, prevStatus))

        # Find the list of email recipients for this site url
        try:
            email_string = config.get('Site to email list mapping', hostname).strip().replace(" ","")
        except ConfigParser.NoOptionError as e:
            updateConfig('./config.ini', 'Site to email list mapping', hostname, default_recipient)
            email_string = default_recipient
        finally:
            lof_emails = email_string.split(',')
        logger.debug("Alert for %s need to be sent to %s" % (hostname, lof_emails))

        # Instantiate monitor object and append to list of monitors
        lof_monitors.append(monitor(site, prevStatus, smtp_info, lof_emails))

    return lof_monitors

def updateConfig(path, section, option, value=None):
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

    logging.info('Main program finished')



main()

