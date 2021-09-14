# -*- coding: utf-8 -*-

import os
import io
import sys
import logging
import datetime
import random
import string
import json
from ConfigParser import SafeConfigParser

import ckan.plugins.toolkit as t
from ckan.plugins.toolkit import CkanCommand

import requests
import pycsw.core.config
from pycsw.core import metadata, repository, util
import xmltodict
from lxml import etree

from ckanext.onedataportal.helpers import validate_iso_19115_metadata


#fh = logging.FileHandler('/tmp/pycsw_output.log')
sh = logging.StreamHandler(sys.stdout)
handlers = [sh]
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)
log = logging.getLogger(__name__)


class Pycsw(CkanCommand):
    """

        pycsw load [-p pycsw.cfg] [-u http://localhost]
            Import CKAN datasets as records into the pycsw database.
            
            -p: pycsw configuration file.
            -u: URL of the CKAN instance which the datasets will be imported from.
    """
    
    summary = __doc__.split('\n')[0]
    usage = __doc__
    
    def __init__(self, name):
        """Configure parser options.
        """
        super(Pycsw, self).__init__(name)
        self.parser.add_option('-p', '--pycsw-config', dest='pycsw_config',
            default='pycsw.cfg', help='pycsw configuration file.')
        self.parser.add_option('-u', '--ckan-url', dest='ckan_url',
            default='http://localhost', help='URL of the CKAN instance which the datasets will be imported from.')

    def _pycsw_load_config(self, pycsw_config_file):
        """Load pycsw configuration file.
        
        Args:
            pycsw_config_file: path to pycsw configuration file.
        
        Returns:
            SafeConfigParser object.

        Raises:
            AssertionError: if the pycsw configuration file does not exist.
        """
        abs_path = os.path.abspath(pycsw_config_file)
        if not os.path.exists(abs_path):
            raise AssertionError("Cannot find pycsw configuration file {0}.".format(abs_path))
        config = SafeConfigParser()
        config.read(abs_path)
        return config

    def _add_resource_metadata(self, spatial_metadata_dict, url, protocol, name, description):
        """Add gmd:MD_DigitalTransferOptions metadata for the resource to the ISO 19115 spatial metadata dict.
        
        Args:
            spatial_metadata_dict: dict structure of the spatial metadata.
            url: string URL to add as gmd:URL element.
            protocol: string of the URL's protocol (e.g. OGC:WMS, OGC:WFS) to add to gmd:protocol.
            name: string of resource's name to add to gmd:name.
            name: string of resource's description to add to gmd:description.
        
        Returns:
            The spatial_metadata_dict with the added gmd:MD_DigitalTransferOptions metadata element.
        """
        if 'gmd:distributionInfo' not in spatial_metadata_dict['gmd:MD_Metadata']:
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo'] = {}
        if 'gmd:MD_Distribution' not in spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']:
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution'] = {}
        if 'gmd:transferOptions' not in spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']:
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:transferOptions'] = []
        transferOptions = spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:transferOptions']
        # append ?service=wms or ?service=wfs so resource format is detected properly as wms/wfs by ckanext-spatial CSW harvester
        resource_url = url
        if protocol == 'OGC:WMS':
            if not resource_url.endswith('?service=wms'):
                resource_url = "{}{}".format(resource_url, '?service=wms')
        if protocol == 'OGC:WFS':
            if not resource_url.endswith('?service=wfs'):
                resource_url = "{}{}".format(resource_url, '?service=wfs')
        resource_name = name
        resource_description = description
        urlDict = {
            'gmd:MD_DigitalTransferOptions': {
                'gmd:onLine': {
                    'gmd:CI_OnlineResource': {
                        'gmd:linkage': {
                            'gmd:URL': resource_url
                        },
                        'gmd:protocol': {
                            'gco:CharacterString': protocol
                        },
                        'gmd:name': {
                            'gco:CharacterString': resource_name
                        },
                        'gmd:description': {
                            'gco:CharacterString': resource_description
                        }
                    }
                }
            }
        }
        transferOptions.append(urlDict)
        """
        # override distributionFormat with WMS
        if 'gmd:distributionFormat' not in spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']:
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat'] = {}
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat'] = {
                'gmd:MD_Format': {
                    'gmd:name': {
                        'gco:CharacterString': ''
                    },
                    'gmd:version': {
                        'gco:CharacterString': ''
                    }
                }
            }
        if protocol == 'OGC:WMS':
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat']['gmd:MD_Format']['gmd:name']['gco:CharacterString'] = 'WMS'
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat']['gmd:MD_Format']['gmd:version']['gco:CharacterString'] = '1.3.0'
        """
         # override existing distributionFormat with WMS
        if 'gmd:distributionFormat' in spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']:
            distributionFormat = spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat']
            if isinstance(distributionFormat, dict):
                spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat'] = {}
                spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat'] = {
                    'gmd:MD_Format': {
                        'gmd:name': {
                            'gco:CharacterString': ''
                        },
                        'gmd:version': {
                            'gco:CharacterString': ''
                        }
                    }
                }
                spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat']['gmd:MD_Format']['gmd:name']['gco:CharacterString'] = 'WMS'
                spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat']['gmd:MD_Format']['gmd:version']['gco:CharacterString'] = '1.3.0'
        # if distributionFormat is not set, initialize as list of formats
        if 'gmd:distributionFormat' not in spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']:
            spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat'] = []
        distributionFormat = spatial_metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:distributionFormat']
        if protocol == 'OGC:WMS':
            # SDP Oskari Server Extension WMS version defaults to 1.3.0
            formatDict = {
                'gmd:MD_Format': {
                    'gmd:name': {
                        'gco:CharacterString': 'WMS'
                    },
                    'gmd:version': {
                        'gco:CharacterString': '1.3.0'
                    }
                }
            }
            if isinstance(distributionFormat, list):
                distributionFormat.append(formatDict)
        elif protocol == 'OGC:WFS':
            # SDP Oskari Server Extension WFS version defaults to 1.1.0
            formatDict = {
                'gmd:MD_Format': {
                    'gmd:name': {
                        'gco:CharacterString': 'WFS'
                    },
                    'gmd:version': {
                        'gco:CharacterString': '1.1.0'
                    }
                }
            }
            if isinstance(distributionFormat, list):
                distributionFormat.append(formatDict)
        #print(json.dumps(transferOptions, indent=4, sort_keys=True))
        return spatial_metadata_dict

    def _append_random_string_to_identifier(self, spatial_metadata_dict):
        """Append a random 8 character string to the end of gmd:fileIdentifier spatial metadata element.
        
        In cases where the spatial metadata can have the same gmd:fileIdentifier string value it is
        neccessary to append random characters so the pycsw record has a unique identifier primary key.
        
        Args:
            spatial_metadata_dict: dict structure of the spatial metadata.
        
        Returns:
            The spatial_metadata_dict with the modified gmd:fileIdentifier element.
        """
        fileIdentifier = spatial_metadata_dict['gmd:MD_Metadata']['gmd:fileIdentifier']['gco:CharacterString']
        fileIdentifier += '_' + ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(8))
        spatial_metadata_dict['gmd:MD_Metadata']['gmd:fileIdentifier']['gco:CharacterString'] = fileIdentifier
        return spatial_metadata_dict

    def _get_record(self, context, repo, ckan_id, ckan_info):
        """Create a pycsw record object by extracting and parsing the spatial metadata of the dataset or resource.
        
        Args:
            context: pycsw context.
            repo: connection to pycsw database repository.
            ckan_id: the id of the dataset (package) or resource.
            ckan_info: dict containing spatial metadata and WMS/WFS URLs info of the CKAN dataset or resource.
        
        Returns:
            The pycsw record with the populated spatial metadata.
        """
        xml = None
        if 'spatial_metadata_iso_19115' in ckan_info and ckan_info['spatial_metadata_iso_19115']:
            try:
                metadata_dict = json.loads(ckan_info['spatial_metadata_iso_19115'])
                #print(json.dumps(metadata_dict, indent=4, sort_keys=True))
                # append wms_url and wfs_url to metadata gmd:URL element
                resource_name = ''
                resource_description = ''
                if 'resource_name' in ckan_info and ckan_info['resource_name']:
                        resource_name = ckan_info['resource_name']
                if 'resource_description' in ckan_info and ckan_info['resource_description']:
                        resource_description = ckan_info['resource_description']
                if 'wms_url' in ckan_info and ckan_info['wms_url']:
                    metadata_dict = self._add_resource_metadata(metadata_dict, ckan_info['wms_url'], 'OGC:WMS', resource_name, resource_description)
                if 'wfs_url' in ckan_info and ckan_info['wfs_url']:
                    metadata_dict = self._add_resource_metadata(metadata_dict, ckan_info['wfs_url'], 'OGC:WFS', resource_name, resource_description)
                if 'resource_url' in ckan_info and ckan_info['resource_url']:
                    metadata_dict = self._add_resource_metadata(metadata_dict, ckan_info['resource_url'], 'url', resource_name, resource_description)
                metadata_dict = self._append_random_string_to_identifier(metadata_dict)
                xml = xmltodict.unparse(metadata_dict)
                xml = bytes(bytearray(xml, encoding='utf-8'))
                xml = etree.XML(xml)
            except Exception as e:
                log.debug("Unable to parse JSON string to XML")
                log.error(e)
                raise
        try:
            record = metadata.parse_record(context, xml, repo)[0]
        except Exception, err:
            log.error("Could not extract metadata from {}, Error: {}".format(ckan_id, err))
            return
        if not record.identifier:
            record.identifier = ckan_id
        record.ckan_id = ckan_id
        record.ckan_modified = ckan_info['metadata_modified']
        return record

    def _OBSOLETE_import_spatial_metadata_to_pycsw(self, pycsw_config, ckan_url):
        """Import spatial metadata from CKAN datasets and resources as records into the pycsw database.
        
        OBSOLETE: replaced by import_spatial_metadata_to_pycsw() below.
        
        This method looks for ISO 19115 spatial metadata stored in the 'spatial_metadata_iso_19115'
        extra field on the dataset and resource level. For spatial metadata on the dataset level it is
        assumed that the metadata is uploaded as a separate XML file resource, while on the resource
        level the metadata XML file is assumed to be embedded within a zipped shapefile.
        
        Only ISO 19115 spatial metadata that pass validation according to the mandatory fields defined
        in validate_iso_19115_metadata() will be imported to pycsw.
        
        Args:
            pycsw_config: pycsw configuration object.
            ckan_url: string URL of the CKAN instance which the resources will be imported from.
        """
        log.info("Start importing spatial metadata to pycsw: {}".format(str(datetime.datetime.now())))
        count_dataset_metadata = 0
        count_resource_metadata = 0
        gathered_metadata = {}
        package_list_response = requests.get(ckan_url + 'api/action/package_list')
        package_list = package_list_response.json()
        if not isinstance(package_list, dict):
                raise RuntimeError, "Wrong API response: {}".format(package_list)
        package_list_result = package_list.get('result')
        for package_id in package_list_result:
            package_show_response = requests.get(ckan_url + 'api/action/package_show?id={}'.format(package_id))
            package = package_show_response.json()
            if not isinstance(package, dict):
                raise RuntimeError, "Wrong API response: {}".format(package)
            #print(json.dumps(package, indent=4, sort_keys=True))
            package_result = package.get('result')
            # check if the dataset has ISO 19115 spatial metadata
            package_id = package_result.get('id')
            package_metadata_modified = package_result.get('metadata_modified')
            spatial_metadata_iso_19115 = package_result.get('spatial_metadata_iso_19115')
            wms_url = package_result.get('wms_url')
            wfs_url = package_result.get('wfs_url')
            # dataset must have ISO 19115 metadata and either WMS URL or WFS URL
            if spatial_metadata_iso_19115 and (wms_url or wfs_url):
                # ISO 19115 spatial metadata must pass validation to be synced to pycsw
                spatial_metadata_passes_validation = validate_iso_19115_metadata(json.loads(spatial_metadata_iso_19115))
                if spatial_metadata_passes_validation:
                    # use package id as ckan_id for pycsw record
                    gathered_metadata[package_id] = {
                        'metadata_modified': package_metadata_modified,
                        'spatial_metadata_iso_19115': spatial_metadata_iso_19115,
                        'wms_url': wms_url,
                        'wfs_url': wfs_url
                    }
                    count_dataset_metadata += 1
            # check if resources have ISO 19115 spatial metadata
            for resource in package_result['resources']:
                #print(json.dumps(resource, indent=4, sort_keys=True))
                resource_id = resource.get('id')
                resource_last_modified = resource.get('last_modified')
                spatial_metadata_iso_19115 = resource.get('spatial_metadata_iso_19115')
                wms_url = resource.get('wms_url')
                wfs_url = resource.get('wfs_url')
                # dataset must have ISO 19115 metadata and either WMS URL or WFS URL
                if spatial_metadata_iso_19115 and (wms_url or wfs_url):
                    # ISO 19115 spatial metadata must pass validation to be synced to pycsw
                    spatial_metadata_passes_validation = validate_iso_19115_metadata(json.loads(spatial_metadata_iso_19115))
                    if spatial_metadata_passes_validation:
                        # use resource id as ckan_id for pycsw record
                        gathered_metadata[resource_id] = {
                            'metadata_modified': resource_last_modified,
                            'spatial_metadata_iso_19115': spatial_metadata_iso_19115,
                            'wms_url': wms_url,
                            'wfs_url': wfs_url
                        }
                        count_resource_metadata += 1
        #print(json.dumps(gathered_metadata, indent=4, sort_keys=True))
        log.info("============================================================")
        log.info("Finished gathering {0} spatial metadata (that passed validation): {1}".format(len(gathered_metadata.keys()), str(datetime.datetime.now())))
        log.info("Dataset spatial metadata found: {}".format(count_dataset_metadata))
        log.info("Resource spatial metadata found: {}".format(count_resource_metadata))
        log.info("============================================================")
        pycsw_database = pycsw_config.get('repository', 'database')
        pycsw_table = pycsw_config.get('repository', 'table', 'records')
        context = pycsw.core.config.StaticContext()
        repo = repository.Repository(pycsw_database, context, table=pycsw_table)
        existing_records = {}
        pycsw_query = repo.session.query(repo.dataset.ckan_id, repo.dataset.ckan_modified)
        for row in pycsw_query:
            existing_records[row[0]] = row[1]
        repo.session.close()
        new = set(gathered_metadata) - set(existing_records)
        deleted = set(existing_records) - set(gathered_metadata)
        changed = set()
        #print("##############################")
        #print(new, deleted, changed)
        for key in set(gathered_metadata) & set(existing_records):
            if gathered_metadata[key]['metadata_modified'] > existing_records[key]:
                changed.add(key)
        count_records_deleted = count_records_inserted = count_records_updated = 0
        for ckan_id in deleted:
            try:
                repo.session.begin()
                repo.session.query(repo.dataset.ckan_id).filter_by(
                ckan_id=ckan_id).delete()
                log.info("Deleted {}".format(ckan_id))
                repo.session.commit()
                count_records_deleted += 1
            except Exception, err:
                repo.session.rollback()
                raise
        for ckan_id in new:
            ckan_info = gathered_metadata[ckan_id]
            record = self._get_record(context, repo, ckan_id, ckan_info)
            if not record:
                log.info("Skipped record {}".format(ckan_id))
                continue
            try:
                repo.insert(record, 'local', util.get_today_and_now())
                log.info("Inserted {}".format(ckan_id))
                count_records_inserted += 1
            except Exception, err:
                log.error("ERROR: not inserted {} Error:{}".format(ckan_id, err))
        for ckan_id in changed:
            ckan_info = gathered_metadata[ckan_id]
            record = self._get_record(context, repo, ckan_id, ckan_info)
            if not record:
                continue
            update_dict = dict([(getattr(repo.dataset, key),
            getattr(record, key)) \
            for key in record.__dict__.keys() if key != '_sa_instance_state'])
            try:
                repo.session.begin()
                repo.session.query(repo.dataset).filter_by(
                ckan_id=ckan_id).update(update_dict)
                repo.session.commit()
                log.info("Changed {}".format(ckan_id))
                count_records_updated += 1
            except Exception, err:
                repo.session.rollback()
                raise RuntimeError, "ERROR: %s".format(str(err))
        log.info("============================================================")
        log.info("Finished importing spatial metadata to pycsw: {}".format(str(datetime.datetime.now())))
        log.info("Spatial metadata records inserted: {}".format(count_records_inserted))
        log.info("Spatial metadata records update: {}".format(count_records_updated))
        log.info("Spatial metadata records deleted: {}".format(count_records_deleted))
        log.info("============================================================")

    def _import_spatial_metadata_to_pycsw(self, pycsw_config, ckan_url):
        """Import spatial metadata from CKAN datasets and resources as records into the pycsw database.
        
        This method looks for ISO 19115 spatial metadata stored in the 'spatial_metadata_iso_19115'
        extra field on the dataset and resource level. For spatial metadata on the dataset level it is
        assumed that the metadata is uploaded as a separate XML file resource, while on the resource
        level the metadata XML file is assumed to be embedded within a zipped shapefile.
        
        Only ISO 19115 spatial metadata that pass validation according to the mandatory fields defined
        in validate_iso_19115_metadata() will be imported to pycsw.
        
        This method differs from _OBSOLETE_import_spatial_metadata_to_pycsw() where only resources matching
        specific formats that can be synced to Oskari + GeoServer are imported to pycsw as records compared
        to the previous implementation where both the dataset and resource are imported.
        
        Args:
            pycsw_config: pycsw configuration object.
            ckan_url: string URL of the CKAN instance which the resources will be imported from.
        """
        log.info("Start importing spatial metadata to pycsw: {}".format(str(datetime.datetime.now())))
        count_dataset_metadata = 0
        count_resource_metadata = 0
        synced_spatial_formats = {'wms', 'wmts', 'wfs', 'shp', 'tif', 'tiff'}
        gathered_metadata = {}
        package_list_response = requests.get(ckan_url + 'api/action/package_list')
        package_list = package_list_response.json()
        if not isinstance(package_list, dict):
                raise RuntimeError, "Wrong API response: {}".format(package_list)
        package_list_result = package_list.get('result')
        for package_id in package_list_result:
            package_show_response = requests.get(ckan_url + 'api/action/package_show?id={}'.format(package_id))
            package = package_show_response.json()
            if not isinstance(package, dict):
                raise RuntimeError, "Wrong API response: {}".format(package)
            #print(json.dumps(package, indent=4, sort_keys=True))
            package_result = package.get('result')
            # check if the dataset has ISO 19115 spatial metadata
            package_id = package_result.get('id')
            package_metadata_modified = package_result.get('metadata_modified')
            dataset_spatial_metadata_iso_19115 = package_result.get('spatial_metadata_iso_19115')
            # check if ISO 19115 metadata passes on dataset level
            dataset_spatial_metadata_passes_validation = False
            if dataset_spatial_metadata_iso_19115:
                # ISO 19115 spatial metadata must pass validation to be synced to pycsw
                dataset_spatial_metadata_passes_validation = validate_iso_19115_metadata(json.loads(dataset_spatial_metadata_iso_19115))
            # check if resources have ISO 19115 spatial metadata
            for resource in package_result['resources']:
                resource_format = resource.get('format')
                resource_format = resource_format.lower()
                # only process resource formats that are synced to Oskari + GeoServer
                if resource_format in synced_spatial_formats:
                    log.info("Found matching synced resource format: {}".format(resource_format))
                    #print(json.dumps(resource, indent=4, sort_keys=True))
                    resource_id = resource.get('id')
                    resource_last_modified = resource.get('last_modified')
                    resource_spatial_metadata_iso_19115 = resource.get('spatial_metadata_iso_19115')
                    resource_name = resource.get('name')
                    resource_description = resource.get('description')
                    resource_url = resource.get('url')
                    wms_url = resource.get('wms_url')
                    wfs_url = resource.get('wfs_url')
                    if dataset_spatial_metadata_passes_validation and (wms_url or wfs_url):
                        # spatial resource with separate ISO 19115 spatial metadata on the dataset level
                        gathered_metadata[resource_id] = {
                            #'metadata_modified': resource_last_modified,
                            'metadata_modified': package_metadata_modified, # use dataset's metadata_modified due to resource last_modified bug https://github.com/ckan/ckan/issues/5190
                            'spatial_metadata_iso_19115': dataset_spatial_metadata_iso_19115,
                            'resource_name': resource_name,
                            'resource_description': resource_description,
                            'resource_url': resource_url,
                            'wms_url': wms_url,
                            'wfs_url': wfs_url
                        }
                        count_dataset_metadata += 1
                    else:
                        # spatial resource with embedded ISO 19115 metadata and either WMS URL or WFS URL
                        if resource_spatial_metadata_iso_19115 and (wms_url or wfs_url):
                            # ISO 19115 spatial metadata must pass validation to be synced to pycsw
                            resource_spatial_metadata_passes_validation = validate_iso_19115_metadata(json.loads(resource_spatial_metadata_iso_19115))
                            if resource_spatial_metadata_passes_validation:
                                # use resource id as ckan_id for pycsw record
                                gathered_metadata[resource_id] = {
                                    #'metadata_modified': resource_last_modified,
                                    'metadata_modified': package_metadata_modified, # use dataset's metadata_modified due to resource last_modified bug https://github.com/ckan/ckan/issues/5190
                                    'spatial_metadata_iso_19115': resource_spatial_metadata_iso_19115,
                                    'resource_name': resource_name,
                                    'resource_description': resource_description,
                                    'resource_url': resource_url,
                                    'wms_url': wms_url,
                                    'wfs_url': wfs_url
                                }
                                count_resource_metadata += 1
        #print(json.dumps(gathered_metadata, indent=4, sort_keys=True))
        log.info("============================================================")
        log.info("Finished gathering {0} spatial metadata (that passed validation): {1}".format(len(gathered_metadata.keys()), str(datetime.datetime.now())))
        log.info("Dataset spatial metadata found: {}".format(count_dataset_metadata))
        log.info("Resource spatial metadata found: {}".format(count_resource_metadata))
        log.info("============================================================")
        pycsw_database = pycsw_config.get('repository', 'database')
        pycsw_table = pycsw_config.get('repository', 'table', 'records')
        context = pycsw.core.config.StaticContext()
        repo = repository.Repository(pycsw_database, context, table=pycsw_table)
        existing_records = {}
        pycsw_query = repo.session.query(repo.dataset.ckan_id, repo.dataset.ckan_modified)
        for row in pycsw_query:
            existing_records[row[0]] = row[1]
        repo.session.close()
        new = set(gathered_metadata) - set(existing_records)
        deleted = set(existing_records) - set(gathered_metadata)
        changed = set()
        #print("##############################")
        #print(new, deleted, changed)
        for key in set(gathered_metadata) & set(existing_records):
            if gathered_metadata[key]['metadata_modified'] > existing_records[key]:
                changed.add(key)
        count_records_deleted = count_records_inserted = count_records_updated = 0
        for ckan_id in deleted:
            try:
                repo.session.begin()
                repo.session.query(repo.dataset.ckan_id).filter_by(
                ckan_id=ckan_id).delete()
                log.info("Deleted {}".format(ckan_id))
                repo.session.commit()
                count_records_deleted += 1
            except Exception, err:
                repo.session.rollback()
                raise
        for ckan_id in new:
            ckan_info = gathered_metadata[ckan_id]
            record = self._get_record(context, repo, ckan_id, ckan_info)
            if not record:
                log.info("Skipped record {}".format(ckan_id))
                continue
            try:
                repo.insert(record, 'local', util.get_today_and_now())
                log.info("Inserted {}".format(ckan_id))
                count_records_inserted += 1
            except Exception, err:
                log.error("ERROR: not inserted {} Error:{}".format(ckan_id, err))
        for ckan_id in changed:
            ckan_info = gathered_metadata[ckan_id]
            record = self._get_record(context, repo, ckan_id, ckan_info)
            if not record:
                continue
            update_dict = dict([(getattr(repo.dataset, key),
            getattr(record, key)) \
            for key in record.__dict__.keys() if key != '_sa_instance_state'])
            try:
                repo.session.begin()
                repo.session.query(repo.dataset).filter_by(
                ckan_id=ckan_id).update(update_dict)
                repo.session.commit()
                log.info("Changed {}".format(ckan_id))
                count_records_updated += 1
            except Exception, err:
                repo.session.rollback()
                raise RuntimeError, "ERROR: %s".format(str(err))
        log.info("============================================================")
        log.info("Finished importing spatial metadata to pycsw: {}".format(str(datetime.datetime.now())))
        log.info("Spatial metadata records inserted: {}".format(count_records_inserted))
        log.info("Spatial metadata records update: {}".format(count_records_updated))
        log.info("Spatial metadata records deleted: {}".format(count_records_deleted))
        log.info("============================================================")

    def command(self):
        """Parse command line arguments and call appropriate method.
        """
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            self.parser.print_usage()
            sys.exit(1)
        cmd = self.args[0]
        # below needed if requiring settings from CKAN config file -c /etc/ckan/ckan/production.ini
        #self._load_config()
        if cmd == 'load':
            pycsw_config_file = self.options.pycsw_config
            ckan_url = self.options.ckan_url.rstrip('/') + '/'
            default_msg = "Using default parameters for: {} {}"
            if pycsw_config_file == 'pycsw.cfg' and ckan_url == 'http://localhost/':
                log.info(default_msg.format('-p ' + pycsw_config_file, '-u ' + ckan_url))
            elif pycsw_config_file == 'pycsw.cfg':
                log.info(default_msg.format('-p ' + pycsw_config_file, ''))
            elif ckan_url == 'http://localhost/':
                log.info(default_msg.format('-u ' + ckan_url, ''))
            pycsw_config = self._pycsw_load_config(pycsw_config_file)
            self._import_spatial_metadata_to_pycsw(pycsw_config, ckan_url)
        else:
            self.parser.print_usage()
            sys.exit(1)
