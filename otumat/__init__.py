import os
import hashlib
import pathlib
import distutils.errors
import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.backends
import cryptography.hazmat.primitives.asymmetric
import cryptography.hazmat.primitives
import base64
from .version import __version__

__all__ = ['__version__']

DISABLE_USAGE_TRACKING_PACKAGES = []


# based on setuptools.dist:assert_string_list
def assert_string(dist, attr, value):
    """Verify that value is a string"""
    try:
        # verify that value is string
        assert isinstance(value, str)
    except (TypeError, ValueError, AttributeError, AssertionError):
        raise distutils.errors.DistutilsSetupError(
            "%r must be a string (got %r)" % (attr, value)
        )


# based on setuptools.command.egg_info:write_arg
def write_arg(cmd, basename, filename, force=False):
    argname = 'pubkey_path' if basename == '.pub' else 'privkey_path'
    arg_value = getattr(cmd.distribution, argname, None)
    if arg_value is not None and os.path.isfile(os.path.expanduser(arg_value)):
        arg_value = os.path.expanduser(arg_value)
        egg_dir = str(pathlib.Path(filename).parents[0])
        pkg_dir = os.path.splitext(egg_dir)[0]
        pkg_name = os.path.basename(pkg_dir)
        if argname == 'privkey_path':
            write_value = sign(privkey_path=arg_value, data=hash_pkg(pkgpath=pkg_dir))
        else:
            write_value = pathlib.Path(arg_value).read_text()
        write_filename = str(pathlib.Path(egg_dir, '{}{}'.format(pkg_name, basename)))
        cmd.write_or_delete_file(argname, write_filename, write_value, force)


def sign(*, privkey_path, data):
    with open(privkey_path, "rb") as key_file:
        private_key = cryptography.hazmat.primitives.serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=cryptography.hazmat.backends.default_backend())
    signature = private_key.sign(
        data.encode(),
        cryptography.hazmat.primitives.asymmetric.padding.PSS(
            mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                cryptography.hazmat.primitives.hashes.SHA256()),
            salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH),
        cryptography.hazmat.primitives.hashes.SHA256())
    return base64.b64encode(signature).decode('utf-8') + '\n'


def verify(*, pubkey_path, data, signature):
    with open(pubkey_path, "rb") as key_file:
        pub_key = cryptography.hazmat.primitives.serialization.load_pem_public_key(
            key_file.read(),
            backend=cryptography.hazmat.backends.default_backend())
    pub_key.verify(
        base64.b64decode(signature.encode()),
        data.encode(),
        cryptography.hazmat.primitives.asymmetric.padding.PSS(
            mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                cryptography.hazmat.primitives.hashes.SHA256()),
            salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH),
        cryptography.hazmat.primitives.hashes.SHA256())


def hash_pkg(*, pkgpath):
    refpath = pathlib.Path(pkgpath).absolute().parents[0]
    details = ''
    details = _update_details_dir(dirpath=pkgpath, refpath=refpath, details=details)
    # hash output to prepare for signing
    return hashlib.sha1('blob {}\0{}'.format(len(details), details).encode()).hexdigest()


def _update_details_dir(*, dirpath, refpath, details):
    paths = sorted(pathlib.Path(dirpath).absolute().glob('*'))
    # walk a directory to collect info
    for path in paths:
        if 'pycache' not in str(path):
            if os.path.isdir(str(path)):
                details = _update_details_dir(dirpath=path, refpath=refpath, details=details)
            else:
                details = _update_details_file(filepath=path, refpath=refpath, details=details)
    return details


def _update_details_file(*, filepath, refpath, details):
    data = pathlib.Path(filepath).read_text()
    # perfrom a SHA1 hash (same as git) that closely matches: git ls-files -s <dirname>
    mode = 100644
    hash = hashlib.sha1('blob {}\0{}'.format(len(data), data).encode()).hexdigest()
    stage_no = 0
    relative_path = str(filepath.relative_to(refpath))
    details = '{}{} {} {}\t{}\n'.format(details, mode, hash, stage_no, relative_path)
    return details
