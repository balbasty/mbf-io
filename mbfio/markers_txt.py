from numbers import Number
import re


def read_markers(fname, vx=1e-3, split_groups=False):
    """Read marker coordinates file into freesurfer-compatible json format

    The input file looks like this:
    ```
    ;Marker Coordinate File
    X(um)    Y(um)     Z(um)  Marker Diameter
    1 12108.17 -8056.31  -118.80     1.65
    1 12845.47 -8010.11  -118.80     1.65
    1 12852.07 -7965.56  -118.80     1.65
    1 12804.22 -8008.46  -118.80     1.65
    ...
    ```

    Parameters are returned in voxel space. The image that was used to
    create the coordinates must be known to convert them to some sort of
    RAS space.

    Parameters
    ----------
    fname : str
        Path to marker file
    vx : sequence[float], default=1
        Voxel size
    split_groups : bool, default=False
        If True, return one dictionary per marker type.

    Returns
    -------
    coord : dict (or list of dict)
        A dictionary that can be dumped as json

    """
    patterns = {
        int: r'(\d+)',
        float: r'([\+\-]?\d+\.?\d*(?:[eE][\+\-]?\d+)?)',
        str: r'(.*)\s*$'
    }

    # ensure vx is a list of length 3
    if isinstance(vx, Number):
        vx = [vx]
    vx = list(vx)
    vx = vx + vx[-1:] * max(0, 3 - len(vx))
    vx = vx[:3]

    coordinates = []
    groups = []
    with open(fname) as f:
        f.readline()  # skip first line
        i = 0
        for line in f:
            i += 1
            line = line.rstrip()
            print(f'{i} | {line}', end='\r')
            match = re.search(f'(?P<group>{patterns[int]})\s+'
                              f'(?P<x>{patterns[float]})\s+'
                              f'(?P<y>{patterns[float]})\s+'
                              f'(?P<z>{patterns[float]})\s+'
                              f'(?P<file>{patterns[float]})\s*', line)
            if not match:
                continue
            groups.append(int(match.group('group')))
            coordinates.append([
                float(match.group('x')),
                float(match.group('y')),
                float(match.group('z')),
            ])
    print('')

    pointset = dict()
    pointset['data_type'] = 'fs_pointset'
    pointset['points'] = list()
    for (x, y, z), g in zip(coordinates, groups):
        pointset['points'].append(dict())
        pointset['points'][-1]['coordinates'] = dict(x=+x * 1e-3 / vx[0],
                                                     y=-y * 1e-3 / vx[1],
                                                     z=-z * 1e-3 / vx[2])
        pointset['points'][-1]['legacy_stat'] = 1
        pointset['points'][-1]['statistics'] = dict(group=g)
    pointset['vox2ras'] = 'scanner_ras'  # ?

    if not split_groups:
        return pointset

    all_groups = set(groups)
    subsets = []
    for g in all_groups:
        subset = dict()
        subset['data_type'] = 'fs_pointset'
        subset['points'] = [p for p in pointset['points'] if
                            p['statistics']['group'] == g]
        subset['vox2ras'] = 'scanner_ras'  # ?
        subsets.append(subset)

    return subsets
