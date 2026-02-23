__all__ = ["create_app"]


def create_app():
    from ranking_web.app import create_app as _create_app

    return _create_app()
