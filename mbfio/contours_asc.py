from numbers import Number
import re


def read_contours_asc(fname, vx=1):
    """Read a MicroBrightField asc file that contains vertices of
    closed regions of interest.

    The input file looks like this:
    ```
    ;	V3 text file written for MicroBrightField products.

    (Description
    )  ;  End of description
    (Sections S1 "Section 1" -132 49.5 49.5
     S2 "Section 2" -181.5 49.5 49.5
     S3 "Section 3" -231 49.5 49.5
     S4 "Section 4" -280.5 49.5 49.5
     S5 "Section 5" -330 49.5 49.5
     S6 "Section 6" -379.5 49.5 49.5
     S7 "Section 7" -429 49.5 49.5
     S8 "Section 8" -478.5 49.5 49.5
     S9 "Section 9" -528 49.5 49.5
     S10 "Section 10" -577.5 49.5 49.5
    ) ; End of Sections
    ...
    ```

    Parameters
    ----------
    fname : str
        Path to the file
    vx : sequence[float], default=1
        Voxel size

    Returns
    -------
    asc : dict
        Dictionary with parsed ROIs.
        Voxel coordinates are returned

    """

    # NOTE: 27 May 2021
    #   All z coordinates seem to fall between two integers
    #   (say 174.5 instead of 174), so I guess there is a half voxel shift
    #   somewhere. Maybe (0, 0, 0) is the corner of the first voxel instead
    #   of the center? I am now making this assumption and tweaking the code
    #   to add 0.5 in each direction when converting um to vox.

    # ensure vx is a list of length 3
    if isinstance(vx, Number):
        vx = [vx]
    vx = list(vx)
    vx = vx + vx[-1:] * max(0, 3 - len(vx))
    vx = vx[:3]
    # convert units
    vx = [v*1e3 for v in vx]

    patterns = {
        int: r'\d+',
        float: r'[\+\-]?\d+\.?\d*(?:[eE][\+\-]?\d+)?',
        str: r'\w+'
    }

    def strip_line(line):
        return line.split(';')[0].strip()

    def is_closing(line):
        closed = ')' in line
        if closed:
            line = line[:line.index(')')].rstrip()
        return line, closed

    def parse_section(line):
        p = f'(?P<key>{patterns[str]})\s+"(?P<name>[^"]*)"\s' \
            f'+(?P<z>{patterns[float]})\s+' \
            f'(?P<y>{patterns[float]})\s+' \
            f'(?P<x>{patterns[float]})\s*'
        match = re.match(p, line)
        if match:
            key = match.group('key')
            val = dict(name=match.group('name'),
                       x=float(match.group('x'))/vx[0],
                       y=float(match.group('y'))/vx[1],
                       z=-float(match.group('z'))/vx[2])
            return key, val
        else:
            return None, None

    def parse_point(line):
        p = f'(?P<x>{patterns[float]})\s+' \
            f'(?P<y>{patterns[float]})\s+' \
            f'(?P<z>{patterns[float]})\s+' \
            f'(?P<unknown>{patterns[float]})\s+' \
            f'(?P<section>{patterns[str]})\s*'
        match = re.match(p, line)
        if match:
            val = dict(
                x=float(match.group('x'))/vx[0],
                y=-float(match.group('y'))/vx[1],
                z=-float(match.group('z'))/vx[2],
                unknown=float(match.group('unknown')),
                section=str(match.group('section')),
            )
            return val
        return None

    asc = dict(regions=dict())
    with open(fname) as f:

        while True:
            line = f.readline()
            if not line:
                # end of file
                break
            line = strip_line(line)
            if line.startswith('(Description'):
                line, closed = is_closing(line[12:].lstrip())
                description = line
                while True:
                    if closed:
                        break
                    line, closed = is_closing(strip_line(f.readline()))
                    description += line + ''
                asc['description'] = description.strip()
            elif line.startswith('(Sections'):
                sections = dict()
                line, closed = is_closing(line[9:].lstrip())
                if line:
                    key, val = parse_section(line)
                    if key:
                        sections[key] = val
                while True:
                    if closed:
                        break
                    line, closed = is_closing(strip_line(f.readline()))
                    if line:
                        key, val = parse_section(line)
                        if key:
                            sections[key] = val
                asc['sections'] = sections
            elif line.startswith('("'):
                line = line[2:]
                last = line.index('"')
                name = line[:last]
                shape = dict(points=[])
                while True:
                    line = strip_line(f.readline())

                    # Get rid of properties that we do not care about
                    # (we only care about lines that start with a bracket
                    # then a number, which are coordinates)
                    if line.startswith('(') and strip_line(line[1:])[0] not in '0123456789-':
                        line = strip_line(line[1:])
                        if ')' in line:
                            line = line[line.index(')')+1:]
                        else:
                            while True:
                                line = strip_line(f.readline())
                                if ')' in line:
                                    line = line[line.index(')')+1:]
                                    break
                    line = strip_line(line)
                    if not line:
                        continue

                    if ')' in line and '(' not in line:
                        break
                    line = line[line.index('(')+1:line.index(')')].strip()
                    if not line.startswith(tuple([str(n) for n in range(10)] + ['-'])):
                        continue
                    value = parse_point(line)
                    if value:
                        shape['points'].append(value)
                if name not in asc['regions']:
                    asc['regions'][name] = []
                asc['regions'][name].append(shape)
            elif line.startswith('('):
                line, closed = is_closing(line[1:].lstrip())
                while True:
                    if closed:
                        break
                    line, closed = is_closing(strip_line(f.readline()))
    return asc
