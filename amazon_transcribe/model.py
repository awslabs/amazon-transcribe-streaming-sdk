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

from typing import Optional, List

from amazon_transcribe.eventstream import BaseEvent, BaseStream, EventStream


class Alternative:
    """A list of possible transcriptions for the audio.

    :param transcript: The text that was transcribed from the audio.
    :param items: One or more alternative interpretations of the input audio.
    """

    def __init__(self, transcript, items):
        self.transcript: str = transcript
        self.items: List[Item] = items


class AudioEvent(BaseEvent):
    """Provides a wrapper for the audio chunks that you are sending.

    :param audio_chunk:
        A blob of audio from your application. You audio stream
        consists of one or more audio events.
    """

    def __init__(self, audio_chunk: Optional[bytes]):
        if audio_chunk is None:
            audio_chunk = b""
        super().__init__(payload=audio_chunk)

    @property
    def audio_chunk(self):
        return self.payload


class AudioStream(BaseStream):
    """Input audio stream for transcription stream request.

    This should never be instantiated by the end user. It will be returned
    from the client within a relevant wrapper object.
    """

    async def send_audio_event(self, audio_chunk: Optional[bytes]):
        """Enqueue audio bytes to be sent for transcription.

        :param audio_chunk: byte-string chunk of audio input.
        """
        audio_event = AudioEvent(audio_chunk)
        await super().send_event(audio_event)


class Item:
    """A word or phrase transcribed from the input audio.

    :param start_time:
        The offset from the beginning of the audio stream to the beginning
        of the audio that resulted in the item.

    :param end_time:
        The offset from the beginning of the audio stream to the end of
        the audio that resulted in the item.

    :param item_type: The type of the item.

    :param content:
        The word or punctuation that was recognized in the input audio.

    :param vocabulary_filter_match:
        Indicates whether a word in the item matches a word in the vocabulary
        filter you've chosen for your real-time stream. If True then a word
        in the item matches your vocabulary filter.
    """

    def __init__(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        item_type: Optional[str] = None,
        content: Optional[str] = None,
        vocabulary_filter_match: Optional[bool] = None,
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.item_type = item_type
        self.content = content
        self.vocabulary_filter_match = vocabulary_filter_match


class Result:
    """The result of transcribing a portion of the input audio stream.

    :param result_id: A unique identifier for the result.

    :param start_time:
        The offset in seconds from the beginning of the audio stream to the
        beginning of the result.

    :param end_time:
        The offset in seconds from the beginning of the audio stream to the
        end of the result.

    :param is_partial:
        Amazon Transcribe divides the incoming audio stream into segments at
        natural points in the audio. Transcription results are returned based
        on these segments. True indicates that Amazon Transcribe has additional
        transcription data to send, False to indicate that this is the last
        transcription result for the segment.

    :param alternatives:
        A list of possible transcriptions for the audio. Each alternative
        typically contains one Item that contains the result of the transcription.
    """

    def __init__(
        self,
        result_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        is_partial: Optional[bool] = None,
        alternatives: Optional[List[Alternative]] = None,
    ):
        self.result_id = result_id
        self.start_time = start_time
        self.end_time = end_time
        self.is_partial = is_partial
        self.alternatives = alternatives


class StartStreamTranscriptionRequest:
    """Transcription Request

    :param language_code:
        Indicates the source language used in the input audio stream.

    :param media_sample_rate_hz:
        The sample rate, in Hertz, of the input audio. We suggest that you
        use 8000 Hz for low quality audio and 16000 Hz for high quality audio.

    :param media_encoding:
        The encoding used for the input audio.

    :param vocabulary_name:
        The name of the vocabulary to use when processing the transcription job.

    :param session_id:
        A identifier for the transcription session. Use this parameter when you
        want to retry a session. If you don't provide a session ID,
        Amazon Transcribe will generate one for you and return it in the response.

    :param vocab_filter_method:
        The manner in which you use your vocabulary filter to filter words in
        your transcript.

    :param vocab_filter_name:
        The name of the vocabulary filter you've created that is unique to your AWS account.
    """

    def __init__(
        self,
        language_code=None,
        media_sample_rate_hz=None,
        media_encoding=None,
        vocabulary_name=None,
        session_id=None,
        vocab_filter_method=None,
        vocab_filter_name=None,
    ):

        self.language_code: Optional[str] = language_code
        self.media_sample_rate_hz: Optional[int] = media_sample_rate_hz
        self.media_encoding: Optional[str] = media_encoding
        self.vocabulary_name: Optional[str] = vocabulary_name
        self.session_id: Optional[str] = session_id
        self.vocab_filter_method: Optional[str] = vocab_filter_method
        self.vocab_filter_name: Optional[str] = vocab_filter_name


class StartStreamTranscriptionResponse:
    """Transcription Response

    :param transcript_result_stream:
        Represents the stream of transcription events from
        Amazon Transcribe to your application.

    :param request_id: An identifier for the streaming transcription.

    :param language_code:
        Indicates the source language used in the input audio stream.

    :param media_sample_rate_hz:
        The sample rate, in Hertz, of the input audio. We suggest that you
        use 8000 Hz for low quality audio and 16000 Hz for high quality audio.

    :param media_encoding:
        The encoding used for the input audio.

    :param session_id:
        A identifier for the transcription session. Use this parameter when you
        want to retry a session. If you don't provide a session ID,
        Amazon Transcribe will generate one for you and return it in the response.

    :param vocab_filter_name:
        The name of the vocabulary filter used in your real-time stream.

    :param vocab_filter_method:
        The manner in which you use your vocabulary filter to filter words in
        your transcript.
    """

    def __init__(
        self,
        transcript_result_stream,
        request_id=None,
        language_code=None,
        media_sample_rate_hz=None,
        media_encoding=None,
        vocabulary_name=None,
        session_id=None,
        vocab_filter_name=None,
        vocab_filter_method=None,
    ):
        self.request_id: Optional[str] = request_id
        self.language_code: Optional[str] = language_code
        self.media_sample_rate_hz: Optional[int] = media_sample_rate_hz
        self.media_encoding: Optional[str] = media_encoding
        self.vocabulary_name: Optional[str] = vocabulary_name
        self.session_id: Optional[str] = session_id
        self.transcript_result_stream: TranscriptResultStream = transcript_result_stream
        self.vocab_filter_name: Optional[str] = vocab_filter_name
        self.vocab_filter_method: Optional[str] = vocab_filter_method


class Transcript:
    """The transcription in a TranscriptEvent.

    :param results:
        Result objects that contain the results of transcribing a portion of the
        input audio stream. The array can be empty.
    """

    def __init__(self, results: List[Result]):
        self.results = results


class TranscriptEvent(BaseEvent):
    """Represents a set of transcription results from the server to the client.
    It contains one or more segments of the transcription.

    :param transcript:
        The transcription of the audio stream. The transcription is composed of
        all of the items in the results list.
    """

    def __init__(self, transcript: Transcript):
        self.transcript = transcript


class TranscriptResultStream(EventStream):
    """Transcription result stream containing returned TranscriptEvent output.

    Results are surfaced through the async iterator interface (i.e. async for)

    :raises BadRequestException:
        A client error occurred when the stream was created. Check the parameters
        of the request and try your request again.

    :raises LimitExceededException:
        Your client has exceeded one of the Amazon Transcribe limits, typically
        the limit on audio length. Break your audio stream into smaller chunks
        and try your request again.

    :raises InternalFailureException:
        A problem occurred while processing the audio.
        Amazon Transcribe terminated processing.

    :raises ConflictException:
        A new stream started with the same session ID.
        The current stream has been terminated.

    :raises ServiceUnavailableException:
        Service is currently unavailable. Try your request later.
    """


class StartStreamTranscriptionEventStream:
    """Event stream wrapper containing both input and output interfaces to
    Amazon Transcribe. This should only be created by the client.

    :param audio_stream:
        Audio input stream generated by client for new transcription requests.

    :param response: Response object from Amazon Transcribe.
    """

    def __init__(self, audio_stream: AudioStream, response):
        self._response = response
        self._audio_stream = audio_stream

    @property
    def response(self) -> StartStreamTranscriptionResponse:
        """Response object from Amazon Transcribe containing metadata and
        response output stream.
        """
        return self._response

    @property
    def input_stream(self) -> AudioStream:
        """Audio stream to Amazon Transcribe that takes input audio."""
        return self._audio_stream

    @property
    def output_stream(self) -> TranscriptResultStream:
        """Response stream containing transcribed event output."""
        return self.response.transcript_result_stream
