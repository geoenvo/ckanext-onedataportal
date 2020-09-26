# -*- coding: utf-8 -*-

import logging


log = logging.getLogger(__name__)


def add_time(dt, weeks=0, days=0, hours=0, minutes=0, seconds=0):
    """Return a new datetime after timedelta.
    """
    from datetime import timedelta
    from datetime import datetime
    import six
    if isinstance(dt, six.string_types):
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')
    return dt + timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)

def naive_to_utc(dt, is_dst=None):
    """Convert a naive datetime to utc datetime.
    """
    from datetime import datetime
    import six
    import pytz
    import tzlocal
    from ckan.common import config
    if isinstance(dt, six.string_types):
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')
    timezone_name = config.get('ckan.display_timezone') or 'utc'
    local = None
    if timezone_name == 'server':
        local = tzlocal.get_localzone()
    if not local:
        local = pytz.timezone(timezone_name)
    local_dt = local.localize(dt, is_dst=is_dst)
    return local_dt.astimezone(pytz.utc)

def geoportal_url():
    """Return string value of the geoportal url, the value must be a valid url or path.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.geoportal_url', False)
    if value:
        if value.lower().startswith(('http://', 'https://', '/')):
            return value
        else:
            return False
    return value

def geoportal_name():
    """Return string value of the geoportal name, if empty return default value.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.geoportal_name', 'Geoportal')
    return value

def navlink1_url():
    """Return string value of the navlink1 url, the value must be a valid url or path.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.navlink1_url', False)
    if value:
        if value.lower().startswith(('http://', 'https://', '/')):
            return value
        else:
            return False
    return value

def navlink1_name():
    """Return string value of the navlink1 name, if empty return default value.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.navlink1_name', 'Link 1')
    return value

def navlink2_url():
    """Return string value of the navlink2 url, the value must be a valid url or path.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.navlink2_url', False)
    if value:
        if value.lower().startswith(('http://', 'https://', '/')):
            return value
        else:
            return False
    return value

def navlink2_name():
    """Return string value of the navlink2 name, if empty return default value.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.navlink2_name', 'Link 2')
    return value

def navlink3_url():
    """Return string value of the navlink3 url, the value must be a valid url or path.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.navlink3_url', False)
    if value:
        if value.lower().startswith(('http://', 'https://', '/')):
            return value
        else:
            return False
    return value

def navlink3_name():
    """Return string value of the navlink3 name, if empty return default value.
    """
    from ckan.common import config
    value = config.get('ckan.onedataportal.navlink3_name', 'Link 3')
    return value

def _json2dict_or_empty(value):
    """Try to parse a JSON string and return as dict object.
    """
    import json
    try:
        #log.debug(value)
        json_dict = json.loads(value)
    except Exception as e:
        log.warn('Unable to parse JSON string')
        json_dict = {}
    #log.debug(json.dumps(json_dict, indent=4))
    return (json_dict)

def get_json_as_dict(value):
    """Template helper function.
    
    Returns the value as a dictionary. If if is already
    a dictionary, the original value is returned. If it is
    a json dump, it will be parsed into a dictionary. Otherwise
    an empty dictionary is returned.
    """
    #log.debug('>>>>>>> get_json_as_dict')
    if isinstance(value, dict):
        return value
    else:
        return(_json2dict_or_empty(value))
