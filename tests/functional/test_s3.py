# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from tests import unittest, mock, BaseSessionTest

import botocore.session
from botocore.client import Config
from botocore.exceptions import ParamValidationError


class TestS3BucketValidation(unittest.TestCase):
    def test_invalid_bucket_name_raises_error(self):
        session = botocore.session.get_session()
        s3 = session.create_client('s3')
        with self.assertRaises(ParamValidationError):
            s3.put_object(Bucket='adfgasdfadfs/bucket/name',
                          Key='foo', Body=b'asdf')


class TestS3GetBucketLifecycle(BaseSessionTest):
    def setUp(self):
        super(TestS3GetBucketLifecycle, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            's3', self.region)
        self.session_send_patch = mock.patch('botocore.endpoint.Session.send')
        self.http_session_send_mock = self.session_send_patch.start()

    def tearDown(self):
        super(TestS3GetBucketLifecycle, self).tearDown()
        self.session_send_patch.stop()

    def test_multiple_transitions_returns_one(self):
        http_response = mock.Mock()
        http_response.status_code = 200
        http_response.content = (
            '<?xml version="1.0" ?>'
            '<LifecycleConfiguration xmlns="http://s3.amazonaws.'
            'com/doc/2006-03-01/">'
            '	<Rule>'
            '		<ID>transitionRule</ID>'
            '		<Prefix>foo</Prefix>'
            '		<Status>Enabled</Status>'
            '		<Transition>'
            '			<Days>40</Days>'
            '			<StorageClass>STANDARD_IA</StorageClass>'
            '		</Transition>'
            '		<Transition>'
            '			<Days>70</Days>'
            '			<StorageClass>GLACIER</StorageClass>'
            '		</Transition>'
            '	</Rule>'
            '	<Rule>'
            '		<ID>noncurrentVersionRule</ID>'
            '		<Prefix>bar</Prefix>'
            '		<Status>Enabled</Status>'
            '		<NoncurrentVersionTransition>'
            '			<NoncurrentDays>40</NoncurrentDays>'
            '			<StorageClass>STANDARD_IA</StorageClass>'
            '		</NoncurrentVersionTransition>'
            '		<NoncurrentVersionTransition>'
            '			<NoncurrentDays>70</NoncurrentDays>'
            '			<StorageClass>GLACIER</StorageClass>'
            '		</NoncurrentVersionTransition>'
            '	</Rule>'
            '</LifecycleConfiguration>'
        )
        http_response.headers = {}
        self.http_session_send_mock.return_value = http_response
        s3 = self.session.create_client('s3')
        response = s3.get_bucket_lifecycle(Bucket='mybucket')
        # Each Transition member should have at least one of the
        # transitions provided.
        self.assertEqual(
            response['Rules'][0]['Transition'],
            {'Days': 40, 'StorageClass': 'STANDARD_IA'}
        )
        self.assertEqual(
            response['Rules'][1]['NoncurrentVersionTransition'],
            {'NoncurrentDays': 40, 'StorageClass': 'STANDARD_IA'}
        )


class BaseS3AddressingStyle(BaseSessionTest):
    def setUp(self):
        super(BaseS3AddressingStyle, self).setUp()
        self.http_response = mock.Mock()
        self.http_response.status_code = 200
        self.http_response.headers = {}
        self.http_response.content = b''


class TestVirtualHostStyle(BaseS3AddressingStyle):
    def test_default_endpoint_for_virtual_addressing(self):
        s3 = self.session.create_client(
            's3', config=Config(s3={'addressing_style': 'virtual'}))
        with mock.patch('botocore.endpoint.Session.send') \
                as mock_send:
            mock_send.return_value = self.http_response
            s3.put_object(Bucket='mybucket', Key='mykey', Body='mybody')
            request_sent = mock_send.call_args[0][0]
            self.assertEqual(
                'https://mybucket.s3.amazonaws.com/mykey', request_sent.url)

    def test_provided_endpoint_url_for_virtual_addressing(self):
        s3 = self.session.create_client(
            's3', config=Config(s3={'addressing_style': 'virtual'}),
            endpoint_url='https://foo.amazonaws.com')
        with mock.patch('botocore.endpoint.Session.send') \
                as mock_send:
            mock_send.return_value = self.http_response
            s3.put_object(Bucket='mybucket', Key='mykey', Body='mybody')
            request_sent = mock_send.call_args[0][0]
            self.assertEqual(
                'https://mybucket.foo.amazonaws.com/mykey', request_sent.url)


class TestPathHostStyle(BaseS3AddressingStyle):
    def test_default_endpoint_for_path_addressing(self):
        s3 = self.session.create_client(
            's3', config=Config(s3={'addressing_style': 'path'}))
        with mock.patch('botocore.endpoint.Session.send') \
                as mock_send:
            mock_send.return_value = self.http_response
            s3.put_object(Bucket='mybucket', Key='mykey', Body='mybody')
            request_sent = mock_send.call_args[0][0]
            self.assertEqual(
                'https://s3.amazonaws.com/mybucket/mykey', request_sent.url)

    def test_provided_endpoint_url_for_path_addressing(self):
        s3 = self.session.create_client(
            's3', config=Config(s3={'addressing_style': 'path'}),
            endpoint_url='https://foo.amazonaws.com')
        with mock.patch('botocore.endpoint.Session.send') \
                as mock_send:
            mock_send.return_value = self.http_response
            s3.put_object(Bucket='mybucket', Key='mykey', Body='mybody')
            request_sent = mock_send.call_args[0][0]
            self.assertEqual(
                'https://foo.amazonaws.com/mybucket/mykey', request_sent.url)