import logging
import json
from io import BytesIO
from zipfile import ZipFile

import xmltodict
import requests

import ckan.plugins.toolkit as t
import ckan.lib.uploader as uploader


log = logging.getLogger(__name__)


def save_shapefile_metadata(resource):
    log.debug('>>>>>>> save_shapefile_metadata')
    #log.debug(resource)
    try:
        resource_file = None
        if resource.get(u'url_type') == u'upload':
            upload = uploader.get_resource_uploader(resource)
            if isinstance(upload, uploader.ResourceUpload):
                resource_file = upload.get_path(resource[u'id'])
        if not resource_file:
            resource_file = resource.get(u'url')
        #log.debug(resource_file)
        spatial_metadata = None
        # resource_file can be a URL or path to local file
        if resource_file.startswith('http') or resource_file.startswith('https'):
            response = requests.get(resource_file)
            #log.debug(response.status_code)
            if response.status_code == requests.codes.ok:
                zf = ZipFile(BytesIO(response.content))
                for item in zf.namelist():
                    if item.lower().endswith('qmd'):
                        qgis_metadata = zf.open(item).read()
                        try:
                            spatial_metadata = xmltodict.parse(qgis_metadata)
                        except Exception as e:
                            log.error(e)
                        break
        else:
            with ZipFile(resource_file, 'r') as zf:
                for item in zf.namelist():
                    if item.lower().endswith('qmd'):
                        qgis_metadata = zf.open(item).read()
                        try:
                            spatial_metadata = xmltodict.parse(qgis_metadata)
                        except Exception as e:
                            log.error(e)
                        break
        if spatial_metadata:
            #log.debug('saving spatial_metadata resource field')
            #log.debug(json.dumps(spatial_metadata, indent=4))
            spatial_metadata = json.dumps(spatial_metadata)
            # save in resource's spatial_metadata field
            #log.debug(t.get_action('get_site_user')({'ignore_auth': True})['name'])
            context = {'ignore_auth': True, 'user': t.get_action('get_site_user')({'ignore_auth': True})['name']}
            resource_data = {'id': resource['id'], 'spatial_metadata': spatial_metadata}
            t.get_action('resource_patch')(context, resource_data)
    except Exception as e:
        log.error(e)
