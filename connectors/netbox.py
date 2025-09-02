import logging
import sys
from pathlib import Path
import configparser

import pynetbox


class NB:
    """ Main Netbox class"""
    def __init__(self):
        config = configparser.ConfigParser()
        config.read(
            Path(__file__).resolve(strict=True).parents[1].joinpath('settings.ini')
        )
        self.address = config['NETBOX']['address']
        self.token = config['NETBOX']['token']
        self.nb = pynetbox.api(
            self.address,
            token=self.token,
        )
        self.nb.http_session.verify = False

    def add_interfaces(self, data):
        for device in data:
            nb_device = self.nb.dcim.devices.get(name=device['hostname'])
            for interface in device['interfaces']:
                interface['device'] = nb_device.id
                new_interface = self.nb.dcim.interfaces.create(**interface)
