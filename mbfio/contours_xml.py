import numpy as np
from .xml import parse_simple


SITE_KEYS = ('TopRight', 'LeftBottom')


def parse_contours(fileobj, exclude_keys=SITE_KEYS, include_keys=None, dtype=None):
    """
    Parse a MBF XML file and extract contours into a JSON

    !!! note
        - Only true contours are returned (not Circles or Boxes)

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.
    exclude_keys : list[str]
        Skip these contours
        (default: contours encoding stereoloical counting sites)
    include_keys : list[str]
        Only parse these contours
    dtype : np.dtype
        Datatype to use for the coordinates array. (default: float64)

    Returns
    -------
    contours : list[{
        'name':   str,      # ROI name
        'closed': bool,     # First point is last point
        'color':  str,      # Color to use for display
        'points': array,    # (N, 4) [x, y, z, d] coordinates
        'sid':    str,      # Section ID: S1, S2, ..., SN
    }]
    """
    if not isinstance(fileobj, dict):
        fileobj = parse_simple(fileobj)
    obj = fileobj

    if isinstance(exclude_keys, str):
        exclude_keys = [exclude_keys]
    if isinstance(include_keys, str):
        include_keys = [include_keys]

    contours = []
    for contour in obj['contour']:
        name = contour['@name']
        if include_keys and name not in include_keys:
            continue
        if exclude_keys and name in exclude_keys:
            continue
        if contour['@shape'] != 'Contour':
            continue
        points = np.asarray(
            [_get_point(p) for p in contour['point']],
            dtype=dtype
        )
        contours.append({
            'name': name,
            'closed': contour['@closed'],
            'color': contour['@color'],
            'resolution': contour['resolution'],
            'sid': contour['point'][0].get('@sid', None),
            'points': points,
        })
    return contours


def parse_sites(fileobj, dtype=None):
    """
    Parse a MBF XML file and extract site contours into a JSON

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.
    dtype : np.dtype
        Datatype to use for the coordinates array. (default: float64)

    Returns
    -------
    sites : {
        <sid>: {
            # MBF native encoding
            'TopRight': array,      # (Ns, 3, 4) [x, y, z, d] coordinates
            'LeftBottom': array,    # (Ns, 4, 4) [x, y, z, d] coordinates
            # derived metrics,
            'grid': array,          # (Ns, 2) coordinate in the site grid
            'center': array,        # (Ns, 4) [x, y, z, d] coordinates
            'area': array,          # (Ns,) site area
            'corners': array,       # (Ns, 4, 4) [x, y, z, d] coordinates
        },
    }
    """
    if not isinstance(fileobj, dict):
        fileobj = parse_simple(fileobj)
    obj = fileobj

    sites = {}

    # get all native coordinates
    for contour in obj['contour']:
        name = contour['@name']
        if name not in SITE_KEYS:
            continue
        sid = contour['point'][0]['@sid']
        sites.setdefault(sid, {'TopRight': [], 'LeftBottom': []})
        points = np.asarray(
            [_get_point(p) for p in contour['point']],
            dtype=dtype
        )
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


def parse_stereo_markers(fileobj, dtype=None):
    """
    Parse a MBF XML file and extract stereology markers into a JSON

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.
    dtype : np.dtype
        Datatype to use for the coordinates array. (default: float64)

    Returns
    -------
    markers : {
        'coord': array,         # (Nm, 4) [x, y, z, d] coordinates
        'site': array,          # (Nm, 2) grid index of each marker's site
    }
    """
    if not isinstance(fileobj, dict):
        fileobj = parse_simple(fileobj)
    obj = fileobj

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
        point = _get_point(marker['point'][0])
        markers[sid]['coord'].append(point)

    # concatenate
    for sid in markers:
        markers[sid]['coord'] = np.asarray(markers[sid]['coord'], dtype=dtype)
        markers[sid]['site'] = np.asarray(markers[sid]['site'])

    return markers


def parse_stereo(fileobj, dtype=None):
    """
    Parse a MBF XML file and extract stereology into a JSON

    Parameters
    ----------
    fileobj : str or file-like
        Path (or reader) to an XML file, or a pre-loaded XML file.
    dtype : np.dtype
        Datatype to use for the coordinates array. (default: float64)

    Returns
    -------
    rois : {<rid>: str}
    info : {
        <sid>: {
            'contours': [{
                'name':   str,      # ROI name
                'closed': bool,     # First point is last point
                'color':  str,      # Color to use for display
                'points': array,    # (Np, 4) [x, y, z, d] coordinates
            }],
            'sites': {
                # MBF native encoding
                'TopRight': array,      # (Ns, 3, 4) [x, y, z, d] coordinates
                'LeftBottom': array,    # (Ns, 4, 4) [x, y, z, d] coordinates
                # derived metrics,
                'grid_coord': array,    # (Ns, 2) coordinate in the site grid
                'center': array,        # (Ns, 4) [x, y, z, d] coordinates
                'area': array,          # (Ns,) site area
                'corners': array,       # (Ns, 4, 4) [x, y, z, d] coordinates
                'roi': array[int],      # (Ns,) roi_id of each site
            },
            'markers': {
                'coord': array,         # (Nm, 4) [x, y, z, d] coordinates
                'site': array,          # (Nm,) site_id of each marker
            },
        }
    }

    """
    if not isinstance(fileobj, dict):
        fileobj = parse_simple(fileobj)
    obj = fileobj

    rois = {}
    info = {}

    # 1) Parse ROI contours
    contours = parse_contours(obj, dtype=dtype)
    for contour in contours:
        sid = contour.pop('sid')
        roi = contour.pop('name')
        rois.setdefault(roi, 1 + len(rois))
        info.setdefault(sid, {})
        info[sid].setdefault('contours', [])
        info[sid]['contours'].append(contour)

    # 2) Parse sites
    sites = parse_sites(obj, dtype=dtype)
    for sid, subsites in sites.items():
        info.setdefault(sid, {})
        info[sid]['sites'] = subsites

    # 3) Parse markers
    markers = parse_stereo_markers(obj, dtype=dtype)
    for sid, markers in sites.items():
        info.setdefault(sid, {})
        info[sid]['markers'] = markers

    return rois, info


def _vmax_to_dtype(vmax):
    if vmax < 2**8:
        itype = np.uint8
    elif vmax < 2**16:
        itype = np.uint16
    elif vmax < 2**32:
        itype = np.uint32
    elif vmax < 2**64:
        itype = np.uint64
    else:
        itype = np.uint128
    return itype


def _get_point(point):
    dims = ['@x', '@y', '@z', '@d']
    return list(map(float, [point[d] for d in dims]))
