from whitenoise.middleware import WhiteNoiseMiddleware


class SvelteKitWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """Extend WhiteNoise's immutable-file detection for SvelteKit.

    WhiteNoise's default ``immutable_file_test`` uses Django's static-files
    manifest to identify content-hashed assets under ``STATIC_ROOT``.  It
    always returns ``False`` for files served from ``WHITENOISE_ROOT``
    because their URLs don't start with the ``/static/`` prefix.

    SvelteKit places all content-hashed bundles under ``_app/immutable/``,
    so we add a path-based check for those while preserving the parent
    behaviour for Django's own hashed static files.
    """

    def immutable_file_test(self, path, url):
        if "_app/immutable/" in url:
            return True
        return super().immutable_file_test(path, url)
