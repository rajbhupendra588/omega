"""High-complexity module — elevated Ω signals."""


def process(items, mode, threshold, callback, extra=None):
    result = []
    for i, item in enumerate(items):
        if mode == "strict":
            if item > threshold:
                if callback:
                    if extra:
                        result.append(callback(item, extra))
                    else:
                        result.append(callback(item))
                else:
                    result.append(item * 2)
        elif mode == "loose":
            for j in range(3):
                if j % 2 == 0 and item > 0:
                    result.append(item + j)
        else:
            while item > 0:
                item -= 1
                result.append(item)
    return result


def legacy_handler(data):
    if data is None:
        return None
    if len(data) == 0:
        return []
    if data[0] == "x":
        return legacy_handler(data[1:])
    return data
