"""Downloading packages to a directory."""

import os
import tempfile

import pip
from pip._vendor.packaging.version import parse as parse_version
from pip.status_codes import SUCCESS


class PackageDownloadErr(Exception):
    def __init__(self, status, args):
        Exception.__init__(self)
        self.status = status
        self.args = args
        self.message = 'package failed download, exit %d. Arguments: %s' % (status, args)


class PackageDownloader(object):

    """Downloads source distributions from PyPI to a directory.

    Runs ``pip install`` command, e.g.::

        >>> downloader = PackageDownloader('~/.packages')
        >>> downloader.download(['mock', 'requests==1.2.1'])

    Would run:

    .. code-block:: bash

        $ pip install -d ~/.packages mock requests==1.2.1

    And this:

        >>> downloader = PackageDownloader('~/.packages')
        >>> downloader.download(requirements_file='requirements.txt')

    Would run:

    .. code-block:: bash

        $ pip install -d ~/.packages -r requirements.txt

    :param download_path:
        Optional path to directory where the packages should be downloaded,
        will be set as :attr:`download_path`.

        If doesn't exist, will be created on :meth:`download`.
        If not given, will create a temporary directory and update
        :attr:`download_path` on :meth:`download`.

    """

    def __init__(self, download_path=None):
        #: Path to directory where the packages should be downloaded.
        self.download_path = download_path

    def download(
            self,
            requirements=None,
            requirements_file=None,
            no_use_wheel=False):
        """Download the packages using ``pip install`` command.

        Either ``requirements`` or ``requirements_file`` must be given,
        otherwise raise :exc:`ValueError`.

        Return a generator yielding full paths to the downloaded packages.

        :param requirements:
            Optional list of packages names to download.
        :param requirements_file:
            Optional path to a requirements file.
        :param no_use_wheel:
            Do not find and prefer wheel archives, default to ``False``.
            Corresponds to ``--no-use-wheel`` option from ``pip install``.

        """
        self._make_download_dir()
        args = self._build_args(requirements, requirements_file, no_use_wheel)
        pip_result = pip.main(args)
        if pip_result != SUCCESS:
            raise PackageDownloadErr(pip_result, args)


        return self._list_download_dir()

    def _build_args(
            self,
            requirements=None,
            requirements_file=None,
            no_use_wheel=False):

        pip_command = 'download'
        if parse_version(pip.__version__) < parse_version('8.0.0'):
            pip_command = 'install'

        args = [
            pip_command,
            '-d',
            self.download_path,
        ]
        if no_use_wheel:
            args.append('--no-use-wheel')
        if requirements is not None:
            args.extend(requirements)
        elif requirements_file is not None:
            args.extend(['-r', requirements_file])
        else:
            error = 'Either requirements or requirements_file must be given.'
            raise ValueError(error)
        return args

    def _make_download_dir(self):
        if self.download_path is None:
            self.download_path = tempfile.mkdtemp()
        else:
            try:
                os.makedirs(self.download_path)
            except OSError:
                pass

    def _list_download_dir(self):
        for filename in os.listdir(self.download_path):
            fullpath = os.path.join(self.download_path, filename)
            if os.path.isfile(fullpath):
                yield fullpath
