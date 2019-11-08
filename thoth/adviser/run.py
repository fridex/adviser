#!/usr/bin/env python3
# thoth-adviser
# Copyright(C) 2019 Fridolin Pokorny
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Utilities which wrap adviser's and dependency monkey's and run them in a subprocess.

This is useful for a cluster deployment where we restrict resources allocated for an adviser or dependency monkey run.
Annealing is run as a subprocess to the main process - if resources are exhausted (CPU time or memory allocated), the
subprocess is killed (either by liveness probe or by OOM killer) and the main process can still produce an
error message.
"""

from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Union
from typing import Optional
import logging
import os
import sys
import time

from thoth.common import init_logging
from .report import Report
from .dependency_monkey import DependencyMonkeyReport

_LOGGER = logging.getLogger(__name__)
# This file is created by OpenShift's liveness probe on timeout.
_LIVENESS_PROBE_KILL_FILE = "/tmp/thoth_adviser_cpu_timeout"


def subprocess_run(
    asa: Callable[[], Union[Report, DependencyMonkeyReport]],
    print_func: Callable[[float, Union[Dict[str, Any], List[Any]]], None],
    result_dict: Dict[str, Any],
    plot_history: Optional[str] = None,
) -> int:
    """Run the given function (partial annealing method) in a subprocess and output the produced report."""
    start_time = time.monotonic()
    pid = os.fork()

    if pid == 0:  # Child.
        # We need to re-init logging for the sub-process.
        init_logging()
        _LOGGER.debug("Created a child process to compute report")
        try:
            report = asa()
            if plot_history:
                try:
                    report.plot_history(plot_history)
                except Exception as exc:
                    _LOGGER.exception(
                        "Failed to plot history to %r: %s", plot_history, str(exc)
                    )

            result_dict.update(
                dict(error=False, error_msg=None, report=report.to_dict())
            )
        except Exception as exc:
            _LOGGER.exception("Adviser raised an exception: %s", str(exc))
            result_dict.update(dict(error=True, error_msg=str(exc), report=None))
            sys.exit(1)

        print_func(time.monotonic() - start_time, result_dict)
        sys.exit(0)
    else:  # Parent waits for its child to terminate.
        _LOGGER.debug("Waiting for child process %r", pid)
        _, exit_code = os.waitpid(pid, 0)
        if exit_code != 0:
            _LOGGER.error("Child exited with exit code %r", exit_code)
            if exit_code == 137:
                err_msg = (
                    "Adviser was killed as allocated memory has been exceeded (OOM)"
                )
            elif os.path.isfile(_LIVENESS_PROBE_KILL_FILE):
                err_msg = "Adviser was killed as allocated CPU time was exceeded"
            else:
                err_msg = "Unknown error during computing advises"

            _LOGGER.error(err_msg)
            result_dict.update(dict(error=True, error_msg=err_msg, report=None))
            print_func(time.monotonic() - start_time, result_dict)
        else:
            _LOGGER.debug("Subprocess computing report finished successfully")

        # Propagate exit code from child process.
        return exit_code
