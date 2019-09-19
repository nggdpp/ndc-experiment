from bs4 import BeautifulSoup
import requests
import json


# Basic attempt at externalizing the mapping of esoteric source properties to common concepts
property_mapping = {
    "core": {
        "parent_id": "4f4e49dae4b07f02db5e0486",
        "source_identifier": "libno",
        "site_operator": "oper",
        "api_identifier": "apiwel"
    },
    "cutting": {
        "parent_id": "4f4e49d8e4b07f02db5df2d2",
        "source_identifier": "chlibno",
        "site_operator": "operator",
        "api_identifier": "apinum"
    }
}


def make_identifier(crc_record):
    return {
        'type': 'uniqueKey', 
        'scheme': 'CRC Well Catalog Database ID', 
        'key': crc_record["id"]
    }
        


def crcwc_items(sample_type="core", record_count=1000, offset=0):
    if sample_type == "core":
        layer = 0
    elif sample_type == "cutting":
        layer = 1

    params = [
        "where=0%3D0",
        "outFields=*",
        "returnGeometry=true",
        "returnIdsOnly=false",
        "returnCountOnly=false",
        "returnZ=false",
        "returnM=false",
        "returnDistinctValues=false",
        f"resultOffset={offset}",
        f"resultRecordCount={record_count}",
        "returnExtentsOnly=false",
        "f=geojson"
    ]

    ags_url = f"https://my.usgs.gov/arcgis/rest/services/crcwc/crcwc/MapServer/{layer}/query?{'&'.join(params)}"
    
    response = requests.get(ags_url).json()
    
    return response


def extract_crc_data(crcid, sample_type="core"):
    target_schemas = {
        "depth_age_formation": ['Min Depth', 'Max Depth', 'Age', 'Formation'],
        "thin_sections": ['Sequence', 'Min Depth', 'Max Depth', 'View']
    }
    
    url = f"https://my.usgs.gov/crcwc/{sample_type}/report/{crcid}"
    
    r = requests.get(url)
    
    soup = BeautifulSoup(r.content, "html.parser")
    
    data_structures = dict()
    for index, table in enumerate(soup.findAll("table",{"class":"report2"})):
        first_row = table.find("tr")
        labels = [i.text for i in first_row.findAll("td", {"class": "label"})]
        target_data = list(target_schemas.keys())[list(target_schemas.values()).index(labels)]
        data_structures[target_data] = list()

        for row in [r for r in table.findAll("tr")][1:]:
            d_this = dict()
            for i, col in enumerate(row.findAll("td")):
                anchor = col.find("a")
                if anchor:
                    this_data = anchor.get("href")
                else:
                    this_data = col.text
                d_this[labels[i]] = this_data
            data_structures[target_data].append(d_this)

    photos = list()
    documents = list()

    for section in soup.findAll("div",{"class":"report2"}):
        photos.extend(list(set([i.get('href') for i in section.findAll("a",{"title":"see photo"})])))
        documents.extend(list(set([i.get('href') for i in section.findAll("a",{"title":"download analysis document"})])))
        
    if len(photos) > 0:
        data_structures["photos"] = photos
        
    if len(documents) > 0:
        data_structures["documents"] = documents
        
    if not data_structures:
        return None
    else:
        return data_structures


def properties_table(k, v):
    return f"<tr><td>{k}</td><td>{v}</td></tr>"


def crc_title(sample_type, source_identifier):
    return f'Core Research Center {sample_type.capitalize()} {source_identifier}'


def crc_body(sample_type, crc_record, additional_props, macrostrat_info):
    body_string = f'<p>Core Research Center, {sample_type} {crc_record[property_mapping[sample_type]["source_identifier"]]}, from well operated by {crc_record[property_mapping[sample_type]["site_operator"]]}</p>'
    body_string+=f"<h4>Properties from ArcGIS MapServer</h4>"

    body_string+="<div>"
    body_string+=json.dumps(crc_record)
    body_string+="</div>"

    if additional_props is not None:
        body_string+=f"<h4>Properties from Web Page</h4>"
        body_string+="<div>"
        body_string+=json.dumps(additional_props)
        body_string+="</div>"
    
    if macrostrat_info is not None:
        body_string+=f"<h4>Geologic Map Information from Macrostrat</h4>"
        body_string+="<div>"
        body_string+=json.dumps(macrostrat_info)
        body_string+="</div>"

    return body_string


def crc_contacts(site_operator):
    contacts = [
        {
            "name": "Core Research Center",
            "oldPartyId": 17172,
            "type": "Data Owner",
            "contactType": "organization"
        },
        {
            "name": "Jeannine Honey",
            "oldPartyId": 4685,
            "type": "Data Steward",
            "contactType": "person"
        },
        {
            "name": site_operator,
            "type": "Site Operator",
            "contactType": "organization"
        }
    ]
    
    return contacts


def crc_provenance():
    return {"annotation": "Harvested from ArcGIS Server and Core Research Center Web Site"}


def crc_identifiers(identifier, sample_type, crc_record):
    identifiers = [
        {
            "type": "uniqueKey",
            "scheme": "CRC Well Catalog Database ID",
            "key": identifier
        }
    ]
    
    if crc_record[property_mapping[sample_type]["source_identifier"]] is not None:
        identifiers.append({
            "type": "uniqueKey",
            "scheme": "CRC Library Number",
            "key": crc_record[property_mapping[sample_type]["source_identifier"]]
        })

    if crc_record[property_mapping[sample_type]["api_identifier"]] is not None:
        identifiers.append({
            "type": "uniqueKey",
            "scheme": "American Petroleum Institute Number",
            "key": crc_record[property_mapping[sample_type]["api_identifier"]]
        })
    
    return identifiers


def crc_weblinks(sample_type, identifier, extracted_data=None):
    web_links = [
        {
            "type": "webLink",
            "typeLabel": "Web Link",
            "uri": f"https://my.usgs.gov/crcwc/{sample_type}/report/{identifier}",
            "rel": "related",
            "title": "Core Research Center Well Catalog Web Page",
            "hidden": False,
            "itemWebLinkTypeId": "4f4e475de4b07f02db47debf"
        }
    ]
    
    if extracted_data is not None:
        if "documents" in extracted_data.keys():
            for doc_link in extracted_data["documents"]:
                web_links.append(
                    {
                        "type": "download",
                        "typeLabel": "Download",
                        "uri": doc_link,
                        "rel": "related",
                        "title": f"Core Research Center Analysis File {doc_link.split('/')[-1]}",
                        "hidden": False,
                        "itemWebLinkTypeId": "4f4e475de4b07f02db47dec0"
                    }
                )

        if "photos" in extracted_data.keys():
            for doc_link in extracted_data["photos"]:
                web_links.append(
                    {
                        "type": "download",
                        "typeLabel": "Photo",
                        "uri": doc_link,
                        "rel": "related",
                        "title": f"Core Research Center Photo {doc_link.split('/')[-1]}",
                        "hidden": False,
                        "itemWebLinkTypeId": "4f4e475de4b07f02db47dec0"
                    }
                )
    
    return web_links


def crc_location(crc_record):
    spatial = {
        "representationalPoint": crc_record["geometry"]["coordinates"]
    }
    
    return spatial


def crc_tags(macrostrat_info):
    tags = list()
    
    if macrostrat_info["rocktype"][0] is not None:
        for rock_type in macrostrat_info["rocktype"]:
            tags.append(
                {
                    "type": "Theme",
                    "scheme": "Rock Type",
                    "name": rock_type[0:80]
                }
            )
        
    if len(macrostrat_info["age"]) > 0:
        tags.append(
            {
                "type": "Theme",
                "scheme": "Geologic Age",
                "name": macrostrat_info["age"][0:80]
            }
        )

    if len(macrostrat_info["name"]) > 0:
        tags.append(
            {
                "type": "Theme",
                "scheme": "Geologic Formation",
                "name": macrostrat_info["name"][0:80]
            }
        )

    if len(tags) == 0:
        return None
    
    return tags

            
def sb_item_from_crcwc(sample_type, crc_record, additional_props=None, macrostrat_info=None):
    extracted_data = extract_crc_data(crc_record["id"], sample_type)

    if extracted_data is not None and "depth_age_formation" in extracted_data.keys():
        additional_props = extracted_data["depth_age_formation"]

    if isinstance(crc_record["properties"]["lat"], float) and isinstance(crc_record["properties"]["lng"], float):
        macrostrat_info = macrostrat_context(lat=crc_record["properties"]["lat"], lng=crc_record["properties"]["lng"])

    sb_item = {
        "parentId": property_mapping[sample_type]["parent_id"],
        "identifiers": crc_identifiers(crc_record["id"], sample_type, crc_record["properties"]),
        "title": crc_title(sample_type, crc_record["properties"][property_mapping[sample_type]["source_identifier"]]),
        "body": crc_body(sample_type, crc_record["properties"], additional_props, macrostrat_info),
        "contacts": crc_contacts(crc_record["properties"][property_mapping[sample_type]["site_operator"]]),
        "provenance": crc_provenance(),
        "browseCategories": ["Physical Item"],
        "webLinks": crc_weblinks(sample_type, crc_record["id"], extracted_data)
    }
    
    if crc_record["geometry"] is not None:
        sb_item["spatial"] = crc_location(crc_record)
    
    if macrostrat_info is not None:
        item_tags = crc_tags(macrostrat_info)
        if item_tags is not None:
            sb_item["tags"] = item_tags
    
    return sb_item


def macrostrat_context(lat, lng):
    api = f"https://macrostrat.org/api/mobile/point?lat={lat}&lng={lng}"
    
    r = requests.get(api, headers={"accept": "application/json"}).json()
    
    if "success" in r.keys() and "data" in r["success"].keys():
        return r["success"]["data"]
    
    return None