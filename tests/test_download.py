"""Tests for :mod:`pypiuploader.download`."""

import os
import shutil
import tempfile
import types

try:
    from unittest import mock
except ImportError:
    import mock
import pytest

from pypiuploader import download


class TestPackageDownloader(object):

    """Tests for :class:`pypiuploader.download.PackageDownloader`."""

    def setup(self):
        self._tmpdirs = []

    def teardown(self):
        for tmpdir in self._tmpdirs:
            try:
                shutil.rmtree(tmpdir)
            except OSError:
                pass

    def test_init(self):
        downloader = download.PackageDownloader('/foo/bar')
        assert downloader.download_path == '/foo/bar'

    def test_init_without_download_path(self):
        downloader = download.PackageDownloader()
        assert downloader.download_path is None

    def test_make_download_dir(self):
        tmpdir = self._mkdtemp()
        download_path = os.path.join(tmpdir, 'packages')
        downloader = download.PackageDownloader(download_path)

        downloader._make_download_dir()
        assert os.path.isdir(download_path)
        downloader._make_download_dir()
        assert os.path.isdir(download_path)
        shutil.rmtree(tmpdir)
        downloader._make_download_dir()
        assert os.path.isdir(download_path)

    def test_download_command_word(self):
        downloader = download.PackageDownloader()
        assert downloader.download_command_word('8.0.1') == 'download'
        assert downloader.download_command_word('8.0.0') == 'download'
        assert downloader.download_command_word('7.1.12') == 'install'

    def test_make_download_dir_when_not_set(self):
        downloader = download.PackageDownloader()
        downloader._make_download_dir()
        assert downloader.download_path is not None
        self._tmpdirs.append(downloader.download_path)
        assert os.path.isdir(downloader.download_path)

    def test_build_args_with_requirements(self):
        downloader = download.PackageDownloader('/foo/bar')
        args = downloader._build_args(requirements=['requests==1.2.1', 'mock'])
        pip_command = downloader.download_command_word()
        assert args == [pip_command, '-d', '/foo/bar',
                        'requests==1.2.1', 'mock']

    def test_build_args_with_requirements_file(self):
        downloader = download.PackageDownloader('/foo/bar')
        args = downloader._build_args(requirements_file='requirements.txt')
        pip_command = downloader.download_command_word()
        assert args == [pip_command, '-d', '/foo/bar',
                        '-r', 'requirements.txt']

    def test_build_args_without_arguments(self):
        downloader = download.PackageDownloader('/foo/bar')
        with pytest.raises(ValueError):
            downloader._build_args()

    def test_build_args_no_use_wheel(self):
        downloader = download.PackageDownloader('/foo/bar')
        args = downloader._build_args(
            requirements_file='requirements.txt',
            no_use_wheel=True)
        pip_command = downloader.download_command_word()
        assert args == [
            pip_command,
            '-d', '/foo/bar',
            '--no-use-wheel',
            '-r', 'requirements.txt',
        ]

    def test_list_download_dir(self):
        download_path = self._mkdtemp()
        __, package1 = tempfile.mkstemp(dir=download_path)
        __, package2 = tempfile.mkstemp(dir=download_path)
        tempfile.mkdtemp(dir=download_path)
        downloader = download.PackageDownloader(download_path)

        paths = downloader._list_download_dir()

        assert isinstance(paths, types.GeneratorType)
        assert sorted(list(paths)) == sorted([package1, package2])

    @mock.patch('pip.main', autospec=True)
    @mock.patch.object(
        download.PackageDownloader, '_list_download_dir', autospec=True)
    def test_download_requirements(self, list_dir_mock, pip_main_mock):
        list_dir_mock.return_value = ('mock-1.0.1.tar.gz',)
        download_path = '/foo/bar'
        downloader = download.PackageDownloader(download_path)

        downloaded = downloader.download(requirements=['mock'])

        assert sorted(list(downloaded)) == ['mock-1.0.1.tar.gz']
        pip_command = downloader.download_command_word()
        expected_call = mock.call([pip_command, '-d', download_path, 'mock'])
        assert pip_main_mock.call_args == expected_call

    @mock.patch('pip.main', autospec=True)
    def test_download_requirements_file(self, pip_main_mock):
        download_path = self._mkdtemp()
        downloader = download.PackageDownloader(download_path)

        downloader.download(requirements_file='requirements.txt')
        pip_command = downloader.download_command_word()
        expected_call = mock.call(
            [pip_command, '-d', download_path, '-r', 'requirements.txt'])
        assert pip_main_mock.call_args == expected_call

    @mock.patch('pip.main', autospec=True)
    def test_download_no_use_wheel(self, pip_main_mock):
        download_path = self._mkdtemp()
        downloader = download.PackageDownloader(download_path)

        downloader.download(
            requirements_file='requirements.txt',
            no_use_wheel=True)

        pip_command = downloader.download_command_word()
        expected_call = mock.call([
            pip_command,
            '-d', download_path,
            '--no-use-wheel',
            '-r', 'requirements.txt',
        ])
        assert pip_main_mock.call_args == expected_call

    def _mkdtemp(self):
        tmpdir = tempfile.mkdtemp()
        self._tmpdirs.append(tmpdir)
        return tmpdir
