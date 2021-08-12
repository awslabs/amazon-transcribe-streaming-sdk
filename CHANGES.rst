Changes
=======

0.5.0 (2021-08-12)
------------------

* The required version of awscrt has been upgraded to 0.11.24 (#47)

* Added official support for Python 3.9 (#46)

* Added `confidence` score to the `Item` class. (#45)

* Added stabilization features with `enable_partial_results_stabilization`,
  `partial_results_stability` and `Item.stable`. (#48)


0.4.0 (2021-05-11)
------------------

* The required version of awscrt has been upgraded to 0.11.15


0.3.0 (2021-04-22)
------------------

* The required version of awscrt has been upgraded to 0.11.11 (#20, #22)


0.2.0 (2020-11-13)
-----------------

* The `create_client` helper function has been removed in favor of
  creating `TranscribeStreamingClient` directly.

* Added support for the `vocab_filter_name` argument in
  `start_stream_transcription`. (#11)

* Added support for multi-channel audio transcription and speaker labels (#13)


0.1.0 (2020-07-27)
-------------------

* Initial release of Amazon Transcribe Streaming SDK for Python.
