# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


from amazon_transcribe.model import TranscriptEvent, TranscriptResultStream


class TranscriptResultStreamHandler:
    def __init__(self, transcript_result_stream: TranscriptResultStream):
        self._transcript_result_stream = transcript_result_stream

    async def handle_events(self):
        """Process generic incoming events from Amazon Transcribe
        and delegate to appropriate sub-handlers.
        """
        async for event in self._transcript_result_stream:
            if isinstance(event, TranscriptEvent):
                await self.handle_transcript_event(event)

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """Specific handling for TranscriptionEvent responses from Amazon Transcribe.

        This should be implemented by the end user with desired data handling.
        """
        raise NotImplementedError
