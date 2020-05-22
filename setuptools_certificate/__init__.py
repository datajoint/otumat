import os
import hashlib
from pathlib import Path
from distutils.errors import DistutilsSetupError

from cryptography.hazmat.primitives.serialization import load_pem_private_key, \
                                                            load_pem_public_key
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64
from .version import __version__


# based on setuptools.dist:assert_string_list
def assert_string(dist, attr, value):
    """Verify that value is a string"""
    try:
        # verify that value is string
        assert isinstance(value, str)
    except (TypeError, ValueError, AttributeError, AssertionError):
        raise DistutilsSetupError(
            "%r must be a string (got %r)" % (attr, value)
        )


# based on setuptools.command.egg_info:write_arg
def write_arg(cmd, basename, filename, force=False):
    argname = 'pubkey_path' if basename == '.pub' else 'privkey_path'
    arg_value = getattr(cmd.distribution, argname, None)
    if arg_value is not None and os.path.isfile(os.path.expanduser(arg_value)):
        arg_value = os.path.expanduser(arg_value)
        egg_dir = str(Path(filename).parents[0])
        pkg_dir = os.path.splitext(egg_dir)[0]
        pkg_name = os.path.basename(pkg_dir)
        if argname == 'privkey_path':
            write_value = sign(arg_value, hash_pkg(pkg_dir))
        else:
            with open(arg_value, "r") as key_file:
                write_value = key_file.read()
        write_filename = str(Path(egg_dir, '{}{}'.format(pkg_name, basename)))
        cmd.write_or_delete_file(argname, write_filename, write_value, force)


def sign(privkey_path, data):
    with open(privkey_path, "rb") as key_file:
        private_key = load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend())
    signature = private_key.sign(
        data.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    return base64.b64encode(signature).decode('utf-8') + '\n'


def verify(pubkey_path, data, signature):
    with open(pubkey_path, "rb") as key_file:
        pub_key = load_pem_public_key(
            key_file.read(),
            backend=default_backend())
    pub_key.verify(
        base64.b64decode(signature.encode()),
        data.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())


def hash_pkg(pkgpath):
    refpath = Path(pkgpath).absolute().parents[0]
    details = ''
    details = _update_details_dir(pkgpath, refpath, details)
    # hash output to prepare for signing
    return hashlib.sha1('blob {}\0{}'.format(len(details), details).encode()).hexdigest()


def _update_details_dir(dirpath, refpath, details):
    paths = sorted(Path(dirpath).absolute().glob('*'))
    # walk a directory to collect info
    for path in paths:
        if 'pycache' not in str(path):
            if os.path.isdir(str(path)):
                details = _update_details_dir(path, refpath, details)
            else:
                details = _update_details_file(path, refpath, details)
    return details


def _update_details_file(filepath, refpath, details):
    with open(str(filepath), 'r') as f:
        data = f.read()
    # perfrom a SHA1 hash (same as git) that closely matches: git ls-files -s <dirname>
    mode = 100644
    hash = hashlib.sha1('blob {}\0{}'.format(len(data),data).encode()).hexdigest()
    stage_no = 0
    relative_path = str(filepath.relative_to(refpath))
    details = '{}{} {} {}\t{}\n'.format(details, mode, hash, stage_no, relative_path)
    return details
