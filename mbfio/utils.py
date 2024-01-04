__all__ = [
    'vmax_to_dtype',
    'convert_unit',
    'convert_unit_',
    'get_unit_scale',
    'make_vox2mbf',
]
import numpy as np



def vmax_to_dtype(vmax: int) -> np.dtype:
    """
    Find smallest datatype able to store a given value
    """
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


def make_vox2mbf(scale=1, origin=0):
    """
    Build the voxel-to-MBF affine matrix

    In MBF space:
    * +x maps towards the right of the image
    * +y maps towards the bottom of the image
    * +z maps towards the top of the stack
    * x, y, and z are expressed in micrometers
    * The coordinate of the corner of the top-left voxel is stored in
      the `<coord>` field of the `<image>` tag.

    ```
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
    ```

    The left/right, bottom/left orientation of the data array follows
    (most likely) the TIFF convention. In TIFF:
    * Plane data is stored in row-major (C) order, so the most rapidly
      changing dimension is `i` (or `x` or `left-right`) and the least
      rapidly changing dimension is `j` (or `y` or `top-bottom`).
    * The first element corresponds to the top-left of the image.

    ```
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
    ```

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
    scale = np.asarray(scale)
    origin = np.asarray(origin)
    affine = np.eye(4)
    affine[[0,1, 2], [0, 1, 2]] = scale
    affine[1, 1] *= -1
    affine[:3, -1] = origin + affine[[0,1, 2], [0, 1, 2]] * 0.5
    affine[:2, -1] += affine[[0, 1], [0, 1]] * 0.5
    # x/y origin is corner of voxel but z origin is center of plane (?)
    return affine


def convert_unit(val, src, dst):
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
    src = get_unit_scale(src)
    dst = get_unit_scale(dst)
    return val * (src / dst)


def convert_unit_(val, src, dst):
    """
    Convert between spatial units, in-place

    Parameters
    ----------
    val : array
    src : {'pm', 'nm', 'um', 'mm', 'cm', 'dm', 'm', 'Dm', 'Hm', 'Km'}
    dst : {'pm', 'nm', 'um', 'mm', 'cm', 'dm', 'm', 'Dm', 'Hm', 'Km'}

    Returns
    -------
    val : array
    """
    src = get_unit_scale(src)
    dst = get_unit_scale(dst)
    val *= (src / dst)
    return val


_unit_scale = {
    'pm': 1e-12,
    'nm': 1e-9,
    'um': 1e-6,
    'mm': 1e-3,
    'cm': 1e-2,
    'dm': 1e-1,
    'm': 1,
    'Dm': 1e1,
    'Hm': 1e2,
    'Km': 1e3,
}
_unit_aliases = {
    'pm': ('pico', 'picometer', 'picometre'),
    'nm': ('nano', 'nanometer', 'nanometre'),
    'um': ('micro', 'micrometer', 'micrometre', 'μm'),
    'mm': ('milli', 'millimeter', 'millimetre'),
    'cm': ('centi', 'centimeter', 'centimetre'),
    'dm': ('deci', 'decimeter', 'decimetre'),
    'm': ('meter', 'metre'),
    'Dm': ('deca', 'decameter', 'decametre'),
    'Hm': ('hecto', 'hectometer', 'hectometre'),
    'Km': ('kilo', 'kilometer', 'kilometre'),
}
for key, aliases in _unit_aliases.items():
    for alias in aliases:
        _unit_scale[alias] = _unit_scale[key]


def get_unit_scale(scl: str) -> float:
    return float(_unit_scale.get(scl, scl))
