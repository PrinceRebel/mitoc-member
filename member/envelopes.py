""" Parse the XML payload delivered when a DocuSign envelope is completed.

Envelopes are delivered to endpoints via the eventNotification setting -
this utility module parses out the MITOC member's information.
"""
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET


class CompletedEnvelope:
    ns = {'docu': "http://www.docusign.net/API/3.0"}
    recipient_status = ['EnvelopeStatus', 'RecipientStatuses', 'RecipientStatus']

    def __init__(self, xml_contents):
        self.root = ET.fromstring(xml_contents)

    def get_element(self, hierarchy, findall=False):
        """ Return a single element from an array of XPath selectors. """
        # (This method exists to ease the pain of namespaces with ElementTree)
        xpath = '/'.join('docu:{}'.format(tag) for tag in hierarchy)
        if findall:
            return self.root.findall(xpath, self.ns)
        return self.root.find(xpath, self.ns)

    def get_val(self, hierarchy):
        return self.get_element(hierarchy).text.strip()

    def _get_hours_offset(self):
        return self.get_val(['TimeZoneOffset'])

    def _first_and_last(self):
        """ A tuple that always contains the last name, and sometimes the last.

        If there's no spacing given in the name, we just assume that the user
        only reported their first name, and no last name.
        """
        return self.releasor_name.split(None, 1)

    @property
    def first_name(self):
        """ First name of the MITOC member this waiver is for. """
        return self._first_and_last()[0]

    @property
    def last_name(self):
        """ Last name of the MITOC member this waiver is for. """
        try:
            return self._first_and_last()[1]
        except IndexError:  # No space given, we don't know the last name
            return ''

    @property
    def time_signed(self):
        """ Return the timestamp when the document was signed. """
        time_signed = self.get_val(self.recipient_status + ['Signed'])
        try:
            hours_offset = int(self._get_hours_offset())
            ts = datetime.strptime(time_signed, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            return datetime.utcnow()
        else:
            utc_datetime = ts - timedelta(hours=hours_offset)
            return utc_datetime.replace(tzinfo=timezone.utc)

    @property
    def releasor_email(self):
        selector = self.recipient_status + ['TabStatuses', 'TabStatus']
        tab_statuses = self.get_element(selector, findall=True)
        for tab in tab_statuses:
            label = tab.find('docu:TabLabel', self.ns)
            if label is not None and label.text.strip() == "Releasor's Email":
                return tab.find('docu:TabValue', self.ns).text.strip()
        else:
            raise ValueError("Missing releasor email!")

    @property
    def releasor_name(self):
        selector = self.recipient_status + ['TabStatuses', 'TabStatus']
        tab_statuses = self.get_element(selector, findall=True)
        for tab in tab_statuses:
            label = tab.find('docu:TabLabel', self.ns)
            if label is not None and label.text.strip() == "Releasor's Name":
                return tab.find('docu:TabValue', self.ns).text.strip()
        else:
            raise ValueError("Missing releasor's name!")