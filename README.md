# mbf-io
Tools to parse microbrightfield model files

## Installation

```shell
pip install git+https://github.com/balbasty/mbf-io
```

### Fast rasterization

One important use-case of this package is to rasterize MBF contours
(which are in-plane closed polygons) on a regular grid. This is achieved
with the function `mbfio.polygons.rasterize`.
Although we provide a pure python implementation of this function, it is
quite slow. A faster implementation is available in the
[`jitfields`](https://github.com/balbasty/jitfields) package, which gets
installed when the `all` extra tag is used:
```shell
pip install git+https://github.com/balbasty/mbf-io[all]
```

However, `jitfields` depends on `torch` and `cppyy`, which are easier to
install with conda. It is therefore advised to install these dependencies
manually with conda:
```shell
conda install -c balbasty -c conda-forge -c pytorch jitfields cppyy==2 pytorch
pip install git+https://github.com/balbasty/mbf-io[all]
```

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
mbfio.asc.parse_contours(fileobj)
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

### Utilities

```python
mbfio.polygons.rasterize(shape, vertices, faces=None)
"""
Rasterize the interior of a polygon or surface.

The polygon or surface *must* be closed.

Parameters
----------
shape : list[int]
    Shape of the raster grid.
vertices : (nv, dim) array
    Vertex coordinates (in raster space)
faces : (nf, dim) array[int]
    Faces are encoded by the indices of its vertices.
    By default, assume that vertices are ordered and define a closed curve

Returns
-------
mask : (*shape) array[bool]
    Rasterized polygon

"""
```

```python
mbfio.polygons.is_inside(points, vertices, faces=None)
"""
Test if a (batch of) point is inside a polygon or surface.

The polygon or surface *must* be closed.

Parameters
----------
points : (..., dim) array
    Coordinates of points to test
vertices : (nv, dim) array
    Vertex coordinates
faces : (nf, dim) array[int]
    Faces are encoded by the indices of its vertices.
    By default, assume that vertices are ordered and define a closed curve

Returns
-------
check : (...) array[bool]

"""
```

```python
mbfio.utils.make_vox2mbf(scale=1, origin=0)
"""
Build the voxel-to-MBF affine matrix

In MBF space:
* +x maps towards the right of the image
* +y maps towards the bottom of the image
* +z maps towards the top of the stack
* x, y, and z are expressed in micrometers
* The coordinate of the corner of the top-left voxel is stored in
    the `<coord>` field of the `<image>` tag.

            +Y
            ▲
            ┃       X0
-X ━━━━━━━━━╋━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━▶ +X
            ┃       ┆
         Y0 ╂┄┄┄┄┄┄ ┌─────────────┐
            ┃       │             │
            ┃       │    image    │
            ┃       │             │
            ┃       └─────────────┘
            ┃
            -Y

The left/right, bottom/left orientation of the data array follows
(most likely) the TIFF convention. In TIFF:
* Plane data is stored in row-major (C) order, so the most rapidly
    changing dimension is `i` (or `x` or `left-right`) and the least
    rapidly changing dimension is `j` (or `y` or `top-bottom`).
* The first element corresponds to the top-left of the image.

      Top
Left ─┼────┬────┬────┬────┬────┬─▶  Right (+i)
      │ 01 │ 02 │ 03 │ 04 │ 05 │
      ├────┼────┼────┼────┼────┤
      │ 06 │ 07 │ 08 │ 09 │ 10 │
      ├────┼────┼────┼────┼────┤
      │ 11 │ 12 │ 13 │ 14 │ 15 │
      ├────┴────┴────┴────┴────┘
      ▼
      Bottom (+j)

Parameters
----------
scale : [list of] float
    Voxel size along (x, y, z) [== (i, j, k)]
origin : [list of] float
    Origin (x0, y0, z0) of the corner of the top-left voxel in MBF space

Returns
-------
affine : (4, 4) array
    Matrix that maps from voxels (i, j, k) to MBF space (x, y, z)

"""
```

```python
mbfio.utils.convert_unit(val, src, dst)
"""
Convert between spatial units

Parameters
----------
val : scalar or array
src : {'pm', 'nm', 'um', 'mm', 'cm', 'dm', 'm', 'Dm', 'Hm', 'Km'}
dst : {'pm', 'nm', 'um', 'mm', 'cm', 'dm', 'm', 'Dm', 'Hm', 'Km'}

Returns
-------
val : scalar or array
"""
```
