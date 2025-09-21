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
    
    def not_update_identic_interface_fields(self, data):
        """ 
        Remove identic fields in normalized data from devices 
        
        Function for single device normalized interfaces, input data looks like:
        {
            "hostname": data['hostname'],
            "interfaces": list()
        }
        
        """
        nb_device = self.nb.dcim.devices.get(name=data['hostname'])
        nb_interfaces = self.get_netbox_interfaces(nb_device)

        for interface in data['interfaces']:
            nb_interface = self._is_this_interfaces_in_netbox(interface, nb_interfaces)
            if nb_interface is not None:  # check only existed interfaces in netbox
                keys_do_not_need_updating = list()
                for key, value in interface.items():
                    # iterate over device interface keys/values 
                    # and compare with NetBox interface values
                    if key == 'name':
                        interface['name'] = nb_interface['name']
                        continue
                    if isinstance(nb_interface[key], dict):  # because some fields in NetBox have nested fields
                        if value == nb_interface[key]['value']:
                            logging.info(
                                f"{data['hostname']} {interface['name']} {key} doesn't need updating"
                            )
                            keys_do_not_need_updating.append(key)
                    else:
                        if value == nb_interface[key]:
                            logging.info(
                                f"{data['hostname']} {interface['name']} {key} doesn't need updating"
                            )
                            keys_do_not_need_updating.append(key)
                for key in keys_do_not_need_updating:
                    del interface[key]
                del keys_do_not_need_updating

        interfaces_do_not_need_updating = list()
        for i, interface in enumerate(data['interfaces']):
            # iterate again to clear interfaces that don't need updating
            if len(interface) == 1:
                logging.info(
                    f"{data['hostname']} interface {interface['name']} doesn't need updating at all"
                )
                interfaces_do_not_need_updating.append(i)
        data['interfaces'] = [i for j, i in enumerate(data['interfaces']) if j not in interfaces_do_not_need_updating]
        return data

    def not_update_identic_devices(self, data):
        """ 
            Remove devices from normalized list 
            if device doesn't need to create or update interfaces
        """
        devices_do_not_need_updating = list()
        for i, device in enumerate(data):
            if len(device['interfaces']) == 0:
                logging.info(
                    f"device {device['hostname']} doesn't need updating at all"
                )
                devices_do_not_need_updating.append(i)
        data = [i for j, i in enumerate(data) if j not in devices_do_not_need_updating]
        return data
    
    def show_diff(self, data):
        """ Show diff between data from devices and NetBox """
        result = list()

        def _add_device_to_result(hostname, result) -> list[dict]:
            """ Create new device in result and return updated result """
            device_in_result = next((result_device for result_device in result if result_device['hostname'] == hostname), None)  # find device in result
            if device_in_result is None:  # new device in result
                result_dict = {
                    "hostname": device['hostname'],
                    "create_interfaces": [],
                    "update_interfaces": [],
                }
                result.append(result_dict.copy())
                del result_dict
                return result
            else:  # don't need to add new device in result
                return result
            
        def _get_device_index_from_result(hostname, result) -> int:
            """ Return device element index from result """
            try:
                index = next(i for i, result_device in enumerate(result) if result_device['hostname'] == hostname)
            except Exception as e:
                logging.error(f"Can't find device index in diff result {e}")
                sys.exit()
            return index

        for device in data:
            hostname = device['hostname']
            nb_device = self.nb.dcim.devices.get(name=hostname)
            nb_interfaces = self.get_netbox_interfaces(nb_device)
            for interface in device['interfaces']:
                nb_interface = self._is_this_interfaces_in_netbox(interface, nb_interfaces)
                if nb_interface is None:  # interface doesn't exist, need to create it
                    result = _add_device_to_result(hostname, result)
                    device_index = _get_device_index_from_result(hostname, result)
                    result[device_index]['create_interfaces'].append(interface.copy())
                else:  # interface exist, need to update it
                    result = _add_device_to_result(hostname, result)
                    device_index = _get_device_index_from_result(hostname, result)
                    result[device_index]['update_interfaces'].append(interface.copy())
        
        return result


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
                        logging.info(f"create {device['hostname']} {interface['name']}")
                        new_interface = self.nb.dcim.interfaces.create(**interface)
                    except pynetbox.core.query.RequestError as e:
                        logging.warning(f"{e} - {device['hostname']} {interface['name']}")
                else:  # interface exists, need to update it
                    try:
                        logging.info(f"update {device['hostname']} {interface['name']}")
                        update_interface = nb_interface.update(interface)
                    except pynetbox.core.query.RequestError as e:
                        logging.warning(f"{e} - {device['hostname']} {interface['name']}")

