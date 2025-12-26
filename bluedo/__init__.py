import sys

__version__ = "v2.5.0-dev"
__projectname__ = "bluedo"

try:
    from . import bluedoapp
except ImportError:
    import bluedoapp


def main(args=None):
    app = bluedoapp.BlueDo()
    return app.run(args)


if __name__ == "__main__":
    sys.exit(main(args=sys.argv))
