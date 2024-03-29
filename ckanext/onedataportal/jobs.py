# -*- coding: utf-8 -*-

import logging

import ckan.plugins.toolkit as t

from ckanext.onedataportal.helpers import (
    is_qgis_metadata,
    is_iso_19115_metadata,
)


log = logging.getLogger(__name__)


def enqueue_job(*args, **kwargs):
    """Enqueue an asynchronous job to RQ.
    """
    try:
        return t.enqueue_job(*args, **kwargs)
    except AttributeError:
        from ckanext.rq.jobs import enqueue as enqueue_job_legacy
        return enqueue_job_legacy(*args, **kwargs)


def save_metadata_from_resource_file(resource):
    """Save the metadata a .qmd or ISO 19115 .xml file.

    Args:
        resource: a resource dict object.

    For non zipped shapefiles, the metadata file (.qmd or ISO 19115 .xml) must be uploaded
    as a separate resource file for the dataset. The XML metadata is saved in the dataset's
    'spatial_metadata' and 'spatial_metadata_iso_19115' scheming field.
    """
    log.debug('>>>>>>> save_metadata_from_resource_file')

    import os
    import json
    import xmltodict
    import requests
    import ckan.lib.uploader as uploader

    try:
        resource_file = None
        if resource.get(u'url_type') == u'upload':
            upload = uploader.get_resource_uploader(resource)
            if isinstance(upload, uploader.ResourceUpload):
                resource_file = upload.get_path(resource[u'id'])
        if not resource_file:
            resource_file = resource[u'url']
        spatial_metadata = None
        spatial_metadata_iso_19115 = None
        metadata_file = None
        if resource_file.startswith('http') or resource_file.startswith('https'):
            response = requests.get(resource_file)
            if response.status_code == requests.codes.ok:
                metadata_file = response.text
        elif os.path.isfile(resource_file):
            metadata_file = open(resource_file, 'r')
        if metadata_file:
            try:
                metadata_dict = xmltodict.parse(metadata_file)
                # check if this is a QGIS metadata
                if is_qgis_metadata(metadata_dict):
                    spatial_metadata = metadata_dict
                # check if this is a ISO 19115 metadata
                if is_iso_19115_metadata(metadata_dict):
                    spatial_metadata_iso_19115 = metadata_dict
            except Exception as e:
                log.error(e)
            metadata_file.close()
        # construct the dict of the dataset to be updated
        dataset_data = {'id': resource['package_id']}
        if spatial_metadata:
            spatial_metadata = json.dumps(spatial_metadata)
            dataset_data['spatial_metadata'] = spatial_metadata
        if spatial_metadata_iso_19115:
            spatial_metadata_iso_19115 = json.dumps(spatial_metadata_iso_19115)
            dataset_data['spatial_metadata_iso_19115'] = spatial_metadata_iso_19115
        if spatial_metadata or spatial_metadata_iso_19115:
            # save in dataset's 'spatial_metadata' and 'spatial_metadata_iso_19115' scheming fields
            context = {'ignore_auth': True, 'user': t.get_action('get_site_user')({'ignore_auth': True})['name'], '_save_metadata_from_resource_file': True}
            t.get_action('package_patch')(context, dataset_data)
            log.debug('SUCCESS: saved "spatial_metadata" / "spatial_metadata_iso_19115" dataset field')
    except Exception as e:
        log.error(e)


def save_shapefile_metadata(resource):
    """Read a zipped shapefile resource and save the metadata from the .qmd file.
    Also looks for metadata in a ISO 19115 .xml file.

    Args:
        resource: a resource dict object.

    The XML metadata in the .qmd file is converted to a JSON string and saved in the 'spatial_metadata' resource field.
    XML metadata from the ISO 19115 .xml file is saved in the 'spatial_metadata_iso_19115' resource scheming field.
    """
    log.debug('>>>>>>> save_shapefile_metadata')

    import os
    import json
    from io import BytesIO
    from zipfile import ZipFile
    import xmltodict
    import requests
    import ckan.lib.uploader as uploader

    try:
        resource_file = None
        if resource.get(u'url_type') == u'upload':
            upload = uploader.get_resource_uploader(resource)
            if isinstance(upload, uploader.ResourceUpload):
                resource_file = upload.get_path(resource[u'id'])
        if not resource_file:
            resource_file = resource[u'url']
        spatial_metadata = None
        spatial_metadata_iso_19115 = None
        zf = None
        if resource_file.startswith('http') or resource_file.startswith('https'):
            response = requests.get(resource_file)
            if response.status_code == requests.codes.ok:
                zf = ZipFile(BytesIO(response.content))
        elif os.path.isfile(resource_file):
            zf = ZipFile(resource_file, 'r')
        if zf:
            for item in zf.namelist():
                if item.lower().endswith('qmd'):
                    shp_metadata_file = zf.open(item).read()
                    try:
                        metadata_dict = xmltodict.parse(shp_metadata_file)
                        # check if this is a QGIS metadata
                        if is_qgis_metadata(metadata_dict):
                            spatial_metadata = metadata_dict
                    except Exception as e:
                        log.error(e)
                elif item.lower().endswith('xml'):
                    shp_metadata_file = zf.open(item).read()
                    try:
                        metadata_dict = xmltodict.parse(shp_metadata_file)
                        # check if this is a ISO 19115 metadata
                        if is_iso_19115_metadata(metadata_dict):
                            spatial_metadata_iso_19115 = metadata_dict
                    except Exception as e:
                        log.error(e)
            zf.close()
        # construct the dict of the resource to be updated
        resource_data = {'id': resource['id']}
        if spatial_metadata:
            #log.debug('saving QGIS metadata')
            #log.debug(spatial_metadata)
            #log.debug(json.dumps(spatial_metadata, indent=4))
            spatial_metadata = json.dumps(spatial_metadata)
            resource_data['spatial_metadata'] = spatial_metadata
        if spatial_metadata_iso_19115:
            #log.debug('saving ISO 19115 metadata')
            #log.debug(spatial_metadata_iso_19115)
            spatial_metadata_iso_19115 = json.dumps(spatial_metadata_iso_19115)
            resource_data['spatial_metadata_iso_19115'] = spatial_metadata_iso_19115
        if spatial_metadata or spatial_metadata_iso_19115:
            #log.debug(t.get_action('get_site_user')({'ignore_auth': True})['name'])
            # save in resource's 'spatial_metadata' and 'spatial_metadata_iso_19115' scheming fields
            context = {'ignore_auth': True, 'user': t.get_action('get_site_user')({'ignore_auth': True})['name'], '_save_shapefile_metadata': True}
            t.get_action('resource_patch')(context, resource_data)
            log.debug('SUCCESS: saved "spatial_metadata" / "spatial_metadata_iso_19115" resource field')
    except Exception as e:
        log.error(e)


def convert_shpz_shapefile(resource):
    """Read a zipped shapefile resource and remove the Z/M-values if it is a PointZ/M, PolyLineZ/M, PolygonZ/M, or MultiPointZ/M.

    Args:
        resource: a resource dict object.

    The original resource file upload is replaced with the converted shapefile. The Z/M-values need to be removed since
    CKAN's ckanext-geoview SHP viewer does not support shapefiles with Z/M-values.
    """
    log.debug('>>>>>>> convert_shpz_shapefile')

    import ckan.lib.uploader as uploader
    import zipfile
    import tempfile
    import glob
    import os
    import shapefile
    import shutil
    import cgi

    SHP_POINT = 1
    SHP_POLYLINE = 3
    SHP_POLYGON = 5
    SHP_MULTIPOINT = 8
    SHP_POINTZ = 11
    SHP_POLYLINEZ = 13
    SHP_POLYGONZ = 15
    SHP_MULTIPOINTZ = 18
    SHP_POINTM = 21
    SHP_POLYLINEM = 23
    SHP_POLYGONM = 25
    SHP_MULTIPOINTM = 28
    SHP_MAP_Z_TO_NORMAL = {
        SHP_POINTZ: SHP_POINT,
        SHP_POLYLINEZ: SHP_POLYLINE,
        SHP_POLYGONZ: SHP_POLYGON,
        SHP_MULTIPOINTZ: SHP_MULTIPOINT,
        SHP_POINTM: SHP_POINT,
        SHP_POLYLINEM: SHP_POLYLINE,
        SHP_POLYGONM: SHP_POLYGON,
        SHP_MULTIPOINTM: SHP_MULTIPOINT
    }

    try:
        resource_file = None
        if resource.get(u'url_type') == u'upload':
            upload = uploader.get_resource_uploader(resource)
            if isinstance(upload, uploader.ResourceUpload):
                resource_file = upload.get_path(resource[u'id'])
        # a converted shapefile will have 'shapefile converted from' substring in its description
        shapefile_already_converted = False
        if 'shapefile converted' in resource[u'description']:
            shapefile_already_converted = True
        # do not reprocess shapefiles that are already converted
        # 20200929 remove shapefile_already_converted check since it blocks converting when a resource file is replaced
        #if resource_file and not shapefile_already_converted:
        if resource_file:
            with zipfile.ZipFile(resource_file, 'r') as zip_input:
                temp_extract_dir = tempfile.mkdtemp()
                # Extract all the contents of zip file to temporary directory
                zip_input.extractall(temp_extract_dir)
                shp_extracted_path = glob.glob(os.path.join(temp_extract_dir, '*.shp'))
                # process if there is only 1 shp file extracted from the zip
                if shp_extracted_path and len(shp_extracted_path) == 1:
                    shp_read = shapefile.Reader(shp_extracted_path[0])
                    output_shp_filename = os.path.basename(shp_extracted_path[0])
                    if shp_read.shapeType in SHP_MAP_Z_TO_NORMAL.keys():
                        log.debug('CONVERTING: "{}" shapefile from Z/M type to normal shapefile'.format(output_shp_filename))
                        temp_output_dir = os.path.join(temp_extract_dir, 'converted')
                        shp_write = shapefile.Writer(os.path.join(temp_output_dir, output_shp_filename))
                        original_shapetype = shp_read.shapeTypeName
                        # convert z shapefiles to non z type, also m shapefiles
                        if shp_read.shapeType == SHP_POINTZ:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_POINTZ]
                        elif shp_read.shapeType == SHP_POLYLINEZ:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_POLYLINEZ]
                        elif shp_read.shapeType == SHP_POLYGONZ:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_POLYGONZ]
                        elif shp_read.shapeType == SHP_MULTIPOINTZ:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_MULTIPOINTZ]
                        elif shp_read.shapeType == SHP_POINTM:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_POINTM]
                        elif shp_read.shapeType == SHP_POLYLINEM:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_POLYLINEM]
                        elif shp_read.shapeType == SHP_POLYGONM:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_POLYGONM]
                        elif shp_read.shapeType == SHP_MULTIPOINTM:
                            shp_write.shapeType = SHP_MAP_Z_TO_NORMAL[SHP_MULTIPOINTM]
                        new_shapetype = shp_write.shapeTypeName
                        # copy shapefile
                        shp_write.fields = shp_read.fields[1:]
                        for shp_record in shp_read.iterShapeRecords():
                            # also update the shapeType of each shape record
                            shp_record.shape.shapeType = shp_write.shapeType
                            shp_write.record(*shp_record.record)
                            shp_write.shape(shp_record.shape)
                        shp_write.close()
                        shp_read.close()
                        # copy all extracted files except shp, shx, and dbf to output directory
                        extracted_all = glob.glob(os.path.join(temp_extract_dir, '*.*'))
                        extracted_shp = glob.glob(os.path.join(temp_extract_dir, '*.shp'))
                        extracted_dbf = glob.glob(os.path.join(temp_extract_dir, '*.dbf'))
                        extracted_shx = glob.glob(os.path.join(temp_extract_dir, '*.shx'))
                        files_to_copy = list(set(extracted_all) - set(extracted_shp) - set(extracted_dbf) - set(extracted_shx))
                        for file_to_copy in files_to_copy:
                            shutil.copy2(file_to_copy, temp_output_dir)
                        # finally zip the output files
                        files_to_zip = glob.glob(os.path.join(temp_output_dir, '*.*'))
                        output_zip_shp_path = os.path.join(temp_output_dir, os.path.basename(resource[u'url']))
                        if os.path.isfile(output_zip_shp_path):
                            log.debug('ERROR: output zip file "{}" already exists'.format(output_zip_shp_path))
                        else:
                            # max zip compression level
                            with zipfile.ZipFile(output_zip_shp_path, 'w', zipfile.ZIP_DEFLATED, 9) as zip_output:
                                # Add files to the zip
                                for file_to_zip in files_to_zip:
                                    zip_output.write(file_to_zip, os.path.basename(file_to_zip))
                            context = {'ignore_auth': True, 'user': t.get_action('get_site_user')({'ignore_auth': True})['name'], '_convert_shpz_shapefile': True}
                            # create a resource file copy of the original PointZ/M, PolyLineZ/M, PolygonZ/M, MultiPointZ/M upload but in zip format
                            with open(resource_file, 'rb') as finput:
                                upload = cgi.FieldStorage()
                                #upload.filename = getattr(finput, 'name', 'data')
                                upload.filename = os.path.basename(resource[u'url']) # use original upload filename
                                upload.file = finput
                                resource_data = {
                                    'package_id': resource[u'package_id'],
                                    'name': resource[u'name'],
                                    'description': '{} (original {} shapefile)'.format(resource[u'description'], original_shapetype),
                                    'upload': upload
                                }
                                t.get_action('resource_create')(context, resource_data)
                            # replace uploaded original resource file
                            with open(output_zip_shp_path, 'rb') as foutput:
                                upload = cgi.FieldStorage()
                                upload.filename = getattr(foutput, 'name', 'data')
                                upload.file = foutput
                                resource_data = {
                                    'id': resource[u'id'],
                                    'description': '{} (shapefile converted from {} to {})'.format(resource[u'description'], original_shapetype, new_shapetype),
                                    'upload': upload
                                }
                                t.get_action('resource_patch')(context, resource_data)
                            log.debug('SUCCESS: converted "{}" shapefile from Z/M type to normal shapefile'.format(output_shp_filename))
                    else:
                        log.debug('ERROR: "{}" shapefile is not a Z/M type'.format(output_shp_filename))
                else:
                    log.debug('ERROR: found more than 1 .shp file extracted in "{}"'.format(temp_extract_dir))
                # finally delete the temp_extract_dir
                try:
                    if os.path.exists(temp_extract_dir):
                        shutil.rmtree(temp_extract_dir)
                except Exception as e:
                    log.error(e)
    except Exception as e:
        log.error(e)
