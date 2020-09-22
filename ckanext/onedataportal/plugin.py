import logging
import json

import ckan.plugins as p
import ckan.plugins.toolkit as t

from ckanext.onedataportal.jobs import save_shapefile_metadata


log = logging.getLogger(__name__)


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

def _json2dict_or_empty(value, field_name = ""):
    '''
    '''
    try:
        #log.debug(value)
        json_dict = json.loads(value)
    except Exception as e:
        log.warn('unable to parse json string')
        json_dict = {}
    #log.debug(json.dumps(json_dict, indent=4))
    return (json_dict)

def get_json_as_dict(value):
    '''Template helper funciton.
    Returns the value as a dictionary. If if is already
    a dictionary, the original value is returned. If it is
    a json dump, it will be parsed into a dictionary. Otherwise
    an empty dictionary is returned.
    '''
    #log.debug('>>>>>>> get_json_as_dict')
    if isinstance(value, dict):
        return value
    else:
        return(_json2dict_or_empty(value))

def enqueue_job(*args, **kwargs):
    '''Enqueue an asynchronous job to RQ
    '''
    try:
        return t.enqueue_job(*args, **kwargs)
    except AttributeError:
        from ckanext.rq.jobs import enqueue as enqueue_job_legacy
        return enqueue_job_legacy(*args, **kwargs)


class OnedataportalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IResourceController, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        t.add_template_directory(config_, 'templates')
        t.add_public_directory(config_, 'public')
        t.add_resource('fanstatic', 'onedataportal')

    # ITemplateHelpers

    def get_helpers(self):
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {
            'onedataportal_add_time': add_time,
            'onedataportal_naive_to_utc': naive_to_utc,
            'onedataportal_geoportal_url': geoportal_url,
            'onedataportal_geoportal_name': geoportal_name,
            'onedataportal_get_json_as_dict': get_json_as_dict
        }

    # IResourceController

    def _data_dict_is_dataset(self, data_dict):
        '''Check if data_dict is a dataset
        '''
        #log.debug('>>>>>>> _data_dict_is_dataset')
        return (
            u'creator_user_id' in data_dict
            or u'owner_org' in data_dict
            or u'resources' in data_dict
            or data_dict.get(u'type') == u'dataset')

    def _resource_is_zip_shapefile(self, resource):
        '''Check if uploaded resource is a zipped file and format is shp
        '''
        if resource.get(u'format', u'').lower() == 'shp' and resource.get(u'url', u'').endswith('zip'):
            return True
        return False

    def before_create(self, context, data_dict):
        '''
        '''
        log.debug('>>>>>>> BEFORE_CREATE')
        return data_dict

    def after_create(self, context, data_dict):
        '''Hook called after saving a new dataset resource
        '''
        log.debug('>>>>>>> AFTER_CREATE')
        is_dataset = self._data_dict_is_dataset(data_dict)

        if is_dataset:
            log.debug('>>>>>>> AFTER_CREATE DATASET')
            for resource in data_dict.get(u'resources', []):
                #log.debug('resource id {}'.format(resource['id']))
                pass
        else:
            log.debug('>>>>>>> AFTER_CREATE RESOURCE')
            # data_dict is resource
            #log.debug(data_dict)
            if self._resource_is_zip_shapefile(data_dict):
                #log.debug('resource file is zip shapefile')
                enqueue_job(save_shapefile_metadata, [data_dict])
            pass

    def before_update(self, context, current_resource, updated_resource):
        '''Hook called before updating an existing dataset resource
        '''
        log.debug('>>>>>>> HOOK BEFORE_UPDATE')
        #log.debug(updated_resource)
        return updated_resource

    def after_update(self, context, data_dict):
        '''Hook called after updating an existing dataset resource
        '''
        log.debug('>>>>>>> HOOK AFTER_UPDATE')
        # data_dict is resource
        #log.debug(data_dict)
        if self._resource_is_zip_shapefile(data_dict):
            #log.debug('>>>>>>> _resource_is_zip_shapefile')
            enqueue_job(save_shapefile_metadata, [data_dict])
        else:
            # resource file changed from zip shapefile?
            #log.debug('resource file changed from zip shapefile')
            spatial_metadata = data_dict.get(u'spatial_metadata', u'')
            # since resource file changed from zip shapefile, clear existing spatial_metadata resource field
            if spatial_metadata:
                #log.debug('found existing spatial_metadata')
                context = {'ignore_auth': True, 'user': t.get_action('get_site_user')({'ignore_auth': True})['name']}
                resource_data = {'id': data_dict['id'], 'spatial_metadata': ''}
                t.get_action('resource_patch')(context, resource_data)
