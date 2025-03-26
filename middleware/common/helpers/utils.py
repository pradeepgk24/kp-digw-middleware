import ast


def convert_str_dict_to_correct_types(dag_instance_parameters: dict = None) -> dict:
    """
    Return dictionary of dag_instance_parameters casted to correct types

    :param dag_instance_parameters: dict with stringed values
    """
    dag_instance_parameters_converted = {}
    for key, value in dag_instance_parameters.items():
        # for safety reason recast is string if anything else was passed
        value = str(value)
        if value.lower() == "true":
            dag_instance_parameters_converted[key] = True
        elif value.lower() == "false":
            dag_instance_parameters_converted[key] = False
        else:
            # if real value is int or dictionary
            try:
                dag_instance_parameters_converted[key] = ast.literal_eval(value)
            # if value was only string and can not be evaluated as int or dictionary, error will be raised
            except (ValueError, SyntaxError):
                dag_instance_parameters_converted[key] = value
    return dag_instance_parameters_converted