import collections.abc


def upsert_obj_key(obj_dict: object, input_dict_keys: list, dict_value, conversion_function=None):
    """
    upsert object key. Check if dict exists and based on that update dict

    :param obj_dict: input dictionary or object with attributes (setters) where all will be stored
    :param input_dict_keys: the keys of input dict
    :param dict_value: the value which will store into input dictionary
    :param conversion_function: conversion function which is call upon the value if it is defined
    """
    actual_key = input_dict_keys.pop(0)
    if len(input_dict_keys) == 0:
        # no key lefts, assign value to leaf and return
        if not _is_attr_empty(dict_value):
            if conversion_function:
                dict_value = conversion_function(dict_value)
            if isinstance(obj_dict, dict):
                obj_dict[actual_key] = dict_value
            else:
                getattr(obj_dict, f"set_{actual_key}")(dict_value)
            return True
        return False

    successful_insert = upsert_obj_key(_get_dict_obj_value(obj_dict, actual_key), input_dict_keys, dict_value,
                                       conversion_function)
    # if at the end there were value which is not valid then remove key from input dict
    if not successful_insert and isinstance(obj_dict, dict) and not obj_dict[actual_key]:
        del obj_dict[actual_key]
    return successful_insert


def _get_dict_obj_value(obj_dict, parameter_key):
    """
    Get value of obj_dict

    :param obj_dict: dictionary or object
    :param parameter_key: key or attr name
    """
    if isinstance(obj_dict, dict):

        if parameter_key not in obj_dict:
            # add new key inside
            obj_dict[parameter_key] = {}
        return obj_dict[parameter_key]
    return getattr(obj_dict, parameter_key)


def map_dict_to_destination(map_config, source_dict, destination_obj, delete_assigned_source_key=False):
    """
    Resolve mapping from one dictionary to another

    :param map_config: configuration of mapping it is tuple with following information
        - on index 0 = source key divided by /
        - on index 1 = destination key divided by /
        - on index 2 = default destination value
        - on index 3 = condition if mapping is needed or not
        - on index 4 - converting function
    :param source_dict: source dict, from where we are taking data
    :param destination_obj: destination dict/object where we are storing data
    :param delete_assigned_source_key: flag indicates if the source key should be deleted or not
    """
    # loop each config
    for map_item in map_config:
        if len(map_item) >= 4 and not map_item[3]:
            # if there is defined condition for mapping and condition is not true then continue with next interation
            continue
        input_dict_keys = map_item[1]
        source_value = source_dict
        source_keys = map_item[0].split("/")
        is_directory_mapping = False
        for source_key in source_keys:
            # check if the value is list and key contains dictionary mapping.
            # something like source_value = [{key1: value1, key2: value2}] and source_key = (key1,key2)
            if isinstance(source_value, list) and source_key.startswith("(") and source_key.endswith(")"):
                # we need to create new value based on destination dictionary mapping
                # give last element of destination key
                is_directory_mapping = True
                destination_key = input_dict_keys.split("/")[-1]
                list_item_mapping = dict(zip(
                    source_key.replace("(", "").replace(")", "").split(","),
                    destination_key.replace("(", "").replace(")", "").split(",")
                ))
                source_value = [{destination_key: source_value_item.get(source_key)
                                 for source_key, destination_key in list_item_mapping.items()}
                                for source_value_item in source_value]
                # remove mapping from destination key
                input_dict_keys = input_dict_keys.replace(f"/{destination_key}", "")
            else:
                source_value = source_value.get(source_key, {}) if source_value else None
        # if value is not there, use default one
        if _is_attr_empty(source_value):
            source_value = map_item[2]
        upsert_obj_key(destination_obj, input_dict_keys.split("/"), source_value,
                       map_item[4] if len(map_item) >= 5 else None)

        if delete_assigned_source_key:
            key_position = 0
            source_dict_to_update = source_dict
            for source_key in source_keys:
                if source_key not in source_dict_to_update:
                    # in case of dummy values ignore removing of assigned values
                    break
                key_position += 1
                if key_position == len(source_keys) or is_directory_mapping:
                    del source_dict_to_update[source_key]
                else:
                    source_dict_to_update = source_dict_to_update[source_key]


def _is_attr_empty(value):
    """
    check if value is empty

    :param value: value to check
    :return: flag indicates if value is empty or not
    """
    if value is None:
        return True
    if isinstance(value, collections.abc.Sized) and len(value) == 0:
        return True
    return False


def name_to_camel_case(name):
    """
    Convert name style to camel case

    :param name:
    :return: converted name style
    """
    return name.replace(" ", "_").lower()
