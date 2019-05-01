import os
from typing import List

#
# get next filename under the [exchange directory]. if there is no folder for filename - the folder will be created
#
def get_next_report_filename(dir, filename_mask):

    filename_mask2 = filename_mask % (dir, 0)

    directory = os.path.dirname(filename_mask2)

    try:
        os.stat(directory)

    except:
        os.mkdir(directory)
        print("New directory created:", directory)

    deals_id = 0
    while os.path.exists(filename_mask % (directory, deals_id)):
        deals_id += 1

    return deals_id


# get next filename in indexed way: if file file.txt exists so the file_0.txt will be created.. and so on
def get_next_filename_index(path):
    path = os.path.expanduser(path)

    # if not os.path.exists(path):
    #     return path

    root, ext = os.path.splitext(os.path.expanduser(path))
    directory = os.path.dirname(root)
    fname = os.path.basename(root)
    candidate = fname+ext
    index = 0
    ls = set(os.listdir(directory))
    while candidate in ls:
            candidate = "{}_{}{}".format(fname,index,ext)
            index += 1
    return os.path.join(directory, candidate)


def dict_value_from_path(src_dict: dict, path: List[str], case_sensitive: bool = False):
    """
    returns the value of dict field specified via "path" in form of  a list of keys. By default the keys are matching
    case insensitive way.

    Example:
    src_dict = {"level1:{"level2":{"level3:value}}}
    list_of_keys = ["level1", "level2", "level3"]

    :param src_dict: dict from where to extract data b
    :param path: list of keys to specify the needed data
    :param case_sensitive: case sensototy flag for matching keys of dict against path entries

    :return: value of a dict branch
    """
    s = src_dict.copy()
    key_upper = dict()
    key = ""

    for p in path:

        if not case_sensitive:
            key_upper_key = {key.upper(): key for key in s.keys()}
            key = key_upper_key[p.upper()] if p.upper() in key_upper_key else None

        else:
            key = p

        try:
            s = s[key]

        except Exception as e:
            s = None
            break

    return s

