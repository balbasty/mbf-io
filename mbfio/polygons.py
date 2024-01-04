__all__ = ['rasterize', 'is_inside']
import numpy as np
try:
    from jitfields.distance import mesh_sdt
    import torch
except (ImportError, ModuleNotFoundError):
    mesh_sdt = torch = None


def rasterize(shape, vertices, faces=None):
    """Rasterize the interior of a polygon or surface.

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
    indices = np.indices(shape, dtype=vertices.dtype)
    return is_inside(indices, vertices, faces)


def is_inside(points, vertices, faces=None):
    """Test if a (batch of) point is inside a polygon or surface.

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
    points = np.asarray(points)
    vertices = np.asarray(vertices)
    if faces is None:
        faces = [(i, i+1) for i in range(len(vertices)-1)]
        faces += [(len(vertices)-1, 0)]
        faces = np.asarray(faces, dtype='int64')

    if mesh_sdt:
        torch_points = torch.as_tensor(points)
        torch_vertices = torch.as_tensor(vertices, dtype=torch_points.dtype)
        torch_faces = torch.as_tensor(faces, dtype=torch.long)
        mask = mesh_sdt(torch_points, torch_vertices, torch_faces) > 0
        return mask.numpy()
    else:
        return is_inside_slow(points, vertices, faces)


def is_inside_slow(points, vertices, faces=None):
    # This function uses a ray-tracing technique:
    #
    #   A half-line is started in each point. If it crosses an even
    #   number of faces, it is inside the shape. If it crosses an even
    #   number of faces, it is not.
    #
    #   In practice, we loop through faces (as we expect there are much
    #   less vertices than voxels) and compute intersection points between
    #   all lines and each face in a batched fashion. We only want to
    #   send these rays in one direction, so we keep aside points whose
    #   intersection have a positive coordinate along the ray.
    batch = points.shape[:-1]
    dim = points.shape[-1]
    if np.issubdtype(points.dtype, np.integer):
        points = points.astype(np.float64)
    eps = np.finfo(points.dtype).resolution
    cross = np.zeros_like(points, shape=batch, dtype='int64')

    ray = np.random.randn(dim).astype(points.dtype)

    for face in faces:
        face = vertices[face]

        # compute normal vector
        origin = face[0]
        if dim == 3:
            u = face[1] - face[0]
            v = face[2] - face[0]
            normal = np.stack([u[1] * v[2] - u[2] * v[1],
                             u[2] * v[0] - u[0] * v[2],
                             u[0] * v[1] - u[1] * v[0]])
        else:
            assert dim == 2
            u = face[1] - face[0]
            normal = np.stack([-u[1], u[0]])

        # check co-linearity between face and ray
        ray_norm = ray / np.linalg.norm(ray)
        normal_norm = normal / np.linalg.norm(normal)
        colinear = np.abs(np.dot(ray_norm, normal_norm)) < eps
        if colinear:
            continue

        # compute intersection between ray and plane
        #   plane: <norm, x - origin> = 0
        #   line: x = p + t*u
        #   => <norm, p + t*u - origin> = 0
        intersection = np.tensordot(normal, points - origin, (-1, -1))
        intersection /= np.dot(normal, ray)
        halfmask = intersection >= 0  # we only want to shoot in one direction
        intersection = intersection[halfmask]
        halfpoints = points[halfmask]
        intersection = intersection[..., None] * (-ray)
        intersection += halfpoints

        # check if the intersection is inside the face
        #   first, we project it onto a frame of dimension `dim-1`
        #   defined by (origin, (u, v))
        intersection -= origin
        if dim == 3:
            interu = np.tensordot(intersection, u, (-1, -1))
            interv = np.tensordot(intersection, v, (-1, -1))
            intersection = (interu >= 0) & (interv > 0) & (interu + interv < 1)
        else:
            intersection = np.tensordot(intersection, u, (-1, -1))
            intersection /= np.dot(u, u)
            intersection = (intersection >= 0) & (intersection < 1)

        cross[halfmask] += intersection

    # check that the number of crossings is even
    cross = (cross & 1) > 0
    return cross
