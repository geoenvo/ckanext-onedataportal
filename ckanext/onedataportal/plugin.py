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
        return {'onedataportal_add_time': add_time, 'onedataportal_naive_to_utc': naive_to_utc}
