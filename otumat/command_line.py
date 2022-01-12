import argparse
from . import __version__ as version
from . import usage as otumat_usage
from . import watch as otumat_watch
import datetime


def otumat(args=None):
    """
    Primary console interface for otumat's shell utilities.

    :param args: List of arguments to be passed in, defaults to reading stdin
    :type args: list, optional
    """
    parser = argparse.ArgumentParser(prog='otumat',
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
                               type=lambda d: datetime.datetime.strptime(
                                    d, '%Y-%m-%dT%H:%M:%S.%f'),
                               required=True,
                               dest='start',
                               help='UTC datetime to start the schedule.')
    parser_upload.add_argument('-f', '--frequency',
                               type=str,
                               required=True,
                               dest='frequency',
                               help='Schedule to send usage data e.g. 30s|1m|15m|1h|12h.')

    parser_upload = subparsers.add_parser(
        'watch',
        description='Watch file for changes and run job on change.')
    parser_upload.add_argument('-f', '--file',
                               type=str,
                               required=True,
                               dest='watch_file',
                               help='Path to file to be watched.')
    parser_upload.add_argument('-s', '--script',
                               type=str,
                               required=True,
                               dest='watch_script',
                               help='Script to run on file change.')
    parser_upload.add_argument('-a', '--arguments',
                               nargs='+',
                               type=str,
                               required=False,
                               dest='watch_args',
                               help='Arguments providing state between runs.')

    kwargs = vars(parser.parse_args(args))
    command = kwargs.pop('subparser')
    if command == 'upload':
        otumat_usage.UsageAgent(**{k: v for k, v in kwargs.items()
                                   if k not in ('start', 'frequency')}).recurring_send(**{
                                        k: v for k, v in kwargs.items()
                                        if k in ('start', 'frequency')})
    elif command == 'watch':
        otumat_watch.WatchAgent(watch_file=kwargs['watch_file'],
                                watch_script=kwargs['watch_script'],
                                watch_args=kwargs['watch_args'])
    raise SystemExit
