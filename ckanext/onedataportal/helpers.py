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
    json_dict = {}
    if value:
        try:
            #log.debug(value)
            json_dict = json.loads(value)
        except Exception as e:
            log.warn('Unable to parse JSON string')
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

def is_qgis_metadata(metadata_dict):
    """Check if the metadata dict parsed from QMD XML is QGIS metadata format.
    """
    try:
        if 'qgis' in metadata_dict:
            log.debug('Metadata dict format is QGIS metadata')
            return True
    except Exception as e:
        log.warn('Metadata dict format is unknown')
        return False
    log.debug('Metadata dict format is not QGIS metadata')
    return False

def get_qgis_metadata_field_value(metadata_dict, field_name):
    """Get the value of a QGIS metadata field.
    """
    field_value = None
    try:
        if field_name == 'version':
            field_value = metadata_dict['qgis']['@version']
        elif field_name == 'parentidentifier':
            field_value = metadata_dict['qgis']['parentidentifier']
        elif field_name == 'identifier':
            field_value = metadata_dict['qgis']['identifier']
        elif field_name == 'title':
            field_value = metadata_dict['qgis']['title']
        elif field_name == 'type':
            field_value = metadata_dict['qgis']['type']
        elif field_name == 'language':
            field_value = metadata_dict['qgis']['language']
        elif field_name == 'abstract':
            field_value = metadata_dict['qgis']['abstract']
        elif field_name == 'keywords':
            field_value = metadata_dict['qgis']['keywords']
        elif field_name == 'fees':
            field_value = metadata_dict['qgis']['fees']
        elif field_name == 'license':
            field_value = metadata_dict['qgis']['license']
        elif field_name == 'rights':
            field_value = metadata_dict['qgis']['rights']
        elif field_name == 'constraints':
            field_value = metadata_dict['qgis']['constraints']
        elif field_name == 'constraint_text':
            constraint_dict = metadata_dict
            field_value = constraint_dict['#text']
        elif field_name == 'constraint_type':
            constraint_dict = metadata_dict
            field_value = constraint_dict['@type']
        elif field_name == 'wkt':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['wkt']
        elif field_name == 'proj4':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['proj4']
        elif field_name == 'srsid':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['srsid']
        elif field_name == 'srid':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['srid']
        elif field_name == 'authid':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['authid']
        elif field_name == 'description':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['description']
        elif field_name == 'projectionacronym':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['projectionacronym']
        elif field_name == 'ellipsoidacronym':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['ellipsoidacronym']
        elif field_name == 'geographicflag':
            field_value = metadata_dict['qgis']['crs']['spatialrefsys']['geographicflag']
        elif field_name == 'minx':
            field_value = metadata_dict['qgis']['extent']['spatial']['@minx']
        elif field_name == 'maxx':
            field_value = metadata_dict['qgis']['extent']['spatial']['@maxx']
        elif field_name == 'miny':
            field_value = metadata_dict['qgis']['extent']['spatial']['@miny']
        elif field_name == 'maxy':
            field_value = metadata_dict['qgis']['extent']['spatial']['@maxy']
        elif field_name == 'minz':
            field_value = metadata_dict['qgis']['extent']['spatial']['@minz']
        elif field_name == 'maxz':
            field_value = metadata_dict['qgis']['extent']['spatial']['@maxz']
        elif field_name == 'crs':
            field_value = metadata_dict['qgis']['extent']['spatial']['@crs']
        elif field_name == 'dimensions':
            field_value = metadata_dict['qgis']['extent']['spatial']['@dimensions']
        elif field_name == 'period_start':
            field_value = metadata_dict['qgis']['extent']['temporal']['period']['start']
        elif field_name == 'period_end':
            field_value = metadata_dict['qgis']['extent']['temporal']['period']['end']
        elif field_name == 'contact_name':
            field_value = metadata_dict['qgis']['contact']['name']
        elif field_name == 'contact_organization':
            field_value = metadata_dict['qgis']['contact']['organization']
        elif field_name == 'contact_role':
            field_value = metadata_dict['qgis']['contact']['role']
        elif field_name == 'contact_position':
            field_value = metadata_dict['qgis']['contact']['position']
        elif field_name == 'contact_voice':
            field_value = metadata_dict['qgis']['contact']['voice']
        elif field_name == 'contact_fax':
            field_value = metadata_dict['qgis']['contact']['fax']
        elif field_name == 'contact_email':
            field_value = metadata_dict['qgis']['contact']['email']
        elif field_name == 'contactaddress':
            field_value = metadata_dict['qgis']['contact']['contactAddress']
        elif field_name == 'contactaddress_type':
            contactaddress_dict = metadata_dict
            field_value = contactaddress_dict['type']
        elif field_name == 'contactaddress_address':
            contactaddress_dict = metadata_dict
            field_value = contactaddress_dict['address']
        elif field_name == 'contactaddress_postalcode':
            contactaddress_dict = metadata_dict
            field_value = contactaddress_dict['postalcode']
        elif field_name == 'contactaddress_city':
            contactaddress_dict = metadata_dict
            field_value = contactaddress_dict['city']
        elif field_name == 'contactaddress_administrativearea':
            contactaddress_dict = metadata_dict
            field_value = contactaddress_dict['administrativearea']
        elif field_name == 'contactaddress_country':
            contactaddress_dict = metadata_dict
            field_value = contactaddress_dict['country']
        elif field_name == 'links':
            field_value = metadata_dict['qgis']['links']
        elif field_name == 'link_name':
            link_dict = metadata_dict
            field_value = link_dict['@name']
        elif field_name == 'link_type':
            link_dict = metadata_dict
            field_value = link_dict['@type']
        elif field_name == 'link_url':
            link_dict = metadata_dict
            field_value = link_dict['@url']
        elif field_name == 'link_description':
            link_dict = metadata_dict
            field_value = link_dict['@description']
        elif field_name == 'link_format':
            link_dict = metadata_dict
            field_value = link_dict['@format']
        elif field_name == 'link_mimetype':
            link_dict = metadata_dict
            field_value = link_dict['@mimeType']
        elif field_name == 'link_size':
            link_dict = metadata_dict
            field_value = link_dict['@size']
        elif field_name == 'history':
            field_value = metadata_dict['qgis']['history']
        return field_value
    except Exception as e:
        log.warn('Error reading QGIS metadata dict for field: {}'.format(field_name))
        return None

def is_iso_19115_metadata(metadata_dict):
    """Check if the metadata dict parsed from XML is ISO 19115 metadata format.
    """
    try:
        if 'ISO 19115' in metadata_dict['gmd:MD_Metadata']['gmd:metadataStandardName']['gco:CharacterString']:
            log.debug('Metadata dict format is ISO 19115 metadata')
            return True
    except Exception as e:
        log.warn('Metadata dict format is unknown')
        return False
    log.debug('Metadata dict format is not ISO 19115 metadata')
    return False

def get_iso_19115_metadata_field_value(metadata_dict, field_name):
    """Get the value of a ISO 19115 metadata field.
    """
    field_value = None
    try:
        if field_name == 'fileIdentifier': # identifier
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:fileIdentifier']['gco:CharacterString']
        elif field_name == 'parentIdentifier':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:parentIdentifier']['gco:CharacterString']
        elif field_name == 'title':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:citation']['gmd:CI_Citation']['gmd:title']['gco:CharacterString']
        elif field_name == 'MD_ScopeCode': # type
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:hierarchyLevel']['gmd:MD_ScopeCode']['@codeListValue']
        elif field_name == 'LanguageCode': # language
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:language']['gmd:LanguageCode']['@codeListValue']
        elif field_name == 'topicCategory': # ISO topic categories
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:topicCategory']
        elif field_name == 'topicCategory_code':
            topiccategory_dict = metadata_dict
            field_value = topiccategory_dict['gmd:MD_TopicCategoryCode']
        elif field_name == 'abstract':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:abstract']['gco:CharacterString']
        elif field_name == 'otherConstraints': # license
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:resourceConstraints']['gmd:MD_LegalConstraints']['gmd:otherConstraints']['gco:CharacterString']
        elif field_name == 'referenceSystemInfo': # coordinate reference systems
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:referenceSystemInfo']
        elif field_name == 'referenceSystem_code':
            referencesystem_dict = metadata_dict
            field_value = referencesystem_dict['gmd:MD_ReferenceSystem']['gmd:referenceSystemIdentifier']['gmd:RS_Identifier']['gmd:code']['gco:CharacterString']
        elif field_name == 'northBoundLatitude': # extent north maxy
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:extent']['gmd:EX_Extent']['gmd:geographicElement']['gmd:EX_GeographicBoundingBox']['gmd:northBoundLatitude']['gco:Decimal']
        elif field_name == 'southBoundLatitude': # extent south miny
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:extent']['gmd:EX_Extent']['gmd:geographicElement']['gmd:EX_GeographicBoundingBox']['gmd:southBoundLatitude']['gco:Decimal']
        elif field_name == 'westBoundLongitude': # extent west maxx
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:extent']['gmd:EX_Extent']['gmd:geographicElement']['gmd:EX_GeographicBoundingBox']['gmd:westBoundLongitude']['gco:Decimal']
        elif field_name == 'eastBoundLongitude': # extent east minx
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:extent']['gmd:EX_Extent']['gmd:geographicElement']['gmd:EX_GeographicBoundingBox']['gmd:eastBoundLongitude']['gco:Decimal']
        elif field_name == 'individualName': # contact name
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:pointOfContact']['gmd:CI_ResponsibleParty']['gmd:individualName']['gco:CharacterString']
        elif field_name == 'organisationName': # contact organisation
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:pointOfContact']['gmd:CI_ResponsibleParty']['gmd:organisationName']['gco:CharacterString']
        elif field_name == 'positionName': # contact position
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:pointOfContact']['gmd:CI_ResponsibleParty']['gmd:positionName']['gco:CharacterString']
        elif field_name == 'voice': # contact voice number
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:pointOfContact']['gmd:CI_ResponsibleParty']['gmd:contactInfo']['gmd:CI_Contact']['gmd:phone']['gmd:CI_Telephone']['gmd:voice']['gco:CharacterString']
        elif field_name == 'facsimile': # contact fax number
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:pointOfContact']['gmd:CI_ResponsibleParty']['gmd:contactInfo']['gmd:CI_Contact']['gmd:phone']['gmd:CI_Telephone']['gmd:facsimile']['gco:CharacterString']
        elif field_name == 'address': # contact addresses
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:identificationInfo']['gmd:MD_DataIdentification']['gmd:pointOfContact']['gmd:CI_ResponsibleParty']['gmd:contactInfo']['gmd:CI_Contact']['gmd:address']
        elif field_name == 'address_deliverypoint': # contact address
            address_dict = metadata_dict
            field_value = address_dict['gmd:CI_Address']['gmd:deliveryPoint']['gco:CharacterString']
        elif field_name == 'address_postalcode': # contact address postal code
            address_dict = metadata_dict
            field_value = address_dict['gmd:CI_Address']['gmd:postalCode']['gco:CharacterString']
        elif field_name == 'address_city': # contact address city
            address_dict = metadata_dict
            field_value = address_dict['gmd:CI_Address']['gmd:city']['gco:CharacterString']
        elif field_name == 'address_administrativearea': # contact address administrative area
            address_dict = metadata_dict
            field_value = address_dict['gmd:CI_Address']['gmd:administrativeArea']['gco:CharacterString']
        elif field_name == 'address_country': # contact address country
            address_dict = metadata_dict
            field_value = address_dict['gmd:CI_Address']['gmd:country']['gco:CharacterString']
        elif field_name == 'address_electronicmailaddress': # contact address email
            address_dict = metadata_dict
            field_value = address_dict['gmd:CI_Address']['gmd:electronicMailAddress']['gco:CharacterString']
        elif field_name == 'links':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:transferOptions']['gmd:MD_DigitalTransferOptions']['gmd:onLine']
        elif field_name == 'link_name':
            link_dict = metadata_dict
            field_value = link_dict['gmd:CI_OnlineResource']['gmd:name']['gco:CharacterString']
        elif field_name == 'link_type':
            link_dict = metadata_dict
            field_value = link_dict['gmd:CI_OnlineResource']['gmd:protocol']['gco:CharacterString']
        elif field_name == 'link_url':
            link_dict = metadata_dict
            field_value = link_dict['gmd:CI_OnlineResource']['gmd:linkage']['gmd:URL']
        elif field_name == 'link_description':
            link_dict = metadata_dict
            field_value = link_dict['gmd:CI_OnlineResource']['gmd:description']['gco:CharacterString']
        elif field_name == 'dataQualityInfo':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:dataQualityInfo']
        elif field_name == 'DQ_ScopeCode':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:dataQualityInfo']['gmd:DQ_DataQuality']['gmd:scope']['gmd:DQ_Scope']['gmd:level']['gmd:MD_ScopeCode']['@codeListValue']
        elif field_name == 'DQ_ScopeDescription':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:dataQualityInfo']['gmd:DQ_DataQuality']['gmd:scope']['gmd:DQ_Scope']['gmd:levelDescription']['gmd:MD_ScopeDescription']['gmd:other']['gco:CharacterString']
        elif field_name == 'DQ_LineageStatement':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:dataQualityInfo']['gmd:DQ_DataQuality']['gmd:lineage']['gmd:LI_Lineage']['gmd:statement']['gco:CharacterString']
        elif field_name == 'DQ_Source':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:dataQualityInfo']['gmd:DQ_DataQuality']['gmd:lineage']['gmd:LI_Lineage']['gmd:source']
        elif field_name == 'DQ_Source_Title':
            dq_source_dict = metadata_dict
            field_value = dq_source_dict['gmd:LI_Source']['gmd:sourceCitation']['gmd:CI_Citation']['gmd:title']['gco:CharacterString']
        elif field_name == 'DQ_Source_Description':
            dq_source_dict = metadata_dict
            field_value = dq_source_dict['gmd:LI_Source']['gmd:description']['gco:CharacterString']
        elif field_name == 'DQ_Source_OrganisationName':
            dq_source_dict = metadata_dict
            field_value = dq_source_dict['gmd:LI_Source']['gmd:sourceCitation']['gmd:CI_Citation']['gmd:citedResponsibleParty']['gmd:CI_ResponsibleParty']['gmd:organisationName']['gco:CharacterString']
        elif field_name == 'DQ_Source_Role':
            dq_source_dict = metadata_dict
            field_value = dq_source_dict['gmd:LI_Source']['gmd:sourceCitation']['gmd:CI_Citation']['gmd:citedResponsibleParty']['gmd:CI_ResponsibleParty']['gmd:role']['gmd:CI_RoleCode']['@codeListValue']
        elif field_name == 'DQ_Source_OtherDetails':
            dq_source_dict = metadata_dict
            field_value = dq_source_dict['gmd:LI_Source']['gmd:sourceCitation']['gmd:CI_Citation']['gmd:otherCitationDetails']['gco:CharacterString']
        elif field_name == 'DQ_ProcessStep':
            field_value = metadata_dict['gmd:MD_Metadata']['gmd:dataQualityInfo']['gmd:DQ_DataQuality']['gmd:lineage']['gmd:LI_Lineage']['gmd:processStep']
        elif field_name == 'DQ_ProcessStep_Description':
            dq_processstep_dict = metadata_dict
            field_value = dq_processstep_dict['gmd:LI_ProcessStep']['gmd:description']['gco:CharacterString']
        elif field_name == 'DQ_ProcessStep_DateTime':
            dq_processstep_dict = metadata_dict
            field_value = dq_processstep_dict['gmd:LI_ProcessStep']['gmd:dateTime']['gco:DateTime']
        elif field_name == 'DQ_ProcessStep_OrganisationName':
            dq_processstep_dict = metadata_dict
            field_value = dq_processstep_dict['gmd:LI_ProcessStep']['gmd:processor']['gmd:CI_ResponsibleParty']['gmd:organisationName']['gco:CharacterString']
        elif field_name == 'DQ_ProcessStep_Role':
            dq_processstep_dict = metadata_dict
            field_value = dq_processstep_dict['gmd:LI_ProcessStep']['gmd:processor']['gmd:CI_ResponsibleParty']['gmd:role']['gmd:CI_RoleCode']['@codeListValue']
        return field_value
    except Exception as e:
        log.warn('Error reading ISO 19115 metadata dict for field: {}'.format(field_name))
        return None
