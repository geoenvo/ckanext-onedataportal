import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


def add_time(dt, weeks=0, days=0, hours=0, minutes=0, seconds=0):
    '''Return a new datetime after timedelta.
    '''
    from datetime import timedelta
    from datetime import datetime
    import six
    if isinstance(dt, six.string_types):
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')
    return dt + timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)

def naive_to_utc(dt, is_dst=None):
    '''Convert a naive datetime to utc datetime.
    '''
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
    '''Return string value of the geoportal url, the value must be a valid url
    '''
    from ckan.common import config
    value = config.get('ckan.onedataportal.geoportal_url', False)
    if value:
        if value.lower().startswith(('http://', 'https://', '/')):
            return value
        else:
            return False
    return value

def geoportal_name():
    '''Return string value of the geoportal name, if empty return default
    '''
    from ckan.common import config
    value = config.get('ckan.onedataportal.geoportal_name', 'Geoportal')
    return value


class OnedataportalPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'onedataportal')
    
    def get_helpers(self):
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {
            'onedataportal_add_time': add_time,
            'onedataportal_naive_to_utc': naive_to_utc,
            'onedataportal_geoportal_url': geoportal_url,
            'onedataportal_geoportal_name': geoportal_name
        }
