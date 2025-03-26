from datetime import datetime


def from_str_to_datetime(str_datetime: str, date_format="%Y-%m-%dT%H:%M:%S.%fZ"):
    """
    Convert input str to datetime

    @param str_datetime
    @param date_format
    """
    try:
        if not str_datetime:
            return None
        if date_format is None:
            return datetime.fromisoformat(str_datetime)
        return datetime.strptime(str_datetime, date_format)
    except ValueError:
        # if there is issue with date parsing, it should not be blocker for processing of whatever data.
        # Simple return None value
        return None


def from_datetime_to_str(obj_datetime: datetime, date_format="%Y-%m-%dT%H:%M:%S.%fZ"):
    """
    Convert input str to datetime
    """
    if not obj_datetime:
        return None
    if date_format is None:
        return obj_datetime.isoformat()
    return obj_datetime.strftime(date_format)[:-4] + 'Z'


def from_datetime_to_standard_no_timezone_str(obj_datetime: datetime):
    """
    Convert datetime to iso format str
    """
    return obj_datetime.strftime("%Y-%m-%d %H:%M:%S")


def from_isoformat_str_to_custom_date_format(str_iso_datetime: str, date_format="%Y-%m-%d %H:%M:%S"):
    """
    Convert str isoformat datetime to another str datetime but with different format
    """
    obj_datetime = from_str_to_datetime(str_iso_datetime)
    return obj_datetime.strftime(date_format)