import six
import logging
from itertools import count


log = logging.getLogger(__name__)


def allowed_users_convert(key, data, errors, context):
    '''Reimplemented from ckanext-privatedatasets
    '''
    #log.debug(data)
    if ('allowed_users',) in data and isinstance(data[('allowed_users',)], list):
        allowed_users = data[('allowed_users',)]
    elif ('allowed_users_str',) in data and isinstance(data[('allowed_users_str',)], six.string_types):
        allowed_users_str = data[('allowed_users_str',)].strip()
        allowed_users = [allowed_user for allowed_user in allowed_users_str.split(',') if allowed_user.strip() != '']
    else:
        allowed_users = None

    if allowed_users is not None:
        current_index = max([int(k[1]) for k in data.keys() if len(k) == 2 and k[0] == key[0]] + [-1])

        if len(allowed_users) == 0:
            data[('allowed_users',)] = []
        else:
            #log.debug('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
            #log.debug(allowed_users)
            data[('allowed_users',)] = allowed_users
            '''
            # when using ckanext-scheming fields for allowed_users_str this loop causes TypeError: 'unicode' object does not support item assignment in dictionaries
            for num, allowed_user in zip(count(current_index + 1), allowed_users):
                log.debug(key[0])
                log.debug(isinstance(key[0], unicode))
                log.debug(allowed_user)
                allowed_user = allowed_user.strip()
                data[(key[0], num)] = allowed_user
            '''
