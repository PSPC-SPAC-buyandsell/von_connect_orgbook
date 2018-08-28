#
# Copyright 2017-2018 Government of Canada
# Public Services and Procurement Canada - buyandsell.gc.ca
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Abstractions to remove direct client dependency on didauth library
"""

import logging
from typing import Mapping

from didauth.base import KeyFinderBase, StaticKeyFinder
from didauth.error import VerifierException
from didauth.headers import HeaderVerifier
from didauth.utils import decode_string

from vonx.indy.client import IndyClient
from vonx.indy.errors import IndyError

LOGGER = logging.getLogger(__name__)


async def verify_signature(
        headers: Mapping, key_finder: KeyFinderBase, method: str = None, path: str = None):
    """
    Verify the DID signature on request headers

    Args:
        headers: the collection of request headers
        key_finder: the key finder (likely IndyKeyFinder or KeyCache)
        method: the HTTP method
        path: the request path including the query string
    """
    verifier = HeaderVerifier(key_finder)
    try:
        return await verifier.verify(headers, method, path)
    except VerifierException as e:
        raise IndyError("Could not verify request headers") from e


class IndyKeyFinder(KeyFinderBase):
    """
    Look up the public key for an issuer
    """

    def __init__(self, client: IndyClient, verifier_id: str, source: KeyFinderBase = None):
        super(IndyKeyFinder, self).__init__(source)
        self._client = client
        self._verifier_id = verifier_id

    async def _lookup_key(self, key_id: str, key_type: str):
        if key_type != "ed25519":
            return None
        if key_id.startswith("did:sov:"):
            short_key_id = key_id[8:]
        else:
            short_key_id = key_id
            key_id = "did:sov:" + short_key_id

        LOGGER.debug("Fetching verkey for DID '%s' from ledger", key_id)
        nym_info = await self._client.resolve_nym(short_key_id, self._verifier_id)
        if nym_info.data:
            return decode_string(nym_info.data["verkey"], "base58")
        return None


class KeyCache(StaticKeyFinder):
    def __init__(self, source: KeyFinderBase):
        super(KeyCache, self).__init__(source, True)


__all__ = ('IndyKeyFinder', 'KeyCache', 'KeyFinderBase', 'verify_signature')