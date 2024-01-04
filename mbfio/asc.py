import numpy as np
import re


def parse_contours(fileobj):
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
    if not hasattr(fileobj, 'readline'):
        with open(fileobj, 'r') as f:
            return parse_contours(f)
    f = fileobj

    patterns = {
        int: r'\d+',
        float: r'[\+\-]?\d+\.?\d*(?:[eE][\+\-]?\d+)?',
        str: r'\w+'
    }

    def strip_line(line):
        if line is None:
            return None
        return line.split(';')[0].strip()

    def is_closing(line):
        closed = ')' in line
        if closed:
            closeindex = line.index(')')
            pre = line[:closeindex].rstrip()
            post = line[closeindex+1:].lstrip()
        else:
            pre, post = line, ''
        if not post:
            post = strip_line(f.readline())
        return pre, closed, post

    def parse_section(line):
        p = f'(?P<key>{patterns[str]})\s+"(?P<name>[^"]*)"\s' \
            f'+(?P<z>{patterns[float]})\s+' \
            f'(?P<y>{patterns[float]})\s+' \
            f'(?P<x>{patterns[float]})\s*'
        match = re.match(p, line)
        if match:
            key = match.group('key')
            val = dict(name=match.group('name'),
                       top=float(match.group('x')),
                       cutthickness=float(match.group('y')),
                       mountedthickness=-float(match.group('z')),
                       contours=[])
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
            coord = [float(match.group(name)) for name in 'xyz']
            section = str(match.group('section'))
            return coord, section
        return None, None

    asc = dict(description='', regions={}, sections={})

    line = None
    while True:
        if not line:
            line = f.readline()
            if not line:
                # end of file
                break
        line = strip_line(line)

        if line.startswith('(Description'):
            description, closed, line = is_closing(line[12:].lstrip())
            while True:
                if closed:
                    break
                value, closed, line = is_closing(line)
                description += value
            asc['description'] = description.strip()
            continue

        if line.startswith('(Sections'):
            sections = dict()
            value, closed, line = is_closing(line[9:].lstrip())
            if value:
                key, value = parse_section(value)
                if key:
                    sections[key] = value
            while True:
                if closed:
                    break
                value, closed, line = is_closing(line)
                if value:
                    key, value = parse_section(value)
                    if key:
                        sections[key] = value
            asc['sections'] = sections
            continue

        if line.startswith('("'):
            line = line[2:]
            last = line.index('"')
            name, line = line[:last], line[last+1:].lstrip()
            shape = dict(name=name, closed=False, points=[])
            section = ''
            while True:
                if not line:
                    line = strip_line(f.readline())

                # Read useful properties
                if line.startswith('(Color'):
                    color, closed, line = is_closing(line[7:].lstrip())
                    while True:
                        if closed:
                            break
                        value, closed, line = is_closing(line)
                        color += line
                    shape['color'] = color
                    continue

                # Get rid of properties that we do not care about
                # (we only care about lines that start with a bracket
                # then a number, which are coordinates)
                if line.startswith('(') and strip_line(line[1:])[0] not in '0123456789-':
                    if line.startswith('(Closed'):
                        shape['closed'] = True
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
                    continue

                if ')' in line and '(' not in line:
                    # this is weird
                    break
                value = line[line.index('(')+1:line.index(')')].strip()
                line = line[line.index(')')+1:].strip()
                if not value.startswith(tuple([str(n) for n in range(10)] + ['-'])):
                    continue
                point, section = parse_point(value)
                if point:
                    shape['points'].append(point)

            _, closed, line = is_closing(line)
            while not closed:
                _, closed, line = is_closing(line)

            asc['regions'].setdefault(name, 1 + len(asc['regions']))
            shape['points'] = np.asarray(shape['points'], dtype=np.float64)
            asc['sections'][section]['contours'].append(shape)
            continue

        if line.startswith('('):
            _, closed, line = is_closing(line[1:].lstrip())
            while True:
                if closed:
                    break
                _, closed, line = is_closing(line)

    return asc
