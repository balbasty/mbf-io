# mbf-io
Tools to parse microbrightfield model files


## API

### MicroBrightfield's XML format

```python
mbfio.xml.parse_stereo(fileobj, dtype=None, space='mbf', unit='um', image=0)
"""
Parse a MBF XML file and extract stereology into a JSON

Parameters
----------
fileobj : str or file-like
    Path (or reader) to an XML file, or a pre-loaded XML file.
dtype : np.dtype
    Datatype to use for the coordinates array. (default: float64)
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
```

```python
mbfio.xml.parse_stereo_markers(fileobj, dtype=None, space='mbf', unit='um', image=0)
"""
Parse a MBF XML file and extract stereology markers into a JSON

Parameters
----------
fileobj : str or file-like
    Path (or reader) to an XML file, or a pre-loaded XML file.
dtype : np.dtype
    Datatype to use for the coordinates array. (default: float64)
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
```

```python
mbfio.xml.parse_sites(fileobj, dtype=None, space='mbf', unit='um', image=0)
"""
Parse a MBF XML file and extract site contours into a JSON

Parameters
----------
fileobj : str or file-like
    Path (or reader) to an XML file, or a pre-loaded XML file.
dtype : np.dtype
    Datatype to use for the coordinates array. (default: float64)
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
```

```python
mbfio.xml.parse_contours(fileobj, exclude_keys=SITE_KEYS, include_keys=None,
                         dtype=None, space='mbf', unit='um', image=0)
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
dtype : np.dtype
    Datatype to use for the coordinates array. (default: float64)
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
```

### MicroBrightfield's ASC format

```python
cmlio.asc.parse_contours(fileobj)
"""
Parse a MicroBrightField asc file that contains vertices of closed
regions of interest.

Parameters
----------
fileobj : str
    Path to the file

Returns
-------
asc : {
    'description': str,
    'regions': {str: int}                 # Region Name / ID
    'sections': {
        str: {                            # Section ID (S1, S2, ...)
            'name': str,                  # Section name (Section 1, ...)
            'top': float,                 # z-coord of the section top (um)
            'cutthickness': float,        # section thickness when cut (um)
            'mountedthickness': float,    # section thickness when mounted (um)
            'contours': [{
                'name':   str,            # ROI name
                'closed': bool,           # First point is last point
                'color':  str,            # Color to use for display
                'points': array,          # (Np, 3) [x, y, z] coordinates
            }],
        }
    }
}
    Dictionary with parsed ROIs.
    All coordinates are in MBF space.

"""
```

### MicroBrightField's Text format


```python
mbfio.txt.parse_markers(fname, split_groups=False)
"""
Parse marker coordinates file into freesurfer-compatible json format

!!! warning "Function likely to change soon"

    I will very probably change this function so that it returns
    a simple array of MBF coordinates, and move the conversion to
    FreeSurfer's format to a different utility.

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
```
