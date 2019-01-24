import math
import re
import time


def re_lmatch(pattern, text):
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None


def current_time():
    return int(math.floor(time.time()))


def parse_input(data, fields):
    error = None
    result = []
    for field in fields:
        arg = ''
        if field == '*' or (field == 'O*' and len(data) > 0):
            arg = data
            if field == '*' and len(arg) < 1:
                error = 'Missing data'
        elif field == 'I' or (field == 'OI' and len(data) > 0):
            arg = lsplit_or_str(data, ' ')
            try:
                arg = int(arg)
            except:
                error = f"Value {arg} should be numeric"
        elif field == 'V' or (field == 'OV' and len(data) > 0):
            arg = lsplit_or_str(data, ' ')
            if field == 'V' and len(arg) < 1:
                error = 'Missing variable'
        elif field[0] == 'V' and len(field) > 1:
            try:
                arg = lsplit_or_str(data, ' ')
                count = field[1:]
                if len(arg) != int(count):
                    error = f"Value {arg} should contain at least {count} characters"
            except:
                arg = "Faulty value"
        elif field == 'B' or (field == 'OB' and len(data) > 0):
            arg = lsplit_or_str(data, ' ')
            try:
                arg = int(arg)
                if arg != 0 and arg != 1:
                    error = f"Value {arg} should be 0 or 1"
            except:
                error = f"Value {arg} should be 0 or 1"
        elif len(data) == 0 and (field == 'OI' or field == 'OV' or field == 'OB' or field == 'O*'):
            arg = ''
        else:
            error = "UNKNOWN INPUT TYPE::" + str(field)
        if len(str(arg)) > 0:
            result.append(arg)
            data = data[len(str(arg)) + 1:]
    if error:
        result = [False, error]
    else:
        result = [True, result]
    return result


def lsplit_or_str(string, stop_char):
    if string.find(stop_char) != -1:
        return string[0:string.find(stop_char)]
    return string
