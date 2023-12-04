from xml.etree import ElementTree


def read_contours_xml(fname):
    """
    Read contours coordinates from an XML file.
    These files also contain information on the sampling scheme.

    The input file looks like this:
    ```
    <?xml version="1.0" encoding="ISO-8859-1"?>
    <mbf version="4.0" appname="Stereo Investigator Cleared Tissue Edition" appversion="2020.1.1" apprrid="SCR_016788" insrrid="SCR_004314">
    <description><![CDATA[]]></description>
    <filefacts>
      <section sid="S1" name="Section 1" top="-108.9" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S2" name="Section 2" top="-158.4" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S3" name="Section 3" top="-207.9" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S4" name="Section 4" top="-257.4" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S5" name="Section 5" top="-306.9" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S6" name="Section 6" top="-356.4" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S7" name="Section 7" top="-405.9" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S8" name="Section 8" top="-455.4" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S9" name="Section 9" top="-504.9" cutthickness="49.5" mountedthickness="49.5"/>
      <section sid="S10" name="Section 10" top="-554.4" cutthickness="49.5" mountedthickness="49.5"/>
      <sectionmanager currentsection="Section 1" sectioninterval="1" startingsection="1"/>
    </filefacts>
    ...
    ```

    Returns
    -------
    sections : dict
        ```
        {
            <Section ID>: {
                'name': [str] <Section Name>,
                'top': [float] <Z coordinate of top of section>,
                'thickness': [float] <section thickness>
            }
        }
        ```

    contours : dict
        ```
        {
            <ROI Name>: { <Section ID>: [
                {
                    'coord': [ (<x>, <y>, <z>), ... ],
                    <property>: <value>,
                }
            ... ] },
            # "inside" limit
            'TopRight': { <Section ID>: [
                {'coord': [
                    (<x>, <y>, <z>),  # top-left
                    (<x>, <y>, <z>),  # top-right
                    (<x>, <y>, <z>),  # bottom-right
                 ] }
            ... ] },
            # "outside" limit
            'LeftBottom': { <Section ID>: [
                {'coord': [
                    (<x>, <y>, <z>),  # top-left
                    (<x>, <y>, <z>),  # bottom-left
                    (<x>, <y>, <z>),  # right
                    (<x>, <y>, <z>),  # bottom-right
                 ] }
            ... ] },
        }

    markers : list[dict]
        ```
        [{'type': str <type>, 'section': str <section>,
          'site': [int <nx>, int <ny>], 'point', (<x>, <y>, <z>) }, ...]
        ```
    """
    ET = ElementTree
    with open(fname) as file:
        root = ET.parse(file)

    # parse section info
    sections = {}
    for fact in root.iterfind('filefacts'):
        for section in fact.iterfind('section'):
            sid = section.get('sid')
            name = section.get('name')
            top = float(section.get('top'))
            thickness = float(section.get('cutthickness'))
            sections[sid] = dict(name=name, top=top, thickness=thickness)

    # parse contour info
    contours = {}
    for contour in root.iterfind('contour'):
        name = contour.get('name')
        if name not in contours:
            contours[name] = {}

        # parse contour coordinates
        for i, point in enumerate(contour.iterfind('point')):
            sid = point.get('sid')
            if sid not in contours[name]:
                contours[name][sid] = []
            if i == 0:
                contours[name][sid].append({})
                this_contour = contours[name][sid][-1]
                this_contour['coord'] = []
            this_contour['coord'] += [(float(point.get('x')),
                                       float(point.get('y')),
                                       float(point.get('z')))]

        # parse sampling scheme
        for property in contour.iterfind('property'):
            if property.get('name') != 'Stereology':
                continue
            title = None
            values = []
            for elem in property.iter():
                if elem.tag == 'l':
                    if title is not None:
                        this_contour[title] = values
                        title = None
                        values = []
                    for subelem in elem.itertext():
                        title = subelem
                        break
                if elem.tag == 'n':
                    for subelem in elem.itertext():
                        values.append(float(subelem))
                        break

    # parse markers
    markers = []
    for marker in root.iterfind('marker'):
        marker1 = dict()
        marker1['type'] = marker.get('name')
        for property in marker.iterfind('property'):
            if property.get('name') == 'Site':
                values = []
                for elem in property.iter():
                    if elem.tag == 'n':
                        for subelem in elem.itertext():
                            values.append(int(subelem))
                            break
                marker1['site'] = values
        for point in marker.iterfind('point'):
            marker1['point'] = [float(point.get('x')),
                                float(point.get('y')),
                                float(point.get('z'))]
            marker1['section'] = point.get('sid')
        markers.append(marker1)

    return sections, contours, markers
