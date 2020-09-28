# -*- coding: utf-8 -*-

import logging

import ckan.plugins as p
import ckan.plugins.toolkit as t
from ckan.common import config

from ckanext.onedataportal.helpers import (
    add_time,
    naive_to_utc,
    geoportal_url,
    geoportal_name,
    navlink1_url,
    navlink1_name,
    navlink2_url,
    navlink2_name,
    navlink3_url,
    navlink3_name,
    get_json_as_dict,
)
from ckanext.onedataportal.jobs import (
    enqueue_job,
    save_shapefile_metadata,
    convert_shpz_shapefile,
)
from ckanext.onedataportal.converters import allowed_users_convert


log = logging.getLogger(__name__)


class OnedataportalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IValidators)
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
            'onedataportal_navlink1_url': navlink1_url,
            'onedataportal_navlink1_name': navlink1_name,
            'onedataportal_navlink2_url': navlink2_url,
            'onedataportal_navlink2_name': navlink2_name,
            'onedataportal_navlink3_url': navlink3_url,
            'onedataportal_navlink3_name': navlink3_name,
            'onedataportal_get_json_as_dict': get_json_as_dict
        }

    # IValidators

    def get_validators(self):
        return {
            'allowed_users_convert': allowed_users_convert
        }

    # IResourceController

    def _data_dict_is_dataset(self, data_dict):
        """Check if data_dict is a dataset.
        """
        #log.debug('>>>>>>> _data_dict_is_dataset')
        return (
            u'creator_user_id' in data_dict
            or u'owner_org' in data_dict
            or u'resources' in data_dict
            or data_dict.get(u'type') == u'dataset')

    def _resource_is_zip_shapefile(self, resource):
        """Check if an uploaded resource is a zipped file and format is set to shp.
        """
        if resource.get(u'format', u'').lower() == 'shp' and resource.get(u'url', u'').lower().endswith('zip'):
            return True
        return False

    def before_create(self, context, data_dict):
        """IResourceController hook method.
        """
        log.debug('>>>>>>> BEFORE_CREATE')
        return data_dict

    def after_create(self, context, data_dict):
        """IResourceController hook method called after saving a new dataset resource.
        """
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
                convert_shpz = config.get('ckan.onedataportal.convert_shpz', False)
                # 20200924 disable async due to infinite job loop
                #enqueue_job(save_shapefile_metadata, [data_dict])
                save_shapefile_metadata(data_dict)
                if convert_shpz:
                    convert_shpz_shapefile(data_dict)
            pass

    def before_update(self, context, current_resource, updated_resource):
        """IResourceController hook method called before updating an existing dataset resource.
        """
        log.debug('>>>>>>> HOOK BEFORE_UPDATE')
        #log.debug(updated_resource)
        return updated_resource

    def after_update(self, context, data_dict):
        """IResourceController hook method called after updating an existing dataset resource.
        """
        log.debug('>>>>>>> HOOK AFTER_UPDATE')
        # data_dict is resource
        #log.debug(data_dict)
        is_dataset = self._data_dict_is_dataset(data_dict)

        if context.get('_save_shapefile_metadata'):
            # Ugly, but needed to avoid circular loops caused by the
            # save_shapefile_metadata job calling resource_patch (which calls
            # package_update)
            del context['_save_shapefile_metadata']
            return

        if context.get('_convert_shpz_shapefile'):
            del context['_convert_shpz_shapefile']
            return

        if is_dataset:
            pass
        else:
            log.debug('>>>>>>> AFTER_UPDATE RESOURCE')
            if self._resource_is_zip_shapefile(data_dict):
                convert_shpz = config.get('ckan.onedataportal.convert_shpz', False)
                #log.debug('>>>>>>> _resource_is_zip_shapefile')
                # 20200924 disable async due to infinite job loop
                #enqueue_job(save_shapefile_metadata, [data_dict])
                save_shapefile_metadata(data_dict)
                if convert_shpz:
                    convert_shpz_shapefile(data_dict)
            else:
                # resource file changed from zip shapefile?
                #log.debug('resource file changed from zip shapefile')
                spatial_metadata = data_dict.get(u'spatial_metadata', u'')
                # since resource file changed from zip shapefile, clear existing spatial_metadata resource field
                if spatial_metadata:
                    #log.debug('found existing spatial_metadata')
                    context = {'ignore_auth': True, 'user': t.get_action('get_site_user')({'ignore_auth': True})['name'], '_save_shapefile_metadata': True}
                    resource_data = {'id': data_dict['id'], 'spatial_metadata': ''}
                    t.get_action('resource_patch')(context, resource_data)
