__all__ = [
    'parse',
    'parse_contours',
    'parse_sites',
    'parse_stereo_markers',
    'parse_stereo',
]
import numpy as np
from .xml_base import parse
from .utils import make_vox2mbf, convert_unit, convert_unit_


SITE_KEYS = ('TopRight', 'LeftBottom')

def parse_contours(fileobj, exclude_keys=SITE_KEYS, include_keys=None,
                   space='mbf', unit='um', image=0):
    """
    Parse a MBF XML file and extract contours into a JSON

    !!! note "Only true contours are returned (not Circles or Boxes)"

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.
    exclude_keys : list[str]
        Skip these contours
        (default: contours encoding stereoloical counting sites)
    include_keys : list[str]
        Only parse these contours

    Other Parameters
    ----------------
    space : {'mbf', 'voxel'}
        Whether to keep point coordinates in MBF's coordinate system
        ([+x, -y, -z] with origin at corner of top-left voxel) or to
        convert them to voxel space ([+i, +j, +k] with origin at
        center of top-left voxel)
    unit : {'voxel', 'mm', 'um'}
        Convert point coordinates to this unit.
    image : int or str
        Image used to convert MBF coordinates to voxel coordinates
        (Index or name)

    Returns
    -------
    contours : list[{
        'name':   str,      # ROI name
        'closed': bool,     # First point is last point
        'color':  str,      # Color to use for display
        'points': array,    # (N, 3) [x, y, z] coordinates
        'sid':    str,      # Section ID: S1, S2, ..., SN
    }]
    """
    if isinstance(exclude_keys, str):
        exclude_keys = [exclude_keys]
    if isinstance(include_keys, str):
        include_keys = [include_keys]

    # parse file
    if not isinstance(fileobj, dict):
        fileobj = parse(fileobj)
    obj = fileobj

    vox2mbf = _get_vox2mbf(obj, space, unit, image)

    contours = []
    for contour in obj['contour']:
        name = contour['@name']
        if include_keys and name not in include_keys:
            continue
        if exclude_keys and name in exclude_keys:
            continue
        if contour['@shape'] != 'Contour':
            continue
        points = np.asarray([_get_point(p) for p in contour['point']])
        points = _convert_coord(points, vox2mbf, space, unit)

        contours.append({
            'name': name,
            'closed': contour['@closed'],
            'color': contour['@color'],
            'resolution': float(contour['resolution']),
            'sid': contour['point'][0].get('@sid', None),
            'points': points,
        })
    return contours


def parse_sites(fileobj, space='mbf', unit='um', image=0):
    """
    Parse a MBF XML file and extract site contours into a JSON

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.

    Other Parameters
    ----------------
    space : {'mbf', 'voxel'}
        Whether to keep point coordinates in MBF's coordinate system
        ([+x, -y, -z] with origin at corner of top-left voxel) or to
        convert them to voxel space ([+i, +j, +k] with origin at
        center of top-left voxel)
    unit : {'voxel', 'mm', 'um'}
        Convert point coordinates to this unit.
    image : int or str
        Image used to convert MBF coordinates to voxel coordinates
        (Index or name)

    Returns
    -------
    sites : {
        <sid>: {
            # MBF native encoding
            'TopRight': array,      # (Ns, 3, 3) [x, y, z] coordinates
            'LeftBottom': array,    # (Ns, 4, 3) [x, y, z] coordinates
            # derived metrics,
            'grid': array,          # (Ns, 2) coordinate in the site grid
            'center': array,        # (Ns, 3) [x, y, z] coordinates
            'area': array,          # (Ns,) site area
            'corners': array,       # (Ns, 4, 3) [x, y, z] coordinates
        },
    }
    """
    if not isinstance(fileobj, dict):
        fileobj = parse(fileobj)
    obj = fileobj

    vox2mbf = _get_vox2mbf(obj, space, unit, image)

    sites = {}

    # get all native coordinates
    for contour in obj['contour']:
        name = contour['@name']
        if name not in SITE_KEYS:
            continue
        sid = contour['point'][0]['@sid']
        sites.setdefault(sid, {'TopRight': [], 'LeftBottom': []})
        points = np.asarray([_get_point(p) for p in contour['point']])
        points = _convert_coord(points, vox2mbf, space, unit)
        sites[sid][name].append(points)

    for sid in sites:

        # stack
        sites[sid] = {
            'TopRight': np.stack(sites[sid]['TopRight']),
            'LeftBottom': np.stack(sites[sid]['LeftBottom']),
        }
        site = sites[sid]

        # compute derivatives

        #       ②-------③----❹
        #       |        |
        #       |        |
        #  ❶----①-------❷
        #
        # . filled circles = LeftBottom
        # . empty circles  = TopRight
        # Note that 3 is part of both LeftBottom and TopRight

        corners = np.concatenate([
            site['TopRight'], site['LeftBottom'][:, 1:2]
        ], 1)
        center = corners.mean(1)
        area = np.abs(corners[:, 0, 0] - corners[:, 1, 0]) * \
               np.abs(corners[:, 1, 1] - corners[:, 2, 1])

        # FIXME: not sure about this
        uniq_x = np.unique(corners[:, 0, 0])
        uniq_y = np.unique(corners[:, 0, 1])
        nx, ny = len(uniq_x), len(uniq_y)
        all_x, all_y = 1 + np.arange(nx), 1 + np.arange(ny)
        grid_x = corners[:, 0, 0, None] == uniq_x
        grid_x = all_x[grid_x.nonzero()[-1]]
        grid_y = corners[:, 0, 1, None] == uniq_y
        grid_y = all_y[grid_y.nonzero()[-1]]
        grid = np.stack([grid_x, grid_y], -1)

        site['center'] = center
        site['area'] = area
        site['corners'] = corners
        site['grid'] = grid

    return sites


def parse_stereo_markers(fileobj, space='mbf', unit='um', image=0):
    """
    Parse a MBF XML file and extract stereology markers into a JSON

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.

    Other Parameters
    ----------------
    space : {'mbf', 'voxel'}
        Whether to keep point coordinates in MBF's coordinate system
        ([+x, -y, -z] with origin at corner of top-left voxel) or to
        convert them to voxel space ([+i, +j, +k] with origin at
        center of top-left voxel)
    unit : {'voxel', 'mm', 'um'}
        Convert point coordinates to this unit.
    image : int or str
        Image used to convert MBF coordinates to voxel coordinates
        (Index or name)

    Returns
    -------
    markers : {
        'coord': array,         # (Nm, 3) [x, y, z] coordinates
        'site': array,          # (Nm, 2) grid index of each marker's site
    }
    """
    if not isinstance(fileobj, dict):
        fileobj = parse(fileobj)
    obj = fileobj

    vox2mbf = _get_vox2mbf(obj, space, unit, image)

    markers = {}

    for marker in obj['marker']:
        sid = marker['point'][0]['@sid']
        markers.setdefault(sid, {'coord': [], 'site': []})

        # site coordinate
        i = j = 0
        for property in marker['property']:
            if property['@name'] == 'Site':
                i, j = property['n']
                break
        i, j = int(i), int(j)
        markers[sid]['site'].append([i, j])

        # marker coordinate
        point = np.asarray(_get_point(marker['point'][0]))
        point = _convert_coord(point, vox2mbf, space, unit)

        markers[sid]['coord'].append(point)

    # concatenate
    for sid in markers:
        markers[sid]['coord'] = np.asarray(markers[sid]['coord'])
        markers[sid]['site'] = np.asarray(markers[sid]['site'])

    return markers


def parse_stereo(fileobj, space='mbf', unit='um', image=0):
    """
    Parse a MBF XML file and extract stereology into a JSON

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.

    Other Parameters
    ----------------
    space : {'mbf', 'voxel'}
        Whether to keep point coordinates in MBF's coordinate system
        ([+x, -y, -z] with origin at corner of top-left voxel) or to
        convert them to voxel space ([+i, +j, +k] with origin at
        center of top-left voxel)
    unit : {'voxel', 'mm', 'um'}
        Convert point coordinates to this unit.
    image : int or str
        Image used to convert MBF coordinates to voxel coordinates
        (Index or name)

    Returns
    -------
    info : {
        'description': str,
        'regions' : {<rid>: str},
        'sections' : {
            <sid>: {
                'contours': [{
                    'name':   str,          # ROI name
                    'closed': bool,         # First point is last point
                    'color':  str,          # Color to use for display
                    'points': array,        # (Np, 3) [x, y, z] coordinates
                }],
                'sites': {
                    # MBF native encoding
                    'TopRight': array,      # (Ns, 3, 3) [x, y, z] coordinates
                    'LeftBottom': array,    # (Ns, 4, 3) [x, y, z] coordinates
                    # derived metrics,
                    'grid_coord': array,    # (Ns, 2) coordinate in the site grid
                    'center': array,        # (Ns, 3) [x, y, z] coordinates
                    'area': array,          # (Ns,) site area
                    'corners': array,       # (Ns, 4, 3) [x, y, z] coordinates
                    'roi': array[int],      # (Ns,) roi_id of each site
                },
                'markers': {
                    'coord': array,         # (Nm, 3) [x, y, z] coordinates
                    'site': array,          # (Nm,) site_id of each marker
                },
            }
        }
    }

    """
    if not isinstance(fileobj, dict):
        fileobj = parse(fileobj)
    obj = fileobj

    info = dict(description=obj['description'], regions={}, sections={})
    opt = dict(space=space, unit=unit, image=image)

    # 1) Parse ROI contours
    contours = parse_contours(obj, **opt)
    for contour in contours:
        sid = contour.pop('sid')
        roi = contour.get('name')
        info['regions'].setdefault(roi, 1 + len(info['regions']))
        info['sections'].setdefault(sid, {})
        info['sections'][sid].setdefault('contours', [])
        info['sections'][sid]['contours'].append(contour)

    # 2) Parse sites
    sites = parse_sites(obj, **opt)
    for sid, subsites in sites.items():
        info['sections'].setdefault(sid, {})
        info['sections'][sid]['sites'] = subsites

    # 3) Parse markers
    markers = parse_stereo_markers(obj, **opt)
    for sid, markers in sites.items():
        info['sections'].setdefault(sid, {})
        info['sections'][sid]['markers'] = markers

    return info


def _get_point(point):
    dims = ['@x', '@y', '@z'] # '@d' -> diameter, which we do not use
    return list(map(float, [point[d] for d in dims]))


def _get_vox2mbf(obj, space, unit, image=0, dtype='float64'):
    space, unit = space.lower(), unit.lower()
    vox2mbf = None
    if space[0] == 'v' or unit[0] == 'v':
        imgindex = image
        images = obj['images']['image']
        if isinstance(imgindex, str):
            for image in images:
                if image['filename'].endwith(imgindex):
                    break
            image = None
        else:
            assert isinstance(imgindex, int)
            image = images[imgindex]
        if image is None:
            image = images[0]
        scale = list(map(float, (
            image['scale']['@x'], image['scale']['@y'], image['zspacing']['@z']
        )))
        origin = list(map(float, (
            image['coord']['@x'], image['coord']['@y'], image['coord']['@z']
        )))
        scale = np.asarray(scale, dtype=dtype)
        origin = np.asarray(origin, dtype=dtype)
        vox2mbf = make_vox2mbf(scale, origin)
    return vox2mbf


def _convert_coord(points, vox2mbf, space, unit):
    space, unit = space.lower(), unit.lower()
    mbf2vox = np.linalg.inv(vox2mbf)
    scale = np.abs(np.diag(vox2mbf)[:3])
    if space[0] == 'v':
        points[...] = np.matmul(mbf2vox[:3, :3], points[..., None])[..., 0]
        points += mbf2vox[:3, -1]
        if unit[0] != 'v':
            points *= convert_unit(np.abs(scale), 'um', unit)
    elif unit[0] == 'v':
        points /= np.abs(scale)
    else:
        convert_unit_(points, 'um', unit)
    return points
