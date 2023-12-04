import os
import xmlschema


def parse_simple(fileobj):
    """
    Parse a MBF XML file as a JSON

    This function uses a XSD 1.1 schema and the `xmlschema` library to
    validate and parse the XML.

    It returns a JSON object, where children elements and attributes
    are saved as (key, value) pairs in a python dictionary, with
    attribute names prepended with a "@".
    Element keys only map to a value if the schema specifies that
    a single instance must exist (minOccurs == maxOccurs == 1).
    Otherwise, element keys map to a list of instances.

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.

    Returns
    -------
    obj : object
        a JSON-like object
    """
    xmlstr = _loadxml(fileobj)
    schema = _get_schema('1.1')
    return schema.to_dict(xmlstr)


class _SCHEMAS:
    FNAMES = {
        '1.0': os.path.join(os.path.dirname(__file__), 'mbf.10.xsd'),
        '1.1': os.path.join(os.path.dirname(__file__), 'mbf.11.xsd')
    }
    VALIDATORS = {}


def _get_schema(version='1.1'):
    if version in _SCHEMAS.VALIDATORS:
        return _SCHEMAS.VALIDATORS[version]
    if version == '1.1':
        XMLSchema = xmlschema.XMLSchema11
    elif version == '1.0':
        XMLSchema = xmlschema.XMLSchema
    else:
        raise ValueError('version must be 1.0 or 1.1')
    validator = XMLSchema(_SCHEMAS.FNAMES[version])
    _SCHEMAS.VALIDATORS[version] = validator
    return validator


def _loadxml(fileobj):
    # if a file -> open it and read it
    if os.path.exists(fileobj):
        with open(fileobj) as f:
            return f.read()
    # if a fileobj -> read it
    if hasattr(fileobj, 'read'):
        return fileobj.read()
    return fileobj
