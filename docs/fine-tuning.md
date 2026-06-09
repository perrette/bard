# Fine-tuning

```bash
bard --chunk-size 500  # that's the default
```

This sets the maximum length (in characters) of a request. That means about 30
seconds of speech. The program will split up the text in chunks (according to
the punctuation) and download them sequentially. The reading will start with the
first chunk, that's why it is convenient to keep it small.

You can set that smaller or up to the maximum allowed by the backend (4096 for
OpenAI).
