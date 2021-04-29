from argparse import ArgumentParser
from . import __version__ as version
from .usage import UsageAgent
from datetime import datetime


def otumat(args=None):
    parser = ArgumentParser(prog='otumat',
                            description='Otumat console interface.')
    parser.add_argument('-V', '--version', action='version', version=f'Otumat {version}')
    subparsers = parser.add_subparsers(dest='subparser')
    parser_upload = subparsers.add_parser('upload',
                                          description='Upload buffered usage data.')
    parser_upload.add_argument('-a', '--author',
                               type=str,
                               required=True,
                               dest='author',
                               help='Author of package which to collect usage data.')
    parser_upload.add_argument('-d', '--data-directory',
                               type=str,
                               required=True,
                               dest='data_directory',
                               help='Directory name for usage data home.')
    parser_upload.add_argument('-p', '--package-name',
                               type=str,
                               required=True,
                               dest='package_name',
                               help='Name of package which to collect usage data.')
    parser_upload.add_argument('-s', '--start',
                               type=lambda d: datetime.strftime(d, '%Y-%m-%dT%H:%M:%S.%f'),
                               required=True,
                               dest='start',
                               help='UTC datetime to start the schedule.')
    parser_upload.add_argument('-f', '--frequency',
                               type=str,
                               required=True,
                               dest='frequency',
                               help='Schedule to send usage data e.g. 30s|1m|15m|1h|12h.')

    kwargs = vars(parser.parse_args(args))
    command = kwargs.pop('subparser')
    if command == 'upload':
        print(kwargs, flush=True)
        UsageAgent(**{k: v for k, v in kwargs.items()
                      if k not in ('start', 'frequency')}).recurring_send(**{
                        k: v for k, v in kwargs.items() if k in ('start', 'frequency')})
    raise SystemExit
