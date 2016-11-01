import random
import re
import string


def random_string(length):
    return ''.join(
        [random.SystemRandom().choice("{}{}".format(string.ascii_letters, string.digits)) for i in range(length)])


def checkRequiredArguments(opts, parser):
    missing_options = []
    for opt in parser.option_list:
        if re.match(r'^\[REQUIRED\]', opt.help) and eval('opts.' + opt.dest) == None:
            missing_options.extend(opt._long_opts)
    if len(missing_options) > 0:
        parser.error('Missing REQUIRED parameters: ' + str(missing_options))
