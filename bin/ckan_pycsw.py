import sys
import logging
import datetime
import io
import os
import argparse

# from configparser import SafeConfigParser
from configparser import ConfigParser

import requests
from lxml import etree

from pycsw.core import metadata, repository, util
import pycsw.core.config
import pycsw.core.admin

logging.basicConfig(format="%(message)s", level=logging.INFO)

log = logging.getLogger(__name__)


def setup_db(pycsw_config):
    """Setup database tables and indexes"""

    from sqlalchemy import Column, Text

    database = pycsw_config.get("repository", "database")
    # table_name = pycsw_config.get("repository", "table", "records")
    table_name = pycsw_config.get("repository", "table", fallback="records")

    ckan_columns = [
        Column("ckan_id", Text, index=True),
        Column("ckan_modified", Text),
    ]

    pycsw.core.admin.setup_db(
        database,
        table_name,
        "",
        create_plpythonu_functions=False,
        extra_columns=ckan_columns,
    )


def set_keywords(pycsw_config_file, pycsw_config, ckan_url, limit=20):
    """set pycsw service metadata keywords from top limit CKAN tags"""

    log.info("Fetching tags from %s", ckan_url)
    url = ckan_url + "api/tag_counts"
    response = requests.get(url)
    tags = response.json()

    log.info("Deriving top %d tags", limit)
    # uniquify and sort by top limit
    tags_unique = [list(x) for x in set(tuple(x) for x in tags)]
    tags_sorted = sorted(tags_unique, key=lambda x: x[1], reverse=1)[0:limit]
    keywords = ",".join("%s" % tn[0] for tn in tags_sorted)

    log.info("Setting tags in pycsw configuration file %s", pycsw_config_file)
    pycsw_config.set("metadata:main", "identification_keywords", keywords)
    with open(pycsw_config_file, "wb") as configfile:
        pycsw_config.write(configfile)


def load(pycsw_config, ckan_url):

    database = pycsw_config.get("repository", "database")
    # table_name = pycsw_config.get("repository", "table", "records")
    table_name = pycsw_config.get("repository", "table", fallback="records")

    context = pycsw.core.config.StaticContext()
    repo = repository.Repository(database, context, table=table_name)

    log.info(
        "Started gathering CKAN datasets identifiers: {0}".format(
            str(datetime.datetime.now())
        )
    )

    query = 'api/search/dataset?qjson={"fl":"id,metadata_modified,extras_harvest_object_id,extras_metadata_source", "q":"harvest_object_id:[\\"\\" TO *]", "limit":1000, "start":%s}'

    start = 0

    gathered_records = {}

    while True:
        url = ckan_url + query % start

        response = requests.get(url)
        listing = response.json()
        if not isinstance(listing, dict):
            raise RuntimeError("Wrong API response: %s" % listing)
        results = listing.get("results")
        if not results:
            break
        for result in results:
            gathered_records[result["id"]] = {
                "metadata_modified": result["metadata_modified"],
                "harvest_object_id": result["extras"]["harvest_object_id"],
                "source": result["extras"].get("metadata_source"),
            }

        start = start + 1000
        log.debug("Gathered %s" % start)

    log.info(
        "Gather finished ({0} datasets): {1}".format(
            len(gathered_records.keys()), str(datetime.datetime.now())
        )
    )

    existing_records = {}

    query = repo.session.query(repo.dataset.ckan_id, repo.dataset.ckan_modified)
    for row in query:
        existing_records[row[0]] = row[1]
    repo.session.close()

    new = set(gathered_records) - set(existing_records)
    deleted = set(existing_records) - set(gathered_records)
    changed = set()

    for key in set(gathered_records) & set(existing_records):
        if gathered_records[key]["metadata_modified"] > existing_records[key]:
            changed.add(key)

    for ckan_id in deleted:
        try:
            repo.session.begin()
            repo.session.query(repo.dataset.ckan_id).filter_by(ckan_id=ckan_id).delete()
            log.info("Deleted %s" % ckan_id)
            repo.session.commit()
        except Exception:
            repo.session.rollback()
            raise

    for ckan_id in new:
        ckan_info = gathered_records[ckan_id]
        record = get_record(context, repo, ckan_url, ckan_id, ckan_info)
        if not record:
            log.info("Skipped record %s" % ckan_id)
            continue
        try:
            repo.insert(record, "local", util.get_today_and_now())
            log.info("Inserted %s" % ckan_id)
        except Exception as err:
            log.error("ERROR: not inserted %s Error:%s" % (ckan_id, err))

    for ckan_id in changed:
        ckan_info = gathered_records[ckan_id]
        record = get_record(context, repo, ckan_url, ckan_id, ckan_info)
        if not record:
            continue
        update_dict = dict(
            [
                (getattr(repo.dataset, key), getattr(record, key))
                for key in record.__dict__.keys()
                if key != "_sa_instance_state"
            ]
        )
        try:
            repo.session.begin()
            repo.session.query(repo.dataset).filter_by(ckan_id=ckan_id).update(
                update_dict
            )
            repo.session.commit()
            log.info("Changed %s" % ckan_id)
        except Exception as err:
            repo.session.rollback()
            raise RuntimeError("ERROR: %s" % str(err))


def clear(pycsw_config):

    from sqlalchemy import create_engine, MetaData, Table

    database = pycsw_config.get("repository", "database")
    # table_name = pycsw_config.get("repository", "table", "records")
    table_name = pycsw_config.get("repository", "table", fallback="records")

    log.debug("Creating engine")
    engine = create_engine(database)
    records = Table(table_name, MetaData(engine))
    records.delete().execute()
    log.info("Table cleared")


def get_record(context, repo, ckan_url, ckan_id, ckan_info):
    query = ckan_url + "harvest/object/%s"
    url = query % ckan_info["harvest_object_id"]
    response = requests.get(url)

    if ckan_info["source"] == "arcgis":
        return

    try:
        xml = etree.parse(io.BytesIO(response.content))
    except Exception as err:
        log.error("Could not pass xml doc from %s, Error: %s" % (ckan_id, err))
        return

    try:
        record = metadata.parse_record(context, xml, repo)[0]
    except Exception as err:
        log.error("Could not extract metadata from %s, Error: %s" % (ckan_id, err))
        return

    if not record.identifier:
        record.identifier = ckan_id
    record.ckan_id = ckan_id
    record.ckan_modified = ckan_info["metadata_modified"]

    return record


def import_spatial_metadata_to_pycsw(pycsw_config, ckan_url):
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
    log.info(
        "Start importing spatial metadata to pycsw: {}".format(
            str(datetime.datetime.now())
        )
    )
    count_dataset_metadata = 0
    count_resource_metadata = 0
    synced_spatial_formats = {"wms", "wmts", "wfs", "shp", "tif", "tiff"}
    gathered_metadata = {}
    package_list_response = requests.get(ckan_url + "api/action/package_list")
    package_list = package_list_response.json()
    if not isinstance(package_list, dict):
        raise RuntimeError("Wrong API response: {}".format(package_list))
    package_list_result = package_list.get("result")
    for package_id in package_list_result:
        package_show_response = requests.get(
            ckan_url + "api/action/package_show?id={}".format(package_id)
        )
        package = package_show_response.json()
        if not isinstance(package, dict):
            raise RuntimeError("Wrong API response: {}".format(package))
        # print(json.dumps(package, indent=4, sort_keys=True))
        package_result = package.get("result")
        # check if the dataset has ISO 19115 spatial metadata
        package_id = package_result.get("id")
        package_metadata_modified = package_result.get("metadata_modified")
        dataset_spatial_metadata_iso_19115 = package_result.get(
            "spatial_metadata_iso_19115"
        )
        # check if ISO 19115 metadata passes on dataset level
        # TODO
        dataset_spatial_metadata_passes_validation = True
        if dataset_spatial_metadata_iso_19115:
            # ISO 19115 spatial metadata must pass validation to be synced to pycsw
            # dataset_spatial_metadata_passes_validation = validate_iso_19115_metadata(json.loads(dataset_spatial_metadata_iso_19115))
            pass
        # check if resources have ISO 19115 spatial metadata
        for resource in package_result["resources"]:
            resource_format = resource.get("format")
            resource_format = resource_format.lower()
            # only process resource formats that are synced to Oskari + GeoServer
            if resource_format in synced_spatial_formats:
                log.info(
                    "Found matching synced resource format: {}".format(resource_format)
                )
                # print(json.dumps(resource, indent=4, sort_keys=True))
                resource_id = resource.get("id")
                resource_last_modified = resource.get("last_modified")
                resource_spatial_metadata_iso_19115 = resource.get(
                    "spatial_metadata_iso_19115"
                )
                resource_name = resource.get("name")
                resource_description = resource.get("description")
                resource_url = resource.get("url")
                wms_url = resource.get("wms_url")
                wfs_url = resource.get("wfs_url")
                if dataset_spatial_metadata_passes_validation and (wms_url or wfs_url):
                    # spatial resource with separate ISO 19115 spatial metadata on the dataset level
                    gathered_metadata[resource_id] = {
                        #'metadata_modified': resource_last_modified,
                        "metadata_modified": package_metadata_modified,  # use dataset's metadata_modified due to resource last_modified bug https://github.com/ckan/ckan/issues/5190
                        "spatial_metadata_iso_19115": dataset_spatial_metadata_iso_19115,
                        "resource_name": resource_name,
                        "resource_description": resource_description,
                        "resource_url": resource_url,
                        "wms_url": wms_url,
                        "wfs_url": wfs_url,
                    }
                    count_dataset_metadata += 1
                else:
                    # spatial resource with embedded ISO 19115 metadata and either WMS URL or WFS URL
                    if resource_spatial_metadata_iso_19115 and (wms_url or wfs_url):
                        # ISO 19115 spatial metadata must pass validation to be synced to pycsw
                        # TODO
                        resource_spatial_metadata_passes_validation = True
                        # resource_spatial_metadata_passes_validation = validate_iso_19115_metadata(json.loads(resource_spatial_metadata_iso_19115))
                        if resource_spatial_metadata_passes_validation:
                            # use resource id as ckan_id for pycsw record
                            gathered_metadata[resource_id] = {
                                #'metadata_modified': resource_last_modified,
                                "metadata_modified": package_metadata_modified,  # use dataset's metadata_modified due to resource last_modified bug https://github.com/ckan/ckan/issues/5190
                                "spatial_metadata_iso_19115": resource_spatial_metadata_iso_19115,
                                "resource_name": resource_name,
                                "resource_description": resource_description,
                                "resource_url": resource_url,
                                "wms_url": wms_url,
                                "wfs_url": wfs_url,
                            }
                            count_resource_metadata += 1
    # print(json.dumps(gathered_metadata, indent=4, sort_keys=True))
    log.info("============================================================")
    log.info(
        "Finished gathering {0} spatial metadata (that passed validation): {1}".format(
            len(gathered_metadata.keys()), str(datetime.datetime.now())
        )
    )
    log.info("Dataset spatial metadata found: {}".format(count_dataset_metadata))
    log.info("Resource spatial metadata found: {}".format(count_resource_metadata))
    log.info("============================================================")
    pycsw_database = pycsw_config.get("repository", "database")
    pycsw_table = pycsw_config.get("repository", "table", "records")
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
    # print("##############################")
    # print(new, deleted, changed)
    for key in set(gathered_metadata) & set(existing_records):
        if gathered_metadata[key]["metadata_modified"] > existing_records[key]:
            changed.add(key)
    count_records_deleted = count_records_inserted = count_records_updated = 0
    for ckan_id in deleted:
        try:
            repo.session.begin()
            repo.session.query(repo.dataset.ckan_id).filter_by(ckan_id=ckan_id).delete()
            log.info("Deleted {}".format(ckan_id))
            repo.session.commit()
            count_records_deleted += 1
        except Exception as err:
            repo.session.rollback()
            raise
    for ckan_id in new:
        ckan_info = gathered_metadata[ckan_id]
        record = get_record(context, repo, ckan_id, ckan_info)
        if not record:
            log.info("Skipped record {}".format(ckan_id))
            continue
        try:
            repo.insert(record, "local", util.get_today_and_now())
            log.info("Inserted {}".format(ckan_id))
            count_records_inserted += 1
        except Exception as err:
            log.error("ERROR: not inserted {} Error:{}".format(ckan_id, err))
    for ckan_id in changed:
        ckan_info = gathered_metadata[ckan_id]
        record = get_record(context, repo, ckan_id, ckan_info)
        if not record:
            continue
        update_dict = dict(
            [
                (getattr(repo.dataset, key), getattr(record, key))
                for key in record.__dict__.keys()
                if key != "_sa_instance_state"
            ]
        )
        try:
            repo.session.begin()
            repo.session.query(repo.dataset).filter_by(ckan_id=ckan_id).update(
                update_dict
            )
            repo.session.commit()
            log.info("Changed {}".format(ckan_id))
            count_records_updated += 1
        except Exception as err:
            repo.session.rollback()
            raise RuntimeError("ERROR: %s".format(str(err)))
    log.info("============================================================")
    log.info(
        "Finished importing spatial metadata to pycsw: {}".format(
            str(datetime.datetime.now())
        )
    )
    log.info("Spatial metadata records inserted: {}".format(count_records_inserted))
    log.info("Spatial metadata records update: {}".format(count_records_updated))
    log.info("Spatial metadata records deleted: {}".format(count_records_deleted))
    log.info("============================================================")


usage = """
Manages the CKAN-pycsw integration

    python ckan-pycsw.py setup [-p]
        Setups the necessary pycsw table on the db.

    python ckan-pycsw.py set_keywords [-p] -u
        Sets pycsw server metadata keywords from CKAN site tag list.

    python ckan-pycsw.py load [-p] -u
        Loads CKAN datasets as records into the pycsw db.

    python ckan-pycsw.py clear [-p]
        Removes all records from the pycsw table.

All commands require the pycsw configuration file. By default it will try
to find a file called 'default.cfg' in the same directory, but you'll
probably need to provide the actual location via the -p option:

    python ckan_pycsw.py setup -p /etc/ckan/default/pycsw.cfg

The load command requires a CKAN URL from where the datasets will be pulled:

    python ckan_pycsw.py load -p /etc/ckan/default/pycsw.cfg -u http://localhost

"""


def _load_config(file_path):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise AssertionError("pycsw config file {0} does not exist.".format(abs_path))

    # config = SafeConfigParser()
    config = ConfigParser()
    config.read(abs_path)

    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="\n".split(usage)[0], usage=usage)
    parser.add_argument("command", help="Command to perform")

    parser.add_argument(
        "-p",
        "--pycsw_config",
        action="store",
        default="default.cfg",
        help="pycsw config file to use.",
    )

    parser.add_argument(
        "-u",
        "--ckan_url",
        action="store",
        help="CKAN instance to import the datasets from.",
    )

    if len(sys.argv) <= 1:
        parser.print_usage()
        sys.exit(1)

    arg = parser.parse_args()
    pycsw_config = _load_config(arg.pycsw_config)

    if arg.command == "setup":
        setup_db(pycsw_config)
    elif arg.command in ["load", "set_keywords"]:
        if not arg.ckan_url:
            raise AssertionError("You need to provide a CKAN URL with -u or --ckan_url")
        ckan_url = arg.ckan_url.rstrip("/") + "/"
        if arg.command == "load":
            # load(pycsw_config, ckan_url)
            import_spatial_metadata_to_pycsw(pycsw_config, ckan_url)
        else:
            set_keywords(arg.pycsw_config, pycsw_config, ckan_url)
    elif arg.command == "clear":
        clear(pycsw_config)
    else:
        print("Unknown command {0}".format(arg.command))
        sys.exit(1)
