#!/bin/bash
ffmpeg -i $1 -acodec pcm_s16le -ac 1 -ar 16000  $2
