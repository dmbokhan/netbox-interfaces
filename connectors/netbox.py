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

    def get_netbox_interfaces(self, device):
        """ Get NetBox interfaces by device id """
        interfaces = list(self.nb.dcim.interfaces.filter(device_id=device.id))
        return interfaces
    
    def _is_this_interfaces_in_netbox(self, interface, nb_interfaces):
        """ Return id if interface exists in NetBox """
        interface_id = next(
            (nb_interface for nb_interface in nb_interfaces
             if nb_interface.name.lower().replace(" ","") == interface['name'].lower().replace(" ","")),
            None
        )
        return interface_id

    def add_interfaces(self, data):
        """ Add interfaces to NetBox """
        for device in data:
            nb_device = self.nb.dcim.devices.get(name=device['hostname'])
            nb_interfaces = self.get_netbox_interfaces(nb_device)
            for interface in device['interfaces']:
                nb_interface = self._is_this_interfaces_in_netbox(interface, nb_interfaces)
                if nb_interface is None:  # interface doesn't exist, need to create it
                    interface['device'] = nb_device.id
                    try:
                        new_interface = self.nb.dcim.interfaces.create(**interface)
                    except pynetbox.core.query.RequestError as e:
                        logging.warning(f"{e} - {device['hostname']} {interface['name']}")
                else:  # interface exists, need to update it
                    try:
                        update_interface = nb_interface.update(interface)
                    except pynetbox.core.query.RequestError as e:
                        logging.warning(f"{e} - {device['hostname']} {interface['name']}")

