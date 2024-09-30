import logging
import os
import subprocess
import sys


class _Handler(logging.Handler):
    def emit(self, record):
        try:
            message = self.format(record)
            subprocess.run(
                ["juju-log", "--log-level", record.levelname, message], check=True
            )
        except Exception:
            self.handleError(record)


def set_up_logging() -> None:
    # TODO docstring: call right away (first thing after import)
    # TODO docstring: call only once (in charm entrypoint)
    # TODO docstring: do not call if using ops
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler_ = _Handler()
    handler_.setFormatter(logging.Formatter("{name}:{message}", style="{"))
    logger.addHandler(handler_)

    def except_hook(type_, value, traceback):
        logger.critical(
            "Uncaught exception in charm code", exc_info=(type_, value, traceback)
        )

        if os.environ.get("JUJU_ACTION_NAME"):
            # Print to stderr (so that exception is displayed in output of `juju run`)
            sys.__excepthook__(type_, value, traceback)

    sys.excepthook = except_hook
