"""Tests for :mod:`pypiuploader.upload`."""

import tempfile

try:
    from unittest import mock
except ImportError:
    import mock
import pytest
import requests

from pypiuploader import exceptions
from pypiuploader import upload
from . import utils


class TestPackageUploader(object):

    """Tests for :class:`pypiuploader.upload.PackageUploader`."""

    def setup(self):
        self.uploader = upload.PackageUploader(
            'http://localhost:8000', 'user', 'pass')

    def test_init(self):
        assert self.uploader.host == 'http://localhost:8000'
        assert self.uploader.username == 'user'
        assert self.uploader.password == 'pass'
        assert self.uploader._data == {':action': 'file_upload'}
        assert isinstance(self.uploader._session, requests.Session)
        assert self.uploader._session.auth == ('user', 'pass')

    def test_init_no_username(self):
        uploader = upload.PackageUploader('http://localhost:8000')
        assert uploader.host == 'http://localhost:8000'
        assert uploader.username is None
        assert uploader.password is None
        assert uploader._data == {':action': 'file_upload'}
        assert isinstance(uploader._session, requests.Session)
        assert uploader._session.auth is None

    def test_init_from_repository_config(self):
        config = {
            'repository': 'http://localhost:8000',
            'username': 'foo',
            'password': 'bar',
        }
        uploader = upload.PackageUploader.from_repository_config(config)
        assert uploader.host == 'http://localhost:8000'
        assert uploader.username == 'foo'
        assert uploader.password == 'bar'
        assert uploader._data == {':action': 'file_upload'}
        assert isinstance(uploader._session, requests.Session)
        assert uploader._session.auth == ('foo', 'bar')

    def test_init_from_repository_config_custom_auth(self):
        config = {
            'repository': 'http://localhost:8000',
            'username': 'foo',
            'password': 'bar',
        }
        uploader = upload.PackageUploader.from_repository_config(
            config, username='bar', password='foo')
        assert uploader.host == 'http://localhost:8000'
        assert uploader.username == 'bar'
        assert uploader.password == 'foo'
        assert uploader._data == {':action': 'file_upload'}
        assert isinstance(uploader._session, requests.Session)
        assert uploader._session.auth == ('bar', 'foo')

    def test_init_from_rc_file(self):
        tmpfile = utils._make_tmp_pypirc_file()
        uploader = upload.PackageUploader.from_rc_file(
            'internal', config_path=tmpfile.name)
        assert uploader.host == 'http://127.0.0.1:8000'
        assert uploader.username == 'bar'
        assert uploader.password == 'foo'
        assert uploader._data == {':action': 'file_upload'}
        assert isinstance(uploader._session, requests.Session)
        assert uploader._session.auth == ('bar', 'foo')

    def test_init_from_rc_file_custom_auth(self):
        tmpfile = utils._make_tmp_pypirc_file()
        uploader = upload.PackageUploader.from_rc_file(
            'internal',
            username='foo',
            password='bar',
            config_path=tmpfile.name)
        assert uploader.host == 'http://127.0.0.1:8000'
        assert uploader.username == 'foo'
        assert uploader.password == 'bar'
        assert uploader._data == {':action': 'file_upload'}
        assert isinstance(uploader._session, requests.Session)
        assert uploader._session.auth == ('foo', 'bar')

    def test_init_from_rc_file_when_no_pypirc(self):
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.close()
        uploader = upload.PackageUploader.from_rc_file(
            'http://localhost:8000',
            username='foo',
            password='bar',
            config_path=tmpfile.name)
        assert uploader.host == 'http://localhost:8000'
        assert uploader.username == 'foo'
        assert uploader.password == 'bar'
        assert uploader._data == {':action': 'file_upload'}
        assert isinstance(uploader._session, requests.Session)
        assert uploader._session.auth == ('foo', 'bar')

    def test_read_file(self):
        tmpfile = utils._make_tmp_pypirc_file(b'foo\nbar\n')
        content = self.uploader._read_file(tmpfile.name)
        assert content == b'foo\nbar\n'

    @mock.patch.object(upload.PackageUploader, '_read_file')
    def test_make_request_files(self, read_file_mock):
        read_file_mock.return_value = b'foo\nbar\n'
        files = self.uploader._make_request_files('/foo/bar/baz.tar.gz')
        assert files == {'content': ('baz.tar.gz', b'foo\nbar\n')}

    def test_raise_for_status_ok(self):
        response = requests.Response()
        response.status_code = 200

        try:
            self.uploader._raise_for_status(response, 'foo.tar.gz')
        except (requests.HTTPError, exceptions.PackageConflictError) as exc:
            raise AssertionError('{0!r} should not be raised.'.format(exc))

    def test_raise_for_status_401(self):
        response = requests.Response()
        response.status_code = 401
        response.reason = 'Foo bar'

        with pytest.raises(requests.HTTPError) as exc:
            self.uploader._raise_for_status(response, 'foo.tar.gz')

        assert str(exc.value).startswith('401 Client Error: Foo bar')
        assert exc.value.response == response

    def test_raise_for_status_conflict_error(self):
        response = requests.Response()
        response.status_code = 409
        response.reason = 'Foo bar'

        with pytest.raises(exceptions.PackageConflictError) as exc:
            self.uploader._raise_for_status(response, 'foo.tar.gz')

        assert str(exc.value) == 'Package foo.tar.gz already uploaded.'

    @mock.patch.object(requests.Session, 'post')
    @mock.patch.object(upload.PackageUploader, '_read_file')
    def test_upload(self, read_file_mock, post_mock):
        read_file_mock.return_value = 'foo\nbar\n'
        response_mock = requests.Response()
        response_mock.status_code = 200
        post_mock.return_value = response_mock

        response = self.uploader.upload('/foo/bar.tar.gz')

        assert response is response_mock
        expected_call = mock.call(
            'http://localhost:8000',
            data={':action': 'file_upload'},
            files={'content': ('bar.tar.gz', 'foo\nbar\n')})
        assert post_mock.call_args == expected_call
