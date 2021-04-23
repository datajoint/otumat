# Otumat: Maintainer Tools & Utilities

Otumat (pronounced "Automate") is a suite of maintainer tools and utilities for pip packages.

It includes a setuptools extension that provides new keyword arguments `privkey_path` and `pubkey_path`. 

By specifying the `privkey_path`, setuptools will generate the git hash (SHA1) of the module directory and sign the output based on the PEM key path passed in. The resulting signature will be stored as egg metadata `{{module_name}}.sig` accessible via `pkg_resources` module. 

If passing `pubkey_path`, this will simply be copied in as egg metadata `{{module_name}}.pub`.

This provides a solution to determining the 'trust-worthiness' of plugins or extensions that may be developed by the community for a given pip package if the public key file is available for the RSA keypair. The choice of what to do for failed verification is up to you.

# Use

## Extensible Package e.g. `base`

``` python
setuptools.setup(
    ...
    setup_requires=['otumat'],
    pubkey_path='./pubkey.pem',
    ...
```

## Plugin Package e.g. `plugin1`

``` python
setuptools.setup(
    ...
    setup_requires=['otumat'],
    privkey_path='~/keys/privkey.pem',
    ...
```

## Verifying Contents

``` python
import pkg_resources
from pathlib import Path
from otumat import hash_pkg, verify

base_name = 'base'
plugin_name = 'plugin1'
base_meta = pkg_resources.get_distribution(base_name)
plugin_meta = pkg_resources.get_distribution(plugin_name)

data = hash_pkg(str(Path(plugin_meta.module_path, plugin_name)))
signature = plugin_meta.get_metadata('{}.sig'.format(plugin_name))
pubkey_path = str(Path(base_meta.egg_info, '{}.pub'.format(base_name)))

verify(pubkey_path, data, signature)
```


# Compatibility with `git` and `openssl` CLI

For reference, certificates may also be generated and verified using `git` and `openssl` by the following process:

## Generate

``` shell
$ cd {{/path/to/local/repo/dir}}
$ git add . --all
$ GIT_HASH=$(git ls-files -s {{/pip/package/dir}} | git hash-object --stdin)
$ printf $GIT_HASH | openssl dgst -sha256 -sign {{/path/to/privkey/pem}} -out {{pip_package_name}}.sigbin -sigopt rsa_padding_mode:pss
$ openssl enc -base64 -in {{pip_package_name}}.sigbin -out {{pip_package_name}}.sig
$ rm {{pip_package_name}}.sigbin
$ git reset
```

## Verify

``` shell
$ cd {{/path/to/local/repo/dir}}
$ git add . --all
$ GIT_HASH=$(git ls-files -s {{/pip/package/dir}} | git hash-object --stdin)
$ openssl enc -base64 -d -in {{pip_package_name}}.sig -out {{pip_package_name}}.sigbin
$ printf $GIT_HASH | openssl dgst -sha256 -verify {{/path/to/pubkey/pem}} -signature {{pip_package_name}}.sigbin -sigopt rsa_padding_mode:pss
$ rm {{pip_package_name}}.sigbin
$ git reset
```