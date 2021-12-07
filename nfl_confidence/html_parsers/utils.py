def convert_percent_to_float(percent_str: str):
    assert percent_str[-1] == "%"
    return float(percent_str[:-1])
