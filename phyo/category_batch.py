# Copyright 2016 Intel Corporation
# Copyright 2017 Wind River
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import hashlib
import base64
from base64 import b64encode
import time
import requests
import yaml
import datetime
import json
#import sawtooth_signing.secp256k1_signer as signing

#
from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey
#

from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchList
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch

from sawtooth_category.exceptions import CategoryException


def _sha512(data):
    return hashlib.sha512(data).hexdigest()


class CategoryBatch:
    def __init__(self, base_url):
        self._base_url = base_url
################################################################################
#
################################################################################    
    def create_category(self, category_id, category_name, description, 
                            private_key, public_key):
        return self.send_category_transactions(category_id,category_name,description, "create",
                                private_key,public_key, str(datetime.datetime.utcnow()))
                                
    def list_category(self):
        category_prefix = self._get_prefix()

        result = self._send_request(
            "state?address={}".format(category_prefix)
        )

        try:
            encoded_entries = yaml.safe_load(result)["data"]

            return [
                base64.b64decode(entry["data"]) for entry in encoded_entries
            ]

        except BaseException:
            return None

    def retreive_category(self, category_id):
        address = self._get_address(category_id)
        result = self._send_request("state/{}".format(address), category_id=category_id)

        try:
            return base64.b64decode(yaml.safe_load(result)["data"])

        except BaseException:
            return None
    
    def update_category(self, category_id, category_name, description,
                            private_key, public_key):
        response_bytes = self.retreive_category(category_id)
        
        if response_bytes != None:
            response = str(response_bytes)
            response = response[response.find('{') : response.find('}') + 1]
            
            jresponse = json.loads(response)
            
            if jresponse['category_name'] == category_name and jresponse['description'] == description:
                return None
            else:
                return self.send_category_transactions(category_id, category_name,
                            description, "update", private_key,public_key,
                            str(datetime.datetime.utcnow()))
                            
        return None
    
################################################################################
#
################################################################################
    def _get_prefix(self):
        return _sha512('category'.encode('utf-8'))[0:6]

    def _get_address(self, category_id):
        category_prefix = self._get_prefix()
        address = _sha512(category_id.encode('utf-8'))[0:64]
        return category_prefix + address

    def _send_request(
            self, suffix, data=None,
            content_type=None, category_id=None):
        if self._base_url.startswith("http://"):
            url = "{}/{}".format(self._base_url, suffix)
        else:
            url = "http://{}/{}".format(self._base_url, suffix)

        headers = {}
        if content_type is not None:
            headers['Content-Type'] = content_type

        try:
            if data is not None:
                result = requests.post(url, headers=headers, data=data)
            else:
                result = requests.get(url, headers=headers)

            if result.status_code == 404:
                raise CategoryException("No such Category: {}".format(category_id))

            elif not result.ok:
                raise CategoryException("Error {}: {}".format(
                    result.status_code, result.reason))

        except BaseException as err:
            print(err)
            raise CategoryException(err)
        
        return result.text

    def send_category_transactions(self, category_id, category_name, description, 
                                    action,private_key,public_key, timestamp):
        
        self._public_key = public_key
        self._private_key = private_key
        
        payload = ",".join([category_id,category_name,description, action, timestamp]).encode()

        # Form the address
        address = self._get_address(category_id)

        header = TransactionHeader(
            signer_public_key = self._public_key,
            family_name = "category",
            family_version = "1.0",
            inputs = [address],
            outputs = [address],
            dependencies = [],
            # payload_encoding="csv-utf8",
            payload_sha512 = _sha512(payload),
            batcher_public_key = self._public_key,
            nonce=time.time().hex().encode()
        ).SerializeToString()

        signature = CryptoFactory(create_context('secp256k1')) \
            .new_signer(Secp256k1PrivateKey.from_hex(self._private_key)).sign(header)

        transaction = Transaction(
            header=header,
            payload=payload,
            header_signature=signature
        )

        batch_list = self._create_batch_list([transaction])
        
        return self._send_request(
            "batches", batch_list.SerializeToString(),
            'application/octet-stream'
        )

    def _create_batch_list(self, transactions):
        transaction_signatures = [t.header_signature for t in transactions]

        header = BatchHeader(
            signer_public_key = self._public_key,
            transaction_ids = transaction_signatures
        ).SerializeToString()

        signature = CryptoFactory(create_context('secp256k1')) \
            .new_signer(Secp256k1PrivateKey.from_hex(self._private_key)).sign(header)

        batch = Batch(
            header = header,
            transactions = transactions,
            header_signature = signature
        )
        return BatchList(batches=[batch])
